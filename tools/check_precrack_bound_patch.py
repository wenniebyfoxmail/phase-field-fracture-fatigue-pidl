"""Algebraic full-mesh patch check against saved C candidates, no NN/optimizer."""
import argparse,json,sys
from pathlib import Path
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile')]
from field_computation import NonsmoothSigmoid
from nodal_damage_alignment import NodalDamageAlignment
from q4_quadrature import q4_shape_data,q4_interpolate,q4_gradient


def main(a):
    torch.set_num_threads(1)
    z=np.load(a.run/'fixed_inputs.npz');xy=torch.tensor(z['node_coords'],dtype=torch.float32)
    cells=torch.tensor(z['connectivity'],dtype=torch.long);d0=torch.tensor(z['FEM_initial_damage'])
    line=torch.tensor(z['crack_mask']);s=NonsmoothSigmoid()
    # A dummy algebraic raw origin, NOT the saved network or GPU raw origin.
    # Invert the monotone legacy scalar map to replay existing physical values.
    reference=torch.zeros_like(d0)
    legacy=NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d0,raw_reference=reference,expected_crack_mask=line)
    bounded=NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d0,raw_reference=reference,expected_crack_mask=line,hard_lower_box=True)
    initial=bounded(xy,reference,s);assert torch.equal(initial,d0)
    d=torch.tensor(np.load(a.run/'C/update200/fields.npz')['d'])
    mapped=s(legacy.anchor_raw)+(d-d0)
    shifted=torch.where(mapped<0,mapped/.001-2,torch.where(mapped>1,(mapped-1)/.001+2,4*mapped-2))
    raw=reference+(shifted-legacy.anchor_raw)
    replay=legacy(xy,raw,s);roundtrip=float((replay-d).abs().max())
    assert roundtrip<=torch.finfo(d.dtype).eps
    feasible=bounded(xy,raw,s)
    assert bool(((feasible>=d0)&(feasible<=1)).all()) and bool((feasible[line]==1).all())
    N,B,w=q4_shape_data(xy,cells);gp=q4_interpolate(feasible,cells,N);lower_gp=q4_interpolate(d0,cells,N)
    assert bool(((gp>=lower_gp)&(gp<=1)).all())
    assert bool(torch.isfinite(q4_gradient(feasible,cells,B)).all())
    raw0=reference.clone().requires_grad_(True)
    grad=torch.autograd.grad(bounded(xy,raw0,s).sum(),raw0)[0]
    mobile=(d0<1)&(~line)
    assert bool((grad[mobile]==.25).all()) and torch.count_nonzero(grad[~mobile])==0
    # Restore the explicit opt-in; a default map must reject this new contract.
    restore=NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d0,raw_reference=reference,expected_crack_mask=line,hard_lower_box=True)
    restore.load_state_dict(bounded.state_dict());assert torch.equal(restore(xy,raw,s),feasible)
    result=dict(status='DETERMINISTIC_FEASIBILITY_PATCH_CHECK_PASS_NOT_TRAINED',nodes=len(xy),cells=len(cells),GP=int(w.numel()),
        source_C_physical_field=str(a.run/'C/update200/fields.npz'),algebraic_roundtrip_Linf=roundtrip,
        initial_damage_exact=True,hard_line_nodes=int(line.sum()),nodal_lower_violation=float(torch.relu(d0-feasible).max()),
        nodal_upper_violation=float(torch.relu(feasible-1).max()),GP_lower_violation=float(torch.relu(lower_gp-gp).max()),
        GP_upper_violation=float(torch.relu(gp-1).max()),initial_free_raw_gradient_min=float(grad[mobile].min()),
        initial_free_raw_gradient_max=float(grad[mobile].max()),state_roundtrip_exact=True,NN_inference=0,optimizer_steps=0,FEM_solves=0,
        scope='Algebraic physical-candidate replay with dummy zero raw origin, not saved-network/GPU checkpoint replay. No projected fields or FEM accuracy scores saved; original A/B/C endpoint files untouched.',
        limitations='Opt-in changes the trial space. Nodal lower is sufficient and stronger than four-point-only GP lower; clamp has nonsmooth equality convention and saturated zero gradients. Training behavior untested; not enabled in any runner/config.')
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
