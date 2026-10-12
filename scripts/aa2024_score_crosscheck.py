"""Read-only closed-form projection crosscheck; no q or mechanics fitting."""
import argparse
import json
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('validation',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
with np.load(a.validation/'validation_fields.npz',allow_pickle=False) as z:
    f={k:z[k] for k in z.files}
w=f['weights'];xy=f['xy'];center=np.sum(w[:,None]*xy,axis=0)/w.sum()
pos=xy-center
rotation=np.column_stack((-pos[:,1],pos[:,0]))
out={}
for k in ('candidate','secant','intact','d0_only'):
    r=f[k]-f['target']
    shift=np.sum(w[:,None]*r,axis=0)/w.sum()
    theta=np.sum(w*np.sum(rotation*(r-shift),axis=1))/np.sum(w*np.sum(rotation**2,axis=1))
    projected=r-shift-theta*rotation
    out[k]={'vector_MAE_mm':float(np.sum(w*np.sqrt(np.sum(projected**2,axis=1)))/w.sum()),
        'stored_residual_max_abs_difference_mm':float(np.max(np.abs(projected-f[k+'_residual']))),
        'all_finite':bool(np.isfinite(projected).all())}
report={'method':'closed form centered weighted rigid projection; elementwise sums, no BLAS matmul or lstsq',
    'eligible':len(xy),'comparisons':out,
    'limits':'arithmetic crosscheck only; not independent scientific review or physical identification'}
a.output.write_text(json.dumps(report,indent=2,allow_nan=False))
print(json.dumps(report,indent=2))
