"""Private explicit breadth producer; no learner/evaluator/Store import.

The pure scalar primitives support guarded short fixtures. Full generation and
publication require a separately reviewed isolated operation; none is admitted
by this module, its output hashes, or the candidate export status.
"""
from datetime import timedelta
import hashlib
import math
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator
from contracts.domain.common import Identifier, StrictModel, VersionRef
from contracts.domain.breadth import (LAW_VERSION,HISTORY_VERSION,FEATURE_VERSION,LAW_REF,HISTORY_REF,FEATURE_REF,
    SOURCE_IDS,ADAPTERS,ObservedEvent,BreadthHistory,BreadthExport,support_features,canonical)


class ScheduledAction(StrictModel):
    """Private producer input; a logged action is not an inferred policy."""
    day: Annotated[int,Field(ge=0,le=125)]
    component: Literal['behavioral','medication','support']
    option: Literal['behavioral_continue','behavioral_escalate','MED_A','MED_B','support_prompt','no_prompt'] | None
    assignment_id: Identifier
    policy: VersionRef
    chosen_probability: Annotated[float,Field(gt=0,le=1)]
    support_available: tuple[bool,bool] | None
    support_probabilities: tuple[Annotated[float,Field(ge=0,le=1)],Annotated[float,Field(ge=0,le=1)]] | None

    @model_validator(mode='after')
    def matching_action(self):
        allowed={'behavioral':('behavioral_continue','behavioral_escalate'),'medication':('MED_A','MED_B',None),'support':('no_prompt','support_prompt')}
        if self.option not in allowed[self.component]:raise ValueError('scheduled component/option mismatch')
        if (self.component=='support')!=(self.support_available is not None):raise ValueError('only support actions carry the actual mask')
        if (self.component=='support')!=(self.support_probabilities is not None):raise ValueError('logged full support distribution required')
        if self.component=='support':
            index=int(self.option=='support_prompt')
            if (not self.support_available[index] or abs(sum(self.support_probabilities)-1)>1e-12
                    or self.chosen_probability!=self.support_probabilities[index]
                    or any(p!=0 for p,available in zip(self.support_probabilities,self.support_available) if not available)):
                raise ValueError('unavailable or inconsistent support distribution')
        return self


class BreadthRequest(StrictModel):
    """New exact private wire branch, never an old generator request widening."""
    law_version: Literal['poc-breadth-longitudinal-v3']
    namespace: Annotated[str,Field(min_length=1,max_length=256)]
    seed: Annotated[int,Field(ge=0,le=2147483647)]
    index: Annotated[int,Field(ge=0,lt=120)]
    patient_id: Identifier
    origin: AwareDatetime
    family: Literal['V','N','S']
    population: Literal['target','external']
    scenario: Literal['reference','external_conflict','sharp_null']
    through_day: Annotated[int,Field(ge=0,le=126)]
    support_mode: Literal['S0','S1','S2'] | None
    actions: Annotated[list[ScheduledAction],Field(max_length=378)]

    @model_validator(mode='after')
    def fixed_family_schedule(self):
        if self.population=='target' and self.index>=12 or self.population=='external' and self.family!='V':
            raise ValueError('complete12 target or120-member external V study ordinal required')
        if self.family!='V' and self.scenario!='reference':raise ValueError('only five prespecified family/scenario cells')
        if (self.family=='S')!=(self.support_mode is not None):raise ValueError('support policy mode must be explicit only for S')
        keys=[(a.day,a.component) for a in self.actions]
        if keys!=sorted(set(keys)) or len({a.assignment_id for a in self.actions})!=len(self.actions):raise ValueError('unique chronological original action identities required')
        if any(a.day>=self.through_day for a in self.actions):raise ValueError('action cannot follow requested observation prefix')
        behavior=[a for a in self.actions if a.component=='behavioral']
        if self.through_day and (not behavior or behavior[0].day!=0):raise ValueError('original day0 behavioral assignment required')
        if self.family!='V' and any(a.option!='behavioral_continue' for a in behavior):raise ValueError('N/support background continuation fixed')
        if self.family!='N' and any(a.component=='medication' for a in self.actions):raise ValueError('medications only in N family')
        support=[a for a in self.actions if a.component=='support']
        if self.family!='S' and support:raise ValueError('V/N support is fixed off')
        if self.family=='S':
            if [a.day for a in support]!=list(range(self.through_day)):raise ValueError('every support decision needs logged probability and availability')
            prompts=[]
            for action in support:
                eligible=(action.day-1 not in prompts and sum(action.day-6<=d<action.day for d in prompts)<3)
                if action.support_available!=(True,eligible):raise ValueError('support hard-constraint availability mismatch')
                if not eligible and action.chosen_probability!=1.:raise ValueError('forced no-prompt probability must be1')
                if self.support_mode=='S0' and (action.option!='no_prompt' or action.chosen_probability!=1.):raise ValueError('S0 fixed no-prompt')
                if self.support_mode=='S1' and eligible and action.chosen_probability!=.5:raise ValueError('S1 actual randomized q=.5 required')
                if self.support_mode=='S2' and eligible and not .1<=action.chosen_probability<=.9:raise ValueError('S2 actual eligible probability outside [.1,.9]')
                if action.option=='support_prompt':prompts.append(action.day)
        return self


def observed_entry(patient,kind,identifier,event_at,recorded_at,available_at,**values):
    """Existing raw observed envelope/hash pattern, with new closed source IDs."""
    payload=dict(schema_version='3.0.0',synthetic=True,kind=kind,record_id=identifier,patient_id=patient,
        event_at=event_at.isoformat(),recorded_at=recorded_at.isoformat(),available_at=available_at.isoformat(),lineage_id=identifier,
        revision=1,supersedes=None,duplicate_of=None,record_status='active',**values)
    raw=canonical(payload)
    payload['source']=dict(id=SOURCE_IDS[kind],version='3.0.0',adapter=ADAPTERS[kind],raw_sha256=hashlib.sha256(raw).hexdigest())
    TypeAdapter(ObservedEvent).validate_json(canonical(payload))
    # Keep the exact source timestamp spelling that was hashed, rather than
    # roundtripping aware datetimes through a different JSON representation.
    return dict(record=payload,raw_source=raw.decode())


def history_from_entries(patient,origin,entries):
    """Validate complete source envelopes before projection strips no lineage."""
    records=[]
    for entry in entries:
        if set(entry)!={'record','raw_source'} or type(entry['raw_source']) is not str:raise ValueError('closed observed source entry required')
        record=TypeAdapter(ObservedEvent).validate_json(canonical(entry['record']))
        without_source={k:v for k,v in entry['record'].items() if k!='source'}
        if canonical(without_source).decode()!=entry['raw_source'] or hashlib.sha256(entry['raw_source'].encode()).hexdigest()!=record.source.raw_sha256:
            raise ValueError('observed source envelope/bytes/hash mismatch')
        records.append(record)
    return BreadthHistory(version=HISTORY_VERSION,synthetic=True,law=LAW_REF,patient_id=patient,origin=origin,records=records)


def export_candidate(histories,*,member_order,run_id,cohort_id,replicate,role,cutoff,source_commit,runtime):
    """Whole new-profile export only; old registration/admission still refuses.

    No file is read/written and no trust/qualification marker is produced. A
    future reviewed producer role supplies authoritative histories and expected
    source/runtime; B3.3 separately qualifies admission and normal app transport.
    """
    if not histories:raise ValueError('no observed histories')
    if any(type(h) is not BreadthHistory for h in histories):raise ValueError('new typed breadth histories required')
    projections=[h.project(cutoff) for h in histories]
    return BreadthExport(version='poc-breadth-observed-export-v1',synthetic=True,run_id=run_id,cohort_id=cohort_id,replicate=replicate,role=role,
        law=LAW_REF,history_definition=HISTORY_REF,feature_definition=FEATURE_REF,source_commit=source_commit,runtime=runtime,cutoff=cutoff,
        origin=histories[0].origin,member_order=member_order,histories=projections,support=[support_features(p) for p in projections],
        publication_status='candidate_requires_independent_source_runtime_export_admission')


def uniform(seed,namespace,index,day,process):
    # Same stateless SHA256/53-bit mechanism as the old generator, NEW namespace.
    # Analytics configuration is deliberately absent from exogenous keys.
    key=canonical([LAW_VERSION,namespace,seed,index,day,process])
    number=int.from_bytes(hashlib.sha256(key).digest()[:8],'big')>>11
    return (number+.5)/2**53


def normal(seed,namespace,index,day,process):
    u=uniform(seed,namespace,index,day,process+'-u');v=uniform(seed,namespace,index,day,process+'-v')
    return math.sqrt(-2*math.log(u))*math.cos(2*math.pi*v)


def clip(value,low,high):return min(high,max(low,value))


def baseline(draw_uniform,draw_normal):
    """Independent baseline draws; caller supplies fixed named exogenous draws."""
    age=30+45*draw_uniform('age');a=(age-52.5)/22.5
    code=int(draw_uniform('sex')<.5);s=2*code-1
    b=19+1.5*a+.5*s-3+6*draw_uniform('baseline')
    response=math.exp(-.15*a)*(.8+.4*draw_uniform('response'))
    device_bias=15+10*draw_normal('device-bias')
    return dict(age=age,a=a,sex_code=code,s=s,b=b,response=response,device_bias=device_bias)


def step(state,person,day,*,eta,xi,taken,assigned_drug,coefficients=(2.,4.)):
    """One exact adopted transition. Latent state stays inside the generator."""
    steroid=int(day%21 in (0,1,2))
    x=.60*state['x_previous']+.12*(state['z']-19)+.50*steroid+.20*person['a']+.10*person['s']+.50*eta
    error=.55*state['e']+.80*xi
    c=.65*state['c']+.35*int(taken['behavioral_continue'])
    e=.80*state['escalate']+.20*int(taken['behavioral_escalate'])
    ma=.50*state['ma']+.50*int(taken['MED_A']);mb=.50*state['mb']+.50*int(taken['MED_B'])
    rebound=.50*state['rebound']+int(state['previous_assigned_drug']=='MED_B' and assigned_drug!='MED_B')
    z=(person['b']+.55*math.sin(2*math.pi*(day+1)/21)+.60*x+.80*steroid+error
        -coefficients[0]*person['response']*c-coefficients[1]*person['response']*e
        -1.5*person['response']*ma-2.5*person['response']*mb+rebound)
    return dict(x_previous=x,z=z,e=error,c=c,escalate=e,ma=ma,mb=mb,rebound=rebound,previous_assigned_drug=assigned_drug)


def measurements(person,*,x,z,steroid,previous_support,prompt_count,clinical_noise,device_noise,report_noise,clinical_missing,device_status,report_missing,round_value):
    """Measurement formulas only; clock/nonwear/tie policy awaits clarification."""
    p=None if clinical_missing else round_value(clip(4+x+.30*clinical_noise,0,10),1)
    d=None if device_status!='observed' else round_value(clip(480-8*z+person['device_bias']+25*device_noise,0,480),1)
    q=None if report_missing else round_value(clip(10-z/3+previous_support*(.60*person['response']-.10*prompt_count-.20*steroid)+.45*report_noise,0,10),3)
    return dict(clinical=p,device=d,estimated_wake=None if d is None else 480-d,quality=q)
