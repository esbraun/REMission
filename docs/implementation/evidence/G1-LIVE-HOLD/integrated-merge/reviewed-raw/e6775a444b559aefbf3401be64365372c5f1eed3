"""Validate the entire archive before any publication or clinical mutation."""
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from contracts.domain.boundaries import lineage_heads, visible_records
from contracts.domain.evidence_v2 import exact_ref, payload_hash, reconstruct_hold, resolve, validate_hold, validate_outcome_link, validate_support_decision
from contracts.domain.observed_v2 import ObservedHistoryV2
from .common import canonical, read_artifact, sha256
from .coverage_v2 import CompletionReceiptV2, StageLedgerV2, SupportCoverageV2, SupportMechanismV2, derive_slots
from .observed_v2 import CLINICAL_KINDS, ExportAuthorityV2, ObservedExportV2, ReplayBatchV2


def validate_partition_record(record, schedule, run_id, partition_id):
    """Bind generated facts to their enclosing archive and accepted local grid.

    Receipt/correction clocks may extend beyond generation. Reviews, closure,
    follow-up and audit bookkeeping do not manufacture a new clinical state.
    This gate is scoped to generated v2 exports, never global live ingestion.
    """
    if record.kind in ('hold_review_evidence', 'hold_transition_bundle', 'support_stage_closure'):
        if (record.run_id, record.partition_id) != (run_id, partition_id):
            raise ValueError('embedded record run/partition differs from containing archive')
    generated_facts = CLINICAL_KINDS | {'consent', 'decision_snapshot', 'recommendation', 'approval', 'assignment',
                                       'delivery', 'support_decision', 'hold_transition_bundle'}
    day = (record.event_at.astimezone(ZoneInfo(schedule.timezone)).date() - schedule.time_zero_local_date).days
    if record.kind in generated_facts and not -14 <= day <= schedule.planned_horizon:
        raise ValueError('generated event outside accepted local horizon -14..84')
    return day


def deterministic_record_id(identity, kind, revision):
    # The process key gives a stable reservation before outputs exist. Exact
    # input hashes remain in the manifest-bound identity, avoiding forward-hash
    # cycles through post-execution completion receipts.
    return 'obs2-' + sha256(canonical([identity.model_dump(mode='json', exclude={'input_refs'}), kind, revision]))[:48]


def record_input_references(record, history, bindings):
    """Exhaustive explicit input hashes, independent of a producer's summary."""
    from contracts.domain.common import VersionRef
    references = [bindings.protocol.model_dump(mode='json'), bindings.observed_representation.model_dump(mode='json')]
    by_id = {r.record_id: r for r in history.records}
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {'record_id', 'payload_sha256'}:
                dependency = by_id.get(value['record_id'])
                if dependency is None or payload_hash(dependency) != value['payload_sha256']:
                    raise ValueError('missing or changed exact provenance input')
                references.append(dict(id=dependency.record_id, version=dependency.schema_version, sha256=value['payload_sha256']))
            elif set(value) == {'id', 'version', 'sha256'}:
                references.append(value)
            else:
                for key, item in value.items():
                    if key in ('decision_id', 'approval_id', 'assignment_id', 'order_ref') and isinstance(item, str) and item in by_id:
                        dependency = by_id[item]
                        references.append(dict(id=item, version=dependency.schema_version, sha256=payload_hash(dependency)))
                    elif key != 'assignment_id' or record.kind != 'support_decision':
                        visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    payload = record.model_dump(mode='json', exclude={'source'})
    # The preallocated assignment ID is the one intentional forward link.
    if record.kind == 'support_decision':
        payload.pop('assignment_id')
    visit(payload)
    return [VersionRef.model_validate_json(value) for value in sorted({canonical(r) for r in references})]


def verify_export_v2(raw: bytes, root: Path, authority: ExportAuthorityV2):
    if sha256(raw) != authority.export_sha256:
        raise ValueError('untrusted v2 export digest')
    manifest = ObservedExportV2.model_validate_json(raw)
    if (manifest.id, manifest.run_id, manifest.producer, manifest.source_commit, manifest.runtime, manifest.run_manifest.sha256, manifest.bindings) != (authority.export_id, authority.run_id, authority.producer, authority.source_commit, authority.runtime, authority.manifest_sha256, authority.bindings):
        raise ValueError('untrusted v2 run/producer/source/runtime/bindings')
    if manifest.execution == 'contract_fixture' and not authority.allow_contract_fixture:
        raise ValueError('fixture cannot prove production')
    if manifest.execution == 'engine_run' and authority.producer_qualification is None:
        raise ValueError('real producer qualification pending')
    trusted = {p.partition_id: p for p in authority.partitions}
    if set(trusted) != {p.id for p in manifest.partitions}:
        raise ValueError('untrusted or omitted patient partition')
    admitted = []
    for partition in manifest.partitions:
        trust = trusted[partition.id]
        history_raw = read_artifact(root, partition.history, 'observed')
        replay_raw = read_artifact(root, partition.replay, 'replay')
        history = ObservedHistoryV2.model_validate_json(history_raw)
        batch = ReplayBatchV2.model_validate_json(replay_raw)
        coverage_raw = read_artifact(root, partition.coverage, 'configuration')
        coverage = SupportCoverageV2.model_validate_json(coverage_raw)
        if sha256(coverage_raw) != trust.coverage_sha256 or coverage.schedule != trust.schedule or coverage.expected_decisions != trust.expected_decisions:
            raise ValueError('coverage changed independently qualified schedule/terminal evidence')
        schedule = coverage.schedule
        if (schedule.run_id, schedule.partition_id, schedule.patient_id, schedule.unit_id, schedule.cell_id, schedule.cohort_id, schedule.replicate, schedule.preset) != (manifest.run_id, partition.id, partition.patient_id, partition.unit_id, partition.cell_id, partition.cohort_id, partition.replicate, partition.preset):
            raise ValueError('schedule partition/roster identity mismatch')
        if (coverage.run_manifest != manifest.run_manifest or schedule.protocol != manifest.bindings.protocol or schedule.timing != manifest.bindings.timing or schedule.temporal != manifest.bindings.temporal or schedule.representation != manifest.bindings.observed_representation or schedule.dgp != manifest.bindings.dgp or schedule.catalog != manifest.bindings.catalog):
            raise ValueError('schedule configuration binding mismatch')
        if coverage.schedule_input.id != schedule.id or coverage.schedule_input.version != '2.0.0' or coverage.schedule_input.sha256 != sha256(canonical(schedule.model_dump(mode='json'))):
            raise ValueError('immutable planned coverage input mismatch')
        if history.patient_id != partition.patient_id or (batch.run_id, batch.partition_id, batch.patient_id) != (manifest.run_id, partition.id, partition.patient_id):
            raise ValueError('archive patient/run/partition mismatch')
        patient = resolve(history, schedule.patient_ref, {'patient'})
        if patient.timezone != schedule.timezone:
            raise ValueError('patient timezone differs from qualified origin')
        if coverage.receipt_cutoff != manifest.cutoff:
            raise ValueError('coverage cutoff mismatch')
        deaths = [r for r in history.as_known_at(manifest.cutoff + timedelta(microseconds=1)) if r.kind == 'intercurrent_event' and r.event_type == 'death']
        death_at = min((r.event_at for r in deaths), default=None)
        if coverage.death_ref:
            death = resolve(history, coverage.death_ref, {'intercurrent_event'}, cutoff=manifest.cutoff, inclusive=True)
            if death.event_type != 'death' or death.event_at != coverage.death_effective_at or payload_hash(death) != trust.terminal_evidence_sha256:
                raise ValueError('unqualified/stale terminal truncation')
        elif trust.terminal_evidence_sha256 is not None:
            raise ValueError('qualified terminal evidence was omitted')
        if coverage.expected_decisions != derive_slots(trust.schedule, death_at=coverage.death_effective_at):
            raise ValueError('shortened or changed canonical support schedule')
        by_id = {r.record_id: r for r in history.records}
        if set(by_id) != {r.record_id for r in partition.records} or set(by_id) != {e.record.record_id for e in batch.entries}:
            raise ValueError('full archive must retain every observed and administrative record')
        if set(trust.record_identities) != set(by_id) or set(trust.record_key_hashes) != set(by_id):
            raise ValueError('trusted provenance omitted records')
        for entry in batch.entries:
            if entry.record != by_id[entry.record.record_id]:
                raise ValueError('archive/history disagreement')
        for binding in partition.records:
            record = by_id[binding.record_id]
            validate_partition_record(record, schedule, manifest.run_id, partition.id)
            if binding.payload_sha256 != payload_hash(record) or binding.source != record.source:
                raise ValueError('record payload/source provenance mismatch')
            if record.event_at > manifest.cutoff or record.recorded_at > manifest.cutoff or record.available_at > manifest.cutoff:
                raise ValueError('archive includes bytes beyond receipt cutoff')
            if binding.import_to_event_store != (record.kind in CLINICAL_KINDS):
                raise ValueError('generated administrative data cannot grant live authority')
            identity = binding.identity
            if identity != trust.record_identities[record.record_id] or binding.seed_key_sha256 != trust.record_key_hashes[record.record_id]:
                raise ValueError('untrusted record deterministic/full-key identity')
            if identity.input_refs != record_input_references(record, history, manifest.bindings):
                raise ValueError('record provenance omitted or changed exact inputs')
            if (identity.run_id, identity.protocol, identity.cell_id, identity.cohort_id, identity.replicate, identity.patient_id) != (manifest.run_id, schedule.protocol.id, partition.cell_id, partition.cohort_id, partition.replicate, partition.patient_id):
                raise ValueError('record protocol/run/cell/cohort/patient namespace mismatch')
            if record.schema_version == '2.0.0' and record.record_id != deterministic_record_id(identity, record.kind, record.revision):
                raise ValueError('noncanonical deterministic record identity')
            if record.schema_version == '2.0.0' and record.kind == 'daily_report' and record.source.version == '1.2.0' and record.missingness == 'observed' and (record.diary_sleep_minutes is None or record.burden is not None):
                raise ValueError('generated observed report needs its single diary draw and null unspecified burden')
        ledgers = {}
        if {a.id: a.sha256 for a in partition.stage_ledgers} != trust.stage_ledger_hashes:
            raise ValueError('untrusted/exhaustive stage-ledger set mismatch')
        for artifact in partition.stage_ledgers:
            ledger = StageLedgerV2.model_validate_json(read_artifact(root, artifact, 'configuration'))
            if artifact.id != ledger.id or (ledger.run_id, ledger.partition_id, ledger.patient_id) != (manifest.run_id, partition.id, partition.patient_id):
                raise ValueError('stage-ledger identity mismatch')
            ledgers[ledger.id] = (artifact, ledger)
        if {a.id: a.sha256 for a in partition.completion_receipts} != trust.completion_receipt_hashes:
            raise ValueError('untrusted completion receipt set')
        receipts = {}
        for artifact in partition.completion_receipts:
            receipt = CompletionReceiptV2.model_validate_json(read_artifact(root, artifact, 'configuration'))
            if artifact.id != receipt.id or (receipt.run_id, receipt.partition_id, receipt.patient_id, receipt.producer, receipt.source_commit, receipt.runtime) != (manifest.run_id, partition.id, partition.patient_id, manifest.producer, manifest.source_commit, manifest.runtime):
                raise ValueError('completion receipt producer/run provenance mismatch')
            if receipt.schedule_input != coverage.schedule_input or receipt.available_at > manifest.cutoff:
                raise ValueError('receipt changed planned input or future publication')
            for output in receipt.output_artifacts:
                read_artifact(root, output, output.role)
            for ref in receipt.stage_ledgers:
                if ref.id not in ledgers or ledgers[ref.id][0].sha256 != ref.sha256 or ref.version != '2.0.0':
                    raise ValueError('receipt omitted or substituted immutable stage ledger')
                if receipt.output_counts.get(ref.id) != len(ledgers[ref.id][1].event_refs):
                    raise ValueError('receipt stage output count mismatch')
            receipts[receipt.id] = (artifact, receipt)
        if {a.id: a.sha256 for a in partition.mechanisms} != trust.mechanism_hashes:
            raise ValueError('untrusted complete support mechanism')
        mechanisms = {a.id: (a, SupportMechanismV2.model_validate_json(read_artifact(root, a, 'configuration'))) for a in partition.mechanisms}

        def verify_closure(closure, cutoff):
            if (closure.run_id, closure.partition_id) != (manifest.run_id, partition.id):
                raise ValueError('closure run partition mismatch')
            decision = resolve(history, closure.support_decision, {'support_decision'})
            if (closure.decision_index, closure.window_id) != (decision.decision_index, decision.outcome_window.id):
                raise ValueError('closure window/index mismatch')
            if (closure.assignment_ref is None) != (decision.assignment_id is None):
                raise ValueError('closure assignment required unless unavailable')
            if closure.assignment_ref and resolve(history, closure.assignment_ref, {'assignment'}).record_id != decision.assignment_id:
                raise ValueError('closure assignment mismatch')
            if closure.status != 'complete':
                return []
            artifact, ledger = ledgers.get(closure.stage_ledger.id, (None, None))
            if artifact is None or closure.stage_ledger.sha256 != artifact.sha256 or closure.stage_ledger.version != '2.0.0':
                raise ValueError('missing/substituted immutable stage ledger')
            if (ledger.decision_index, ledger.window_id, ledger.stage, ledger.rule, ledger.event_refs) != (closure.decision_index, closure.window_id, closure.stage, closure.rule, closure.stage_event_refs):
                raise ValueError('closure differs from exhaustive stage ledger')
            artifact, receipt = receipts.get(closure.completion_receipt.id, (None, None))
            if artifact is None or artifact.sha256 != closure.completion_receipt.sha256 or receipt.status != 'complete' or receipt.available_at >= cutoff:
                raise ValueError('closure completion evidence missing/not-yet-visible')
            if closure.stage_ledger not in receipt.stage_ledgers or closure.stage_completed_at < receipt.completed_at or closure.recorded_at < receipt.published_at:
                raise ValueError('closure predates actual execution/publication')
            if closure.stage_completed_at < decision.event_at:
                raise ValueError('stage completed before decision')
            events = [resolve(history, ref, {'delivery'}, cutoff=cutoff) for ref in ledger.event_refs]
            for event in events:
                if event.assignment_id != decision.assignment_id or event.stage != closure.stage or not decision.outcome_window.starts_at <= event.event_at < decision.outcome_window.ends_at or event.event_at > closure.stage_completed_at:
                    raise ValueError('stage-event assignment/window/chronology mismatch')
            # Compare all active stage events; deleting either exported event or
            # closure row cannot turn a known positive into an observed zero.
            expected = {r.record_id for r in lineage_heads(visible_records(history.records, cutoff)) if r.record_status != 'retracted' and r.kind == 'delivery' and r.assignment_id == decision.assignment_id and r.stage == closure.stage}
            if expected != {r.record_id for r in events}:
                raise ValueError('stage ledger is not exhaustive against observed delivery events')
            return events

        heads = {r.record_id: r for r in lineage_heads(history.records) if r.record_status != 'retracted'}
        decisions = {r.record_id: r for r in heads.values() if r.kind == 'support_decision'}
        expected_ids = set()
        frozen_scopes = {}
        for row in coverage.slots:
            if row.decision_ref:
                decision = resolve(history, row.decision_ref, {'support_decision'}, cutoff=manifest.cutoff, inclusive=True)
                slot = row.slot
                if (decision.decision_index, decision.event_at, decision.outcome_window.id, decision.outcome_window.assessment_at, decision.outcome_link_id) != (slot.decision_index, slot.decision_at, slot.window_id, slot.assessment_at, slot.outcome_link_id):
                    raise ValueError('support row differs from trusted canonical slot')
                if decision.outcome_window.timezone != schedule.timezone or decision.outcome_window.local_date != decision.event_at.astimezone(__import__('zoneinfo').ZoneInfo(schedule.timezone)).date():
                    raise ValueError('support local date/zone mismatch')
                expected_ids.add(decision.record_id)
                if death_at is not None and decision.event_at >= death_at:
                    raise ValueError('support decision at/after terminal safety phase')
                if row.slot.assessment_at <= manifest.cutoff and row.outcome_ref is None:
                    raise ValueError('due_support_outcome_link_missing')
                artifact, mechanism = mechanisms.get(decision.mechanism.id, (None, None))
                if artifact is None or decision.mechanism.sha256 != artifact.sha256 or mechanism.id != artifact.id or (mechanism.policy, mechanism.mode, mechanism.context_mapping) != (decision.policy, decision.mode, decision.context_mapping):
                    raise ValueError('decision must bind complete executed frozen mechanism')
                if mechanism.mode == 'frozen':
                    origin = canonical(mechanism.frozen_origin.model_dump(mode='json'))
                    if origin in frozen_scopes and frozen_scopes[origin] != decision.mechanism:
                        raise ValueError('complete patient-specific frozen mechanism changed')
                    frozen_scopes[origin] = decision.mechanism
                if validate_support_decision(history, decision) != 'validated' and manifest.status == 'complete':
                    raise ValueError('complete export has unbound assignment')
                receipt_artifact, persistence = receipts.get(decision.execution_receipt.id, (None, None))
                distribution_ref = dict(id='support-distribution', version='2.0.0', sha256=sha256(canonical(decision.probabilities)))
                if receipt_artifact is None or decision.execution_receipt.sha256 != receipt_artifact.sha256 or persistence.status != 'complete' or persistence.process != 'support_distribution_persist' or persistence.completed_at != decision.distribution_persisted_at:
                    raise ValueError('decision requires qualified distribution persistence receipt')
                required = [decision.policy.model_dump(mode='json'), decision.mechanism.model_dump(mode='json'), distribution_ref]
                if any(r not in [c.model_dump(mode='json') for c in persistence.accepted_configuration] for r in required):
                    raise ValueError('persistence receipt changed executed policy/mechanism/vector')
            if row.outcome_ref:
                outcome = resolve(history, row.outcome_ref, {'support_outcome_link'}, cutoff=manifest.cutoff, inclusive=True)
                if row.decision_ref != outcome.support_decision:
                    raise ValueError('coverage endpoint is attached to wrong decision')
                if row.slot.decision_index == 84 and (outcome.reward.status != 'undefined' or outcome.reward.reason != 'outside_generated_horizon'):
                    raise ValueError('day-85 endpoint is administrative undefined only')
                if outcome.reward.reason == 'outside_generated_horizon' and (row.slot.decision_index != 84 or outcome.reward.definition_refs != [manifest.bindings.protocol, manifest.bindings.timing]):
                    raise ValueError('outside-horizon endpoint needs exact accepted protocol/horizon definitions')
                if manifest.status == 'complete':
                    for closure_ref in [outcome.offered_closure_ref, outcome.delivered_closure_ref]:
                        if closure_ref is None or resolve(history, closure_ref, {'support_stage_closure'}).status != 'complete':
                            raise ValueError('complete endpoint requires both closed stage ledgers')
        if expected_ids != set(decisions):
            raise ValueError('missing-middle or unplanned support decision')
        for record in history.records:
            if record.kind == 'support_outcome_link':
                validate_outcome_link(history, record, verify_closure=verify_closure)
            elif record.kind == 'support_stage_closure':
                verify_closure(record, record.available_at + timedelta(microseconds=1))
            elif record.kind == 'hold_transition_bundle':
                validate_hold(history, record)
        if coverage.completion_receipt:
            artifact, receipt = receipts.get(coverage.completion_receipt.id, (None, None))
            if artifact is None or artifact.sha256 != coverage.completion_receipt.sha256 or receipt.status != 'complete':
                raise ValueError('complete coverage lacks qualified execution receipt')
        if manifest.status == 'complete' and coverage.status != 'complete':
            raise ValueError('complete export cannot shorten partial coverage')
        if manifest.status == 'complete' and any(r.kind == 'hold_transition_bundle' for r in history.records):
            if any(i['interval_status'] == 'unresolved' for i in reconstruct_hold(history, manifest.cutoff + timedelta(microseconds=1))):
                raise ValueError('complete archive has unresolved/forked hold dependency chain')
        admitted.append((partition, history, batch, history.project(manifest.cutoff), history_raw, replay_raw))
    return manifest, admitted
