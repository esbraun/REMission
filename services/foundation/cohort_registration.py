"""Trusted run-export admission bridged to owned audit rows, never HTTP input."""
import json

from contracts.domain.analysis import canonical, project_history, sha, PROTOCOL_REF
from contracts.domain.cohort import CohortHistory, CohortManifest, COORDINATE_REF
from contracts.runs.admission import verify_export
from contracts.runs.common import ExportAuthority
from .store import instant, timestamp


def _key(owner, run_id, cohort_id, cutoff):
    return 'cohort-run-'+sha([owner,run_id,cohort_id,timestamp(instant(cutoff))])


def registration(db, owner, run_id, cohort_id, cutoff):
    key=_key(owner,run_id,cohort_id,cutoff)
    rows=db.execute('SELECT id,patient_id,payload FROM state_changes WHERE actor_id=? AND id LIKE ?',
        (owner,key+'-%')).fetchall()
    if len(rows)!=12:
        raise ValueError('Registered research-run artifact and full membership are required.')
    by_id={r['id']:r for r in rows}
    if key+'-00' not in by_id:
        raise ValueError('Research registration anchor is missing.')
    value=json.loads(by_id[key+'-00']['payload'])
    authority=ExportAuthority.model_validate(value['authority'])
    cohort=CohortHistory.model_validate_json(canonical(value['cohort']))
    checksum=sha(value)
    if (cohort.manifest.owner_id!=owner or cohort.manifest.scope!='research'
            or cohort.manifest.research_run_id!=run_id or authority.run_id!=run_id
            or cohort.manifest.cohort_id!=cohort_id or cohort.manifest.cutoff!=instant(cutoff)):
        raise ValueError('Research registration owner/run/cohort/cutoff mismatch.')
    for index,member in enumerate(cohort.manifest.members):
        row=by_id.get(key+f'-{index:02}')
        if row is None or row['patient_id']!=member.patient_id:
            raise ValueError('Research registration membership changed.')
        if index and json.loads(row['payload'])!=dict(kind='research_cohort_member',registration=key,sha256=checksum):
            raise ValueError('Research registration link checksum mismatch.')
    return cohort


def register(store, owner, manifest_bytes, artifact_root, authority, *, cohort_id, patient_versions):
    """Host-only: reuse exact ExportAuthority supplied OUTSIDE uploaded bytes.

    Service/operator configuration owns authority; never deserialize it from a
    user command. Only verified public observed partitions reach this module.
    No private run manifest, seed, truth or evaluator artifact is imported.
    """
    if type(authority) is not ExportAuthority:
        raise ValueError('Explicit trusted v1 export authority required.')
    public,partitions=verify_export(manifest_bytes,artifact_root,authority)
    if public.schema_version!='1.0.0' or public.status!='complete':
        raise ValueError('Complete compatible v1 research export required.')
    selected=[p for p in partitions if p[0].cohort_id==cohort_id]
    if (len(selected)!=12 or len({(p[0].unit_id,p[0].replicate) for p in selected})!=1
            or any(p[0].preset not in ('evaluation','catalog_cell') for p in selected)):
        raise ValueError('Twelve members of one declared research unit/cohort/replicate required.')
    if set(patient_versions)!={p[0].patient_id for p in selected}:
        raise ValueError('Research artifact roster differs from selected owned membership.')
    reduced={p[0].patient_id:project_history(p[1].project(public.cutoff)) for p in selected}
    if any((h.cutoff-h.origin).days<14 for h in reduced.values()):
        raise ValueError('Each research member must reach at least day14.')
    members=[dict(patient_id=patient,patient_version=patient_versions[patient],
        history_sha256=sha(reduced[patient].model_dump(mode='json')),
        provenance_sha256=sha([r.model_dump(mode='json') for r in reduced[patient].provenance]))
        for patient in sorted(reduced)]
    unit,replicate=selected[0][0].unit_id,selected[0][0].replicate
    manifest=dict(schema='poc-cohort-manifest-v1/1.0.0',cohort_id=cohort_id,owner_id=owner,
        panel_id='research-'+sha([public.run_id,unit,cohort_id,replicate]),scope='research',
        research_run_id=public.run_id,research_execution=public.execution,cutoff=timestamp(public.cutoff),origin=timestamp(next(iter(reduced.values())).origin),
        protocol=PROTOCOL_REF,coordinates=COORDINATE_REF,members=members)
    # Hash the typed wire after datetime normalization, as interactive export
    # does. Equivalent UTC spellings must not invalidate a constructed manifest.
    manifest=CohortManifest.model_validate_json(canonical(manifest)).model_dump(mode='json')
    cohort=CohortHistory.model_validate_json(canonical(dict(schema='poc-cohort-history-v1/1.0.0',
        manifest=manifest,manifest_sha256=sha(manifest),histories=[reduced[p].model_dump(mode='json') for p in sorted(reduced)])))
    value=dict(kind='trusted_research_cohort_registration',authority=authority.model_dump(mode='json'),
        execution=public.execution,unit_id=unit,replicate=replicate,cohort=cohort.model_dump(mode='json'))
    key=_key(owner,public.run_id,cohort_id,timestamp(public.cutoff))
    with store.transaction(write=True) as db:
        for member in cohort.manifest.members:
            row=db.execute('SELECT owner_id,version,cutoff,state_json FROM patients WHERE id=?',(member.patient_id,)).fetchone()
            if (row is None or row['owner_id']!=owner or row['version']!=member.patient_version
                    or instant(row['cutoff'])<public.cutoff):
                raise ValueError('Research member requires current administrative ownership/version/reached cutoff.')
            if 'simulation' in json.loads(row['state_json']):
                raise ValueError('Interactive physician simulation cannot enter a research cohort.')
            for previous in db.execute("SELECT payload FROM state_changes WHERE patient_id=? AND id LIKE 'cohort-run-%'",(member.patient_id,)):
                previous=json.loads(previous['payload'])
                if previous['kind']=='research_cohort_member':
                    anchor=db.execute('SELECT payload FROM state_changes WHERE id=?',(previous['registration']+'-00',)).fetchone()
                    if anchor is None:raise ValueError('Research registration anchor is missing.')
                    previous=json.loads(anchor['payload'])
                old_manifest=previous['cohort']['manifest']
                if (old_manifest['research_run_id']!=public.run_id or old_manifest['cohort_id']!=cohort_id
                        or old_manifest['panel_id']!=manifest['panel_id']):
                    raise ValueError('Research member belongs to another run/cohort/unit.')
        old=db.execute('SELECT payload FROM state_changes WHERE id=?',(key+'-00',)).fetchone()
        if old:
            if json.loads(old['payload'])!=value:
                raise ValueError('Research registration is immutable.')
            registration(db,owner,public.run_id,cohort_id,timestamp(public.cutoff))
        else:
            for index,member in enumerate(cohort.manifest.members):
                payload=value if index==0 else dict(kind='research_cohort_member',registration=key,sha256=sha(value))
                db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',(key+f'-{index:02}',member.patient_id,
                    owner,timestamp(store.clock()),canonical(payload)))
    return dict(run_id=public.run_id,cohort_id=cohort_id,manifest_sha256=cohort.manifest_sha256,members=12,
        execution=public.execution,executable=False)


def is_research_member(db, patient_id):
    return db.execute("SELECT 1 FROM state_changes WHERE patient_id=? AND id LIKE 'cohort-run-%' LIMIT 1",(patient_id,)).fetchone() is not None
