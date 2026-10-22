"""Finite public-wire fixtures; not qualified producer or likelihood output."""
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone

from contracts.domain.evidence_v2 import exact_ref, payload_hash
from contracts.domain.evidence_v21 import validate_report_graph, validate_burden_state
from contracts.domain.observed_v21 import (BurdenAssessmentStateV21, DailyReportV21,
    ObservedHistoryV21, RECORD_ADAPTER_V21, ReportObservationDecisionV21,
    ReportingInputV21, ReportUploadReceiptV21, SubjectiveBurdenRatingV21,
    reporting_input_v21)

E = datetime(2026, 10, 2, 7, tzinfo=timezone.utc)
D = E + timedelta(minutes=61)


def ref(name, version='1.0.0-r1'):
    return dict(id=name, version=version, sha256='a'*64)


def header(kind, identity, event=E, *, metadata=False, version='2.1.0', available=None, recorded=None):
    value = dict(schema_version=version, synthetic=True, kind=kind, record_id=identity, patient_id='fixture-patient',
        event_at=event.isoformat(), recorded_at=(recorded or event).isoformat(), available_at=(available or recorded or event).isoformat(),
        source=dict(id='dgp-report-status' if metadata else 'dgp-patient-report',version='1.0.0-r1' if metadata else '1.3.0',
                    adapter='simulation' if metadata else 'patient_report', raw_sha256='b'*64),
        lineage_id=identity, revision=1, supersedes=None, duplicate_of=None, record_status='active')
    if version == '2.1.0':value.update(run_id='fixture-run', partition_id='fixture-partition')
    return value


def window():
    return dict(starts_at=(E-timedelta(days=1)).isoformat(),ends_at=E.isoformat(),timezone='UTC',local_date='2026-10-02')


def pain():
    value=header('observation','pain',E+timedelta(hours=1),version='1.0.0')
    value['source'].update(id='dgp-clinical-pain',version='1.3.0',adapter='synthetic_fhir_shaped')
    value.update(measure=dict(concept='pain',value=1.2,unit='dimensionless',observed_at=value['event_at'],available_at=value['available_at']),lab_reference_context=None)
    return value


def history(records):
    return ObservedHistoryV21.model_validate_json(json.dumps(dict(schema_version='2.1.0',synthetic=True,kind='observed_history',patient_id='fixture-patient',records=records)))


def parse(model, value):return model.model_validate_json(json.dumps(value))


def bundle(*, indicator=1, delay=0, observed=True):
    source=history([pain()]);input=reporting_input_v21(source,report_event_at=E,pain_record_id='pain')
    parent=parse(ReportObservationDecisionV21,dict(**header('report_observation_decision','parent',metadata=True,recorded=D),
        assessment_local_date='2026-10-02',report_event_at=E.isoformat(),decision_at=D.isoformat(),temporal=ref('TIME-01','2.1.0'),
        law=ref('REPORT-STATUS-01'),reporting_process_ref=ref('report-observation','1.3.0'),indicator=indicator,pain_ref=input.pain_ref.model_dump(),
        previous_quality_ref=None,absent_history=True,pre_report_projection_sha256=input.pre_report_projection_sha256,
        execution_receipt_ref=ref('finite-contract-execution'),source_correction_receipt_ref=None))
    records=[*source.records,parent];seq={'pain':1,'parent':2}
    at=D+timedelta(days=delay)
    if indicator:
        daily=parse(DailyReportV21,dict(**header('daily_report','daily',recorded=D,available=at),sleep_quality=6.0,function=7.0,
            adverse_symptoms=[],diary_sleep_minutes=-30.0,goals=[],burden=None,missingness='observed',report_decision_ref=exact_ref(parent).model_dump()))
        rating=parse(SubjectiveBurdenRatingV21,dict(**header('subjective_burden_rating','rating',recorded=D,available=at),
            instrument=ref('synthetic-support-burden-item'),window=window(),score=3,report_decision_ref=exact_ref(parent).model_dump()))
        receipt=parse(ReportUploadReceiptV21,dict(**header('report_upload_receipt','receipt',metadata=True,recorded=at),
            report_decision_ref=exact_ref(parent).model_dump(),daily_report_ref=exact_ref(daily).model_dump(),rating_ref=exact_ref(rating).model_dump(),
            upload_delay_days=delay,payload_available_at=at.isoformat(),completion_receipt_ref=ref('finite-contract-completion'),publication_sequence=5))
        records += [daily,rating,receipt];seq.update(daily=3,rating=4,receipt=5)
    evaluation=E+timedelta(minutes=62)
    state=parse(BurdenAssessmentStateV21,dict(**header('burden_assessment_state','state',metadata=True,recorded=evaluation),
        instrument=ref('synthetic-support-burden-item'),window=window(),status='observed' if indicator and observed else 'pending' if indicator else 'missing',
        reason='finite_contract_fixture',report_decision_ref=exact_ref(parent).model_dump(),terminal_ref=None,
        rating_ref=exact_ref(rating).model_dump() if indicator and observed else None,
        receipt_ref=exact_ref(receipt).model_dump() if indicator and observed else None,evaluated_as_of=evaluation.isoformat(),
        source_refs=[],closure_refs=[],definition_refs=[]))
    records += [state];seq['state']=6
    return history([r.model_dump(mode='json') for r in records]),seq


def validate(h,seq):
    # These resolvers assert exact explicitly labeled finite fixture receipts;
    # they confer no actual producer qualification or source grant.
    def execution(parent,input):
        if parent.execution_receipt_ref.id != 'finite-contract-execution' or payload_hash(input.pre_report_history) != parent.pre_report_projection_sha256:
            raise ValueError('wrong_finite_execution_receipt')
    def completion(receipt,parent,daily,rating):
        if receipt.completion_receipt_ref.id != 'finite-contract-completion':raise ValueError('wrong_finite_completion_receipt')
    return validate_report_graph(h,publication_sequences=seq,verify_execution=execution,verify_completion=completion,reserved_lineage=lambda identity:None)


class ReportStatusV21Tests(unittest.TestCase):
    def test_shared_parent_response_receipt_state_positive_and_strict_cutoff(self):
        h,seq=bundle();validate(h,seq)
        self.assertEqual({r.record_id for r in h.project(D).records},{'pain'})
        self.assertEqual({r.record_id for r in h.project(D+timedelta(microseconds=1)).records},{'pain','parent','daily','rating','receipt'})
        self.assertEqual(next(r for r in h.records if r.kind=='daily_report').diary_sleep_minutes,-30.0)
        self.assertFalse(any(k in h.model_dump_json() for k in ('latent_Q','observation_probability','seed_draw')))

    def test_missing_and_delayed_pending_are_metadata_without_invented_rating(self):
        h,seq=bundle(indicator=0);validate(h,seq)
        self.assertFalse(any(r.kind=='subjective_burden_rating' for r in h.records))
        delayed,seq=bundle(delay=3,observed=False);validate(delayed,seq)
        self.assertEqual({r.record_id for r in delayed.project(D+timedelta(minutes=2)).records},{'pain','parent','state'})
        self.assertEqual(next(r for r in delayed.records if r.kind=='burden_assessment_state').status,'pending')

    def test_strict_fields_reject_private_channels_coercions_missing_rating_zero_alias(self):
        h,_=bundle();objects={r.kind:r.model_dump(mode='json') for r in h.records}
        for model,kind,key,value in [(ReportObservationDecisionV21,'report_observation_decision','indicator',True),
            (ReportObservationDecisionV21,'report_observation_decision','observation_probability',.8),
            (SubjectiveBurdenRatingV21,'subjective_burden_rating','score',True),
            (SubjectiveBurdenRatingV21,'subjective_burden_rating','score',None),
            (SubjectiveBurdenRatingV21,'subjective_burden_rating','score',5),
            (ReportUploadReceiptV21,'report_upload_receipt','upload_delay_days',True),
            (BurdenAssessmentStateV21,'burden_assessment_state','score',0)]:
            value=copy.deepcopy(objects[kind])|{key:value}
            with self.subTest(kind=kind,key=key),self.assertRaises(ValueError):parse(model,value)

    def test_graph_requires_actual_order_exact_scope_and_shared_delay(self):
        h,seq=bundle()
        for change in ('wrong_order','duplicate_order','missing_order','wrong_scope','wrong_hash','wrong_delay','wrong_R'):
            raw=h.model_dump(mode='json');orders=seq.copy()
            if change=='wrong_order':orders['parent'],orders['rating']=orders['rating'],orders['parent']
            elif change=='duplicate_order':orders['rating']=orders['daily']
            elif change=='missing_order':del orders['pain']
            elif change=='wrong_scope':next(r for r in raw['records'] if r['record_id']=='rating')['partition_id']='foreign'
            elif change=='wrong_hash':next(r for r in raw['records'] if r['record_id']=='receipt')['rating_ref']['payload_sha256']='c'*64
            elif change=='wrong_delay':next(r for r in raw['records'] if r['record_id']=='receipt')['upload_delay_days']=1
            else:next(r for r in raw['records'] if r['record_id']=='parent')['indicator']=0
            with self.subTest(change=change),self.assertRaises(ValueError):validate(parse(ObservedHistoryV21,raw),orders)

    def test_equal_time_is_not_strict_analysis_visibility(self):
        h,seq=bundle();state=next(r for r in h.records if r.kind=='burden_assessment_state').model_dump(mode='json')
        state['evaluated_as_of']=D.isoformat()
        with self.assertRaisesRegex(ValueError,'visible'):validate_burden_state(h,parse(BurdenAssessmentStateV21,state),seq)

    def test_nested_response_correction_invalidates_later_state_exact_closure(self):
        h,seq=bundle();arrival=D+timedelta(days=1)
        daily=next(r for r in h.records if r.kind=='daily_report').model_dump(mode='json')
        corrected=daily|dict(record_id='daily-r2',revision=2,supersedes='daily',record_status='corrected',sleep_quality=5.0,
            recorded_at=arrival.isoformat(),available_at=arrival.isoformat())
        changed=history([r.model_dump(mode='json') for r in h.records]+[corrected]);orders=seq|{'daily-r2':7,'state-later':8}
        # The old state remains valid at its original evaluation. A later
        # claim cannot reuse the old receipt's now-stale nested DailyReport.
        old=next(r for r in changed.records if r.kind=='burden_assessment_state')
        validate_burden_state(changed,old,orders)
        raw=old.model_dump(mode='json')|dict(record_id='state-later',evaluated_as_of=(arrival+timedelta(minutes=1)).isoformat(),
            recorded_at=(arrival+timedelta(minutes=1)).isoformat(),available_at=(arrival+timedelta(minutes=1)).isoformat())
        with self.assertRaisesRegex(ValueError,'stale'):validate_burden_state(changed,parse(BurdenAssessmentStateV21,raw),orders)

    def test_correction_old_cutoff_and_retraction_null_not_zero(self):
        h,seq=bundle();rating=next(r for r in h.records if r.kind=='subjective_burden_rating')
        arrival=D+timedelta(days=1)
        revised=rating.model_dump(mode='json')|dict(record_id='rating-r2',revision=2,supersedes='rating',record_status='corrected',score=4,
            recorded_at=arrival.isoformat(),available_at=arrival.isoformat())
        corrected=history([r.model_dump(mode='json') for r in h.records]+[revised])
        self.assertEqual(next(r for r in corrected.as_known_at(arrival) if r.kind=='subjective_burden_rating').score,3)
        self.assertEqual(next(r for r in corrected.as_known_at(arrival+timedelta(microseconds=1)) if r.kind=='subjective_burden_rating').score,4)
        tombstone=revised|dict(record_id='rating-r3',revision=3,supersedes='rating-r2',record_status='retracted',score=None,
            recorded_at=(arrival+timedelta(hours=1)).isoformat(),available_at=(arrival+timedelta(hours=1)).isoformat())
        retracted=history([r.model_dump(mode='json') for r in h.records]+[revised,tombstone])
        self.assertFalse(any(r.kind=='subjective_burden_rating' for r in retracted.as_known_at(arrival+timedelta(hours=2))))
        with self.assertRaises(ValueError):parse(SubjectiveBurdenRatingV21,tombstone|dict(score=0))

    def test_reporting_input_uses_separate_current_pain_and_no_report_draw(self):
        h=history([pain()]);value=reporting_input_v21(h,report_event_at=E,pain_record_id='pain')
        self.assertEqual(value.mar_predictors(),dict(current_observed_pain=1.2,previous_observed_quality=7.0,absent_history=True))
        for edit in [dict(indicator=1),dict(upload_delay_days=0),dict(pre_report_projection_sha256='c'*64)]:
            with self.assertRaises(ValueError):parse(ReportingInputV21,value.model_dump(mode='json')|edit)
        for field,value in [('version','1.2.0'),('adapter','patient_report'),('id','report-derived-pain')]:
            bad=pain();bad['source'][field]=value
            with self.assertRaises(ValueError):reporting_input_v21(history([bad]),report_event_at=E,pain_record_id='pain')
        bad=pain();bad['available_at']=D.isoformat();bad['measure']['available_at']=D.isoformat()
        with self.assertRaises(ValueError):reporting_input_v21(history([bad]),report_event_at=E,pain_record_id='pain')

    def test_prior_recorded_upload_survives_death_but_new_decision_does_not(self):
        h,seq=bundle(delay=3,observed=False)
        death=header('intercurrent_event','death',E+timedelta(hours=2),version='1.0.0')|dict(event_type='death',detail='finite_fixture')
        history([r.model_dump(mode='json') for r in h.records]+[death])
        death['event_at']=death['recorded_at']=death['available_at']=(E+timedelta(minutes=30)).isoformat()
        with self.assertRaises(ValueError):history([r.model_dump(mode='json') for r in h.records]+[death])

    def test_unknown_version_kind_and_cross_version_correction_refused(self):
        h,_=bundle();raw=next(r for r in h.records if r.kind=='subjective_burden_rating').model_dump(mode='json')
        for change in [dict(schema_version='2.2.0'),dict(kind='private_full_burden'),dict(schema_version='2.0.0')]:
            with self.assertRaises(ValueError):RECORD_ADAPTER_V21.validate_json(json.dumps(raw|change))
        daily=next(r for r in h.records if r.kind=='daily_report').model_dump(mode='json')
        old={k:v for k,v in daily.items() if k not in ('run_id','partition_id','report_decision_ref')}
        old.update(schema_version='1.0.0',record_id='legacydaily',lineage_id='shared',diary_sleep_minutes=450.)
        arrival=D+timedelta(days=1)
        new=daily|dict(lineage_id='shared',revision=2,supersedes='legacydaily',record_status='corrected',recorded_at=arrival.isoformat(),available_at=arrival.isoformat())
        with self.assertRaisesRegex(ValueError,'cross_version'):history([old,new])


if __name__=='__main__':unittest.main()
