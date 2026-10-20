"""Read-only identity/unit/time audit of already obtained MD03 author files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy.io import loadmat

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
WORK=ROOT/'.codex/worktrees/crackmnist-tokenizer-mvp'
SRC=ROOT/'local_archive/experiments/S03-E049-MD03/reference_attachment_check_20261020/R001/unpacked/Four point bending test data'
OUT=ROOT/'local_archive/experiments/S03-E049-MD03/reference_mapping_20261020/R001'


def main():
    assert not OUT.exists()
    beams=loadmat(SRC/'beamDispData.mat',simplify_cells=True)['beamData']
    inputs=[SRC/'beamDispData.mat',SRC/'analyzeFlexuralBeamData.m']
    report=dict(started_utc=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='existing-file identity/time/units only; no fit/CV/forecast or download',
        image_filename_binding='candidate numeric-suffix to present; no explicit IMG basename in MAT',beams={},three_frames=[])
    for key,file in [('PLA3','paghdasi-PLA beam #3--07121731 copy.txt'),('PLA5','paghdasi-PLA beam #5--07121804 copy.txt')]:
        inputs.append(SRC/file);b=beams[key];td=b['testData'];raw=np.loadtxt(SRC/file)
        mt=td['datatime'].astype(int);n=td['n'].astype(int);pt=td['time'].astype(int)
        present=td['present'].astype(int); missing=td['missing'].astype(int)
        dic_t=b['time'].astype(int)
        bad=mt[n-1]!=pt
        lhs=b['Ext2']['Y']-b['Ext1']['Y']/2
        rhs=-b['Ext3']['Y']-b['Ext1']['Y']/2
        report['beams'][key]=dict(firstPhoto=int(td['firstPhoto']),folderPath=td['folderPath'],
            raw_shape=list(raw.shape),dic_data_shape=list(b['data'].shape),
            present_count=len(pt),n_time_exact_count=int(np.count_nonzero(~bad)),
            n_time_mismatches=[dict(photo_number=int(k),expected_key=int(t),n_1based=int(ix),n_actual_key=int(a))
                 for k,t,ix,a in zip(present[bad],pt[bad],n[bad],mt[n-1][bad])],
            missing_keys_absent_machine_count=int(np.count_nonzero(~np.isin(5*(missing-int(td['firstPhoto'])+1),mt))),
            missing_count=len(missing),
            photo_time_formula_exact=bool(np.array_equal(pt,5*(present-int(td['firstPhoto'])+1))),
            machine_time_matches_rounded_raw_exact=bool(np.array_equal(mt,np.rint(raw[:,0]).astype(int))),
            load_equals_raw_col2_times_4_4482=bool(np.array_equal(td['load'],raw[:,1]*4.4482)),
            lvdt_mm_equals_raw_col4_times_25_4=bool(np.array_equal(td['disp'],raw[:,3]*25.4)),
            all7_data_triplets_exact=all(np.array_equal(b['data'][:,3*(i-1)+j],b['Ext%d'%i][v])
                         for i in range(1,8) for j,v in enumerate(['Total','X','Y'])),
            stored_midspan_formula_exact=bool(np.array_equal(b['midDispYL'],lhs) and
                  np.array_equal(b['midDispYR'],rhs) and np.array_equal(b['midDispYAvg'],(lhs+rhs)/2)))
        if key=='PLA3':
            for photo in [89,132,175]:
                idx=int(np.flatnonzero(present==photo)[0]);t=int(pt[idx]);mr=np.flatnonzero(mt==t);dr=np.flatnonzero(dic_t==t)
                assert len(mr)==len(dr)==1
                m=int(mr[0]);d=int(dr[0]);assert int(n[idx])==m+1
                report['three_frames'].append(dict(filename='IMG_%04d.tif'%photo,
                    binding_status='conditional on published suffix=author photo number',beam=key,
                    photo_metadata_row_1based=idx+1,time_key=t,time_unit_status='unit not explicitly labelled on DIC time array',
                    machine_row_1based=m+1,raw_machine_time=float(raw[m,0]),dic_row_1based=d+1,
                    load_kN_author=float(td['load'][m]),lvdt_mm_author=float(td['disp'][m]),
                    dic_midspan_mm_by_author_usage=float(b['midDispYAvg'][d]),
                    old_width_reference=False,known_future_loading_input=False))
    report['inputs_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    report.update(ended_utc=datetime.now(timezone.utc).isoformat(),new_TIFF=0,new_models=0,new_scores=0,author_code_executed=False)
    OUT.mkdir(parents=True)
    (OUT/'mapping.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['beams','three_frames']},indent=2))


if __name__=='__main__':main()
