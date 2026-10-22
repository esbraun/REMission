"""Consumer-safe wire fixtures. These bytes never qualify a production run."""
from datetime import date, datetime, timedelta, timezone
import json
from types import SimpleNamespace
from pathlib import Path

from contracts.domain.evidence_v2 import exact_ref, payload_hash, projection_hash
from contracts.domain.observed_v2 import ObservedHistoryV2, RECORD_ADAPTER_V2
from contracts.runs.admission_v2 import deterministic_record_id, record_input_references
from contracts.runs.common import canonical, sha256
from contracts.runs.coverage_v2 import ScheduleInputV2, derive_slots
from contracts.runs.observed_v2 import BindingsV2, RecordIdentityV2

ZERO = '0' * 64
ORIGIN = datetime(2026, 1, 1, tzinfo=timezone.utc)


def ref(identifier, version='2.0.0', digest=ZERO):
    return dict(id=identifier, version=version, sha256=digest)


def build(root: Path, *, hold=False, prompt=False, cutoff=None, cell_id='S23', registry=None, transform=None, complete=False, service_owner=None,
          run_name='obs2-fixture-run',threshold_concern=False,extra_hold=False,extra_threshold=False,multi_followup=False,same_followup_due=False,archive_resolution=False,late_trigger_correction_at=None,late_trigger_retracted=False,export_name='fixture-export'):
    root.mkdir(parents=True, exist_ok=True)
    owner=service_owner or 'sim-owner'
    owner_role='doctor' if service_owner else 'simulated_clinician'
    bindings = json.loads(Path('contracts/runs/bindings-v2.json').read_bytes())
    typed_bindings = BindingsV2.model_validate_json(canonical(bindings))
    runtime = dict(image_sha256=ZERO, numerical_lock=ref('numerical'), service_lock=ref('service'), python_version='3.13.7',
                   numpy_version='2.5.4', prng='PCG64DXSM', seed_derivation='remission-seed-v1', precision='float64')
    producer = dict(id='obs2-wire-fixture', version='2.0.0', role='contract_fixture')
    run_id, partition_id, patient_id = run_name, 'obs2-partition', 'SYN-02'
    records, entries, identities, typed_records = [], [], {}, []
    policy = ref('complete-fixed-no-prompt-mechanism')
    model = ref('explicit-no-estimator')
    registry = registry or ref('fixture-source-registry')
    transform = transform or ref('fixture-transform-registry')
    mechanism = dict(schema_version='2.0.0', synthetic=True, kind='support_mechanism', id='fixture-mechanism', policy=policy, mode='fixed', parameter_refs=[ref('approved-fixed-action')],
                     action_versions={a: ref(a) for a in ['support_prompt', 'no_prompt']}, probability_rule=ref('fixed-mass-one'), context_mapping=ref('fixed-context'), burden_behavior=ref('accepted-operational-cap-rule'), constraints=ref('approved-envelope'), frozen_origin=None, approximation_settings=None, approximation_error=None)

    def history():
        return ObservedHistoryV2.model_validate_json(canonical(dict(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id=patient_id, records=records)))

    def add(kind, event, *, version='1.0.0', identifier=None, process=None, substream='main', **fields):
        identity = RecordIdentityV2.model_validate_json(canonical(dict(protocol=bindings['protocol']['id'], phase='fixture', run_id=run_id, cell_id=cell_id, cohort_id='cohort', replicate=0,
                         patient_id=patient_id, time_index=(event.date() - ORIGIN.date()).days - (1 if kind == 'support_outcome_link' else 0), process=process or kind,
                         substream=substream, namespace='measurement' if kind == 'daily_report' else 'assignment' if kind in ('support_decision', 'assignment') else 'generation',
                         source_registry=registry, transformation=transform, input_refs=[], draw_consumed=False)))
        revision = fields.get('revision', 1)
        identifier = identifier or deterministic_record_id(identity, kind, revision) if version == '2.0.0' else identifier or kind + '-' + substream
        data = dict(schema_version=version, synthetic=True, kind=kind, record_id=identifier, patient_id=patient_id, event_at=event.isoformat(),
                    recorded_at=event.isoformat(), available_at=event.isoformat(), lineage_id=identifier, revision=1, supersedes=None, duplicate_of=None, record_status='active')
        data.update(fields)
        data['source'] = dict(id='fixture-diary' if kind == 'daily_report' else 'fixture-simulation', version='1.2.0', adapter='patient_report' if kind == 'daily_report' else 'simulation', raw_sha256=ZERO)
        source = canonical({k: v for k, v in data.items() if k != 'source'})
        data['source']['raw_sha256'] = sha256(source)
        record = RECORD_ADAPTER_V2.validate_json(canonical(data))
        records.append(record.model_dump(mode='json'))
        typed_records.append(record)
        identity.input_refs = record_input_references(record, SimpleNamespace(records=typed_records), typed_bindings)
        entries.append(dict(record=record.model_dump(mode='json'), raw_source=source.decode()))
        identities[record.record_id] = identity.model_dump(mode='json')
        return record

    patient = add('patient', ORIGIN - timedelta(days=14), identifier='patient-source', covariates=[], diagnosis_context='Synthetic', clinical_context='Synthetic', preferences=[], goals=[], baseline_eligibility=[], care_team=[owner], timezone='UTC')
    add('consent', ORIGIN - timedelta(days=13), identifier='generated-active-consent', component='mrt_bandit', consent_version='fixture', oversight_version='fixture', consent_status='active', oversight_status='approved_synthetic', effective_at=(ORIGIN - timedelta(days=13)).isoformat(), expires_at=None, withdrawn_at=None)
    schedule = ScheduleInputV2.model_validate_json(canonical(dict(schema_version='2.0.0', synthetic=True, kind='support_schedule_input', id='schedule', run_id=run_id, partition_id=partition_id,
                        protocol=bindings['protocol'], timing=bindings['timing'], temporal=bindings['temporal'], representation=bindings['observed_representation'], dgp=bindings['dgp'], catalog=bindings['catalog'],
                        cell_id=cell_id, preset='evaluation', unit_id='unit', cohort_id='cohort', replicate=0, patient_id=patient_id, patient_ref=exact_ref(patient).model_dump(), timezone='UTC',
                        time_zero_local_date=ORIGIN.date().isoformat(), time_zero_utc=ORIGIN.isoformat(), timezone_database=ref('fixture-tzdb'), derivation=ref('TIME-01-daily-0-84'), planned_horizon=84)))
    slots = derive_slots(schedule)
    schedule_ref = ref(schedule.id, digest=sha256(canonical(schedule.model_dump(mode='json'))))

    def snapshot(identifier, at, *, held=False, version=1, reason_code='clinician_concern'):
        elig = [dict(action=a, status='excluded' if held else 'eligible' if a == ('support_prompt' if prompt else 'no_prompt') else 'excluded', reasons=['hold' if held else 'fixed mechanism']) for a in ['support_prompt', 'no_prompt']]
        return add('decision_snapshot', at, identifier=identifier, cutoff=at.isoformat(), patient_version=version, state_version=version, consent_version=1, eligibility_version=version,
                   workflow=dict(clinical='clinical_hold' if held else 'assessment', learning='none', data_readiness='ready', hold_reasons=(reason_code if isinstance(reason_code,list) else [reason_code]) if held else [], support_policy=policy, support_mode='paused' if held else 'fixed'),
                   view=dict(patient_id=patient_id, mode='current', snapshot_id=None), eligibility=elig, outcome='sleep_quality', horizon_days=1, estimand=ref('EST-MRT'), model=model, posterior=None, evidence=[], policy=policy)

    hold_records = []

    def add_hold(seq, at):
        predecessor = hold_records[-1] if hold_records else None
        predecessor_snap = next((r for r in history().records if predecessor and r.record_id == predecessor.snapshot_ref.record_id), None)
        held = seq >= 1
        threshold=threshold_concern or extra_threshold and seq>1
        reason_code='experimental_stability_review' if threshold else 'clinician_concern'
        reasons=['clinician_concern',reason_code] if extra_threshold and seq>1 else [reason_code]
        hold_snap = snapshot('hold-snapshot-' + str(seq), at, held=held, version=seq + 2,reason_code=reasons if extra_threshold and seq>1 else reason_code)
        task = add('follow_up', at, identifier='hold-task-' + str(seq), owner=owner, due_at=(at + timedelta(days=1)).isoformat(), trigger='synthetic review required', status='pending', escalation_destination='sim-care-team')
        follow_up_refs=[exact_ref(task).model_dump()]
        if held and multi_followup:
            extra=add('follow_up',at,identifier='hold-task-extra-'+str(seq),owner=owner,due_at=(at+timedelta(days=1 if same_followup_due else 2)).isoformat(),trigger='second explicit synthetic review',status='pending',escalation_destination='sim-care-team' if same_followup_due else 'sim-second-team')
            follow_up_refs.append(exact_ref(extra).model_dump())
        trigger = None
        rule_id='accepted-observed-threshold' if threshold else 'accepted-script-concern'
        if seq>1:rule_id+='-strengthen-'+str(seq)
        requirement_id='review-threshold' if threshold else 'review-concern'
        if held:
            trigger = add('hold_review_evidence', at, version='2.0.0', process='hold_review', substream='main' if seq==1 else 'strengthen-'+str(seq),run_id=run_id, partition_id=partition_id, hold_episode_id='episode', evidence_type='trigger_observation', rule=ref(rule_id), requirement=ref(requirement_id), actor_id=owner, actor_role=owner_role, origin='simulation', ownership_ref=exact_ref(patient).model_dump(), assessed_at=at.isoformat(), facts_refs=[], finding='simulated observed concern, no hidden numeric coordinates; threshold clearance law unspecified' if threshold_concern else 'simulated clinician concern, no hidden numeric coordinates', review_result='requires_hold', follow_up_refs=follow_up_refs)
        transition='baseline' if not held else 'enter' if seq==1 else 'change_reason'
        bundle = add('hold_transition_bundle', at, version='2.0.0', process='hold_transition', substream='baseline' if not held else 'enter' if seq==1 else 'strengthen-'+str(seq), run_id=run_id, partition_id=partition_id, hold_episode_id='episode', transition_sequence=seq, transition_type=transition, effective_at=at.isoformat(), snapshot_ref=exact_ref(hold_snap).model_dump(), predecessor_bundle_ref=exact_ref(predecessor).model_dump() if predecessor else None, predecessor_snapshot_ref=exact_ref(predecessor_snap).model_dump() if predecessor_snap else None,
                     reason_codes=reasons if held else [], reason='simulated hold' if held else 'initial baseline', trigger_refs=[exact_ref(trigger).model_dump()] if trigger else [], changed_fact_refs=[], blocked_actions=['MED_A', 'MED_B', 'support_prompt', 'no_prompt'] if held else [], context_cutoff=at.isoformat(), causal_context_refs=[], context_projection_sha256=projection_hash(history(), at), policy=policy, model=model, eligibility_configuration=ref('paused-experiment-eligibility'), owner_id=owner, owner_role=owner_role, ownership_ref=exact_ref(patient).model_dump(), follow_up_refs=follow_up_refs, required_reviews=[dict(requirement_id=requirement_id,definition=ref(requirement_id),responsible_role='doctor',status='pending',evidence_refs=[])] if service_owner and held else [], review_refs=[], clearance=dict(status='pending' if held else 'not_applicable', rule=None, evidence_refs=[], assessment_snapshot_ref=None), evidence_roles=[dict(ref=exact_ref(trigger).model_dump(), role='transition_trigger')] if trigger else [])
        hold_records.append(bundle)

    if hold:
        add_hold(0, ORIGIN - timedelta(hours=1))
    artifacts, ledger_artifacts, receipt_artifacts = {}, [], []

    def artifact(identifier, path, value, role='configuration'):
        raw = canonical(value)
        artifacts[path] = raw
        return dict(id=identifier, path=path, sha256=sha256(raw), bytes=len(raw), role=role, media_type='application/json')

    mechanism_artifacts = [artifact(mechanism['id'], 'mechanisms/fixed.json', mechanism)]

    assert not (complete and hold), 'complete hold trajectory requires its own accepted clearance script'
    decisions, links = {}, {}
    for index in range(85 if complete else 1):
        slot = slots[index]
        suffix = '' if index == 0 else '-d' + str(index)
        snap = snapshot('support-snapshot' + suffix, slot.decision_at)
        add('approval', slot.decision_at, identifier='historical-approval' + suffix, decision_id=snap.record_id, option='support_prompt' if prompt else 'no_prompt', permitted_options=[], clinician_id='sim-owner', purpose='ordinary_treatment', expected_patient_version=1, expected_state_version=1, expected_consent_version=1, expected_eligibility_version=1)
        decision = add('support_decision', slot.decision_at, version='2.0.0', process='support_assignment', decision_snapshot=exact_ref(snap).model_dump(), decision_index=index, cutoff=slot.decision_at.isoformat(),
                       context=[exact_ref(patient).model_dump()], context_projection_sha256=projection_hash(history(), slot.decision_at), context_mapping=ref('fixed-context'), policy=policy, mechanism=ref(mechanism['id'], digest=sha256(canonical(mechanism))), mode='fixed', eligibility=[e.model_dump() for e in snap.eligibility],
                       availability='deterministic', unavailable_reasons=[], probabilities={'support_prompt': float(prompt), 'no_prompt': float(not prompt)}, probability_tolerance=1e-12, assignment_id='fixed-assignment' + suffix, distribution_persisted_at=slot.decision_at.isoformat(), execution_receipt=ref('persist-before-draw' + suffix),
                       outcome_window=dict(id=slot.window_id, starts_at=slot.decision_at.isoformat(), ends_at=slot.assessment_at.isoformat(), assessment_at=slot.assessment_at.isoformat(), timezone='UTC', local_date=slot.decision_at.date().isoformat(), endpoint_definition=ref('next-morning-quality')), outcome_link_id=slot.outcome_link_id)
        assignment = add('assignment', slot.decision_at, identifier='fixed-assignment' + suffix, process='support_assignment', decision_id=snap.record_id, approval_id='historical-approval' + suffix, option='support_prompt' if prompt else 'no_prompt', experimental=False, component=None, probability=None, seed=None, support_policy=policy, patient_blinded=False, clinician_blinded=False, clinician_override=None, override_reason=None)
        deliveries = []
        if prompt:
            deliveries = [add('delivery', slot.decision_at + timedelta(minutes=1), identifier='offered-delivery' + suffix, assignment_id=assignment.record_id, option='support_prompt', stage='offered', adherence=None, rescue=False, protocol_deviations=[])]
        stage_ledgers, point_ledger_artifacts = [], []
        for stage in ['offered', 'delivered']:
            stage_events = [exact_ref(r).model_dump() for r in deliveries if r.stage == stage]
            ledger = dict(schema_version='2.0.0', synthetic=True, kind='support_stage_ledger', id='ledger-' + stage + suffix, run_id=run_id, partition_id=partition_id, patient_id=patient_id,
                          decision_index=index, window_id=slot.window_id, stage=stage, rule=ref('fixture-explicit-stage-execution'), event_refs=stage_events)
            stage_ledgers.append(ledger)
            point_ledger_artifacts.append(artifact(ledger['id'], 'ledgers/' + stage + suffix + '.json', ledger))
        completed_at = slot.decision_at + timedelta(minutes=2)
        receipt = dict(schema_version='2.0.0', synthetic=True, kind='completion_receipt', id='completed-stages' + suffix, run_id=run_id, partition_id=partition_id, patient_id=patient_id, producer=producer, source_commit='6bc8bd998e8a0baaef9884998e740665fb5fd7b1', runtime=runtime,
                       accepted_configuration=[bindings['observed_representation']], schedule_input=schedule_ref, stage_ledgers=[ref(a['id'], digest=a['sha256']) for a in point_ledger_artifacts], process='fixture-stage-execution', time_start=slot.decision_at.isoformat(), time_end=completed_at.isoformat(),
                       completed_at=completed_at.isoformat(), recorded_at=completed_at.isoformat(), published_at=completed_at.isoformat(), available_at=completed_at.isoformat(), output_artifacts=[], output_counts={l['id']: len(l['event_refs']) for l in stage_ledgers}, dependency_manifests=[], status='complete', failure_reason=None, checkpoint_id='fixture-checkpoint', resume_from=None)
        stage_receipt_artifact = artifact(receipt['id'], 'receipts/stages' + suffix + '.json', receipt)
        receipt_artifacts.append(stage_receipt_artifact)
        persistence = {**receipt, 'id': 'persist-before-draw' + suffix, 'stage_ledgers': [], 'process': 'support_distribution_persist',
                       'time_end': slot.decision_at.isoformat(), 'completed_at': slot.decision_at.isoformat(), 'recorded_at': slot.decision_at.isoformat(),
                       'published_at': slot.decision_at.isoformat(), 'available_at': slot.decision_at.isoformat(), 'output_counts': {},
                       'accepted_configuration': [policy, ref(mechanism['id'], digest=sha256(canonical(mechanism))), ref('support-distribution', digest=sha256(canonical(decision.probabilities)))]}
        persistence_artifact = artifact(persistence['id'], 'receipts/distribution' + suffix + '.json', persistence)
        receipt_artifacts.append(persistence_artifact)
        decision_data = decision.model_dump(mode='json')
        decision_data['execution_receipt'] = ref(persistence['id'], digest=persistence_artifact['sha256'])
        decision_raw = canonical({k: v for k, v in decision_data.items() if k != 'source'})
        decision_data['source']['raw_sha256'] = sha256(decision_raw)
        decision = RECORD_ADAPTER_V2.validate_json(canonical(decision_data))
        records[:] = [decision_data if r['record_id'] == decision.record_id else r for r in records]
        entries[:] = [dict(record=decision_data, raw_source=decision_raw.decode()) if e['record']['record_id'] == decision.record_id else e for e in entries]
        typed_records[:] = [decision if r.record_id == decision.record_id else r for r in typed_records]
        identities[decision.record_id]['input_refs'] = [r.model_dump(mode='json') for r in record_input_references(decision, history(), typed_bindings)]
        closures = []
        for ledger, ledger_artifact in zip(stage_ledgers, point_ledger_artifacts):
            closure = add('support_stage_closure', completed_at + timedelta(minutes=1), version='2.0.0', process='support_stage_closure', substream=ledger['stage'], run_id=run_id, partition_id=partition_id,
                          support_decision=exact_ref(decision).model_dump(), assignment_ref=exact_ref(assignment).model_dump(), window_id=slot.window_id, decision_index=index, stage=ledger['stage'], rule=ledger['rule'], stage_completed_at=(completed_at + timedelta(minutes=1)).isoformat(), status='complete',
                          stage_event_refs=ledger['event_refs'], stage_ledger=ref(ledger_artifact['id'], digest=ledger_artifact['sha256']), row_count=len(ledger['event_refs']), reason='verified fixture ledger, including empty stage', completion_receipt=ref(receipt['id'], digest=stage_receipt_artifact['sha256']))
            closures.append(closure)
        if hold and index == 0:
            add_hold(1, ORIGIN + timedelta(hours=10))
        report = None
        if index < 84:
            report = add('daily_report', slot.assessment_at, version='2.0.0', process='diary_report', recorded_at=(slot.assessment_at + timedelta(hours=1, minutes=1)).isoformat(), available_at=(slot.assessment_at + timedelta(hours=1, minutes=1)).isoformat(), sleep_quality=6.0, function=5.0, adverse_symptoms=[], diary_sleep_minutes=-25.0, goals=[], burden=None, missingness='observed')
        link_time = slot.assessment_at + timedelta(hours=2)
        link = add('support_outcome_link', slot.assessment_at, version='2.0.0', process='support_outcome', recorded_at=link_time.isoformat(), available_at=link_time.isoformat(), lineage_id=slot.outcome_link_id,
                   support_decision=exact_ref(decision).model_dump(), assignment_ref=exact_ref(assignment).model_dump(), window_id=slot.window_id, assessment_at=slot.assessment_at.isoformat(), evaluated_as_of=link_time.isoformat(),
                   reward=dict(status='observed', report_ref=exact_ref(report).model_dump(), field='sleep_quality', unit='quality_points', reason=None, evidence_refs=[], definition_refs=[]) if report else dict(status='undefined', report_ref=None, field='sleep_quality', unit='quality_points', reason='outside_generated_horizon', evidence_refs=[], definition_refs=[bindings['protocol'], bindings['timing']]),
                   burden=[dict(definition=ref('unique-' + c.stage + '-assignment-window'), type=c.stage + '_prompt_count', unit='count', status='observed', value=1 if prompt and c.stage == 'offered' else 0, source_refs=[r.model_dump() for r in c.stage_event_refs]) for c in closures],
                   offered_closure_ref=exact_ref(closures[0]).model_dump(), delivered_closure_ref=exact_ref(closures[1]).model_dump())
        decisions[index], links[index] = decision, link
        ledger_artifacts.extend(point_ledger_artifacts)
    if extra_hold:
        assert hold and not complete
        # Explicit structural duplicate-clock concern, no scientific law.
        add_hold(2,ORIGIN+timedelta(hours=10))
    if archive_resolution:
        assert hold and not complete and not extra_hold and service_owner
        # Deliberate structural archive fixture, never live clearance authority.
        at=ORIGIN+timedelta(hours=11);prior=hold_records[-1]
        previous_snapshot=next(r for r in history().records if r.record_id==prior.snapshot_ref.record_id)
        assessment=snapshot('archive-resolution-assessment',at,version=5)
        follow=add('follow_up',at,identifier='archive-resolution-task',owner=owner,due_at=(at+timedelta(days=3)).isoformat(),trigger='explicit archive amendment fixture',status='pending',escalation_destination='sim-resolution-team')
        rule=ref('explicit-archive-structural-resolution');requirement=prior.required_reviews[0]
        review=add('hold_review_evidence',at,version='2.0.0',process='hold_review',substream='archive-resolution',run_id=run_id,partition_id=partition_id,hold_episode_id='episode',evidence_type='clearance',rule=rule,requirement=requirement.definition.model_dump(mode='json'),actor_id=owner,actor_role=owner_role,origin='simulation',ownership_ref=exact_ref(patient).model_dump(),assessed_at=at.isoformat(),facts_refs=[],finding='Explicit structural archive fixture, no live clearance',review_result='requirements_satisfied',follow_up_refs=[exact_ref(follow).model_dump()])
        reference=exact_ref(review).model_dump()
        resolved=add('hold_transition_bundle',at,version='2.0.0',process='hold_transition',substream='archive-resolution',run_id=run_id,partition_id=partition_id,hold_episode_id='episode',transition_sequence=2,transition_type='resolve_to_assessment',effective_at=at.isoformat(),snapshot_ref=exact_ref(assessment).model_dump(),predecessor_bundle_ref=exact_ref(prior).model_dump(),predecessor_snapshot_ref=exact_ref(previous_snapshot).model_dump(),reason_codes=[],reason='Explicit archive structural resolution',trigger_refs=[],changed_fact_refs=[],blocked_actions=[],context_cutoff=at.isoformat(),causal_context_refs=[],context_projection_sha256=projection_hash(history(),at),policy=policy,model=model,eligibility_configuration=ref('paused-experiment-eligibility'),owner_id=owner,owner_role=owner_role,ownership_ref=exact_ref(patient).model_dump(),follow_up_refs=[exact_ref(follow).model_dump()],required_reviews=[dict(requirement_id=requirement.requirement_id,definition=requirement.definition.model_dump(mode='json'),responsible_role='doctor',status='satisfied',evidence_refs=[reference])],review_refs=[reference],clearance=dict(status='documented',rule=rule,evidence_refs=[reference],assessment_snapshot_ref=exact_ref(assessment).model_dump()),evidence_roles=[dict(ref=reference,role='later_review')])
        hold_records.append(resolved)
    if late_trigger_correction_at is not None:
        assert hold and not complete and not extra_hold
        prior=next(r for r in history().records if r.kind=='hold_review_evidence')
        fields=prior.model_dump(mode='json')
        for key in ['schema_version','synthetic','kind','record_id','patient_id','event_at','source']:fields.pop(key)
        fields.update(lineage_id=prior.lineage_id,revision=2,supersedes=prior.record_id,recorded_at=late_trigger_correction_at.isoformat(),available_at=late_trigger_correction_at.isoformat(),record_status='retracted' if late_trigger_retracted else 'active',finding='Late structural concern correction; retains hold')
        add('hold_review_evidence',prior.event_at,version='2.0.0',process='hold_review',**fields)
    if complete:
        cutoff = cutoff or ORIGIN + timedelta(days=85, hours=10)
    cutoff = cutoff or ORIGIN + timedelta(days=1, hours=10)
    run_manifest = ref(run_id)
    coverage = dict(schema_version='2.0.0', synthetic=True, kind='support_coverage', id='coverage', run_manifest=run_manifest, schedule_input=schedule_ref, schedule=schedule.model_dump(mode='json'), expected_decisions=[s.model_dump(mode='json') for s in slots], first_decision_index=0, last_decision_index=84, first_decision_at=slots[0].decision_at.isoformat(), last_decision_at=slots[-1].decision_at.isoformat(), receipt_cutoff=cutoff.isoformat(), coverage_through=cutoff.isoformat(), status='partial', execution_status='partial', endpoint_status='pending',
                    slots=[dict(slot=s.model_dump(mode='json'), decision_ref=exact_ref(decisions[s.decision_index]).model_dump() if s.decision_index in decisions else None, status='available' if s.decision_index in decisions else 'pending' if s.decision_at <= cutoff else 'planned', endpoint_status='available' if s.decision_index in links else 'pending' if s.assessment_at <= cutoff else 'not_yet_due', outcome_ref=exact_ref(links[s.decision_index]).model_dump() if s.decision_index in links else None) for s in slots], death_ref=None, death_effective_at=None, terminal_phase=None, terminal_reconciliation=None, no_terminal_event_evidence=None, completion_receipt=None)
    if complete:
        completion = {**receipt, 'id': 'all-execution-and-endpoint-completion', 'process': 'fixture-full-horizon-bookkeeping',
                      'time_start': slots[0].decision_at.isoformat(), 'time_end': slots[-1].assessment_at.isoformat(),
                      **{clock: (cutoff - timedelta(minutes=1)).isoformat() for clock in ['completed_at', 'recorded_at', 'published_at', 'available_at']},
                      'stage_ledgers': [ref(a['id'], digest=a['sha256']) for a in ledger_artifacts],
                      'output_counts': {a['id']: len(json.loads(artifacts[a['path']])['event_refs']) for a in ledger_artifacts}}
        completed_artifact = artifact(completion['id'], 'receipts/all-complete.json', completion)
        receipt_artifacts.append(completed_artifact)
        completed_ref = ref(completed_artifact['id'], digest=completed_artifact['sha256'])
        coverage.update(status='complete', execution_status='complete', endpoint_status='complete', no_terminal_event_evidence=completed_ref, completion_receipt=completed_ref)
    coverage_artifact = artifact('coverage', 'coverage/partition.json', coverage)
    history_artifact = artifact('history', f'observed/{run_id}/{partition_id}.json', history().model_dump(mode='json'), 'observed')
    replay_artifact = artifact('replay', f'replay/{run_id}/{partition_id}.json', dict(schema_version='2.0.0', synthetic=True, kind='observed_replay_batch', contract_version='2.0.0', run_id=run_id, partition_id=partition_id, patient_id=patient_id, entries=entries), 'replay')
    from contracts.runs.observed_v2 import CLINICAL_KINDS
    partition = dict(id=partition_id, unit_id='unit', cell_id=cell_id, preset='evaluation', cohort_id='cohort', replicate=0, patient_id=patient_id, history=history_artifact, replay=replay_artifact, coverage=coverage_artifact, stage_ledgers=ledger_artifacts, completion_receipts=receipt_artifacts, mechanisms=mechanism_artifacts,
                     records=[dict(record_id=r.record_id, payload_sha256=payload_hash(r), source=r.source.model_dump(), seed_key_sha256=ZERO, identity=identities[r.record_id], import_to_event_store=r.kind in CLINICAL_KINDS, exclusion_reason=None if r.kind in CLINICAL_KINDS else 'administrative_event_not_live_authority') for r in history().records])
    manifest = dict(schema_version='2.0.0', synthetic=True, kind='observed_export', contract_version='2.0.0', id=export_name, run_id=run_id, run_manifest=run_manifest, producer=producer, execution='contract_fixture', source_commit='6bc8bd998e8a0baaef9884998e740665fb5fd7b1', runtime=runtime, bindings=bindings, cutoff=cutoff.isoformat(), created_at=cutoff.isoformat(), status='complete' if complete else 'partial', partitions=[partition])
    raw = canonical(manifest)
    authority = dict(contract_version='2.0.0', run_id=run_id, producer=producer, manifest_sha256=ZERO, source_commit=manifest['source_commit'], runtime=runtime, allow_contract_fixture=True, export_id=manifest['id'], export_sha256=sha256(raw), bindings=bindings, producer_qualification=None,
                     partitions=[dict(partition_id=partition_id, schedule=schedule.model_dump(mode='json'), expected_decisions=[s.model_dump(mode='json') for s in slots], coverage_sha256=coverage_artifact['sha256'], terminal_evidence_sha256=None, stage_ledger_hashes={a['id']: a['sha256'] for a in ledger_artifacts}, completion_receipt_hashes={a['id']: a['sha256'] for a in receipt_artifacts}, mechanism_hashes={a['id']: a['sha256'] for a in mechanism_artifacts}, record_identities=identities, record_key_hashes={r.record_id: ZERO for r in history().records})])
    for path, payload in artifacts.items():
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    (root / 'manifest.json').write_bytes(raw)
    (root / 'authority.json').write_bytes(canonical(authority))
    return dict(raw=raw, authority=authority, manifest=manifest, history=history(), entries=entries, artifacts=artifacts, coverage=coverage, schedule=schedule, decision=decision, link=link, report=report, closures=closures, hold_records=hold_records, identities=identities, decisions=decisions, links=links)
