"""Bounded UNIT generation/projection controls, never production qualification."""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch

from contracts.domain.analysis import canonical, sha
from contracts.domain.evidence_v2 import exact_ref, projection_hash
from contracts.domain.protocol import ObservedHistoryV21, RECORD_ADAPTER_V21
from contracts.runs.support_research import StageVerifier, SupportCompletion, SupportResearchIndex, SupportRuntime, version_ref
from methods.support.data import PublicHistory, build_features
from methods.support.wcls import fit
from services.foundation.protocol import project_protocol, validate_support_v21
from services.generator import research_support as producer

ROOT=Path(__file__).resolve().parents[2]
START=producer.START
WALL=datetime(2026,10,22,12,tzinfo=timezone.utc)


def runtime():
    import numpy
    def lock(name,path):return dict(id=name,version='20261021',sha256=sha_bytes((ROOT/path).read_bytes().replace(b'\r\n',b'\n')))
    return SupportRuntime.model_validate_json(canonical(dict(image_sha256=os.environ['RESEARCH_TEST_IMAGE'].removeprefix('sha256:'),
        numerical_lock=lock('numerical-lock','tooling/library/requirements.lock'),service_lock=lock('service-lock','tooling/foundation/requirements.lock'),
        python_version=platform.python_version(),numpy_version=numpy.__version__,prng='keyed-SHA256-53bit-BoxMuller-v1',
        seed_derivation=producer.MAPPING,precision='float64')))


def sha_bytes(raw):
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def history(records):return producer._history('UNIT-SUPPORT',records)


class SupportProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.pins=runtime();cls.source=os.environ['RESEARCH_TEST_SOURCE'];cls.plan_sha=sha('UNIT-frozen-plan')
        cls.products={}
        for mode in ('S0','S1'):
            folder=cls.root/mode;folder.mkdir()
            persisted=[]
            def draw(*args):
                saved=json.loads((folder/f'UNIT-{mode}/decisions/{args[-1]}.json').read_bytes())
                if saved['support_decision']!=persisted[-1].model_dump(mode='json'):
                    raise AssertionError('Final distribution/context not durably persisted before draw')
                return .1
            # A fixed artificial draw stream exercises burden boundaries without
            # modifying or balancing any genuine production assignment stream.
            with patch.object(producer,'_draw',side_effect=draw):
                product=producer.trajectory('UNIT-SUPPORT',mode,seed=12345,index=2,assignment_seed='UNIT-only',
                    run_id='UNIT-run',partition_id='UNIT-'+mode,runtime=cls.pins,source_commit=cls.source,
                    plan_sha=cls.plan_sha,root=folder,horizon=8,now=lambda:WALL,on_persist=persisted.append)
            cls.products[mode]=(*product,folder,persisted)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def proof(self,mode='S1',full=None,ledgers=None,receipts=None):
        base,ls,rs,_,root,_=self.products[mode]
        return StageVerifier(full or base,ls if ledgers is None else ledgers,rs if receipts is None else receipts,root,
            run_id='UNIT-run',partition_id='UNIT-'+mode,source_commit=self.source,runtime=self.pins,frozen_plan_sha256=self.plan_sha)

    def project(self,mode='S1',full=None,cutoff=None,**proof):
        full=full or self.products[mode][0]
        return project_protocol(full,cutoff or START+timedelta(days=8),family='support',origin=START,
            verify_closure=self.proof(mode,full,**proof))

    def test_actual_projection_S0_masked_S1_randomized_and_no_leakage(self):
        for mode in ('S0','S1'):
            projected=self.project(mode)
            decisions=[r for r in projected.records if r.kind=='support_decision']
            self.assertEqual(len(decisions),8)
            available={r.record_id:r for r in projected.records}
            for decision in decisions:
                assignment=available[decision.assignment_id]
                if decision.availability=='deterministic':
                    self.assertEqual(decision.probabilities,dict(support_prompt=0.,no_prompt=1.))
                    self.assertFalse(assignment.experimental)
                    self.assertIsNone(assignment.component);self.assertIsNone(assignment.probability)
                else:
                    self.assertTrue(assignment.experimental);self.assertEqual(assignment.probability,.5)
            text=canonical(projected.model_dump(mode='json'))
            for forbidden in ('generation_seed','assignment_seed','adapter_seed','raw_sha256','payload_sha256','namespace','private_recipe','ProtocolPanel','index_map'):
                self.assertNotIn('"'+forbidden+'"',text)
            self.assertEqual([r.decision_index for r in decisions],list(range(8)))
        self.assertEqual({r.availability for r in self.project('S0').records if r.kind=='support_decision'},{'deterministic'})
        self.assertEqual({r.availability for r in self.project().records if r.kind=='support_decision'},{'deterministic','randomized'})

    def test_burden_and_persistence_before_draw(self):
        full,_,_,_,_,persisted=self.products['S1']
        decisions=[r for r in full.records if r.kind=='support_decision']
        assignments={r.record_id:r for r in full.records if r.kind=='assignment'}
        self.assertEqual([r.availability for r in decisions],['randomized','deterministic','randomized','deterministic','randomized','deterministic','deterministic','randomized'])
        self.assertEqual([r.decision_index for r in persisted],list(range(8)))
        for decision in decisions:
            self.assertLessEqual(decision.distribution_persisted_at,assignments[decision.assignment_id].event_at)
            prior=history([r for r in full.records if r.available_at<decision.cutoff])
            self.assertEqual(producer.distribution(prior,decision.cutoff,'S1')[2],decision.probabilities)
        self.assertIn('max_three_in_seven',decisions[6].eligibility[0].reasons)
        self.assertIn('no_consecutive_nights',decisions[1].eligibility[0].reasons)

    def test_public_consent_expiry_withdrawal_oversight_hold_pause(self):
        full=self.products['S1'][0];at=START+timedelta(days=1)
        before=history([r for r in full.records if r.available_at<at])
        consent=next(r for r in before.records if r.kind=='consent')
        for change in (dict(expires_at=at),dict(withdrawn_at=at),dict(oversight_status='expired'),dict(consent_status='missing')):
            altered=history([r.model_copy(update=change) if r.record_id==consent.record_id else r for r in before.records])
            for mode in ('S0','S1'):
                eligibility,availability,masses,reasons=producer.distribution(altered,at,mode)
                self.assertEqual(availability,'unavailable');self.assertEqual(sum(masses.values()),0.)
                self.assertTrue(all(e['status']=='excluded' for e in eligibility));self.assertTrue(reasons)
        for kwargs in (dict(held=True),dict(paused=True)):
            self.assertEqual(producer.distribution(before,at,'S1',**kwargs)[1],'unavailable')
        latest=max((r for r in before.records if r.kind=='decision_snapshot'),key=lambda r:r.event_at)
        for workflow in (latest.workflow.model_copy(update=dict(clinical='clinical_hold',hold_reasons=['UNIT hold'])),
                         latest.workflow.model_copy(update=dict(support_mode='paused')),
                         latest.workflow.model_copy(update=dict(data_readiness='incomplete'))):
            altered=history([r.model_copy(update=dict(workflow=workflow)) if r.record_id==latest.record_id else r for r in before.records])
            self.assertEqual(producer.distribution(altered,at,'S1')[1],'unavailable')

    def test_offline_runner_import_and_observed_baseline_summaries(self):
        import importlib.util
        path=ROOT/'docs/implementation/evidence/support-producer-20261022/run_support_once.py'
        spec=importlib.util.spec_from_file_location('UNIT_offline_support_runner',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        baseline=module._summary([self.project('S0')]);mrt=module._summary([self.project('S1')])
        self.assertEqual(baseline['decision_count'],8)
        self.assertEqual(baseline['report_count'],8)
        self.assertEqual(baseline['burden'],dict(offered_prompt_count=0,delivered_prompt_count=0))
        self.assertEqual(mrt['burden']['offered_prompt_count'],4)
        self.assertEqual(mrt['burden']['delivered_prompt_count'],4)

    def test_deterministic_projection_retains_separate_consent_gate(self):
        # Rebind the entire first-window audit after a consent change. Failure
        # must come from the consent gate, not an unrelated stale hash.
        full=self.products['S0'][0];cutoff=START+timedelta(days=1)
        selected=[r for r in full.records if r.available_at<cutoff]
        consent=next(r for r in selected if r.kind=='consent')
        changed=[r.model_copy(update=dict(expires_at=START)) if r.record_id==consent.record_id else r for r in selected]
        new_consent=next(r for r in changed if r.kind=='consent')
        frozen=next(r for r in changed if r.kind=='protocol_snapshot')
        new_frozen=frozen.model_copy(update=dict(consent_refs=[exact_ref(new_consent)]))
        changed=[new_frozen if r.record_id==frozen.record_id else r for r in changed]
        decision=next(r for r in changed if r.kind=='support_decision')
        updated=decision.model_copy(update=dict(context_projection_sha256=projection_hash(history(changed),START),
            policy_constraint=decision.policy_constraint.model_copy(update=dict(snapshot_ref=exact_ref(new_frozen)))))
        changed=[updated if r.record_id==decision.record_id else r for r in changed]
        closures={r.record_id:r.model_copy(update=dict(support_decision=exact_ref(updated))) for r in changed if r.kind=='support_stage_closure'}
        changed=[closures.get(r.record_id,r) for r in changed]
        outcome=next(r for r in changed if r.kind=='support_outcome_link')
        new_outcome=outcome.model_copy(update=dict(support_decision=exact_ref(updated),
            offered_closure_ref=exact_ref(closures[outcome.offered_closure_ref.record_id]),
            delivered_closure_ref=exact_ref(closures[outcome.delivered_closure_ref.record_id])))
        changed=[new_outcome if r.record_id==outcome.record_id else r for r in changed]
        with self.assertRaisesRegex(ValueError,'support_component_consent_oversight_required'):
            self.project('S0',full=history(changed),cutoff=cutoff)

    def test_unavailable_actual_projection(self):
        # An existing complete typed public unavailable fixture; no assignment
        # and pending burden do not need a false zero-completion receipt.
        from protocol_fixtures import full_history
        full=full_history()
        projected=project_protocol(full,START+timedelta(days=2),family='support',origin=START)
        decision=next(r for r in projected.records if r.kind=='support_decision')
        self.assertEqual(decision.availability,'unavailable');self.assertIsNone(decision.assignment_id)
        self.assertEqual(sum(decision.probabilities.values()),0.)

    def test_malformed_deterministic_randomized_mix_rejected_by_projection(self):
        full=self.products['S1'][0]
        decision=next(r for r in full.records if r.kind=='support_decision' and r.availability=='deterministic')
        assignment=next(r for r in full.records if r.record_id==decision.assignment_id)
        # A schema-valid randomized assignment cannot own a deterministic point.
        wrong=assignment.model_copy(update=dict(experimental=True,component='mrt_bandit',probability=.5,
            seed=next(r.seed for r in full.records if r.kind=='assignment' and r.experimental)))
        altered=history([wrong if r.record_id==assignment.record_id else r for r in full.records])
        with self.assertRaises(ValueError):self.project(full=altered)
        # Ordinary arbitrary MRT-policy assignments have no validated owner.
        orphan=assignment.model_copy(update=dict(record_id='UNIT-orphan',lineage_id='UNIT-orphan'))
        with self.assertRaisesRegex(ValueError,'fixed_protocol_background'):
            self.project(full=history([orphan,*full.records]))

    def test_exact_noon_delivery_and_strict_report_clocks(self):
        full=self.products['S1'][0]
        for decision in (r for r in full.records if r.kind=='support_decision'):
            self.assertEqual(decision.cutoff,START+timedelta(days=decision.decision_index))
            self.assertEqual(decision.outcome_window.assessment_at,decision.cutoff+timedelta(days=1,minutes=-1))
        for event in (r for r in full.records if r.kind=='delivery' and r.option=='support_prompt'):
            self.assertEqual((event.event_at.hour,event.event_at.minute),(20,0))
        for outcome in (r for r in full.records if r.kind=='support_outcome_link'):
            self.assertLess(outcome.assessment_at,outcome.evaluated_as_of)
            self.assertLess(outcome.evaluated_as_of,outcome.available_at)
            self.assertLess(outcome.available_at,outcome.assessment_at+timedelta(minutes=1))
        receipt=self.products['S1'][2][0]
        self.assertEqual(receipt.execution_started_at,WALL)
        self.assertLess(receipt.simulated_available_at,WALL)
        # October actual execution is compatible with January projection.
        self.project(cutoff=START+timedelta(days=1))
        with self.assertRaises(ValueError):SupportCompletion.model_validate_json(canonical(receipt.model_dump(mode='json')|dict(execution_ended_at=(WALL-timedelta(seconds=1)).isoformat())))

    def test_positive_zero_closure_and_omission_tamper_member_rejection(self):
        full,ledgers,receipts,_,root,_=self.products['S1'];proof=self.proof();cutoff=START+timedelta(days=8)
        closures=[r for r in full.records if r.kind=='support_stage_closure']
        self.assertTrue(any(proof(c,cutoff)==[] for c in closures))
        positive=next(c for c in closures if c.stage=='offered' and c.row_count==1)
        self.assertEqual(proof(positive,cutoff)[0].option,'support_prompt')
        for bad in (positive.model_copy(update=dict(partition_id='foreign')),positive.model_copy(update=dict(window_id='foreign'))):
            with self.assertRaises(ValueError):proof(bad,cutoff)
        with self.assertRaisesRegex(ValueError,'missing_or_substituted'):self.proof(receipts=[])(positive,cutoff)
        ledger=next(r for r in ledgers if r.id==positive.stage_ledger.id)
        with self.assertRaisesRegex(ValueError,'missing_or_substituted'):
            self.proof(ledgers=[r.model_copy(update=dict(event_refs=[])) if r.id==ledger.id else r for r in ledgers])(positive,cutoff)
        receipt=next(r for r in receipts if r.id==positive.completion_receipt.id)
        target=root/receipt.output_artifacts[0].path;original=target.read_bytes()
        try:
            target.write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError,'artifact_hash'):proof(positive,cutoff)
        finally:target.write_bytes(original)
        event_id=positive.stage_event_refs[0].record_id
        with self.assertRaises(ValueError):self.proof(full=history([r for r in full.records if r.record_id!=event_id]))(positive,cutoff)
        # An omitted claim with recomputed ledger/receipt/closure hashes still
        # fails exhaustive active-event comparison (not just a hash check).
        empty=ledger.model_copy(update=dict(event_refs=[]))
        edited_receipt=receipt.model_copy(update=dict(stage_ledgers=[version_ref(empty) if v.id==ledger.id else v for v in receipt.stage_ledgers]))
        edited_closure=positive.model_copy(update=dict(stage_ledger=version_ref(empty),completion_receipt=version_ref(edited_receipt),stage_event_refs=[],row_count=0))
        edited=history([edited_closure if r.record_id==positive.record_id else r for r in full.records])
        with self.assertRaisesRegex(ValueError,'not_exhaustive'):
            self.proof(full=edited,ledgers=[empty if r.id==ledger.id else r for r in ledgers],
                receipts=[edited_receipt if r.id==receipt.id else r for r in receipts])(edited_closure,cutoff)

    def test_partial_foreign_receipt_and_corrected_future_event_denied(self):
        full,ledgers,receipts,_,_,_=self.products['S1'];cutoff=START+timedelta(days=8)
        closure=next(r for r in full.records if r.kind=='support_stage_closure' and r.row_count)
        receipt=next(r for r in receipts if r.id==closure.completion_receipt.id)
        for change in (dict(status='partial',reason='UNIT interrupted'),dict(patient_id='foreign'),dict(partition_id='foreign')):
            bad=receipt.model_copy(update=change)
            linked=closure.model_copy(update=dict(completion_receipt=version_ref(bad)))
            edited=history([linked if r.record_id==closure.record_id else r for r in full.records])
            with self.assertRaises(ValueError):
                self.proof(full=edited,receipts=[bad if r.id==receipt.id else r for r in receipts])(linked,cutoff)
        event=next(r for r in full.records if r.record_id==closure.stage_event_refs[0].record_id)
        for change in (dict(patient_id='foreign'),dict(available_at=cutoff,recorded_at=cutoff),
                       dict(event_at=cutoff,recorded_at=cutoff,available_at=cutoff)):
            with self.assertRaises(ValueError):
                altered=history([r.model_copy(update=change) if r.record_id==event.record_id else r for r in full.records])
                self.proof(full=altered)(closure,cutoff)
        correction=event.model_copy(update=dict(record_id='UNIT-correction',revision=2,supersedes=event.record_id,
            recorded_at=event.recorded_at+timedelta(seconds=1),available_at=event.available_at+timedelta(seconds=1)))
        with self.assertRaises(ValueError):self.proof(full=history([*full.records,correction]))(closure,cutoff)
        with self.assertRaises(ValueError):history([*full.records,event])

    def test_replay_identical_when_test_wall_identity_is_frozen(self):
        full=self.products['S1'][0]
        with tempfile.TemporaryDirectory() as folder,patch.object(producer,'_draw',return_value=.1):
            repeated=producer.trajectory('UNIT-SUPPORT','S1',seed=12345,index=2,assignment_seed='UNIT-only',run_id='UNIT-run',
                partition_id='UNIT-S1',runtime=self.pins,source_commit=self.source,plan_sha=self.plan_sha,
                root=Path(folder),horizon=8,now=lambda:WALL)[0]
        self.assertEqual(full,repeated)

    def test_cutoff_prefix_frozen_after_later_data_and_order(self):
        full=self.products['S1'][0];cutoff=START+timedelta(days=4)
        early=self.project(cutoff=cutoff)
        prefix=history([r for r in full.records if r.available_at<cutoff])
        self.assertEqual(early,self.project(full=prefix,cutoff=cutoff))
        # Full audit projection identity is order-bound; reordering an already
        # committed source must be rejected, rather than silently rehashed.
        with self.assertRaises(ValueError):self.project(full=history(list(reversed(full.records))),cutoff=cutoff)
        self.assertEqual(sha(early.model_dump(mode='json')),sha(self.project(cutoff=cutoff).model_dump(mode='json')))

    def test_generator_prefix_pairing_missing_and_policy_response(self):
        s0,s1=self.products['S0'][0],self.products['S1'][0]
        r0=[r for r in s0.records if r.kind=='daily_report'];r1=[r for r in s1.records if r.kind=='daily_report']
        self.assertEqual([r.missingness for r in r0],[r.missingness for r in r1])
        self.assertEqual([r.function for r in r0],[r.function for r in r1])
        self.assertEqual([r.items for r in s0.records if r.kind=='isi'],[r.items for r in s1.records if r.kind=='isi'])
        self.assertTrue(any(a.sleep_quality!=b.sleep_quality for a,b in zip(r0,r1)))
        background=next(r for r in s1.records if r.kind=='assignment' and r.option=='behavioral_continue')
        schedule=[dict(day=d.decision_index,option=next(a.option for a in s1.records if a.record_id==d.assignment_id),assignment_id=d.assignment_id)
                  for d in s1.records if d.kind=='support_decision']
        short=producer._generated(12345,2,'UNIT-SUPPORT',4,background,schedule[:4])
        long=producer._generated(12345,2,'UNIT-SUPPORT',8,background,schedule)
        by_id={r.record_id:r for r in long}
        self.assertTrue(all(by_id[r.record_id]==r for r in short))
        data=build_features([PublicHistory(s1.patient_id,START,START+timedelta(days=8),tuple(self.project().records))])
        self.assertTrue(all(r.reward is None or r.reward>0 for r in data.rows))
        self.assertEqual(fit(data,provenance_seed='fit/wcls-unused-provenance/UNIT').status,'abstained')

    def test_interrupted_prepare_has_no_complete_index_and_private_root_is_separate(self):
        plan=dict(version='poc-support-research-plan-v1',namespace='UNIT-only-private-namespace',run_id='UNIT-interrupted',cohort_id='UNIT-cohort',
            patients=['UNIT-member-'+str(i) for i in range(12)])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(producer,'trajectory',side_effect=RuntimeError('UNIT interruption')):
                with self.assertRaisesRegex(RuntimeError,'interruption'):
                    producer.prepare(plan,root/'private',root/'public',runtime=self.pins.model_dump(mode='json'),source_commit=self.source)
            self.assertFalse((root/'public/manifest.json').exists())
            self.assertTrue((root/'private/recipe.json').exists())
            with self.assertRaisesRegex(ValueError,'separate'):
                producer.prepare(plan,root,root/'nested',runtime=self.pins.model_dump(mode='json'),source_commit=self.source)

    def test_index_exact_modes_pairs_origin_sources_and_scientific_refs(self):
        artifact=producer._write(self.root,'UNIT-index-schema-artifact','UNIT-index-schema.json',dict(UNIT='schema only'))
        members=['UNIT-member-'+str(i) for i in range(12)]
        value=dict(version='poc-support-research-v1',synthetic=True,execution='historical-research-only',run_id='UNIT-index',cohort_id='UNIT-cohort',
            members=members,origin=START.isoformat(),horizon=84,cuts=[14,42,84],law=producer.LAW_REF,protocol=producer.SUPPORT_REF,
            estimand=producer.S1_ESTIMAND,source_commit=self.source,generator_sources={name:sha('UNIT-source-'+name)
                for name in ('restricted.py','restricted_v2.py','research_support.py')},runtime=self.pins.model_dump(mode='json'),
            frozen_plan_sha256=self.plan_sha,private_recipe_sha256=sha('UNIT-private-recipe'),shared_pair_sha256=sha('UNIT-shared-pairs'),
            trajectories=[dict(member_id=p,paired_member_id='UNIT-pair-'+str(i),mode=mode,partition_id='UNIT-'+str(i)+'-'+mode,
                history=artifact.model_dump(mode='json'),projections={str(d):artifact.model_dump(mode='json') for d in (14,42,84)},
                stage_ledgers=artifact.model_dump(mode='json'),completions=artifact.model_dump(mode='json'))
                for i,p in enumerate(members) for mode in ('S0','S1')])
        SupportResearchIndex.model_validate_json(canonical(value))
        changes=[dict(origin=(START+timedelta(hours=1)).isoformat()),dict(generator_sources={}),dict(horizon=42),
            dict(members=[members[0]]*12),dict(law=producer.SUPPORT_REF)]
        for change in changes:
            with self.assertRaises(ValueError):SupportResearchIndex.model_validate_json(canonical(value|change))
        bad=copy.deepcopy(value);bad['trajectories'][1]['paired_member_id']='UNIT-wrong-pair'
        with self.assertRaisesRegex(ValueError,'paired_identity'):SupportResearchIndex.model_validate_json(canonical(bad))


class FullHorizonUnitTests(unittest.TestCase):
    def test_one_UNIT_member84_all_frozen_cuts(self):
        pins=runtime();source=os.environ['RESEARCH_TEST_SOURCE'];plan_sha=sha('UNIT84-plan')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            full,ledgers,receipts,_=producer.trajectory('UNIT84','S1',seed=12345,index=2,assignment_seed='UNIT84-independent',
                run_id='UNIT84-run',partition_id='UNIT84-partition',runtime=pins,source_commit=source,plan_sha=plan_sha,
                root=root,horizon=84,now=lambda:WALL)
            proof=StageVerifier(full,ledgers,receipts,root,run_id='UNIT84-run',partition_id='UNIT84-partition',
                source_commit=source,runtime=pins,frozen_plan_sha256=plan_sha)
            self.assertEqual(len([r for r in full.records if r.kind=='support_decision']),84)
            self.assertEqual(max(r.decision_index for r in full.records if r.kind=='support_decision'),83)
            for day in (14,42,84):
                cutoff=START+timedelta(days=day)
                projection=project_protocol(full,cutoff,family='support',origin=START,verify_closure=proof)
                reports=[r for r in projection.records if r.kind=='daily_report']
                self.assertEqual(len(reports),day)
                self.assertEqual(len([r for r in projection.records if r.kind=='support_decision']),day)
                self.assertEqual(len([r for r in projection.records if r.kind=='support_outcome_link']),day)
                self.assertTrue(all(r.available_at<cutoff for r in projection.records))
                features=build_features([PublicHistory(full.patient_id,START,cutoff,tuple(projection.records))])
                self.assertEqual(sum(r.reward is None for r in features.rows),
                    sum(r.reward.status=='missing' and next(d.availability for d in projection.records if d.record_id==r.support_decision.record_id)=='randomized'
                        for r in projection.records if r.kind=='support_outcome_link'))
                self.assertEqual(fit(features,provenance_seed='fit/wcls-unused-provenance/UNIT84').status,'abstained')
                self.assertEqual(len([r for r in projection.records if r.kind=='support_stage_closure']),day*2)


if __name__=='__main__':unittest.main()
