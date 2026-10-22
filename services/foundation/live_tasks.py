"""Immutable anchor/additional follow-ups, exact binding identity and event view."""
import json
from .store import canonical,digest


def binding_value(grant,follow,archive_episode_id):
    return dict(archive_id=grant.archive_id,package_sha256=grant.package_sha256,partition_id=grant.partition_id,
        source_id=grant.source_id,source_version=grant.source_version,run_id=grant.run_id,
        archive_episode_id=archive_episode_id,follow_up=follow.model_dump(mode='json'))


def target(db,task_id):
    row=db.execute('SELECT * FROM live_hold_task_bindings WHERE task_id=?',(task_id,)).fetchone()
    if row is None:raise ValueError('followup_binding_unavailable')
    return row,'live_hold_tasks' if row['anchor_task_id'] else 'live_hold_additional_tasks',\
        'live_hold_task_events' if row['anchor_task_id'] else 'live_hold_additional_task_events'


def event(db,task_id,operation_id,value):
    _,_,table=target(db,task_id)
    identifier='task-event-'+digest(canonical([task_id,operation_id,value]))[:40]
    db.execute('INSERT INTO '+table+' VALUES(?,?,?,?)',(identifier,task_id,operation_id,canonical(value)))


def add_bindings(db,patient_id,episode_id,generation,owner,values,obligations,operation_id,episode,*,record_pending=True):
    ids=set(episode.get('task_ids',[]))
    for value in sorted(values,key=canonical):
        encoded=canonical(value);full_hash=digest(encoded);follow=value['follow_up']
        if follow['owner_id']!=owner:raise ValueError('followup_owner_mismatch')
        prior=db.execute('SELECT task_id,payload FROM live_hold_task_bindings WHERE episode_id=? AND generation=? AND full_binding_sha256=?',
            (episode_id,generation,full_hash)).fetchone()
        if prior:
            if prior['payload']!=encoded:raise ValueError('followup_binding_hash_conflict')
            ids.add(prior['task_id']);continue
        anchor=db.execute('SELECT id FROM live_hold_tasks WHERE episode_id=? AND generation=?',(episode_id,generation)).fetchone() is None
        task_id=('hold-review-' if anchor else 'hold-followup-')+digest(canonical([episode_id,generation,full_hash]))[:40]
        table='live_hold_tasks' if anchor else 'live_hold_additional_tasks'
        payload=canonical(dict(policy=follow['policy'],escalation_destination=follow['escalation_destination'],requirements=obligations,source_binding=value))
        db.execute('INSERT INTO '+table+' VALUES(?,?,?,?,?,?,?)',(task_id,patient_id,episode_id,generation,owner,follow['due_at'],payload))
        db.execute('INSERT INTO live_hold_task_bindings VALUES(?,?,?,?,?,?,?)',
            (episode_id,generation,full_hash,task_id,task_id if anchor else None,None if anchor else task_id,encoded))
        ids.add(task_id)
    episode['task_ids']=sorted(ids)
    if record_pending:
        for task_id in episode['task_ids']:
            event(db,task_id,operation_id,dict(status='pending',trigger_set_sha256=episode['trigger_set_sha256'],obligations=obligations))


def all_tasks(db,patient_id):
    result=[]
    for table,events in [('live_hold_tasks','live_hold_task_events'),('live_hold_additional_tasks','live_hold_additional_task_events')]:
        for row in db.execute('SELECT * FROM '+table+' WHERE patient_id=? ORDER BY id',(patient_id,)):
            task=dict(row);task['payload']=json.loads(task['payload'])
            task['events']=[json.loads(r[0]) for r in db.execute('SELECT payload FROM '+events+' WHERE task_id=? ORDER BY rowid',(task['id'],))]
            result.append(task)
    return sorted(result,key=lambda t:(t['due_at'],t['id']))
