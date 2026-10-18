"""CPU-only descriptive analysis of an already saved no-step failure.

No network forward, optimizer, target FEM, tolerance change or GPU use.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import torch


def main(a):
    torch.set_num_threads(1)
    a.out.mkdir(parents=True,exist_ok=False)
    meta=json.loads((a.run/'preflight_origin_gradients.failure.json').read_text())
    v=torch.load(a.run/'preflight_origin_gradients.failure.pt',map_location='cpu',weights_only=True)
    network=torch.load(a.run/'initial_bundle.pt',map_location='cpu',weights_only=False)['network']
    assert set(v)=={'Eel','Ed','Eh','R','expected','direct'}
    assert all(t.device.type=='cpu' and t.ndim==1 and torch.isfinite(t).all() for t in v.values())
    expected,direct=v['expected'],v['direct'];delta=expected-direct
    tol=1e-6+1e-4*direct.abs();ratio=delta.abs()/tol;bad=delta.abs()>tol
    assert not torch.allclose(expected,direct,atol=1e-6,rtol=1e-4)
    assert int(bad.sum())==meta['failing_components']
    assert float(delta.abs().max())==meta['difference_Linf']
    assert math.isclose(float(delta.double().norm()),meta['difference_L2'],rel_tol=1e-10)
    assert int(delta.abs().argmax())==meta['largest_difference_flat_index']
    rows=[];failures=[];offset=0;max_abs=None
    for name,t in network.items():
        n=t.numel();sl=slice(offset,offset+n);shape=list(t.shape)
        local_abs=int(delta[sl].abs().argmax())
        local_ratio=int(ratio[sl].argmax())
        def position(flat):
            remaining=flat;coords=[]
            for size in reversed(shape):coords.append(remaining%size);remaining//=size
            return list(reversed(coords))
        def item(local):
            k=offset+local
            return dict(parameter=name,shape=shape,parameter_local_flat_index=local,
                indices_zero_based=position(local),global_flat_index=k,
                expected=float(expected[k]),direct=float(direct[k]),
                signed_difference=float(delta[k]),absolute_difference=float(delta[k].abs()),
                original_allowed_difference=float(tol[k]),ratio_to_original_tolerance=float(ratio[k]),
                fails_original_guard=bool(bad[k]))
        row=dict(parameter=name,shape='x'.join(map(str,shape)) or 'scalar',offset=offset,
            components=n,failing_components=int(bad[sl].sum()),
            difference_Linf=float(delta[sl].abs().max()),difference_L2=float(delta[sl].double().norm()),
            direct_L2=float(direct[sl].double().norm()),max_ratio_to_tolerance=float(ratio[sl].max()))
        rows.append(row)
        for local in torch.nonzero(bad[sl]).ravel().tolist():failures.append(item(local))
        if offset<=meta['largest_difference_flat_index']<offset+n:max_abs=item(local_abs)
        offset+=n
    assert offset==direct.numel()
    assert max_abs['parameter']==meta['largest_difference_parameter']
    assert max_abs['parameter_local_flat_index']==meta['parameter_local_flat_index']
    failures.sort(key=lambda q:(-q['ratio_to_original_tolerance'],q['global_flat_index']))
    beta=meta['beta'];S=meta['energy'];coeff=1/(math.log(10)*S)
    # This changes only CPU accumulation of saved parameter gradients. It is
    # not a double-precision NN replay or a replacement of the original guard.
    reaccum64=(v['Eel'].double()+v['Ed'].double()+beta*v['Eh'].double())*coeff+1e-5*v['R'].double()
    err64=reaccum64-direct.double()
    result=dict(run=str(a.run),metadata=meta,parameters=direct.numel(),
        guard='original pointwise abs(expected-direct)<=1e-6+1e-4*abs(direct)',guard_relaxed=False,
        optimizer_updates=0,history_commits=0,FEM_solves=0,analysis_device='cpu',
        maximum_absolute_difference=max_abs,failures=failures,
        failing_components=int(bad.sum()),failing_fraction=float(bad.sum())/direct.numel(),
        max_ratio_to_original_tolerance=float(ratio.max()),
        zero_raw_Eh_gradient=bool(torch.count_nonzero(v['Eh'])==0),
        final_parameter_accumulation64=dict(difference_to_direct_Linf=float(err64.abs().max()),
            difference_to_direct_L2=float(err64.norm()),
            difference_to_saved_expected_Linf=float((reaccum64-expected.double()).abs().max()),
            failing_components_at_original_tolerance=int((err64.abs()>(1e-6+1e-4*direct.double().abs())).sum()),
            scope='saved float32 component gradients only; no NN or energy replay'),
        tensors=rows,
        limitation='Quantifies disagreement and location, not a reference gradient or a confirmed root cause. No training or tolerance change.')
    (a.out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for filename,records in [('parameter_tensors.csv',rows),('violating_components.csv',failures)]:
        with (a.out/filename).open('w') as f:
            w=csv.DictWriter(f,list(records[0]));w.writeheader();w.writerows(records)
    print(json.dumps({k:x for k,x in result.items() if k not in ('tensors',)},indent=2,allow_nan=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())
