"""Independent saved-output arithmetic/NCC audit, no new method selection."""
import json
from datetime import datetime,timezone
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from md03_grouped_observability import BASE,GROUP,XS,YS,NAMES
from md01_cached_stage_forecast import sha,save


def independent_match(a,b,x,y):
    p=a[y-15:y+16,x-15:x+16].astype(float);p=p-p.mean()
    s=b[y-19:y+20,x-19:x+20].astype(float)
    windows=sliding_window_view(s,(31,31))
    centered=windows-windows.mean(axis=(-2,-1),keepdims=True)
    denom=np.sqrt((p*p).sum()*(centered*centered).sum(axis=(-2,-1)))
    scores=(centered*p).sum(axis=(-2,-1))/denom
    hits=np.argwhere(scores==scores.max())
    yy,xx=min(hits.tolist(),key=lambda p:((p[1]-4)**2+(p[0]-4)**2,p[0],p[1]))
    def offset(v):
        den=v[0]-2*v[1]+v[2]
        return float(np.clip(.5*(v[0]-v[2])/den,-.5,.5)) if den<0 else 0.
    dx=xx-4+(offset(scores[yy,xx-1:xx+2]) if 0<xx<8 else 0)
    dy=yy-4+(offset(scores[yy-1:yy+2,xx]) if 0<yy<8 else 0)
    return dx,dy,float(scores[yy,xx])


def main():
    root=GROUP/'R001';protected=json.loads((root/'protected_inputs.json').read_text())
    assert all(sha(p)==v for p,v in protected.items())
    summary=json.loads((root/'summary.json').read_text());spec=json.loads((root/'specification.json').read_text())
    assert spec['xs']==XS.tolist() and spec['ys']==YS.tolist()
    audit=[]
    for row in summary['rows']:
        name=row['case']
        with np.load(root/name/'evidence.npz') as z:d={k:z[k] for k in z.files}
        assert d['valid'].shape==(21,39) and np.array_equal(d['valid'],~(d['censored']|d['constant']))
        assert np.all(np.isfinite(d['jump_x'][d['valid']]))
        assert np.array_equal(d['motion_residual'],d['reference'].astype(float)-d['b_image'].astype(float))
        ix=int(np.flatnonzero(XS==2750)[0]);iy=int(np.flatnonzero(YS==1900)[0])
        assert row['center_assessable']==int(d['valid'][:,ix].sum())
        assert np.isclose(row['center']['jump_x']['median'],np.median(d['jump_x'][:,ix][d['valid'][:,ix]]))
        # Fixed midspan/mid-height probe, same footprint and six offsets; not a hot spot.
        x,y=250,180;matches=[]
        for side in [-1,1]:
            matches.append([independent_match(d['reference'],d['b_image'],x+side*off,y) for off in [24,48,72]])
        coef=np.array([4/3,1/3,-2/3])
        left=sum(coef[j]*matches[0][j][0] for j in range(3))
        right=sum(coef[j]*matches[1][j][0] for j in range(3))
        calc=right-left
        assert abs(calc-d['jump_x'][iy,ix])<.005
        min_ncc=min(p[2] for side in matches for p in side)
        assert abs(min_ncc-d['ncc_min'][iy,ix])<1e-4
        delta=d['reference'].astype(float)-d['b_image'].astype(float)
        q=delta[y-15:y+16,x-2:x+3].mean()-.5*(delta[y-15:y+16,x-13:x-5].mean()+delta[y-15:y+16,x+6:x+14].mean())
        assert abs(q-d['gap_contrast'][iy,ix])<1e-8
        assert np.isclose(d['old_fraction'][iy,ix],d['old_mask'][y-15:y+16,x-2:x+3].mean())
        if name.startswith('real_'):
            b=int(name.split('_')[-1]);old=BASE/'R002_history'/str(b) if b!=175 else BASE/'R003_target'
            with np.load(old/'arrays.npz') as z:assert np.array_equal(d['old_mask'],z['band_mask'])
        audit.append(dict(case=name,fixed_probe=[2750,1900],numpy_NCC_jump=calc,
            saved_jump=float(d['jump_x'][iy,ix]),numpy_NCC_min=min_ncc,center_matches=matches,
            injected_gap=row['known_gap'],center_median=row['center']['jump_x']['median'],
            assessable=row['assessable_probes']))
    save(GROUP/'qa.json',dict(execution='succeeded',utc=datetime.now(timezone.utc).isoformat(),
        old_protected_files=len(protected),all_old_hashes_unchanged=True,
        meaning='implementation/reproducibility checks, not independent real crack reference',
        evidence=audit))
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
