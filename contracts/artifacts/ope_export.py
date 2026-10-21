"""Deterministic maintained-type schemas for the narrow OPE boundary."""
import argparse
import json
from pathlib import Path
from pydantic import TypeAdapter
from .ope import (Decision, OPEOutput, OPERequest, Predictions, Reward, Targets,
    TrainingPlan, TrainingReceipt, TrainingRow, EvaluationProtocol)

ROOT=Path(__file__).resolve().parent
ADAPTERS={"request":TypeAdapter(OPERequest),"output":TypeAdapter(OPEOutput),"roster":TypeAdapter(list[Decision]),
    "rewards":TypeAdapter(list[Reward]),"q":TypeAdapter(Predictions),"targets":TypeAdapter(Targets),
    "training-plan":TypeAdapter(TrainingPlan),"training":TypeAdapter(list[TrainingRow]),"training-receipt":TypeAdapter(TrainingReceipt),
    "protocol":TypeAdapter(EvaluationProtocol)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--check",action="store_true");args=parser.parse_args()
    for name,adapter in ADAPTERS.items():
        text=json.dumps(adapter.json_schema(),indent=2,sort_keys=True)+"\n"
        path=ROOT/("ope-"+name+".schema.json")
        if args.check:
            if path.read_text(encoding="utf-8")!=text:raise SystemExit("OPE schema drift: "+name)
        else:path.write_text(text,encoding="utf-8")
    print("PASS: ten OPE schemas match typed source" if args.check else "Exported ten OPE schemas")


if __name__=="__main__":main()
