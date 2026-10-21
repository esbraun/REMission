"""Re-admit the unchanged independently authored full-horizon public wire."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from contracts.runs.admission_v2 import verify_export_v2
from contracts.runs.observed_v2 import ExportAuthorityV2

out = Path(__file__).resolve().parent / 'reviewer-surviving/full-horizon-addendum/complete-attempt-002'
root = out / 'wire'
authority = ExportAuthorityV2.model_validate_json((root / 'authority.json').read_bytes())
manifest, partitions = verify_export_v2((root / 'manifest.json').read_bytes(), root, authority)
assert manifest.status == 'complete' and authority.allow_contract_fixture
calendar = json.loads((out / 'independent-calendar.json').read_bytes())
records = partitions[0][1].records
decisions = sorted((r for r in records if r.kind == 'support_decision'), key=lambda r: r.decision_index)
for decision, expected in zip(decisions, calendar, strict=True):
    assert decision.decision_index == expected['index']
    assert decision.event_at == datetime.fromisoformat(expected['decision_at'])
    assert decision.outcome_window.assessment_at == datetime.fromisoformat(expected['assessment_at'])
origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
reports = [r for r in records if r.kind == 'daily_report']
assert len(reports) == 84 and max(r.event_at for r in reports) == origin + timedelta(days=84, hours=7)
delayed = next(r for r in reports if r.event_at == origin + timedelta(days=84, hours=7))
assert delayed.available_at == origin + timedelta(days=85, hours=8, minutes=1)
final = next(r for r in records if r.kind == 'support_outcome_link' and r.assessment_at == origin + timedelta(days=85, hours=7))
assert final.reward.status == 'undefined' and final.reward.reason == 'outside_generated_horizon' and final.reward.report_ref is None
print('PASS: unchanged independent full85 wire and direct calendar re-admitted; delayed day84 report and day85 administrative endpoint retained; fixture authority only')
