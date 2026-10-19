"""Separate scalar, saved-matrix, sign and sampling audit; no image fitting."""
import json
from pathlib import Path
import sys
from datetime import datetime,timezone
import numpy as np
from md03_fixed_triplet import BASE
from md01_cached_stage_forecast import sha, save


def main():
    root=BASE/'D3_20261019';run=root/'R001'
    protected=json.loads((run/'protected_inputs.json').read_text())
    assert all(sha(p)==h for p,h in protected.items())
    spec=json.loads((run/'input_specification.json').read_text())
    summary=json.loads((run/'summary.json').read_text())
    h=json.loads((BASE/'R002_history/predictions_before_target.json').read_text())
    t=json.loads((BASE/'R003_target/summary.json').read_text())
    expected=[h['history_view_diagnostic']['affine_roi_pixels'],t['target_view_diagnostic']['affine_roi_pixels']]
    roi,band=spec['roi'],spec['band'];bx,by=band[0]-roi[0],band[1]-roi[1]
    rows=[]
    for row,m in zip(summary['rows'],expected):
        a,b=row['pair'];assert row['matrix']==m
        with np.load(run/f'{a}_{b}/residual_arrays.npz') as z:d={k:z[k] for k in z.files}
        v=d['common_valid'];assert v.shape==(360,500) and v.dtype==bool
        assert np.array_equal(d['d0'],d['a'].astype(float)-d['b'].astype(float))
        assert np.array_equal(d['d1'],d['warped_a'].astype(float)-d['b'].astype(float))
        for key,kind in [('d0','raw'),('d1','compensated')]:
            val=d[key][v].astype(float)
            assert np.isclose(np.mean(abs(val)),row[kind]['mean_abs'],rtol=0,atol=1e-10)
            assert np.isclose(np.sqrt(np.mean(val**2)),row[kind]['rmse'],rtol=0,atol=1e-10)
        # Independently invert homogeneous matrix and hand-calculate bilinear interpolation
        # at a deterministic21x21 interior grid. No OpenCV warp/remap in this audit.
        mat=np.vstack([m,[0,0,1]]);inv=np.linalg.inv(mat)
        xx,yy=np.meshgrid(np.linspace(16,483,21,dtype=int),np.linspace(16,343,21,dtype=int))
        xx=xx.ravel();yy=yy.ravel()
        # Explicit tiny-array arithmetic avoids spurious BLAS floating-status
        # warnings seen in this runtime; finite results required, never silenced.
        p=inv[:,0,None]*(xx+bx)+inv[:,1,None]*(yy+by)+inv[:,2,None]
        assert np.isfinite(p).all()
        sx,sy=p[0]-bx,p[1]-by;ix,iy=np.floor(sx).astype(int),np.floor(sy).astype(int)
        assert np.all((ix>=0)&(iy>=0)&(ix+1<500)&(iy+1<360))
        fx,fy=sx-ix,sy-iy
        q00=d['a'][iy,ix];q10=d['a'][iy,ix+1];q01=d['a'][iy+1,ix];q11=d['a'][iy+1,ix+1]
        exact=(1-fx)*(1-fy)*q00+fx*(1-fy)*q10+(1-fx)*fy*q01+fx*fy*q11
        err=abs(exact-d['warped_a'][yy,xx])
        horizontal=np.maximum(abs(q10-q00),abs(q11-q01))
        vertical=np.maximum(abs(q01-q00),abs(q11-q10))
        # OpenCV uses quantised interpolation weights, unlike ideal bilinear formula.
        tolerance=(horizontal+vertical)/16+.02
        assert np.all(err<=tolerance)
        old=BASE/'R002_history'/str(b) if b!=175 else BASE/'R003_target'
        with np.load(old/'arrays.npz') as z:assert np.array_equal(d['old_mask_b'],z['band_mask'])
        rows.append(dict(pair=[a,b],independent_bilinear_grid_points=len(xx),
                         max_sampling_quantisation_error=float(err.max()),
                         sampling_direction_and_scalar_checks=True))
    save(root/'qa_v2.json',dict(execution='succeeded',utc=datetime.now(timezone.utc).isoformat(),
         protected_old_files=len(protected),all_protected_hashes_unchanged=True,checks=rows,
         meaning='Implementation/scalar agreement only; no crack truth or physical registration proof'))
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
