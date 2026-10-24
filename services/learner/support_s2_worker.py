"""S2 stdlib pre-import entry. Production admission is unconditionally OFF.

Private file access/scientific imports occur only inside the prepared qualified
implementation, after the contract gate. No environment string enables it.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

FLAGS='base_compiledir=/tmp/pytensor-s2,floatX=float64,cast_policy=numpy+floatX'
SCIENCE={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas','statsmodels'}


def construction_policy(environ):
    if any(name.split('.')[0] in SCIENCE for name in sys.modules):
        raise ValueError('S2_policy_must_precede_all_scientific_imports')
    if environ.get('PYTENSORRC') not in (None,''):
        raise ValueError('S2_nonempty_PYTENSORRC_refused')
    if environ.get('PYTENSOR_FLAGS') not in (None,'',FLAGS):
        raise ValueError('S2_conflicting_construction_flags_refused')
    environ['PYTENSOR_FLAGS']=FLAGS
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        if environ.get(name) not in (None,'','1'):raise ValueError('S2_single_native_thread_required')
        environ[name]='1'


class Budget:
    """One operation origin supplied by the existing supervisor, never reset.

    Wall deadline carries the supervisor's original operation origin across
    processes; the worker also freezes a monotonic bound on entry. It cannot
    grant extra time if the system clock moves backward. Parent supervision
    handles blocked compiler/native steps and collection/ingestion/reaping.
    """
    def __init__(self,origin_epoch, *, clock=time.time,monotonic=time.monotonic):
        self.clock=clock;self.monotonic=monotonic
        if type(origin_epoch) not in (int,float) or not math.isfinite(origin_epoch):
            raise ValueError('S2_common_absolute_operation_origin_required')
        now=clock()
        if not 0<=now-origin_epoch<6900:
            raise ValueError('S2_preflight_origin_expired_or_future')
        self.origin=origin_epoch;self.start=monotonic();self.remaining=6900-(now-origin_epoch)
        self.sequence=0;self.phase='preparing'
    def check(self):
        if self.clock()>=self.origin+6900 or self.monotonic()-self.start>=self.remaining:
            raise TimeoutError('S2_absolute_fit_work_deadline')
    def stage(self,value):
        self.check()
        phase=value.get('stage')
        if phase not in ('preparing','fitting','diagnostics') or (self.phase=='diagnostics' and phase!='diagnostics'):
            raise ValueError('S2_stage_veto')
        self.phase=phase;self.sequence+=1
        if self.sequence>250:raise ValueError('S2_progress_event_cap')
        self.check()

    def require_preflight(self,extension):
        self.check()
        if not extension and self.clock()-self.origin>=120:
            raise TimeoutError('S2_initial_preflight_deadline')


def strict_json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('S2_duplicate_JSON_key')
            value[key]=item
        return value
    value=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('S2_nonfinite_JSON')))
    count=0
    def bounded(item,depth=0):
        nonlocal count
        count+=1
        if depth>32 or count>200000:raise ValueError('S2_JSON_structure_cap')
        if isinstance(item,dict):
            if len(item)>128:raise ValueError('S2_JSON_object_cap')
            for key,child in item.items():bounded(key,depth+1);bounded(child,depth+1)
        elif isinstance(item,list):
            if len(item)>12000:raise ValueError('S2_JSON_array_cap')
            for child in item:bounded(child,depth+1)
        elif isinstance(item,str):
            if len(item)>2048:raise ValueError('S2_JSON_string_cap')
        elif type(item) in (int,float):
            if not math.isfinite(item):raise ValueError('S2_nonfinite_JSON_scalar')
        elif item is not None and type(item) is not bool:raise ValueError('S2_JSON_scalar_type')
    bounded(value)
    return value


def publish(path,value,cap):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>cap:raise ValueError('S2_scalar_output_cap')
    if path.exists() or path.is_symlink():raise ValueError('S2_immutable_result_exists')
    temporary=path.with_suffix('.partial')
    with temporary.open('xb') as stream:stream.write(raw)
    temporary.replace(path)


def _qualified_fit(product,out, *, budget,trusted,progress,extension_authority=None):
    """Prepared role implementation; called only after future reviewed admission.

    One input selects initial OR explicit extension. There is no in-worker
    retry/extension decision. An extension keeps original artifacts in their
    original attempt directory under the same supervisor operation origin.
    """
    from contracts.domain.analysis import canonical
    from contracts.domain.support_s2_native import (NativeResult, CONFIG_REF,
        RESULT_CAP, PROGRESS_CAP, ownership, validate_result, dimension_bound,validate_extension_admission)
    dimension_bound(product.initial.export.provenance.cutoff_day,product.draws)
    budget.require_preflight(product.extension is not None)
    budget.check()
    if product.extension is not None:
        if not isinstance(extension_authority,dict) or set(extension_authority)!={'parent','parent_product','parent_trusted','indicator_failed'}:
            raise ValueError('S2_extension_service_owned_parent_admission_required')
        validate_extension_admission(product,extension_authority['parent'],extension_authority['parent_product'],
            extension_authority['parent_trusted'],indicator_failed=extension_authority['indicator_failed'])
    elif extension_authority is not None:raise ValueError('S2_initial_attempt_has_no_parent')
    from methods.support.s2_data import prepare
    from methods.support.s2_fit import sample, diagnostics
    from .support_s2_artifacts import write
    budget.check();sequence=0
    def stage(value):
        nonlocal sequence
        budget.stage(value);sequence+=1
        event=dict(schema='s2-native-progress-v1',attempt_id=product.attempt_id,
            input_sha256=ownership(product)['input_sha256'],sequence=sequence,
            stage=value['stage'],extension=product.extension is not None,
            elapsed_seconds=budget.clock()-budget.origin)
        if len(canonical(event).encode())>PROGRESS_CAP:raise ValueError('S2_progress_byte_cap')
        # Existing monitor may veto while pm.sample is blocked; every callback
        # observes that veto synchronously. No progress output stream/spool.
        progress(event)
        budget.check()
    stage(dict(stage='preparing'))
    data=prepare(product.initial.export.histories,product.initial.export.provenance)
    trace,execution=sample(data,product,stage=stage,check=budget.check)
    stage(dict(stage='diagnostics'))
    budget.check()
    # Persist all original chains before diagnosing. A refused diagnostic/API
    # leaves the exact named private posterior for failed-attempt retention.
    semantics=write(trace,out,product,check=budget.check)
    del trace
    import xarray as xr
    # Diagnostics belong to the same bytes that will be transported/admitted.
    saved=xr.open_datatree(out/'posterior.nc',engine='netcdf4')
    try:diagnostic=diagnostics(saved,python_warnings=execution['python_warnings'])
    finally:saved.close()
    result=NativeResult.model_validate_json(canonical(dict(schema_version='s2-native-source-1.0.0',
        kind='poc_support_s2_native_fit_result',attempt_id=product.attempt_id,configuration=CONFIG_REF,
        ownership=ownership(product),diagnostics=diagnostic.model_dump(mode='json'),
        semantics=semantics.model_dump(mode='json'),execution=dict(launch=trusted,**execution),
        status='completed' if diagnostic.accepted else 'abstained',
        reason=None if diagnostic.accepted else 'fit_diagnostics_unmet',serving_authority=False)))
    validate_result(result,product,trusted)
    budget.check();publish(out/'result.json',result.model_dump(mode='json'),RESULT_CAP)
    return result


def run(input_path,out, *, origin_epoch=None,trusted=None,progress=None,extension_authority=None):
    # No input/output/stat, environment policy mutation, entropy, scientific
    # import or process creation occurs before this unconditional admission.
    from contracts.domain.support_s2_native import require_executable
    require_executable()
    construction_policy(os.environ)
    from contracts.domain.analysis import canonical
    from contracts.domain.support_s2_native import NativeInput, INPUT_CAP
    budget=Budget(origin_epoch)
    if (input_path.is_symlink() or not input_path.is_file() or input_path.stat().st_size>INPUT_CAP
            or out.is_symlink() or not out.is_dir()):
        raise ValueError('S2_owned_bounded_input_output_required')
    with input_path.open('rb') as stream:raw=stream.read(INPUT_CAP+1)
    if len(raw)>INPUT_CAP:raise ValueError('S2_input_byte_cap')
    product=NativeInput.model_validate_json(canonical(strict_json(raw)))
    if trusted is None or progress is None:raise ValueError('S2_owned_launch_and_supervisor_progress_required')
    return _qualified_fit(product,out,budget=budget,trusted=trusted,progress=progress,extension_authority=extension_authority)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:run(args.input,args.output)
    except Exception:return 1  # no private scientific traceback/error stream
    return 0


if __name__=='__main__':sys.exit(main())
