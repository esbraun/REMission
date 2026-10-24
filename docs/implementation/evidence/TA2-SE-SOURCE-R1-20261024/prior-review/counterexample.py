from pathlib import Path
p=Path('tests/run_ta2_sampling_se_source.py').resolve()
s=p.read_text()
needle="result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_ta2_sampling_se_source'))"
replacement='''from test_ta2_sampling_se_source import fixture, canonical
        from methods.truth import sampling_se as s
        class BoundaryTests(unittest.TestCase):
            def test_extension_seed_collision_is_currently_admitted(self):
                design,*_=fixture()
                raw=design.model_dump(mode='json')
                seed=raw['planned'][0]['fit_seeds'][0]['nuts']
                raw['planned'][1]['fit_seeds'][0]['nuts']=seed+1
                parsed=s.SamplingDesign.model_validate_json(canonical(raw))
                self.assertEqual(parsed.planned[1].fit_seeds[0].nuts,parsed.planned[0].fit_seeds[0].nuts+1)
                print('OBSERVED: independently planned cohort initial nuts seed equals first cohort permitted extension seed')
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BoundaryTests))'''
assert s.count(needle)==1
s=s.replace(needle,replacement).replace("ROOT/'artifacts/ta2-sampling-se-source'","ROOT/'artifacts/ta2-independent-review'")
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
