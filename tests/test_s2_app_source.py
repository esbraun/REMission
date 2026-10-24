"""Finite inert source fixtures, never genuine histories/receipts/fit products.

Execute the actual new adapter AST without importing services or Store. Only
the history I/O seam is replaced with existing labeled scalar public fixtures;
ownership, metadata export, s2_data.prepare, contracts and SQL decisions run.
"""
import ast
import copy
from datetime import timedelta
import importlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from contracts.domain.analysis import canonical, reference, sha
from contracts.domain.entities import Consent
from contracts.domain.protocol import LAW_REF, SUPPORT_REF
from contracts.domain.support_s2 import CONFIG_REF as PREDICT_CONFIG, DEFINITIONS as PREDICT_DEFS, HSTAR_REF
from contracts.domain.support_s2_app import *
from s2_model_fixtures import cohort, ORIGIN

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'services/foundation/support_s2_analysis.py'
NOW = ORIGIN+timedelta(days=300)
CURRENT = dict(account_id='UNIT-owner',token_hash='inert-session-hash-not-a-real-session')
COMMIT = '1'*40


def namespace():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    ns = dict(__name__='inert_actual_s2_adapter_source')
    exec(compile(tree,str(SOURCE),'exec'), ns)
    ns['public_history'] = lambda db, patient: SimpleNamespace(records=db.full[patient])
    ns['public_histories'] = lambda db, owner, ids, cutoff: tuple(db.histories[i] for i in ids)
    return ns


def consent(patient):
    return Consent.model_validate(dict(schema_version='1.0.0',synthetic=True,record_id=patient+'-live-consent',
        patient_id=patient,event_at=ORIGIN,recorded_at=ORIGIN,available_at=ORIGIN,
        source=dict(id='UNIT-public-consent',version='1.0.0',adapter='research_configuration',raw_sha256='0'*64),
        lineage_id=patient+'-live-consent',revision=1,supersedes=None,duplicate_of=None,record_status='active',kind='consent',
        component='mrt_bandit',consent_version='UNIT-1',oversight_version='UNIT-1',consent_status='active',
        oversight_status='approved_synthetic',effective_at=ORIGIN,expires_at=None,withdrawn_at=None))


class Cursor(list):
    def fetchone(self):return self[0] if self else None
    def fetchall(self):return list(self)


class InertDB:
    """Exact finite SQL seam; unknown SQL fails, no database/SQLite backend."""
    def __init__(self):
        self.patients={}
        self.full={}
        self.histories={}
        self.receipts=[]
        self.attempts=[]
        self.pending=[]
        self.writes=[]
        self.control=dict(database_instance_id='UNIT-store',authority_generation=1,enabled=True)
        for i in range(12):
            patient=f'UNIT-S2-{i:02}'
            state=dict(workflow=dict(hold_reasons=[],clinical='treatment_active',support_mode='mrt'),
                simulation=dict(law=LAW_REF,protocol=SUPPORT_REF,law_version=LAW_REF['id'],family='support',
                    panel_id='UNIT-generation',origin=ORIGIN.isoformat(),day=0,research_run_id=None))
            self.patients[patient]=dict(id=patient,owner_id=CURRENT['account_id'],version=1,cutoff=ORIGIN.isoformat(),state_json=canonical(state))
            self.full[patient]=[consent(patient)]
    def execute(self, sql, args=()):
        if sql.startswith('SELECT database_instance_id,authority_generation,enabled'):
            return Cursor([self.control])
        if sql.startswith('SELECT * FROM patients WHERE id=? AND owner_id=?'):
            row=self.patients.get(args[0]);return Cursor([row] if row and row['owner_id']==args[1] else [])
        if sql.startswith('SELECT id FROM patients WHERE owner_id=?'):
            return Cursor([dict(id=p['id']) for p in sorted(self.patients.values(),key=lambda x:x['id'])
                if p['owner_id']==args[0] and json.loads(p['state_json'])['simulation']['panel_id']==args[1]])
        if sql.startswith('SELECT * FROM receipts WHERE owner_id=? AND key=?'):
            return Cursor([r for r in self.receipts if r['owner_id']==args[0] and r['key']==args[1]])
        if sql.startswith('SELECT 1 FROM receipts WHERE owner_id=? AND scope=?'):
            return Cursor([r for r in self.receipts if r['owner_id']==args[0] and r['scope']==args[1]])
        if sql=='INSERT INTO receipts VALUES(?,?,?,?,?,?)':
            self.writes.append('receipt')
            self.receipts.append(dict(zip(('owner_id','session_hash','key','scope','payload_sha256','response'),args)))
            return Cursor()
        if sql.startswith('SELECT * FROM analysis_attempts WHERE owner_id=? AND json_extract'):
            return Cursor([r for r in self.attempts if r['owner_id']==args[0] and json.loads(r['request_json'])['kind']=='poc_support_s2_app_fit_input'])
        if sql.startswith('SELECT job_id,cohort_json FROM analysis_attempts'):
            return Cursor([r for r in self.attempts if r['status'] in ('queued','running')])
        if sql.startswith('SELECT job_id,status FROM analysis_attempts'):
            return Cursor([dict(job_id=r['job_id'],status=r['status']) for r in self.attempts if r['status'] in ('queued','running')])
        if sql.startswith('SELECT * FROM analysis_attempts WHERE job_id=?'):
            return Cursor([r for r in self.attempts if r['job_id']==args[0] and (len(args)==1 or r['owner_id']==args[1])])
        if sql.startswith('SELECT * FROM analysis_attempts WHERE owner_id=? AND job_id=?'):
            return Cursor([r for r in self.attempts if r['owner_id']==args[0] and r['job_id']==args[1]])
        if sql=='INSERT INTO pending_work VALUES(?,?,?,?)':
            self.writes.append('pending');self.pending.append(args);return Cursor()
        if sql.startswith('INSERT INTO analysis_attempts('):
            self.writes.append('attempt')
            names=sql.split('(',1)[1].split(')',1)[0].split(',')
            self.attempts.append(dict(zip(names,args),claim_token=None,started_at=None,result_json=None,finished_at=None))
            return Cursor()
        raise AssertionError('unhandled inert SQL: '+sql)
    def advance(self,day=14,**fixture_options):
        self.histories={h.patient_id:h for h in cohort(day,**fixture_options)}
        for p in self.patients.values():
            state=json.loads(p['state_json']);state['simulation']['day']=day
            p.update(version=day+1,cutoff=(ORIGIN+timedelta(days=day)).isoformat(),state_json=canonical(state))


def selection(db):
    return dict(schema_version='s2-app-source-1.0.0',target_id='UNIT-S2-07',cohort_id='UNIT-predeclared12',
        members=[dict(patient_id=p,patient_version=db.patients[p]['version']) for p in sorted(db.patients)],configuration=CONFIG_REF)


def exported(ns,db,day=14,**options):
    ns['select'](db,CURRENT,'UNIT-selection-key',selection(db),now=NOW)
    db.advance(day,**options)
    members=selection(db)['members']
    return ns['export'](db,CURRENT['account_id'],'UNIT-selection-key',members,ORIGIN+timedelta(days=day),source_commit=COMMIT)


def submission(export):
    return S2Submission.model_validate_json(canonical(dict(schema_version='s2-app-source-1.0.0',kind='support_s2_fit_submission',selection_key='UNIT-selection-key',
        members=[dict(patient_id=m.patient_id,patient_version=m.patient_version) for m in export.provenance.members],
        cutoff=export.provenance.cutoff.isoformat(),approved_export=export.reference.model_dump(),configuration=CONFIG_REF))).model_dump(mode='json')


def seed(export,job='UNIT-inert-fit-attempt',replicate=112233,process=INITIAL_PROCESS):
    key=dict(namespace='fit',protocol=SUPPORT_REF['id'],scenario=job,replicate=replicate,
        patient=export.provenance.target_id,time_index=export.provenance.cutoff_day,process=process)
    return dict(record_id=job+'-seed-record',attempt_id=job,owner_id=export.provenance.owner_id,created_at=NOW.isoformat(),
        policy=SEED_POLICY_REF,key=key,sampler_seed=int(sha(key)[:8],16)%2147483647)


def fit_input(export):
    return S2FitInput.model_validate_json(canonical(dict(schema_version='s2-app-source-1.0.0',kind='poc_support_s2_app_fit_input',
        purpose=FIT_PURPOSE,attempt_id='UNIT-inert-fit-attempt',export=export.model_dump(mode='json'),seed_record=seed(export),
        configuration=CONFIG_REF,posterior_schema=POSTERIOR_SCHEMA_REF,executable=False)))


class TrustedExportTests(unittest.TestCase):
    def setUp(self):self.ns=namespace();self.db=InertDB()
    def test_actual_adapter_complete12_day14_day28_and_nonfirst_anchor(self):
        for day in (14,28):
            db=InertDB();product=exported(self.ns,db,day,target_missing=True)
            self.assertEqual(product.provenance.target_id,'UNIT-S2-07')
            self.assertEqual(len(product.histories),12)
            self.assertEqual(product.provenance.cutoff_day,day)
            self.assertTrue(product.counts[7].prior_hierarchy_only)
            self.assertEqual(product.reference.model_dump(),reference('poc-support-s2-trusted-export-v1',product.model_dump(mode='json',exclude={'reference'})))
            self.assertEqual(db.writes,['receipt'])
    def test_day0_explicit_selection_original_receipt_is_idempotent_across_session(self):
        payload=selection(self.db)
        first=self.ns['select'](self.db,CURRENT,'UNIT-key',payload,now=NOW)
        self.db.advance()
        again=self.ns['select'](self.db,dict(CURRENT,token_hash='inert-new-session'), 'UNIT-key',payload,now=NOW)
        self.assertEqual(first,again);self.assertEqual(len(self.db.receipts),1)
        self.assertEqual(first['selected_at'],ORIGIN.isoformat().replace('+00:00','Z'))
    def test_postoutcome_target_selection_and_second_anchor_rejected(self):
        self.db.advance()
        with self.assertRaisesRegex(ValueError,'day0'):self.ns['select'](self.db,CURRENT,'late',selection(self.db),now=NOW)
        db=InertDB();payload=selection(db);self.ns['select'](db,CURRENT,'first',payload,now=NOW)
        payload['target_id']='UNIT-S2-08'
        with self.assertRaisesRegex(ValueError,'already_has'):self.ns['select'](db,CURRENT,'second',payload,now=NOW)
        with self.assertRaisesRegex(ValueError,'conflict'):self.ns['select'](db,CURRENT,'first',payload,now=NOW)
    def test_foreign_stale_held_consent_wrongfamily_panel_and_extra_peer_reject(self):
        mutations=[lambda db:db.patients['UNIT-S2-11'].update(owner_id='UNIT-foreign'),
            lambda db:db.patients['UNIT-S2-11'].update(version=2),
            lambda db:self.state(db,'UNIT-S2-11',workflow=dict(hold_reasons=['UNIT-hold'],clinical='clinical_hold',support_mode='paused')),
            lambda db:db.full.update({'UNIT-S2-11':[]}),
            lambda db:self.simulation(db,family='nof1_med'),lambda db:self.simulation(db,panel_id='UNIT-other'),
            lambda db:db.patients.update({'UNIT-extra':dict(db.patients['UNIT-S2-11'],id='UNIT-extra')})]
        for mutation in mutations:
            db=InertDB();payload=selection(db);mutation(db)
            with self.subTest(mutation=mutations.index(mutation)),self.assertRaises(ValueError):self.ns['select'](db,CURRENT,'UNIT-key',payload,now=NOW)
            self.assertFalse(db.writes)
    @staticmethod
    def state(db,patient,**changes):
        state=json.loads(db.patients[patient]['state_json']);state.update(changes);db.patients[patient]['state_json']=canonical(state)
    @staticmethod
    def simulation(db,**changes):
        p=db.patients['UNIT-S2-11'];s=json.loads(p['state_json']);s['simulation'].update(changes);p['state_json']=canonical(s)
    def test_missing_extra_duplicate_reordered_members_rejected_by_contract(self):
        for transform in (lambda x:x[:-1],lambda x:x+[x[-1]],lambda x:x[:-1]+[x[0]],lambda x:list(reversed(x))):
            payload=selection(self.db);payload['members']=transform(payload['members'])
            with self.assertRaises(ValidationError):S2Selection.model_validate_json(canonical(payload))
    def test_selection_receipt_owner_store_generation_and_payload_tampering_reject(self):
        self.ns['select'](self.db,CURRENT,'UNIT-key',selection(self.db),now=NOW)
        original=copy.deepcopy(self.db.receipts[0])
        for field,value in [('owner_id','UNIT-foreign'),('generation_id','UNIT-other'),('store_id','UNIT-other')]:
            row=copy.deepcopy(original);payload=json.loads(row['response']);payload[field]=value;row['response']=canonical(payload)
            self.db.receipts=[row]
            with self.assertRaises(ValueError):self.ns['selected'](self.db,CURRENT['account_id'],'UNIT-key')
        self.db.receipts=[original];self.db.control['authority_generation']=2
        with self.assertRaisesRegex(ValueError,'authority_changed'):self.ns['selected'](self.db,CURRENT['account_id'],'UNIT-key')
    def test_unknown_selection_never_resubmits(self):
        with self.assertRaisesRegex(ValueError,'unknown'):self.ns['selected'](self.db,CURRENT['account_id'],'missing')
        self.assertEqual(self.db.writes,[])
    def test_actual_adapter_rejects_held_bad_context_wrong_outcome_or_no_observation(self):
        for change in (dict(held=3),dict(bad_probability=3),dict(bad_window=3),dict(missing_feature=3),dict(correction=3)):
            db=InertDB()
            with self.subTest(change=change),self.assertRaises(ValueError):exported(self.ns,db,member_change=change)
        with self.assertRaises(ValueError):exported(self.ns,InertDB(),all_missing=True)
    def test_latest_withdrawal_expiry_oversight_and_unknown_current_mode_refuse(self):
        for change in ('withdrawn','expired','oversight','unknown_mode'):
            db=InertDB()
            if change=='unknown_mode':self.state(db,'UNIT-S2-11',workflow=dict(hold_reasons=[],clinical='treatment_active'))
            else:
                old=db.full['UNIT-S2-11'][0]
                data=old.model_dump()
                data.update(record_id='ZZ-UNIT-new-'+change,lineage_id='ZZ-UNIT-lineage-'+change)
                if change=='withdrawn':data.update(consent_status='withdrawn',withdrawn_at=ORIGIN)
                if change=='expired':data.update(consent_status='expired')
                if change=='oversight':data.update(oversight_status='pending')
                db.full['UNIT-S2-11'].append(Consent.model_validate(data))
            with self.subTest(change=change),self.assertRaises(ValueError):self.ns['select'](db,CURRENT,'key',selection(db),now=NOW)
    def test_day0_clock_does_not_authorize_selection_after_recorded_outcome(self):
        self.db.full['UNIT-S2-11'].append(next(r for r in cohort()[11].records if r.kind=='daily_report'))
        with self.assertRaisesRegex(ValueError,'recorded_support_outcomes'):self.ns['select'](self.db,CURRENT,'key',selection(self.db),now=NOW)
    def test_changed_hstar_counts_projection_and_refs_cannot_be_rehashed_into_admission(self):
        product=exported(self.ns,self.db)
        for change in ('counts','contributions','history','member','projection'):
            value=product.model_dump(mode='json')
            if change=='counts':value['counts'][0]['observed'][0]+=1
            elif change=='contributions':value['contribution_sha256']='f'*64
            elif change=='history':value['histories'][0]['patient_id']='UNIT-foreign'
            elif change=='member':value['provenance']['members'][0]['history_sha256']='f'*64
            else:
                value['provenance']['members'][0]['source_projection_sha256']='f'*64
                value['provenance']['membership_sha256']=sha(value['provenance']['members'])
            value['reference']=reference('poc-support-s2-trusted-export-v1',{k:v for k,v in value.items() if k!='reference'})
            with self.subTest(change=change),self.assertRaises(ValueError):S2Export.model_validate_json(canonical(value))
    def test_equal_cutoff_public_record_cannot_cross_strict_export_boundary(self):
        product=exported(self.ns,self.db)
        h=self.db.histories['UNIT-S2-11'];records=list(h.records)
        index=next(i for i,r in enumerate(records) if r.kind=='daily_report')
        records[index]=records[index].model_copy(update=dict(available_at=product.provenance.cutoff))
        self.db.histories[h.patient_id]=h.model_copy(update=dict(records=records))
        with self.assertRaises(ValueError):self.ns['export'](self.db,CURRENT['account_id'],'UNIT-selection-key',submission(product)['members'],product.provenance.cutoff,source_commit=COMMIT)
    def test_ordinary_advancement_preserves_fitted_evidence_but_correction_does_not(self):
        product=exported(self.ns,self.db);fit=fit_input(product);row=row_for(fit)
        for p in self.db.patients.values():p.update(version=p['version']+1,cutoff=(ORIGIN+timedelta(days=15)).isoformat())
        self.assertEqual(self.ns['revalidate'](self.db,row,'UNIT-selection-key',source_commit=COMMIT),fit)
        original=self.db.full['UNIT-S2-11'][0]
        corrected=Consent.model_validate(dict(original.model_dump(),record_id='UNIT-later-correction',revision=2,
            supersedes=original.record_id,recorded_at=ORIGIN+timedelta(days=14,hours=1),available_at=ORIGIN+timedelta(days=14,hours=1)))
        self.db.full['UNIT-S2-11'].append(corrected)
        with self.assertRaisesRegex(ValueError,'corrected_fitted'):self.ns['revalidate'](self.db,row,'UNIT-selection-key',source_commit=COMMIT)
    def test_unknown_source_and_wrong_cutoff_or_versions_refuse_export(self):
        product=exported(self.ns,self.db);members=submission(product)['members']
        for source,cutoff,roster in [(None,product.provenance.cutoff,members),(COMMIT,ORIGIN+timedelta(days=13),members),
                (COMMIT,product.provenance.cutoff,[dict(m,patient_version=999) for m in members])]:
            with self.assertRaises(ValueError):self.ns['export'](self.db,CURRENT['account_id'],'UNIT-selection-key',roster,cutoff,source_commit=source)


def row_for(fit):
    p=fit.export.provenance
    return dict(job_id=fit.attempt_id,patient_id=p.target_id,owner_id=p.owner_id,previous_attempt=None,
        request_json=fit.model_dump_json(),input_sha256=sha(fit.model_dump(mode='json')),history_sha256=p.histories_sha256,
        cutoff=p.cutoff.isoformat(),configuration_json=canonical(CONFIG_REF),cohort_json=canonical([m.patient_id for m in p.members]),
        status='queued',stage='queued',claim_token=None,started_at=None)


class OrdinaryJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns=namespace();cls.db=InertDB();cls.export=exported(cls.ns,cls.db);cls.fit=fit_input(cls.export)
    def test_submission_defaultoff_before_entropy_job_or_persistence(self):
        db=copy.deepcopy(self.db);ns=namespace()
        with patch.object(ns['secrets'],'randbelow',side_effect=AssertionError('no seed before qualification')), \
                patch.object(ns['uuid'],'uuid4',side_effect=AssertionError('no invented attempt in PREP')):
            with self.assertRaisesRegex(ValueError,'not_qualified'):ns['submit'](db,CURRENT,'fit-key',submission(self.export),now=NOW,source_commit=COMMIT)
        self.assertEqual(db.writes,['receipt']);self.assertFalse(db.attempts or db.pending)
    def test_rehashed_different_approved_export_refuses_before_dispatch(self):
        payload=submission(self.export);payload['approved_export']=dict(payload['approved_export'],sha256='f'*64)
        with self.assertRaisesRegex(ValueError,'approved_S2_export_changed'):self.ns['submit'](copy.deepcopy(self.db),CURRENT,'fit-key',payload,now=NOW,source_commit=COMMIT)
    def test_inert_test_only_gate_replacement_exercises_actual_atomic_insert_and_real_anchor(self):
        db=copy.deepcopy(self.db);ns=namespace();ns['require_executable']=lambda p:None
        # Deliberately inert test of unreachable persistence branch, not an
        # executable configuration/queue receipt or actual app seed record.
        fake_uuid=SimpleNamespace(hex='unit'+'2'*28)
        with patch.object(ns['uuid'],'uuid4',return_value=fake_uuid),patch.object(ns['secrets'],'randbelow',return_value=12345):
            response=ns['submit'](db,CURRENT,'inert-fit-key',submission(self.export),now=NOW,source_commit=COMMIT)
        self.assertEqual(db.pending[0][1],'UNIT-S2-07');self.assertEqual(len(db.attempts),1)
        self.assertEqual(db.writes,['receipt','pending','attempt','receipt'])
        actual=S2FitInput.model_validate_json(db.attempts[0]['request_json'])
        self.assertEqual(actual.seed_record.key.process,INITIAL_PROCESS)
        self.assertEqual(actual.seed_record.key.patient,'UNIT-S2-07');self.assertFalse(actual.executable)
        before=copy.deepcopy(db.writes)
        again=ns['submit'](db,dict(CURRENT,token_hash='inert-reauth'), 'inert-fit-key',submission(self.export),now=NOW,source_commit=COMMIT)
        self.assertEqual(again['id'],response['id']);self.assertEqual(db.writes,before)
        with self.assertRaisesRegex(ValueError,'one_S2_cohort_cutoff'):ns['submit'](db,CURRENT,'different-key',submission(self.export),now=NOW,source_commit=COMMIT)
    def test_receipt_unknown_original_conflict_foreign_and_ambiguous(self):
        ns=namespace();db=copy.deepcopy(self.db)
        self.assertEqual(ns['reconcile'](db,CURRENT['account_id'],'unknown'),dict(status='unknown',attempt=None))
        fit=self.fit;db.attempts=[row_for(fit)]
        payload=submission(self.export)
        receipt=dict(owner_id=CURRENT['account_id'],key='fit-key',scope='support-s2-fit:UNIT-selection-key',
            payload_sha256=sha(payload),response=canonical(dict(id=fit.attempt_id)))
        db.receipts.append(receipt)
        self.assertEqual(ns['reconcile'](db,CURRENT['account_id'],'fit-key')['status'],'found')
        self.assertEqual(ns['reconcile'](db,'UNIT-foreign','fit-key')['status'],'unknown')
        bad=copy.deepcopy(payload);bad['approved_export']['sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'conflict'):ns['submit'](db,CURRENT,'fit-key',bad,now=NOW,source_commit=COMMIT)
        db.receipts.append(receipt)
        with self.assertRaisesRegex(ValueError,'original'):ns['reconcile'](db,CURRENT['account_id'],'fit-key')
    def queued_fixture(self):
        db=copy.deepcopy(self.db);db.attempts=[row_for(self.fit)];payload=submission(self.export)
        db.receipts.append(dict(owner_id=CURRENT['account_id'],key='fit-key',scope='support-s2-fit:UNIT-selection-key',
            payload_sha256=sha(payload),response=canonical(dict(id=self.fit.attempt_id))))
        return db,dict(owner=CURRENT['account_id'],job=self.fit.attempt_id,key='fit-key',submission=payload,source_commit=COMMIT)
    def test_actual_queued_export_retains_original_receipt_and_is_defaultoff(self):
        db,args=self.queued_fixture()
        with self.assertRaisesRegex(ValueError,'not_qualified'):self.ns['queued_request'](db,**args)
        ns=namespace();ns['require_executable']=lambda p:None
        value=ns['queued_request'](db,**args)
        self.assertEqual(value['receipt']['key'],'fit-key');self.assertEqual(value['input']['attempt_id'],self.fit.attempt_id)
        self.assertEqual(value['input_sha256'],sha(self.fit.model_dump(mode='json')))
    def test_queued_missing_foreign_conflicting_claimed_extra_running_refuse(self):
        mutations=[lambda db,args:args.update(owner='UNIT-foreign'),lambda db,args:args.update(key='unknown'),
            lambda db,args:db.attempts[0].update(claim_token='inert-claim'),lambda db,args:db.attempts[0].update(started_at=NOW.isoformat()),
            lambda db,args:db.attempts.append(dict(row_for(self.fit),job_id='UNIT-other-running',status='running')),
            lambda db,args:db.attempts[0].update(input_sha256='f'*64)]
        for mutation in mutations:
            db,args=self.queued_fixture();mutation(db,args)
            with self.subTest(mutation=mutations.index(mutation)),self.assertRaises(ValueError):self.ns['queued_request'](db,**args)
    def test_seed_namespace_process_target_attempt_time_policy_and_derivation(self):
        good=seed(self.export)
        for field,value in [('namespace','assignment'),('process','generator'),('scenario','UNIT-other')]:
            bad=copy.deepcopy(good);bad['key'][field]=value
            with self.assertRaises(ValueError):FitSeedRecord.model_validate_json(canonical(bad))
        for field,value in [('patient','UNIT-S2-00'),('time_index',28)]:
            bad=self.fit.model_dump(mode='json');bad['seed_record']['key'][field]=value
            bad['seed_record']['sampler_seed']=int(sha(bad['seed_record']['key'])[:8],16)%2147483647
            with self.assertRaises(ValueError):S2FitInput.model_validate_json(canonical(bad))
    def test_result_content_binding_and_no_success_or_authority_toggle(self):
        result=dict(schema_version='s2-app-source-1.0.0',kind='poc_support_s2_app_fit_result',attempt_id=self.fit.attempt_id,
            input_reference=reference('poc-support-s2-app-fit-input-v1',self.fit.model_dump(mode='json')),
            configuration=CONFIG_REF,status='unavailable_source_preparation',reason='production_worker_artifact_and_diagnostics_unqualified',serving_authority=False)
        self.assertEqual(validate_fit_result(S2FitResult.model_validate_json(canonical(result)),self.fit).status,'unavailable_source_preparation')
        for field,value in [('status','completed'),('serving_authority',True),('extra_science_blob',{})]:
            with self.assertRaises(ValueError):S2FitResult.model_validate_json(canonical(dict(result,**{field:value})))
        bad=copy.deepcopy(result);bad['input_reference']['sha256']='f'*64
        with self.assertRaises(ValueError):validate_fit_result(S2FitResult.model_validate_json(canonical(bad)),self.fit)
    def test_extension_is_single_explicit_same_data_prior_distinct_seed_not_retry(self):
        value=dict(schema_version='s2-app-source-1.0.0',attempt_id='UNIT-extension',parent_attempt_id=self.fit.attempt_id,
            parent_input_reference=reference('poc-support-s2-app-fit-input-v1',self.fit.model_dump(mode='json')),
            original_export_reference=self.export.reference.model_dump(),seed_record=seed(self.export,'UNIT-extension',445566,EXTENSION_PROCESS),
            number=1,trigger='canonical_fit_diagnostics_failed',tune=2000,draws=2000,chains=4,
            retain_initial_artifacts=True,concatenate_attempts=False,executable=False)
        validate_extension(S2ExtensionRequest.model_validate_json(canonical(value)),self.fit)
        for field,bad in [('number',2),('trigger','outcome_or_seed_search'),('draws',1000),('concatenate_attempts',True)]:
            with self.assertRaises(ValueError):S2ExtensionRequest.model_validate_json(canonical(dict(value,**{field:bad})))
        other=copy.deepcopy(value);other['original_export_reference']['sha256']='f'*64
        with self.assertRaises(ValueError):validate_extension(S2ExtensionRequest.model_validate_json(canonical(other)),self.fit)


class PredictionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ns=namespace();db=InertDB();cls.export=exported(ns,db);cls.fit=fit_input(cls.export)
        p=cls.export.provenance
        cls.fit_result=S2FitResult.model_validate_json(canonical(dict(schema_version='s2-app-source-1.0.0',
            kind='poc_support_s2_app_fit_result',attempt_id=cls.fit.attempt_id,
            input_reference=reference('poc-support-s2-app-fit-input-v1',cls.fit.model_dump(mode='json')),configuration=CONFIG_REF,
            status='unavailable_source_preparation',reason='production_worker_artifact_and_diagnostics_unqualified',serving_authority=False)))
        request=dict(schema_version='s2-prediction-candidate-1.0.0',owner_id=p.owner_id,store_id=p.store_id,
            generation_id=p.generation_id,cohort_id=p.cohort_id,fit_id=cls.fit.attempt_id,
            fit_artifact_sha256=sha('UNIT-inert-label-not-a-real-posterior'),fitted_hstar=HSTAR_REF,
            fitted_snapshot_sha256=p.histories_sha256,configuration=PREDICT_CONFIG,definitions=PREDICT_DEFS,
            members=[dict(patient_id=m.patient_id,patient_version=m.patient_version,history_sha256=m.history_sha256,
                revisions_sha256=m.revisions_sha256,observed=c.observed,missing=c.missing) for m,c in zip(p.members,cls.export.counts)],
            cutoff=14,target_id=p.target_id,context_id='UNIT-predecision-14',context_version=1,current_snapshot_sha256=sha('UNIT-context'),
            decision_day=14,reward_day=15,h=1,expires_before_decision=28,x_current=[5.0,0.0,1.0,15/84])
        cls.product=S2PredictionInput.model_validate_json(canonical(dict(schema_version='s2-app-source-1.0.0',
            kind='poc_support_s2_app_prediction_input',purpose='EST-POLICY:poc-support-prediction-v1',attempt_id='UNIT-prediction',
            fit_input_reference=reference('poc-support-s2-app-fit-input-v1',cls.fit.model_dump(mode='json')),
            fit_result_reference=reference('poc-support-s2-app-fit-result-v1',cls.fit_result.model_dump(mode='json')),
            request=request,patient_version=15,state_version=2,consent_version=3,eligibility_version=4,
            allowed_actions=['support_prompt','no_prompt'],context_cutoff=p.cutoff.isoformat(),origin=p.origin.isoformat(),
            expires_at=(p.origin+timedelta(days=28)).isoformat(),configuration=CONFIG_REF,executable=False)))
    def test_distinct_fit_prediction_identities_bind_all_frozen_members(self):
        validate_prediction_input(self.product,self.fit,self.fit_result)
        self.assertFalse(self.product.executable)
        with self.assertRaisesRegex(ValueError,'not_qualified'):require_executable(self.product)
        for field,value in [('target_id','UNIT-S2-08'),('owner_id','UNIT-foreign'),('fitted_snapshot_sha256','f'*64)]:
            data=self.product.model_dump(mode='json');data['request'][field]=value
            with self.assertRaises(ValueError):validate_prediction_input(S2PredictionInput.model_validate_json(canonical(data)),self.fit,self.fit_result)
        data=self.product.model_dump(mode='json');data['request']['members'][-1]['revisions_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'all_member'):validate_prediction_input(S2PredictionInput.model_validate_json(canonical(data)),self.fit,self.fit_result)
    def current(self):
        p=self.product;r=p.request
        return dict(owner=r.owner_id,store=r.store_id,generation=r.generation_id,target=r.target_id,
            patient_version=p.patient_version,state_version=p.state_version,consent_version=p.consent_version,
            eligibility_version=p.eligibility_version,context_id=r.context_id,context_version=r.context_version,
            snapshot_sha256=r.current_snapshot_sha256,allowed_actions=p.allowed_actions,at=p.context_cutoff)
    def test_context_versions_mask_owner_hash_and_exact_expiry_are_separate_from_fit(self):
        current=self.current();validate_current_context(self.product,**current)
        mutations=dict(owner='UNIT-foreign',store='UNIT-other',generation='UNIT-other',target='UNIT-S2-08',
            patient_version=16,state_version=3,consent_version=4,eligibility_version=5,context_id='UNIT-other',
            context_version=2,snapshot_sha256='f'*64,allowed_actions=('no_prompt',),at=self.product.expires_at)
        for field,value in mutations.items():
            with self.subTest(field=field),self.assertRaises(ValueError):validate_current_context(self.product,**dict(current,**{field:value}))
        with self.assertRaises(ValueError):validate_current_context(self.product,**dict(current,at=self.product.context_cutoff-timedelta(seconds=1)))
    def result(self):
        r=self.product.request
        candidate=dict(schema_version='s2-prediction-candidate-1.0.0',request_sha256=sha(r.model_dump(mode='json')),
            target_id=r.target_id,context_id=r.context_id,context_version=r.context_version,status='arm_unavailable',
            reason='UNIT-inert-fallback-not-a-real-prediction',primary=None,
            cells=[dict(delta0=a,delta1=b,precision=None) for a in (-.5,0.,.5) for b in (-.5,0.,.5)],
            probability=.5,serving_authority=False,empirical_domain_only=True)
        return S2PredictionResult.model_validate_json(canonical(dict(schema_version='s2-app-source-1.0.0',
            kind='poc_support_s2_app_prediction_result',attempt_id=self.product.attempt_id,
            input_reference=reference('poc-support-s2-app-prediction-input-v1',self.product.model_dump(mode='json')),
            candidate=candidate,serving_authority=False)))
    def test_saved_result_context_binding_and_expired_prediction_refusal(self):
        result=self.result();validate_prediction_result(result,self.product,at=self.product.context_cutoff)
        with self.assertRaisesRegex(ValueError,'expiry'):validate_prediction_result(result,self.product,at=self.product.expires_at)
        data=result.model_dump(mode='json');data['candidate']['context_version']=2
        with self.assertRaises(ValueError):validate_prediction_result(S2PredictionResult.model_validate_json(canonical(data)),self.product,at=self.product.context_cutoff)
        for field,value in [('seed',seed(self.export)),('executable',True)]:
            with self.assertRaises(ValueError):S2PredictionInput.model_validate_json(canonical(dict(self.product.model_dump(mode='json'),**{field:value})))
        data=result.model_dump(mode='json');data['serving_authority']=True
        with self.assertRaises(ValueError):S2PredictionResult.model_validate_json(canonical(data))
    def test_no_completion_time_or_context_rewrite_can_extend_original_expiry(self):
        data=self.product.model_dump(mode='json');data['expires_at']=(self.product.expires_at+timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError):S2PredictionInput.model_validate_json(canonical(data))
        data=self.product.model_dump(mode='json');data['request']['decision_day']=28
        with self.assertRaises(ValueError):S2PredictionInput.model_validate_json(canonical(data))


class SourceBoundaryTests(unittest.TestCase):
    def test_recursive_eager_import_closure_and_selected_export_functions_have_no_science(self):
        pending=['services.foundation.support_s2_analysis','contracts.domain.support_s2_app']
        seen=set();external=set()
        selected={'services.foundation.support_s2_analysis':None,
            'services.foundation.protocol':{'export_histories','project_protocol'},
            'services.foundation.workflow':{'history','patient_clock'}}
        while pending:
            module=pending.pop()
            if module in seen:continue
            path=ROOT.joinpath(*module.split('.')).with_suffix('.py')
            if not path.is_file():external.add(module.split('.')[0]);continue
            seen.add(module);tree=ast.parse(path.read_text(encoding='utf-8'))
            nodes=list(tree.body)
            if module in selected:
                for node in tree.body:
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and (selected[module] is None or node.name in selected[module]):
                        nodes.extend(ast.walk(node))
            for node in nodes:
                if isinstance(node,ast.Import):pending.extend(n.name for n in node.names)
                elif isinstance(node,ast.ImportFrom):
                    base=module.split('.')[:-node.level] if node.level else []
                    pending.append('.'.join(base+([node.module] if node.module else [])))
        self.assertIn('methods.support.s2_data',seen)
        self.assertIn('services.foundation.protocol',seen)
        self.assertFalse(external.intersection({'numpy','pymc','pytensor','scipy','arviz','xarray','pandas','statsmodels'}))
    def test_tripwires_refuse_real_science_store_sqlite_process_network(self):
        for name in ('numpy','pymc','pytensor','sqlite3','services.foundation.store'):
            with self.assertRaises(AssertionError):importlib.import_module(name)
        with self.assertRaises(AssertionError):subprocess.run(['never-run'])
        with self.assertRaises(AssertionError):socket.create_connection(('127.0.0.1',1))
    def test_new_foundation_static_imports_scalar_only_and_existing_export_reused(self):
        source=ast.parse(SOURCE.read_text(encoding='utf-8'))
        imports=[n for n in ast.walk(source) if isinstance(n,(ast.Import,ast.ImportFrom))]
        names=[n.module if isinstance(n,ast.ImportFrom) else a.name for n in imports for a in (n.names if isinstance(n,ast.Import) else [None])]
        self.assertFalse(any(n and n.split('.')[0] in ('numpy','pymc','pytensor','scipy','sqlite3') for n in names))
        self.assertIn('methods.support.s2_data',names)
        io=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='public_histories')
        self.assertIn('return export_histories(db, owner, ids, cutoff)',ast.unparse(io))
    def test_new_claim_guard_precedes_claim_token_and_mutation_and_all_new_kinds(self):
        tree=ast.parse((ROOT/'services/foundation/analysis.py').read_text(encoding='utf-8'))
        claim=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='claim')
        text=ast.unparse(claim)
        self.assertLess(text.index("startswith('poc_support_s2_')"),text.index('secrets.token_hex'))
        self.assertLess(text.index('require_executable()'),text.index('UPDATE analysis_attempts'))
        # Execute the actual claim function, removing only its import nodes;
        # no real Store/SQLite/process and no mutation is possible.
        class Imports(ast.NodeTransformer):
            def visit_ImportFrom(self,node):return None
        node=Imports().visit(copy.deepcopy(claim))
        ns=dict(json=json,require_executable=require_executable)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'actual_claim_source','exec'),ns)
        for kind in ('poc_support_s2_app_fit_input','poc_support_s2_app_prediction_input','poc_support_s2_unknown'):
            class DB:
                def execute(self,sql,args=()):
                    if "status='running'" in sql:return Cursor()
                    if "status='queued'" in sql:return Cursor([dict(request_json=canonical(dict(kind=kind)))])
                    raise AssertionError('claim mutated before guard')
            class Transaction:
                def __enter__(self):return DB()
                def __exit__(self,*args):pass
            store=SimpleNamespace(transaction=lambda **kwargs:Transaction())
            with self.assertRaisesRegex(ValueError,'not_qualified'):ns['claim'](store)
    def test_routes_use_existing_session_mutation_transaction_and_no_worker(self):
        tree=ast.parse((ROOT/'services/foundation/app.py').read_text(encoding='utf-8'))
        expected={'select_support_s2','preview_support_s2','submit_support_s2','support_s2_receipt'}
        funcs={n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in expected}
        self.assertEqual(set(funcs),expected)
        for name,node in funcs.items():
            text=ast.unparse(node)
            self.assertIn('store.transaction(',text)
            self.assertIn('session(db, request',text)
            if name!='support_s2_receipt':self.assertIn('mutation=True',text)
            if name in ('select_support_s2','submit_support_s2'):self.assertIn('transaction(write=True)',text)
            self.assertFalse(any(word in text for word in ('Popen','wait(','.sample(','.predict(','worker_module')))
    def test_proposed_sampler_diagnostics_no_canonical_promotion_or_loose_caps(self):
        self.assertEqual(CONFIG_REF,reference('poc-support-s2-app-source-v1',CONFIG))
        self.assertEqual(CONFIG['sampler']['target_accept'],.995)
        self.assertEqual(CONFIG['sampler']['max_treedepth'],12)
        self.assertEqual(CONFIG['diagnostics']['bfmi_strict_lower'],.3)
        self.assertTrue(all(CONFIG['execution'][k] is None for k in ('qualified_production_image','production_source_closure','resource_caps','artifact_caps','installed_diagnostic_api')))
        with self.assertRaises(ValueError):ExecutionPreparation(executable=True)
        with self.assertRaises(ValueError):DiagnosticSettings(bulk_ess_min=100)
        self.assertEqual(__import__('contracts.domain.protocol_request',fromlist=['EXECUTABLE_CONFIGURATIONS']).EXECUTABLE_CONFIGURATIONS,frozenset())
