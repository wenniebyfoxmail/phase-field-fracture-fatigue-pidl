"""Nontraining real-mesh algebra/gradient check on saved raw vectors only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import s04_e027 as old
import s04_e028 as parent
import s04_e029 as m


def main(args):
    torch.set_num_threads(1);args.out.mkdir(parents=True,exist_ok=True)
    lock=json.loads((ROOT/'docs/research/S04/S04-E028/data_lock.json').read_text())['reference_lock']
    a=old.load_reference(Path(lock['root']),lock);p=old.Problem(a);parent.validate_current_lower(p)
    z=np.load(args.raw)
    assert np.array_equal(z['lower'],a['previous']) and np.array_equal(z['target'],a['ref'][:,2])
    origin=torch.as_tensor(z['S0_NN_raw'],dtype=torch.float64)
    seed=torch.as_tensor(z['S0_physical_d'],dtype=torch.float64)
    mapper=m.BoundedIncrement(p.xy,p.previous,p.fixed_d,origin,seed)
    growth=mapper.variable&(p.ref[:,2]>p.previous+1e-10)
    result=dict(protocol=m.PROTOCOL,epsilon=m.EPS,relative_transform='asinh',model_load=False,optimizer_steps=0,
        scope='deterministic saved-vector map stress test, not trained E029 predictions',
        raw_vector_sha256=hashlib.sha256(args.raw.read_bytes()).hexdigest(),checks={})
    for name in ['S0','B200','R200']:
        raw=torch.as_tensor(z[name+'_NN_raw'],dtype=torch.float64).clone().requires_grad_(True)
        d=mapper(p.xy,raw);g=torch.autograd.grad(d.sum(),raw)[0]
        assert bool((g[mapper.variable]>0).all())
        q=old.q4_interpolate(d.detach(),p.conn,p.N)
        gap=float(torch.relu(p.old_gp-q).max());upper=float(torch.relu(q-1).max())
        assert gap<1e-12 and upper<1e-12 and bool((d.detach()[p.fixed_d]==1).all())
        result['checks'][name]=dict(mapper.diagnostics(raw,growth),nodal_lower_violation=float(torch.relu(p.previous-d.detach()).max()),gp_lower_violation=gap,gp_upper_violation=upper,
            autograd_derivative_min_variable=float(g[mapper.variable].min()),autograd_derivative_max_variable=float(g[mapper.variable].max()))
    d0=mapper(p.xy,origin).detach();change=float((d0-seed).abs().max())
    assert change<=m.EPS+1e-14
    result['zero_step_max_damage_change']=change
    oldfields=np.load(args.parent_fields)['mapped0']
    assert np.array_equal(oldfields[:,2],seed.numpy())
    smooth=oldfields.copy();smooth[:,2]=d0.numpy()
    result['old_mapped0_scores']=parent.component_scores(p,torch.as_tensor(oldfields,dtype=torch.float64))
    result['smooth0_scores']=parent.component_scores(p,torch.as_tensor(smooth,dtype=torch.float64))
    np.savez_compressed(args.out/'smooth0_algebra.npz',fields=smooth)
    (args.out/'map_check.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for n in ['raw','out','parent-fields']:ap.add_argument('--'+n,type=Path,required=True)
    main(ap.parse_args())
