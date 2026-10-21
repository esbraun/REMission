"""Foundation observed-export reader. No estimator/assignment engine is present."""
import json
from pathlib import Path
from contracts.domain.boundaries import ObservedHistory


def main():
    raw=Path("/observed/history.json").read_bytes()
    history=ObservedHistory.model_validate_json(raw)
    print(json.dumps({"status":"observed_contract_validated","patient_id":history.patient_id,"record_count":len(history.records),"statistical_engine":"unavailable"}))


if __name__=="__main__":main()
