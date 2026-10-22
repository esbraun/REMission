"""Actual bound service snapshot producer with recoverable manifest-last publication."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import uuid
from contracts.runs.common import canonical as wire, sha256
from contracts.service.live_safety import LiveSafetyExport, TrustedLiveSafetyAuthority
from contracts.service.live_safety_admission import FACTS, fold, verify_live_safety
from .live_hold import LiveError
from .live_journal import control
from .store import canonical, instant, timestamp


@dataclass(frozen=True)
class ExportContext:
    owner_id: str
    key: str
    settings: object
    authorize: object


def publish(root, export_id, manifest, observed, facts):
    root=Path(root)
    if root.is_symlink():
        raise LiveError('unsafe_export_destination')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    destination=root/export_id
    expected={'manifest.json':manifest,'observed-projection.json':observed,'live-hold-facts.json':facts}
    if destination.exists():
        if destination.is_symlink() or {p.name for p in destination.iterdir()}!=set(expected) or any((destination/k).is_symlink() or (destination/k).read_bytes()!=v for k,v in expected.items()):
            raise LiveError('immutable_export_conflict')
        return destination
    partial=root/('.partial-'+export_id+'-'+uuid.uuid4().hex)
    partial.mkdir(mode=0o700)
    for name in ['observed-projection.json','live-hold-facts.json','manifest.json']:
        with (partial/name).open('xb') as stream:
            stream.write(expected[name]);stream.flush();os.fsync(stream.fileno())
        (partial/name).chmod(0o444)
    directory=os.open(partial,os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    # Unique committed export identity; another retry may publish the same bytes.
    try:
        partial.rename(destination)
    except FileExistsError:
        for child in partial.iterdir():child.unlink()
        partial.rmdir()
        return publish(root,export_id,manifest,observed,facts)
    directory=os.open(root,os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return destination


def export_live_safety(store,patient_id,cutoff,configured_destination,authorized_context):
    context=authorized_context;settings=context.settings
    intent=sha256(wire(dict(contract='LIVE-HOLD-01',patient_id=patient_id,cutoff=timestamp(cutoff))))
    with store.transaction(write=True,authorize=context.authorize) as db:
        saved=db.execute('SELECT * FROM live_export_receipts WHERE owner_id=? AND patient_id=? AND key=?',(context.owner_id,patient_id,context.key)).fetchone()
        if saved:
            if saved['request_sha256']!=intent:
                raise LiveError('idempotency_conflict')
            manifest,observed,facts=bytes(saved['manifest']),bytes(saved['observed']),bytes(saved['facts'])
            authority=TrustedLiveSafetyAuthority.model_validate_json(saved['authority'])
        else:
            from .workflow import history
            c=control(db);captured=settings.clock()
            if cutoff>captured:
                raise LiveError('future_export_cutoff',422)
            if captured<instant(c['last_receipt_at']):
                raise LiveError('service_clock_regression')
            if settings.source_commit is None or settings.runtime_ref is None:
                raise LiveError('service_export_runtime_unconfigured',503)
            projection=history(db,patient_id).project(cutoff)
            observed=projection.model_dump_json().encode()
            rows=db.execute('SELECT payload,payload_sha256 FROM live_safety_facts WHERE patient_id=? ORDER BY patient_sequence',(patient_id,)).fetchall()
            visible=[]
            for row in rows:
                value=json.loads(row['payload'])
                if instant(value['event_at'])<=cutoff and instant(value['recorded_at'])<cutoff and instant(value['available_at'])<cutoff:
                    visible.append(value)
                else:
                    break
            facts=wire(visible);typed=FACTS.validate_json(facts)
            baseline,episodes,status=fold(typed)
            head=sha256(wire(visible[-1])) if visible else sha256(b'')
            journal=db.execute('SELECT journal_id FROM live_patient_journals WHERE patient_id=?',(patient_id,)).fetchone()
            if journal is None:
                raise LiveError('patient_journal_uninitialized')
            source_digest=sha256(wire([dict(r) for r in db.execute('SELECT id,payload_sha256,raw_sha256 FROM events WHERE patient_id=? ORDER BY id',(patient_id,))]))
            snapshot=dict(service_instance_id=c['database_instance_id'],patient_id=patient_id,cutoff=timestamp(cutoff),
                observed_sha256=sha256(observed),observed_source_sha256=source_digest,prefix_chain_sha256=head,
                prefix_count=len(visible),authority_generation=c['authority_generation'],authority_sha256=c['authority_sha256'],review_rules_sha256=c['review_rules_sha256'])
            snapshot_sha256=sha256(wire(snapshot));snapshot_id='snapshot-'+snapshot_sha256[:40]
            export_id='live-export-'+uuid.uuid4().hex;receipt_id='export-receipt-'+uuid.uuid4().hex
            binding=json.loads(Path(__file__).resolve().parents[2].joinpath('contracts/service/bindings-v1.json').read_bytes())
            receipt=dict(receipt_id=receipt_id,export_id=export_id,patient_id=patient_id,snapshot_id=snapshot_id,
                snapshot_sha256=snapshot_sha256,cutoff=timestamp(cutoff),observed_sha256=sha256(observed),facts_sha256=sha256(facts),
                prefix_count=len(visible),prefix_head_sha256=head,binding=binding['service_schema_set'])
            receipt_raw=wire(receipt)
            value=dict(schema_version='1.0.0',kind='live_safety_export',synthetic=True,scope='independent_live_holds',export_id=export_id,
                service_contract=binding['live_hold'],schema_binding=binding['service_schema_set'],observed_binding=binding['observed_domain'][projection.schema_version],
                service_instance_id=c['database_instance_id'],service_producer=settings.installed.authority.producer.model_dump(mode='json'),
                source_commit=settings.source_commit,runtime=settings.runtime_ref,execution=settings.installed.authority.execution,
                authority_generation=c['authority_generation'],authority_sha256=c['authority_sha256'],review_rules_sha256=c['review_rules_sha256'],
                patient_id=patient_id,cutoff=timestamp(cutoff),captured_at=timestamp(captured),snapshot_id=snapshot_id,snapshot_sha256=snapshot_sha256,
                observed_source_sha256=source_digest,observed_projection=dict(path='observed-projection.json',sha256=sha256(observed),bytes=len(observed),kind='learner_history',schema_version=projection.schema_version),
                facts=dict(path='live-hold-facts.json',sha256=sha256(facts),bytes=len(facts),count=len(visible)),journal_id=journal[0],baseline_operation_id=baseline,
                through_patient_sequence=len(visible),prefix_chain_sha256=head,completeness='complete_visible_prefix' if baseline else 'uninitialized',
                independent_hold_status=status,active_episodes=episodes,publication_receipt_ref=dict(receipt_id=receipt_id,payload_sha256=sha256(receipt_raw)))
            manifest=wire(LiveSafetyExport.model_validate_json(wire(value)).model_dump(mode='json'))
            roster=[dict(generation=r['generation'],authority_sha256=r['authority_sha256'],review_rules_sha256=r['review_rules_sha256'])
                    for r in db.execute('SELECT * FROM live_authority_history ORDER BY generation') if any(f.authority_generation==r['generation'] for f in typed)]
            auth=dict(schema_version='1.0.0',kind='trusted_live_safety_authority',synthetic=True,
                **{k:value[k] for k in ['service_instance_id','service_producer','source_commit','runtime','export_id','patient_id','cutoff','snapshot_id','snapshot_sha256',
                    'authority_generation','authority_sha256','review_rules_sha256','through_patient_sequence','prefix_chain_sha256','baseline_operation_id']},
                manifest_sha256=sha256(manifest),generations=roster,observed_sha256=sha256(observed),prefix_count=len(visible),
                allow_contract_fixture=settings.installed.authority.execution=='contract_fixture')
            authority=TrustedLiveSafetyAuthority.model_validate_json(wire(auth))
            db.execute('INSERT INTO live_export_receipts VALUES(?,?,?,?,?,?,?,?,?,?,?)',(receipt_id,patient_id,context.owner_id,context.key,intent,
                receipt_raw.decode(),sha256(receipt_raw),manifest,observed,facts,authority.model_dump_json()))
            if settings.fault:settings.fault('before_live_export_commit')
    if settings.fault:settings.fault('after_live_export_commit')
    path=publish(configured_destination,authority.export_id,manifest,observed,facts)
    verify_live_safety(manifest,path,authority)
    return dict(status='published',export_id=authority.export_id,manifest_sha256=authority.manifest_sha256,
        scope='independent_live_holds',execution=json.loads(manifest)['execution'])
