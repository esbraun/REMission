"""Extract ONE explicitly selected lawful reduced history, using stdlib only.

No generator/model import, private workspace, DB or seed is read. The accepted
public CohortInput Git blob is retained in this worktree's ignored artifacts.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
BLOB = 'e8d5c1aa51867d0317e937afe7331b479a4473dd'
PATIENT = 'p-08aa51d3e737479495085ea07881adcf'
OUT = ROOT/'artifacts'/'truth-ta1'/'input'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def main():
    raw = subprocess.check_output(['git', 'show', BLOB], cwd=ROOT)
    assert len(raw) == 335568
    assert hashlib.sha256(raw).hexdigest() == '0be1e829af83456980639e7c93553f30abfda13925d8cd40733665423b29c044'
    value = json.loads(raw)
    assert hashlib.sha256(canonical(value)).hexdigest() == 'dbca579b9c4ae174c2ec7c8ce89762b4b5c8d010bdc000164ca3df180722e889'
    assert value['cohort_sha256'] == '7f8d004352d7e68e667bff84e51b36a404653091c05f36594a4fef380f837563'
    cohort = value['cohort']
    assert cohort['manifest_sha256'] == 'e732730003e8b1b538fbac516c2905637c8dce60befa3c1150c3a119af2d4490'
    manifest = cohort['manifest']
    assert len(manifest['members']) == 12 and all(x['patient_version'] == 19 for x in manifest['members'])
    assert manifest['members'][0]['patient_id'] == PATIENT
    history = next(h for h in cohort['histories'] if h['patient_id'] == PATIENT)
    reduced = canonical(history)
    expected = '5bd8d8ebcd84ff862cb3caa8255f7b9cb8eba73aba3e2d2a7a721993743b3289'
    assert hashlib.sha256(reduced).hexdigest() == expected
    assert manifest['members'][0]['history_sha256'] == expected
    assert history['cutoff'] == manifest['cutoff'] == '2026-01-15T12:00:00Z'
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT/'public-cohort-input.json').write_bytes(raw)
    (OUT/'history.json').write_bytes(reduced)
    record = dict(public_blob=BLOB, public_raw_sha256=hashlib.sha256(raw).hexdigest(),
                  selected_patient=PATIENT, patient_version=19,
                  selection_rule='first ascending manifest patient before numerical evaluation',
                  history_raw_sha256=expected, history_canonical_sha256=expected,
                  bytes=len(reduced), history='artifacts/truth-ta1/input/history.json')
    (OUT/'extraction.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
