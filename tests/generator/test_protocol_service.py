"""Actual isolated authenticated v2 panel route and owned export controls."""
from datetime import timedelta
from pathlib import Path
import sys

import test_service as service_cases
from contracts.domain.analysis import canonical
from contracts.domain.protocol import LAW_REF,PROTOCOL_REFS
from services.foundation.protocol import export_histories
from services.foundation.store import instant


class ProtocolServiceTests(service_cases.SimulationServiceTests):
    def test_explicit_v2_panel_same_route_owner_cutoff_and_no_activation(self):
        families={}
        for family in ['nof1_med','support']:
            body=dict(schema_version='2.0.0',kind='poc_protocol_panel',seed=1245,count=2,
                family=family,law=LAW_REF,protocol=PROTOCOL_REFS[family])
            headers=self.headers('p1-'+family)
            response=self.client.post('/api/panels/generate',json=body,headers=headers)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(self.client.post('/api/panels/generate',json=body,headers=headers).json(),response.json())
            identifiers=response.json()['patient_ids'];families[family]=identifiers
            for patient in identifiers:
                current=self.workspace(patient)
                self.assertEqual(current['simulation']['protocol_status'],'not_activated')
                self.assertEqual(current['simulation']['law_version'],'poc-longitudinal-v2')
                self.assertFalse(any(o['action'].startswith('MED_') for o in current['options']))
                self.assertEqual(self.client.post('/api/patients/'+patient+'/approve',json=self.approve_payload(patient,'MED_A'),headers=self.headers()).status_code,409)
                self.assertEqual(self.step(patient,'day').status_code,200)
                self.assertEqual(self.step(patient,'day').status_code,200)
            cutoff=instant('2026-01-03T12:00:00Z')
            with self.store.transaction() as db:
                exported=export_histories(db,'alice',identifiers,cutoff)
                self.assertEqual(len(exported),2)
                self.assertEqual(any(r.kind=='isi' for r in exported[0].records),family=='nof1_med')
                with self.assertRaises(ValueError):export_histories(db,'bob',identifiers,cutoff)
                with self.assertRaises(ValueError):export_histories(db,'alice',identifiers,cutoff+timedelta(days=1))
                with self.assertRaises(ValueError):export_histories(db,'alice',[identifiers[0]]*2,cutoff)
        with self.store.transaction() as db:
            with self.assertRaises(ValueError):export_histories(db,'alice',[families['nof1_med'][0],families['support'][0]],cutoff)
        invalid=body|dict(law=LAW_REF|dict(sha256='f'*64))
        self.assertEqual(self.client.post('/api/panels/generate',json=invalid,headers=self.headers()).status_code,422)
