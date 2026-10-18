"""CPU, no optimizer: native-Q4 energy/field-gradient and coefficient audit.

Loads only the existing U0 network/checkpoint and FEM U0 initialization. Never
opens a loaded FEM target. Gradients are with respect to physical nodal fields,
NOT NN parameters. No fitting, history update, or FEM solve is present.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import h5py
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'SENS_tensile')]
from compute_energy import compute_energy
from field_computation import FieldComputation, NonsmoothSigmoid
from material_properties import MaterialProperties
from network import NeuralNet
from nodal_damage_alignment import NodalDamageAlignment
from pff_model import PFFModel
from q4_quadrature import q4_shape_data, q4_interpolate


def main(args):
    torch.set_num_threads(1)
    torch.manual_seed(1)
    args.out.mkdir(parents=True, exist_ok=False)
    with h5py.File(args.fem_initial) as h:
        xy = torch.tensor(np.array(h['node_coords']).T, dtype=torch.float32)
        cells = torch.tensor(np.array(h['connectivity']).T.astype(int)-1)
        d0 = torch.tensor(np.array(h['common/d']).ravel(), dtype=torch.float32)
    assert xy.shape == (86756,2) and cells.shape == (86408,4)
    ck = torch.load(args.origin/'u0_checkpoint.pt', map_location='cpu', weights_only=False)
    for k in ('hist_fat', 'psi_plus_prev', 'psi_history_elem'):
        assert torch.count_nonzero(ck[k]) == 0
    net = NeuralNet(2, 3, 8, 400, 'TrainableReLU', 1.)
    net.load_state_dict(torch.load(args.origin/'u0_network.pt', map_location='cpu', weights_only=True))
    net.eval()
    base = FieldComputation(net, xy.new_tensor([[-.5,.5],[-.5,.5]]),
                            xy.new_tensor([.02999988]), xy.new_tensor([math.pi/2]))
    captured = []
    hook = net.register_forward_hook(lambda m,i,o: captured.append(o[:,2].detach().clone()))
    with torch.no_grad():
        u, v, _ = base.fieldCalculation(xy)
    hook.remove()
    mapping = NodalDamageAlignment(xy, mode='fem_initial', initial_damage=d0,
                                  raw_reference=captured[0])
    with torch.no_grad():
        mapped = mapping(xy, captured[0], NonsmoothSigmoid(2.,1e-3))
    assert torch.equal(mapped, d0)
    shape, _, weights = q4_shape_data(xy, cells)
    mat = MaterialProperties(1., .3, 1., .01)
    cfg = {'enable':True, 'mode':'fem_gp_q4', 'spatial_integration':'native_q4_gp4'}
    rows = []
    equivalence = []
    for state in ('C_update0', 'prescribed_1e-4_healing'):
        # Counterfactual is a physical-field probe, never a network update.
        d = d0.clone()
        if state != 'C_update0':
            d[~mapping.crack_mask] -= 1e-4 * d0[~mapping.crack_mask]
        leaves = [z.detach().clone().requires_grad_(True) for z in (u,v,d)]
        eel, ed, eh = compute_energy(xy,*leaves,d0,mat,PFFModel('AT1','volumetric',.005),
                                    weights.sum(1),cells,f_fatigue=1.,irreversibility_penalty_cfg=cfg)
        # Pad so all gradients occupy the same physical-field space.
        def grad_all(e):
            g = torch.autograd.grad(e,leaves,retain_graph=True,allow_unused=True)
            return torch.cat([(torch.zeros_like(p) if z is None else z).ravel() for p,z in zip(leaves,g)])
        gel, ged, geh = [grad_all(e) for e in (eel,ed,eh)]
        e2 = compute_energy(xy,*leaves,d0,mat,PFFModel('AT1','volumetric',.001),
                            weights.sum(1),cells,f_fatigue=1.,irreversibility_penalty_cfg=cfg)
        weighted = eel+ed+25*eh
        direct = sum(e2)
        diff = float((grad_all(weighted)-grad_all(direct)).abs().max())
        assert torch.allclose(weighted,direct,rtol=2e-6,atol=1e-9)
        assert torch.allclose(grad_all(weighted),grad_all(direct),rtol=2e-5,atol=1e-7)
        equivalence.append(dict(state=state,energy_difference=float((weighted-direct).detach()),
                                nodal_gradient_difference_Linf=diff))
        for multiplier in (1.,25.):
            energy = eel + ed + multiplier*eh
            grad = grad_all(torch.log10(energy))
            expected = (gel+ged+multiplier*geh)/(math.log(10)*energy.detach())
            assert torch.allclose(grad,expected,rtol=1e-4,atol=1e-6)
            rows.append(dict(state=state,hist_loss_weight=multiplier,
                effective_gamma=16875*multiplier,Eel=float(eel.detach()),Ed=float(ed.detach()),
                Ehist_base=float(eh.detach()),Ehist_weighted=float((multiplier*eh).detach()),
                total=float(energy.detach()),log10=float(torch.log10(energy).detach()),
                nodal_gradient_L2=float(grad.double().norm()),
                grad_Eel_L2=float(gel.double().norm()),grad_Ed_L2=float(ged.double().norm()),
                grad_Ehist_base_L2=float(geh.double().norm()),
                chain_error_Linf=float((grad-expected).abs().max())))
        if state=='C_update0':
            assert float(eh.detach())==0 and torch.count_nonzero(geh)==0
        else:
            assert float(eh.detach())>0 and geh.norm()>0
    reg=sum(float(p.detach().double().square().sum()) for n,p in net.named_parameters() if 'weight' in n)
    reg_grad_norm=2*math.sqrt(reg)
    # Scalar chain checks only: not an optimizer/parameter update.
    z=torch.tensor([.1,.2,.3],dtype=torch.float64,requires_grad=True)
    g1=torch.autograd.grad(torch.log10(z.square().sum()),z,retain_graph=True)[0]
    g2=torch.autograd.grad(torch.log10(25*z.square().sum()),z)[0]
    assert torch.allclose(g1,g2,rtol=1e-14,atol=1e-14)
    assert PFFModel('AT1','volumetric',.001).irrPenalty()==421875
    result=dict(status='DETERMINISTIC_NO_TRAINING',source_commit=args.source_commit,
        origin=str(args.origin),fem_initial=str(args.fem_initial),loaded_FEM_targets_read=False,
        optimizer_updates=0,history_commits=0,FEM_solves=0,device='cpu',
        gradient_space='physical nodal u/v/d; not NN parameter gradients or RPROP sign flips',
        regularizer_sum_weights_squared=reg,regularizer_at_1e_5=1e-5*reg,
        regularizer_parameter_gradient_L2_at_1e_5=1e-5*reg_grad_norm,
        whole_energy_scaling_gradient_max_difference=float((g1-g2).abs().max()),
        gamma_ratio=25,beta_vs_tol_equivalence=equivalence,rows=rows,
        limitation='No loaded-state accuracy evidence or full-NN gradient conflict measurement; physical field probe need not be network-representable.')
    (args.out/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--origin',type=Path,required=True)
    p.add_argument('--fem-initial',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-commit',required=True)
    main(p.parse_args())
