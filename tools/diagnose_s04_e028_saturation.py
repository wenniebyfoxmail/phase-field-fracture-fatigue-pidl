"""Producer-only read-only NN forward and local map AD. No optimizer or solve."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import torch


def main(args):
    if sys.platform=='darwin':raise PermissionError('full production NN forward belongs on producer')
    sys.path.insert(0,str(args.source/'source'))
    import s04_e027 as old
    import s04_e028 as m
    if torch.cuda.device_count()!=1:raise ValueError('one visible GPU required')
    torch.set_num_threads(1)
    lock=json.loads((args.source/'docs/research/S04/S04-E028/data_lock.json').read_text())
    arrays=old.load_reference(args.data,lock['reference_lock']);p=old.Problem(arrays,'cuda:0')
    m.validate_current_lower(p)
    args.out.mkdir(parents=True,exist_ok=False)
    variable=(~p.fixed_d)&(p.previous<1)
    growth=(p.ref[:,2]>p.previous+1e-10)&variable
    result={'scope':'post-hoc exact saved model forward and true map derivative; no optimization/FEM/history commit',
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.source,text=True).strip(),
            'source_dirty':subprocess.check_output(['git','status','--porcelain'],cwd=args.source,text=True).strip(),
            'variable_nodes':int(variable.sum()),'target_growth_nodes':int(growth.sum()),'states':{}}
    vectors={}
    for name,path,wrapped in [('S0',args.s0,False),('B200',args.parent/'B_200.pt',True),('R200',args.parent/'R_200.pt',True)]:
        loaded=torch.load(path,map_location='cpu',weights_only=True)
        model=old.make_model(loaded['model'] if wrapped else loaded,'cuda:0')
        with torch.no_grad():raw=model(p.xy)[:,2].detach()
        r=raw.clone().requires_grad_(True)
        candidate=torch.where(r>2,.001*(r-2)+1,torch.where(r< -2,.001*(r+2),r/4+.5))
        d=m.project_damage(candidate,p.previous,p.fixed_d)
        derivative=torch.autograd.grad(d.sum(),r)[0]
        margin=raw-(4*p.previous-2)
        def stats(mask):
            vals=margin[mask];g=derivative[mask]
            return dict(nodes=int(mask.sum()),raw_margin_min=float(vals.min()),raw_margin_median=float(vals.median()),raw_margin_max=float(vals.max()),
                below_lower_fraction=float((vals<0).double().mean()),nonzero_true_derivative_fraction=float((g!=0).double().mean()),
                derivative_min=float(g.min()),derivative_max=float(g.max()),damage_increment_max=float((d.detach()[mask]-p.previous[mask]).max()))
        result['states'][name]=dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            variable=stats(variable),target_growth=stats(growth),global_damage_equals_lower=bool(torch.equal(d.detach(),p.previous)))
        for key,val in [('NN_raw',raw),('candidate_before_projection',candidate.detach()),('raw_minus_lower_threshold',margin),('true_dd_draw',derivative),('physical_d',d.detach())]:vectors[name+'_'+key]=val.cpu().numpy()
        del model,loaded,r,candidate,d,derivative,raw
    vectors['lower']=p.previous.cpu().numpy();vectors['target']=p.ref[:,2].cpu().numpy();vectors['variable']=variable.cpu().numpy();vectors['target_growth']=growth.cpu().numpy()
    np.savez_compressed(args.out/'saturation_vectors.npz',**vectors)
    (args.out/'saturation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for n in ['source','data','parent','s0','out']:ap.add_argument('--'+n,type=Path,required=True)
    main(ap.parse_args())
