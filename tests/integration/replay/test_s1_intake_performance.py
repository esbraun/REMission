"""Scalar path and causal-reference regressions; no accepted archive or Store."""
import ast
from collections import Counter
from contextlib import ExitStack
import copy
from datetime import timedelta
import inspect
import json
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from contracts.domain.evidence_v2 import exact_ref,projection_hash
import contracts.domain.evidence_v2 as evidence
from contracts.domain.protocol import PROTOCOL_REFS,RECORD_ADAPTER_V21
from contracts.domain.analysis import reference
from contracts.runs.common import Artifact,canonical,sha256
import contracts.runs.support_research as research
from contracts.runs.support_research import read_artifact,StageVerifier,SupportCompletion
from contracts.runs.coverage_v2 import StageLedgerV2
import services.foundation.protocol as protocol
from services.foundation.protocol import project_protocol
from support_archive_fixtures import START,history,record
from test_support_archive import SupportFixture


def unmemoized_projection():
    """Restore only the prior reduced_ref expression; static evidence binds
    this complete function AST to the exact accepted 08c/f847 implementation.
    No Git process, duplicate reducer, generator or numerical engine in tests.
    """
    tree=ast.parse(inspect.getsource(project_protocol));function=tree.body[0]
    function.body=[n for n in function.body if not (isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='reduced_digests' for t in n.targets))]
    ref=next(n for n in function.body if isinstance(n,ast.FunctionDef) and n.name=='reduced_ref')
    ref.body=[ref.body[0],ast.parse('return dict(record_id=record.record_id,projection_sha256=sha(reduce(record)))').body[0]]
    namespace=dict(vars(protocol))
    exec(compile(ast.fix_missing_locations(tree),'<accepted-unmemoized-projection>','exec'),namespace)
    return namespace['project_protocol']


def projection_observation(function,full,day,*,family='support',proof=None,fault=None):
    """Count real reduced-value SHA calls, preserving actual resolver/proof work.
    Faults inject only at a real resolve boundary AFTER a digest is warmed;
    the original resolver performs every negative decision, not a fake engine.
    """
    counts=Counter();payloads={};trace=[];injected=[];other_hashes=[]
    raw_sha=protocol.sha;raw_resolve=evidence.resolve
    def counted(value):
        if isinstance(value,dict) and 'record_schema' in value:
            identifier=value['record_id'];raw=canonical(value)
            if identifier in payloads:assert payloads[identifier]==raw,'completed reduced value changed'
            payloads[identifier]=raw;counts[identifier]+=1
        else:other_hashes.append(canonical(value))
        return raw_sha(value)
    def resolved(source,ref,kinds=None,**kwargs):
        if fault and counts['decision'] and ref.record_id=='decision' and not injected:
            injected.append(fault)
            target=next(r for r in source.records if r.record_id==ref.record_id)
            if fault=='hash':ref=ref.model_copy(update={'payload_sha256':'0'*64})
            elif fault=='type':kinds={'patient'}
            elif fault=='causal_cutoff':kwargs['cutoff']=target.cutoff
            elif fault=='stale':
                changed=target.model_copy(update={'available_at':kwargs['cutoff'],'recorded_at':kwargs['cutoff']})
                source=source.model_copy(update={'records':[changed if r.record_id==target.record_id else r for r in source.records]})
                ref=exact_ref(changed)
            elif fault in ('corrected','retracted'):
                if fault=='corrected':
                    changed=target.model_copy(update={'record_id':'decision-correction','revision':2,
                        'supersedes':target.record_id,'record_status':'corrected',
                        'available_at':START+timedelta(seconds=1),'recorded_at':START+timedelta(seconds=1)})
                    source=source.model_copy(update={'records':[*source.records,changed]})
                else:
                    changed=target.model_copy(update={'record_status':'retracted'})
                    source=source.model_copy(update={'records':[changed if r.record_id==target.record_id else r for r in source.records]})
                    ref=exact_ref(changed)
            elif fault=='patient':
                changed=target.model_copy(update={'patient_id':'FOREIGN-STRUCTURAL'})
                source=source.model_copy(update={'records':[changed if r.record_id==target.record_id else r for r in source.records]})
                ref=exact_ref(changed)
            else:raise AssertionError('unknown test fault')
        trace.append(('resolve',ref.model_dump(mode='json'),sorted(kinds) if kinds else None,
            kwargs.get('cutoff').isoformat() if kwargs.get('cutoff') else None,kwargs.get('inclusive',False)))
        return raw_resolve(source,ref,kinds,**kwargs)
    def closure(ref,at):
        trace.append(('closure',ref.model_dump(mode='json'),at.isoformat()))
        return proof(ref,at)
    with ExitStack() as stack:
        for module in (protocol,evidence,research):stack.enter_context(patch.object(module,'resolve',resolved))
        stack.enter_context(patch.dict(function.__globals__,sha=counted,resolve=resolved))
        try:
            result=function(full,START+timedelta(days=day),family=family,origin=START,
                verify_closure=closure if proof else None)
            outcome=('ok',canonical(result.model_dump(mode='json')))
        except ValueError as error:outcome=('error',str(error))
    return dict(outcome=outcome,counts=counts,payloads=payloads,trace=trace,injected=injected,other_hashes=other_hashes)


class ArtifactAncestryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.path=self.root/'nested'/'proof.json'
        self.path.parent.mkdir();self.path.write_bytes(b'{}')
        self.artifact=Artifact(id='scalar-proof',path='nested/proof.json',sha256=sha256(b'{}'),bytes=2,
            role='observed',media_type='application/json')

    def tearDown(self):self.temp.cleanup()

    def test_ordinary_nested_read_rechecks_changed_bytes_and_size(self):
        self.assertEqual(read_artifact(self.root,self.artifact),b'{}')
        self.path.write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError,'hash_or_size'):read_artifact(self.root,self.artifact)
        self.path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'hash_or_size'):
            read_artifact(self.root,self.artifact.model_copy(update={'bytes':3}))

    def test_link_and_reparse_metadata_at_leaf_parent_root_and_ancestor(self):
        real_lstat=Path.lstat
        # Inject filesystem metadata at its boundary so Windows privilege and
        # host filesystem do not hide either POSIX links or Windows reparses.
        for target in (self.path,self.path.parent,self.root,self.root.parent):
            for link in (True,False):
                with self.subTest(target=str(target),symlink=link):
                    def metadata(path,*args,**kwargs):
                        if path==target:
                            return SimpleNamespace(st_mode=stat.S_IFLNK if link else stat.S_IFDIR,
                                st_file_attributes=0 if link else stat.FILE_ATTRIBUTE_REPARSE_POINT)
                        return real_lstat(path,*args,**kwargs)
                    with patch.object(Path,'lstat',metadata):
                        with self.assertRaisesRegex(ValueError,'symlink_support_artifact_denied'):
                            read_artifact(self.root,self.artifact)

    def test_missing_directory_hardlink_and_escape_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'unreadable'):
            read_artifact(self.root,self.artifact.model_copy(update={'path':'absent.json'}))
        with self.assertRaisesRegex(ValueError,'ordinary_unlinked'):
            read_artifact(self.root,self.artifact.model_copy(update={'path':'nested'}))
        import os
        alias=self.root/'alias.json';os.link(self.path,alias)
        with self.assertRaisesRegex(ValueError,'ordinary_unlinked'):read_artifact(self.root,self.artifact)
        alias.unlink()
        (self.root/'outside.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'support_artifact_escape'):
            read_artifact(self.path.parent,self.artifact.model_copy(update={'path':'../outside.json'}))


class S1IntakeSourceTests(SupportFixture):
    def structural(self,mode):
        trajectory=next(t for t in self.package[2].descriptor.trajectories if t.mode==mode)
        full=self.verified.histories[trajectory.partition_id];index=self.package[2].descriptor
        ledgers=[StageLedgerV2.model_validate_json(canonical(r)) for r in json.loads(read_artifact(self.package[1],trajectory.stage_ledgers))]
        completions=[SupportCompletion.model_validate_json(canonical(r)) for r in json.loads(read_artifact(self.package[1],trajectory.completions))]
        proof=StageVerifier(full,ledgers,completions,self.package[1],run_id=index.run_id,partition_id=trajectory.partition_id,
            source_commit=index.source_commit,runtime=index.runtime,frozen_plan_sha256=index.frozen_plan_sha256)
        return full,proof

    def assert_equivalent(self,before,after):
        for name in ('outcome','payloads','trace','injected','other_hashes'):
            self.assertEqual(before[name],after[name],name)
        self.assertEqual(set(before['counts']),set(after['counts']))

    def test_reduced_digest_full_artifacts_shared_recursion_work_and_order_all_cuts(self):
        baseline=unmemoized_projection();measurements=[]
        for mode in ('S0','S1'):
            full,proof=self.structural(mode)
            for day in (14,42,84):
                with self.subTest(mode=mode,day=day):
                    before=projection_observation(baseline,full,day,proof=proof)
                    after=projection_observation(project_protocol,full,day,proof=proof)
                    self.assert_equivalent(before,after);self.assertEqual(after['outcome'][0],'ok')
                    self.assertGreater(before['counts']['decision'],1)
                    self.assertGreater(before['counts']['assignment'],1)
                    self.assertEqual(set(after['counts'].values()),{1})
                    self.assertGreater(sum(before['counts'].values()),sum(after['counts'].values()))
                    self.assertTrue(any(row[0]=='closure' for row in after['trace']))
                    measurements.append(dict(mode=mode,cut=day,old=sum(before['counts'].values()),
                        new=sum(after['counts'].values()),per_id_old=dict(sorted(before['counts'].items())),
                        resolve_and_closure_events=len(after['trace']),canonical_sha256=sha256(after['outcome'][1])))
        print('REDUCED_DIGEST_STRUCTURAL_WORK '+json.dumps(measurements,sort_keys=True))

    def test_nof1_existing_snapshot_construction_without_generator(self):
        # Reuse the existing real typed snapshot fixture functions by AST, as
        # the full fixture module imports the forbidden scientific generator.
        # Its unneeded generator base is replaced only by ordinary audited
        # reports from this existing structural fixture, not a numeric engine.
        from services.foundation.workflow import record_header,state_for,SUPPORT
        full,_=self.structural('S0')
        observations=[r for r in full.records if r.kind=='daily_report']
        for day in range(0,85,14):
            end=START+timedelta(days=day,hours=-1)
            isi=record(full.patient_id,'n-isi-'+str(day),end+timedelta(minutes=59),'isi',
                instrument_version='ISI-7-synthetic-14d-v1',recall_days=14,
                recall_start=(end-timedelta(days=14)).isoformat(),recall_end=end.isoformat(),items=[2]*7)
            observations.append(isi.model_copy(update={'source':isi.source.model_copy(update={
                'id':protocol.LAW,'version':'2.0.0','adapter':'simulation'})}))
        namespace=dict(copy=copy,RECORD_ADAPTER_V21=RECORD_ADAPTER_V21,canonical=protocol.canonical,
            sha=protocol.sha,reference=reference,exact_ref=exact_ref,timedelta=timedelta,ORIGIN=START,PATIENT=full.patient_id,
            record_header=record_header,state_for=state_for,SUPPORT=SUPPORT,PROTOCOL_REFS=PROTOCOL_REFS,
            full_history=lambda **kwargs:history(full.patient_id,observations),
            history=lambda records:history(full.patient_id,records))
        source=(Path(__file__).resolve().parents[2]/'protocol_fixtures.py').read_text(encoding='utf-8')
        definitions=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('typed','snapshot_history')]
        self.assertEqual(len(definitions),2)
        exec(compile(ast.Module(body=definitions,type_ignores=[]),'<existing-scalar-nof1-snapshot>','exec'),namespace)
        fixture=namespace['snapshot_history']()
        for day in (14,42,84):
            before=projection_observation(unmemoized_projection(),fixture,day,family='nof1_med')
            after=projection_observation(project_protocol,fixture,day,family='nof1_med')
            self.assert_equivalent(before,after);self.assertEqual(after['outcome'][0],'ok',after['outcome'])
            self.assertEqual(set(after['counts'].values()),{1})

    def test_warmed_digest_never_bypasses_exact_authority_rejections(self):
        full,proof=self.structural('S1')
        expected=dict(hash='exact_dependency_hash_patient_type_mismatch',type='exact_dependency_hash_patient_type_mismatch',
            patient='exact_dependency_hash_patient_type_mismatch',stale='stale_or_not_visible_dependency',
            corrected='stale_or_not_visible_dependency',retracted='retracted_dependency',causal_cutoff='stale_or_not_visible_dependency')
        for fault,error in expected.items():
            with self.subTest(fault=fault):
                before=projection_observation(unmemoized_projection(),full,14,proof=proof,fault=fault)
                after=projection_observation(project_protocol,full,14,proof=proof,fault=fault)
                self.assert_equivalent(before,after)
                self.assertEqual(after['injected'],[fault]);self.assertEqual(after['counts']['decision'],1)
                self.assertEqual(after['outcome'],('error',error))

    def test_maps_are_fresh_between_repeated_calls_and_source_mutation(self):
        full,proof=self.structural('S1')
        first=projection_observation(project_protocol,full,14,proof=proof)
        second=projection_observation(project_protocol,full,14,proof=proof)
        self.assertEqual(first,second);self.assertTrue(second['counts'])
        report=next(r for r in full.records if r.record_id=='report')
        # Mutate the real typed source between calls. The next full exact hash
        # validation must fail instead of accepting a digest from the first.
        changed=report.model_copy(update={'sleep_quality':7.})
        edited=history(full.patient_id,[changed if r.record_id==report.record_id else r for r in full.records])
        before=projection_observation(unmemoized_projection(),edited,14,proof=proof)
        after=projection_observation(project_protocol,edited,14,proof=proof)
        self.assert_equivalent(before,after)
        self.assertEqual(after['outcome'],('error','exact_dependency_hash_patient_type_mismatch'))

    def test_warmed_ref_keeps_membership_reduction_cycle_and_fresh_dict_guards(self):
        # Exercise the actual nested functions at their internal state boundary.
        # Force the existing cycle guard after warming; no need to invent a
        # cryptographic self-referential source payload or bypass a resolver.
        full=self.context_history('S0');record=next(r for r in full.records if r.kind=='consent')
        tree=ast.parse(inspect.getsource(project_protocol)).body[0]
        definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('reduce','reduced_ref')]
        namespace=dict(vars(protocol),records={record.record_id:record},cache={},visiting=set(),
            reduced_digests={},full=full,cutoff=START+timedelta(days=14))
        exec(compile(ast.Module(body=definitions,type_ignores=[]),'<actual-nested-reducer-guards>','exec'),namespace)
        call=namespace['reduced_ref'];digest=namespace['reduced_digests']
        first=call(record);second=call(record)
        self.assertIsNot(first,second);first['projection_sha256']='0'*64
        self.assertNotEqual(first,call(record));self.assertEqual(len(digest),1)
        namespace['cache'].clear();namespace['visiting'].add(record.record_id)
        with self.assertRaisesRegex(ValueError,'^cyclic_protocol_dependency$'):call(record)
        namespace['records'].clear()
        with self.assertRaisesRegex(ValueError,'^unsupported_protocol_conditioning_reference$'):call(record)

    def test_failed_digest_is_not_published(self):
        full=self.context_history('S0');record=next(r for r in full.records if r.kind=='consent')
        tree=ast.parse(inspect.getsource(project_protocol)).body[0]
        definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('reduce','reduced_ref')]
        namespace=dict(vars(protocol),records={record.record_id:record},cache={},visiting=set(),
            reduced_digests={},full=full,cutoff=START+timedelta(days=14))
        exec(compile(ast.Module(body=definitions,type_ignores=[]),'<actual-digest-failure-boundary>','exec'),namespace)
        with patch.dict(namespace,sha=lambda value:(_ for _ in ()).throw(ValueError('scalar hash fault'))):
            with self.assertRaisesRegex(ValueError,'^scalar hash fault$'):namespace['reduced_ref'](record)
        self.assertEqual(namespace['reduced_digests'],{})
        self.assertEqual(namespace['reduced_ref'](record)['projection_sha256'],protocol.sha(namespace['cache'][record.record_id]))

    def context_history(self,mode):
        trajectory=next(t for t in self.package[2].descriptor.trajectories if t.mode==mode)
        original=self.verified.histories[trajectory.partition_id]
        records=[r for r in original.records if r.kind not in {'support_stage_closure','support_outcome_link'}]
        isi=record(original.patient_id,'context-isi',START-timedelta(minutes=1),'isi',
            instrument_version='ISI-fixture',recall_days=14,recall_start=(START-timedelta(days=14,minutes=1)).isoformat(),
            recall_end=(START-timedelta(minutes=1)).isoformat(),items=[0]*7)
        records.append(isi)
        full=history(original.patient_id,records)
        decision=next(r for r in full.records if r.kind=='support_decision')
        consent=next(r for r in full.records if r.kind=='consent')
        changed=decision.model_copy(update={'context':[exact_ref(consent),exact_ref(isi)],
            'context_projection_sha256':projection_hash(full,decision.cutoff)})
        return history(full.patient_id,[changed if r.record_id==decision.record_id else r for r in full.records])

    def project(self,full,day=14):
        return project_protocol(full,START+timedelta(days=day),family='support',origin=START)

    def test_selected_and_omitted_context_positive_at_all_three_cuts(self):
        for mode in ('S0','S1'):
            full=self.context_history(mode)
            for day in (14,42,84):
                with self.subTest(mode=mode,day=day):
                    value=self.project(full,day)
                    decision=next(r for r in value.records if r.kind=='support_decision')
                    self.assertEqual([r.record_id for r in decision.context],['consent'])
                    self.assertFalse(any(r.kind=='isi' for r in value.records))
                    consent=next(r for r in value.records if r.record_id=='consent')
                    self.assertEqual(decision.context[0].projection_sha256,sha256(canonical(consent.model_dump(mode='json'))))

    def test_bad_exact_hash_rejected_for_selected_and_omitted_context(self):
        for mode in ('S0','S1'):
            for identifier in ('consent','context-isi'):
                full=self.context_history(mode)
                decision=next(r for r in full.records if r.kind=='support_decision')
                refs=[r.model_copy(update={'payload_sha256':'0'*64}) if r.record_id==identifier else r for r in decision.context]
                changed=decision.model_copy(update={'context':refs})
                full=history(full.patient_id,[changed if r.record_id==decision.record_id else r for r in full.records])
                with self.subTest(mode=mode,identifier=identifier):
                    before=projection_observation(unmemoized_projection(),full,14)
                    after=projection_observation(project_protocol,full,14)
                    self.assert_equivalent(before,after)
                    self.assertEqual(after['outcome'],('error','exact_dependency_hash_patient_type_mismatch'))
                    if mode=='S0':self.assertEqual(after['counts']['consent'],1)

    def test_omitted_context_strict_causal_cutoff_and_later_correction(self):
        full=self.context_history('S1')
        isi=next(r for r in full.records if r.kind=='isi')
        decision=next(r for r in full.records if r.kind=='support_decision')
        late=isi.model_copy(update={'recorded_at':START,'available_at':START})
        changed=history(full.patient_id,[late if r.record_id==isi.record_id else r for r in full.records])
        rebound=decision.model_copy(update={'context':[exact_ref(late) if r.record_id==isi.record_id else r for r in decision.context],
            'context_projection_sha256':projection_hash(changed,START)})
        changed=history(full.patient_id,[rebound if r.record_id==decision.record_id else r for r in changed.records])
        with self.assertRaisesRegex(ValueError,'stale_or_not_visible_dependency'):self.project(changed)
        for status in ('corrected','retracted'):
            corrected=isi.model_copy(update={'record_id':'isi-correction','revision':2,'supersedes':isi.record_id,
                'record_status':status,'recorded_at':START+timedelta(seconds=1),'available_at':START+timedelta(seconds=1)})
            with self.subTest(status=status),self.assertRaisesRegex(ValueError,'stale_or_not_visible_dependency'):
                self.project(history(full.patient_id,[*full.records,corrected]))

    def test_context_mutation_between_projections_is_not_cached(self):
        full=self.context_history('S1');self.project(full)
        isi=next(r for r in full.records if r.kind=='isi')
        isi.items[0]=1
        with self.assertRaisesRegex(ValueError,'support_context_full_audit_projection_mismatch'):self.project(full)


if __name__=='__main__':unittest.main()
