"""Private producer observed-data checks with independent summary arithmetic."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from contracts.domain.borrowing import SourceBundle
from services.generator.restricted import generate, _generate
from services.generator.studies import prepare


class StudyTests(unittest.TestCase):
    def test_accepted_v1_bytes_unchanged(self):
        fixtures=[dict(seed=20261021,index=0,patient_id='POC-test-01',through_day=84,actions=[]),
            dict(seed=12345,index=7,patient_id='POC-byte-07',through_day=42,actions=[
                dict(day=0,option='behavioral_continue',assignment_id='a'),
                dict(day=14,option='behavioral_escalate',assignment_id='b')])]
        expected=['08e1e38cca1c7fd5e509014ebf7bb17c11d657c303f90995b0a0c42ad255ac35',
            '293d0c1f5a6eb876744cb33157d0969925b88348312a88c6361855dcaf574b51']
        for request,digest in zip(fixtures,expected):
            raw=json.dumps(generate(request),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)

    def test_private_scenarios_and_ordinary_request_bounds(self):
        request=dict(seed=12345,index=0,patient_id='fixture',through_day=42,
            actions=[dict(day=0,option='behavioral_escalate',assignment_id='a')])
        self.assertEqual(generate(request),_generate(request,(2,4)))
        self.assertNotEqual(generate(request),_generate(request,(2,0)))
        self.assertEqual(_generate(request,(2,0)),_generate(request,(0,0)))
        with self.assertRaises(ValueError):generate(dict(request,coefficients=[0,0]))

    def test_observed_summaries_replay_counts_checksum_and_private_separation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            a=prepare(root/'a');b=prepare(root/'b')
            self.assertEqual(a['files'],b['files'])
            all_ids=[]
            for scenario in range(3):
                bundle_id=a['public_bundle_ids'][scenario]
                raw=(root/'a/public'/f'{bundle_id}.json').read_text()
                product=SourceBundle.model_validate_json(raw)
                for forbidden in ('seed','participant','coefficient','baseline_severity','response_multiplier','latent'):
                    self.assertNotIn(forbidden,raw)
                for study,s in enumerate(product.studies):
                    rows=json.loads((root/'a/private'/f'{scenario}-{study}-observed.json').read_text())
                    self.assertEqual(len(rows),120)
                    all_ids.extend(r['participant'] for r in rows)
                    arms=[np.array([r['endpoint'] for r in rows if r['option']==option]) for option in ('behavioral_continue','behavioral_escalate')]
                    self.assertEqual([len(v) for v in arms],[60,60])
                    self.assertAlmostEqual(s.d,arms[1].mean()-arms[0].mean(),places=13)
                    self.assertAlmostEqual(s.se,np.sqrt(sum(v.var(ddof=1)/60 for v in arms)),places=13)
                    for r in rows:
                        isi=[v['record'] for v in r['observed']['records'] if v['record']['kind']=='isi']
                        self.assertEqual(len(isi),4)
                        self.assertEqual(r['endpoint'],sum(isi[-1]['items']))
                        self.assertEqual(isi[-1]['recall_days'],14)
                tampered=json.loads(raw);tampered['studies'][0]['d']+=.1
                with self.assertRaises(ValueError):SourceBundle.model_validate_json(json.dumps(tampered))
                duplicate=json.loads(raw);duplicate['studies'][1]=copy.deepcopy(duplicate['studies'][0])
                with self.assertRaises(ValueError):SourceBundle.model_validate_json(json.dumps(duplicate))
                from datetime import datetime,timezone
                with self.assertRaises(ValueError):product.at_cutoff(datetime(2025,1,1,tzinfo=timezone.utc))
            self.assertEqual(len(set(all_ids)),720)


if __name__=='__main__':unittest.main()
