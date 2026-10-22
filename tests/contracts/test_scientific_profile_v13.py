"""Finite law/profile probes only; no production generator or stochastic pilot."""
import copy,json,unittest
from datetime import date
from pathlib import Path
from contracts.dgp import parameters,scenarios
from contracts.dgp import profile_v13 as p
from contracts.domain.temporal_v21 import TemporalContractV21,temporal_definition


class ScientificProfileV13Tests(unittest.TestCase):
    def test_all82_cells_and_every_legacy_coefficient_are_preserved(self):
        old=scenarios.scenario_manifest();new=p.scenario_manifest()
        self.assertEqual(len(new['cells']),82)
        for a,b in zip(old['cells'],new['cells'],strict=True):
            self.assertEqual({k:v for k,v in a.items() if k!='version'},
                {k:v for k,v in b.items() if k not in ('version','scientific_law_binding')})
        a=parameters.reference_parameters();b=p.reference_parameters()
        self.assertEqual({k:b['parameters'][k] for k in a['parameters']},a['parameters'])
        self.assertEqual(b['version'],'1.3.0');self.assertEqual(b['profile']['observed'],'2.1.0')

    def test_missing_unknown_or_legacy_binding_never_falls_back(self):
        for payload in [parameters.reference_parameters(),{},p.reference_parameters()|{'version':'1.2.0'}]:
            with self.assertRaises(ValueError):p.validate_parameters(payload)
        v=p.reference_parameters();del v['profile']['laws']['SIM-BURDEN-01']
        with self.assertRaises(ValueError):p.validate_parameters(v)
        v=p.scenario_manifest();v['cells'][0]['patients']=3
        with self.assertRaises(ValueError):p.validate_scenarios(v)
        with self.assertRaises(ValueError):p.resolve_cell(p.reference_parameters(),p.scenario_manifest(),'not-a-cell')
        self.assertEqual(p.resolve_cell(p.reference_parameters(),p.scenario_manifest(),'S27.regimen_change.n60')['parameters']['regimen_change_enabled']['value'],1)

    def test_burden_support_not_clipped_and_no_draw_for_D0(self):
        self.assertIsNone(p.burden_probability(0,4))
        for n,expected in [(0,.25),(2,.35),(3,.4)]:self.assertAlmostEqual(p.burden_probability(1,n),expected)
        for d,n in [(2,0),(1,4),(0,5),(True,0),(1,-1),(1,1.5)]:
            with self.assertRaises(ValueError):p.burden_probability(d,n)

    def test_local_07_windows_preserve_DST_23_and25_hours(self):
        for day,hours in [(date(2026,3,8),23),(date(2026,11,1),25),(date(2026,7,1),24)]:
            a,b=p.rating_window(day,'America/New_York');self.assertEqual((b-a).total_seconds(),hours*3600)
        a,b=p.rating_window(date(2026,3,9),'America/New_York');c,d=p.rating_window(date(2026,3,8),'America/New_York');self.assertEqual(a,d)

    def test_new_named_seed_is_keyed_without_changing_legacy_keys(self):
        key=dict(protocol='DGP1.3-SIM-BURDEN1.0.0-r1',phase='fixture',scenario='S20',replicate=0,patient='fixture-patient',time_index=7,root_seed=20261020)
        a=p.process_seed_words('subjective_support_burden',**key)
        self.assertEqual(a,p.process_seed_words('subjective_support_burden',**key))
        self.assertNotEqual(a,p.process_seed_words('synthetic_eligibility_assessment',**key))
        with self.assertRaises(ValueError):p.process_seed_words('unknown',**key)

    def test_temporal_graph_rejects_H_G_mix_and_missing_current_factor(self):
        value=temporal_definition();TemporalContractV21.model_validate_json(json.dumps(value))
        for name,edit in [('eligibility',lambda v:v.update(parents=[])),
                ('available_history',lambda v:v['parents'].append(dict(variable='current_admission_G',day_offset=0))),
                ('severity',lambda v:v['parents'].append(dict(variable='burden_full',day_offset=0)))]:
            fault=copy.deepcopy(value);edit(next(v for v in fault['variables'] if v['id']==name))
            with self.assertRaises(ValueError):TemporalContractV21.model_validate_json(json.dumps(fault))
        native=json.loads(Path('contracts/domain/temporal-v2.json').read_bytes())
        by_id={v['id']:v for v in value['variables']}
        for v in native['variables']:
            self.assertEqual({k:x for k,x in by_id[v['id']]['role_by_estimand'].items() if k!='EST-MRT-BURDEN'},v['role_by_estimand'])


if __name__=='__main__':unittest.main()
