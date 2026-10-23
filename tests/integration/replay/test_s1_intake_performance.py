"""Scalar path and causal-reference regressions; no accepted archive or Store."""
from datetime import timedelta
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from contracts.domain.evidence_v2 import exact_ref,projection_hash
from contracts.runs.common import Artifact,canonical,sha256
from contracts.runs.support_research import read_artifact
from services.foundation.protocol import project_protocol
from support_archive_fixtures import START,history,record
from test_support_archive import SupportFixture


class ArtifactAncestryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.path=self.root/'nested'/'proof.json'
        self.path.parent.mkdir();self.path.write_bytes(b'{}')
        self.artifact=Artifact(id='scalar-proof',path='nested/proof.json',sha256=sha256(b'{}'),bytes=2,
            role='observed',media_type='application/json')

    def tearDown(self):self.temp.cleanup()

    def test_ordinary_nested_read_rechecks_changed_bytes_and_size(self):
        self.assertEqual(read_artifact(self.root,self.artifact),b'{}')
        self.path.write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError,'hash_or_size'):read_artifact(self.root,self.artifact)
        self.path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'hash_or_size'):
            read_artifact(self.root,self.artifact.model_copy(update={'bytes':3}))

    def test_link_and_reparse_metadata_at_leaf_parent_root_and_ancestor(self):
        real_lstat=Path.lstat
        # Inject filesystem metadata at its boundary so Windows privilege and
        # host filesystem do not hide either POSIX links or Windows reparses.
        for target in (self.path,self.path.parent,self.root,self.root.parent):
            for link in (True,False):
                with self.subTest(target=str(target),symlink=link):
                    def metadata(path,*args,**kwargs):
                        if path==target:
                            return SimpleNamespace(st_mode=stat.S_IFLNK if link else stat.S_IFDIR,
                                st_file_attributes=0 if link else stat.FILE_ATTRIBUTE_REPARSE_POINT)
                        return real_lstat(path,*args,**kwargs)
                    with patch.object(Path,'lstat',metadata):
                        with self.assertRaisesRegex(ValueError,'symlink_support_artifact_denied'):
                            read_artifact(self.root,self.artifact)

    def test_missing_directory_hardlink_and_escape_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'unreadable'):
            read_artifact(self.root,self.artifact.model_copy(update={'path':'absent.json'}))
        with self.assertRaisesRegex(ValueError,'ordinary_unlinked'):
            read_artifact(self.root,self.artifact.model_copy(update={'path':'nested'}))
        import os
        alias=self.root/'alias.json';os.link(self.path,alias)
        with self.assertRaisesRegex(ValueError,'ordinary_unlinked'):read_artifact(self.root,self.artifact)
        alias.unlink()
        (self.root/'outside.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'support_artifact_escape'):
            read_artifact(self.path.parent,self.artifact.model_copy(update={'path':'../outside.json'}))


class S1IntakeSourceTests(SupportFixture):
    def context_history(self,mode):
        trajectory=next(t for t in self.package[2].descriptor.trajectories if t.mode==mode)
        original=self.verified.histories[trajectory.partition_id]
        records=[r for r in original.records if r.kind not in {'support_stage_closure','support_outcome_link'}]
        isi=record(original.patient_id,'context-isi',START-timedelta(minutes=1),'isi',
            instrument_version='ISI-fixture',recall_days=14,recall_start=(START-timedelta(days=14,minutes=1)).isoformat(),
            recall_end=(START-timedelta(minutes=1)).isoformat(),items=[0]*7)
        records.append(isi)
        full=history(original.patient_id,records)
        decision=next(r for r in full.records if r.kind=='support_decision')
        consent=next(r for r in full.records if r.kind=='consent')
        changed=decision.model_copy(update={'context':[exact_ref(consent),exact_ref(isi)],
            'context_projection_sha256':projection_hash(full,decision.cutoff)})
        return history(full.patient_id,[changed if r.record_id==decision.record_id else r for r in full.records])

    def project(self,full,day=14):
        return project_protocol(full,START+timedelta(days=day),family='support',origin=START)

    def test_selected_and_omitted_context_positive_at_all_three_cuts(self):
        for mode in ('S0','S1'):
            full=self.context_history(mode)
            for day in (14,42,84):
                with self.subTest(mode=mode,day=day):
                    value=self.project(full,day)
                    decision=next(r for r in value.records if r.kind=='support_decision')
                    self.assertEqual([r.record_id for r in decision.context],['consent'])
                    self.assertFalse(any(r.kind=='isi' for r in value.records))
                    consent=next(r for r in value.records if r.record_id=='consent')
                    self.assertEqual(decision.context[0].projection_sha256,sha256(canonical(consent.model_dump(mode='json'))))

    def test_bad_exact_hash_rejected_for_selected_and_omitted_context(self):
        for identifier in ('consent','context-isi'):
            full=self.context_history('S1')
            decision=next(r for r in full.records if r.kind=='support_decision')
            refs=[r.model_copy(update={'payload_sha256':'0'*64}) if r.record_id==identifier else r for r in decision.context]
            changed=decision.model_copy(update={'context':refs})
            full=history(full.patient_id,[changed if r.record_id==decision.record_id else r for r in full.records])
            with self.subTest(identifier=identifier),self.assertRaisesRegex(ValueError,'exact_dependency_hash_patient_type_mismatch'):
                self.project(full)

    def test_omitted_context_strict_causal_cutoff_and_later_correction(self):
        full=self.context_history('S1')
        isi=next(r for r in full.records if r.kind=='isi')
        decision=next(r for r in full.records if r.kind=='support_decision')
        late=isi.model_copy(update={'recorded_at':START,'available_at':START})
        changed=history(full.patient_id,[late if r.record_id==isi.record_id else r for r in full.records])
        rebound=decision.model_copy(update={'context':[exact_ref(late) if r.record_id==isi.record_id else r for r in decision.context],
            'context_projection_sha256':projection_hash(changed,START)})
        changed=history(full.patient_id,[rebound if r.record_id==decision.record_id else r for r in changed.records])
        with self.assertRaisesRegex(ValueError,'stale_or_not_visible_dependency'):self.project(changed)
        for status in ('corrected','retracted'):
            corrected=isi.model_copy(update={'record_id':'isi-correction','revision':2,'supersedes':isi.record_id,
                'record_status':status,'recorded_at':START+timedelta(seconds=1),'available_at':START+timedelta(seconds=1)})
            with self.subTest(status=status),self.assertRaisesRegex(ValueError,'stale_or_not_visible_dependency'):
                self.project(history(full.patient_id,[*full.records,corrected]))

    def test_context_mutation_between_projections_is_not_cached(self):
        full=self.context_history('S1');self.project(full)
        isi=next(r for r in full.records if r.kind=='isi')
        isi.items[0]=1
        with self.assertRaisesRegex(ValueError,'support_context_full_audit_projection_mismatch'):self.project(full)


if __name__=='__main__':unittest.main()
