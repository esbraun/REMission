import json,pytensor
from pytensor.compile.mode import get_default_mode
from methods.visit.borrow_execution import compilation_options,optimizer_identity
from contracts.domain.borrow_runtime import OPTIMIZER
mode=get_default_mode()
result=dict(floatX=pytensor.config.floatX,default_linker=type(mode.linker).__name__,optimizer=optimizer_identity(mode.provided_optimizer),expected_optimizer=OPTIMIZER)
try:
 options=compilation_options();result.update(guard_pass=True,selected_linker=type(options['mode'].linker).__name__)
except Exception as error:result.update(guard_pass=False,error_type=type(error).__name__,reason=str(error))
print(json.dumps(result,sort_keys=True))
