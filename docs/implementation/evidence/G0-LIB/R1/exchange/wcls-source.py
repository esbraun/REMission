"""Reproduce the existing deterministic fixture without rerunning any Bayesian fit."""
import csv
import math
from pathlib import Path


def definition():
    return {"schema_version": "1.0.0", "synthetic": True, "id": "wcls-fixture-v1",
            "patients": 12, "times_per_patient": 6, "prior": "not_applicable_frequentist_fixture",
            "action": "(patient+time)%2", "x": "(patient-5.5)/6+time/20",
            "y": "1+0.2*x+2*(action-0.5)+0.1*sin(patient+2*time)",
            "logging_probability": .5, "numerator_probability": .5, "availability": 1,
            "unit": "quality_points", "transform": "identity_CSV_columns",
            "provenance": "synthetic_engineering_fixture_not_clinical_data"}


def write_fixture(path: Path):
    rows = []
    for patient in range(12):
        for time in range(6):
            action = (patient+time) % 2
            x = (patient-5.5)/6+time/20
            y = 1+.2*x+2*(action-.5)+.1*math.sin(patient+2*time)
            rows.append([patient,time,y,action,.5,.5,1,x])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["id","time","y","action","logging_probability","numerator_probability","availability","x"])
        writer.writerows(rows)
