"""One offline stage per isolated, network-disabled container; no repository data mount."""
import json
from pathlib import Path
import sys

stage=sys.argv[1]
inputs=Path("/input");output=Path("/output")
allowed={"train":{"training.json","plan.json"},
         "predict":{"roster.json","receipt.json","model.joblib","policies.json"},
         "score":{"protocol.json","roster.json","rewards.json","receipt.json","q.json","policy-a.json","policy-b.json","request.json"}}[stage]
opened=[];denied=[];training_calls=[]


def audit(event,args):
    if event!="open" or not isinstance(args[0],str):return
    path=Path(args[0])
    if path.is_absolute() and path.is_relative_to(inputs):
        if path.name not in allowed:
            denied.append(str(path));raise PermissionError("stage input capability denied")
        opened.append(str(path))


sys.addaudithook(audit)
def profile(frame,event,arg):
    name=frame.f_code.co_name if event=="call" else getattr(arg,"__name__","") if event=="c_call" else ""
    if name in {"fit","fit_transform","partial_fit","predict","learn","choice"}:
        training_calls.append(name)
        if stage=="score":raise AssertionError("fit/learn/predict/action sampling forbidden in scorer")
sys.setprofile(profile)
# Actual read attempts are denied, rather than trusting timestamps/labels alone.
for forbidden in ({"train":["rewards.json","roster.json"],"predict":["rewards.json","training.json"],
                   "score":["training.json","model.joblib"]}[stage]):
    try:(inputs/forbidden).read_bytes()
    except PermissionError:pass
    else:raise AssertionError("forbidden access succeeded")
if stage=="train":
    from methods.ope.nuisance import train
    train(inputs,output)
elif stage=="predict":
    from methods.ope.nuisance import predict
    predict(inputs,output)
else:
    from contracts.artifacts.ope import OPERequest
    from methods.ope.functional import evaluate_files
    assert "sklearn" not in sys.modules,"scorer must not import fitting runtime"
    request=OPERequest.model_validate_json((inputs/"request.json").read_bytes())
    result=evaluate_files(inputs,request)
    (output/"result.json").write_text(result.model_dump_json(indent=2)+"\n")
    assert "sklearn" not in sys.modules
(output/"access.json").write_text(json.dumps({"stage":stage,"allowed_files":sorted(allowed),
    "actually_opened":sorted(set(opened)),"denied_actual_reads":denied,
    "sklearn_imported":"sklearn" in sys.modules,"network":"disabled_by_container",
    "fit_learn_predict_choice_calls":training_calls,
    "source_mount":"curated code only, no full repository/data"},indent=2)+"\n")
