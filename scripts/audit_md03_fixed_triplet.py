"""Read-only numerical/order/hash checks; writes a separate E049 QA receipt."""
import json
from pathlib import Path
import subprocess
from datetime import datetime,timezone

import numpy as np
from md03_fixed_triplet import BASE, WORK, sha, guard


def main():
    lockpath=BASE/'R000_selection/selection_lock.json';lock=json.loads(lockpath.read_text());guard(lock)
    pp=BASE/'R002_history/predictions_before_target.json';saved=json.loads(pp.read_text())
    target=json.loads((BASE/'R003_target/summary.json').read_text())
    start=json.loads((BASE/'R003_target/start_receipt.json').read_text())
    assert sha(pp)==target['predictions_sha256']==start['prediction_sha256']
    assert saved['saved_utc']<start['started_utc']<target['target_decode_started_utc']
    assert not start['target_previously_downloaded']
    assert saved['adapter_sha256']==sha(WORK/'scripts/md03_fixed_triplet.py')
    assert saved['configuration_sha256']==sha(BASE/'history_support.json')
    assert saved['selection_sha256']==sha(lockpath)
    assert all(sha(p)==h for p,h in saved['history_assets'].items())
    folders=[BASE/'R002_history/89',BASE/'R002_history/132',BASE/'R003_target']
    areas=[];supports=[];mass=[];guide=[];geometry=[]
    for folder,f in zip(folders,lock['frames']):
        assert Path(f['source']).stat().st_size==f['bytes'] and sha(f['source'])==f['sha256']
        with np.load(folder/'arrays.npz') as z:
            mask=z['band_mask'];rows=np.count_nonzero(mask,axis=1)
            areas.append(int(np.count_nonzero(mask)));supports.append(int(np.count_nonzero(rows)))
            mass.append(float(areas[-1]/supports[-1]) if supports[-1] else None)
            assert np.array_equal(rows,z['row_mass'])
            guide.append(np.unique(z['guide_path'][:,0]).tolist())
        obs=json.loads((folder/'observation.json').read_text());geometry.append(obs['geometry'])
        assert obs['observation']['area']==areas[-1] and obs['observation']['support']==supports[-1]
        assert obs['observation']['mass']==mass[-1]
    hold=float(areas[1]);trend=float(max(0,2*areas[1]-areas[0]));ref=areas[2]
    assert saved['predictions']['persistence']==hold and saved['predictions']['secant']==trend
    assert target['absolute_area_errors']['persistence']==abs(hold-ref)
    assert target['absolute_area_errors']['secant']==abs(trend-ref)
    gain=abs(hold-ref)-abs(trend-ref)
    assert target['gains_vs_hold']['secant']==gain
    assert supports[0]==supports[1]
    assert np.isclose(saved['predictions']['support_hold'],trend)
    validation=subprocess.run([__import__('sys').executable,str(WORK/'source/validate_figure_sidecars.py'),
         str(BASE/'R004_figures')],capture_output=True,text=True,check=True)
    qa=dict(execution='succeeded',utc=datetime.now(timezone.utc).isoformat(),
       purpose='independent array counting/arithmetic/hash/order, not independent crack truth',
       areas=areas,occupied_rows=supports,row_mass=mass,guide_x=guide,geometry=geometry,
       area_gain=gain,relative_error_reduction=gain/abs(hold-ref),
       protected_files_verified=len(lock['protected']),all3official_sources_verified=True,
       saved_prediction_precedes_target_download_and_decode=True,old_scores_and_halfdepth_unchanged=True,
       skeleton_paths_are_candidate_geometry_only=True,
       sidecar_validation=json.loads(validation.stdout),
       figure_hashes={str(p):sha(p) for p in (BASE/'R004_figures').glob('F*') if p.is_file()},
       observed_readout_coverage='3/3',forecast_pair_calculability='1/1',
       independently_validated_crack_forecast_cases=0,crack_accuracy_not_measured=True,
       remaining_uncertainties=['sprayed speckles vs cracks','file-index vs acquisition order','no physical-width truth'])
    out=BASE/'qa.json'
    with out.open('x') as stream:json.dump(qa,stream,indent=2,allow_nan=False)
    print(json.dumps(qa,indent=2))


if __name__=='__main__':main()
