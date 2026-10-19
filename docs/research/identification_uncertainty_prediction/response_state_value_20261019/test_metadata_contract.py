"""Contract tests use synthetic metadata only; never load PT or fit a predictor."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
import runner

class MetadataContract(unittest.TestCase):
    def fixture(self, root, missing_candidate=None, nonfinite=None, duplicate=False):
        (root/'probe_v1_concentration').mkdir()
        rows=[];candidates=[]
        for g in ['g1','g2','g3','g4','g5']:
            for n in range(1,101):
                rows.append(dict(group=g,stage=n,list_index=n-1,
                                 pt_member=f'published/{g}/InputData.pt',
                                 nonfinite_values=int((g,n)==nonfinite)))
                if (g,n) != missing_candidate:
                    candidates.append(dict(group=g,stage=n,status='candidate',left_px=0,
                        right_px=10,span_px=10,span_px_threshold08=12,
                        span_px_threshold125=8,center_row_from_first_frame=63))
        if duplicate:rows.append(rows[0])
        for name,data in [('pt_frame_inventory.csv',rows),
                          ('probe_v1_concentration/candidate_trajectories.csv',candidates)]:
            with (root/name).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
        for name in ['pt_structure_summary.json','full_csv_header_audit.json']:
            (root/name).write_text('{}')
        return dict(data_root=str(root),history_stage_offsets=[-20,-10,0],
                    horizon_stage_steps=[10,40],origin_stride=5,max_origins_per_group=80,
                    minimum_origins_per_group=6)

    def test_prefix_and_exact_same_chunk_horizons(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.fixture(Path(tmp));m,_,_=runner.build_manifest(c)
            self.assertEqual(len({r['group'] for r in m['cases']}),5)
            for row in m['cases']:
                self.assertLessEqual(max(row['history_stages']),row['origin_stage'])
                self.assertEqual(set(row['targets']),{'10','40'})
                self.assertEqual(row['targets']['40']-row['origin_stage'],40)

    def test_future_scalar_never_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.fixture(Path(tmp),missing_candidate=('g1',61))
            m,_,_=runner.build_manifest(c)
            self.assertTrue(any(r['group']=='g1' and r['origin_stage']==21 for r in m['cases']))

    def test_nonfinite_target_is_common_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.fixture(Path(tmp),nonfinite=('g1',61))
            m,_,_=runner.build_manifest(c)
            self.assertFalse(any(r['group']=='g1' and r['origin_stage']==21 for r in m['cases']))
            self.assertTrue(any(r['group']=='g1' and r.get('origin_stage')==21 for r in m['exclusions']))

    def test_duplicate_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.fixture(Path(tmp),duplicate=True)
            with self.assertRaises(ValueError):runner.build_manifest(c)

if __name__=='__main__':unittest.main()
