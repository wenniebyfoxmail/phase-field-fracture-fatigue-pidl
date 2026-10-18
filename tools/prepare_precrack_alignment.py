"""Read-only preparation: saved U=0 NN/FEM inputs and exact nodal-map checks.

No optimizer, fitting, recovery solve, target loading or history commit exists
in this program. Saved models are evaluated once in bounded CPU chunks.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np,h5py,torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile'),str(ROOT/'tools')]
from network import NeuralNet
from field_computation import NonsmoothSigmoid
from nodal_damage_alignment import NodalDamageAlignment
from audit_saved_physical_parity import Probe


def main(a):
    torch.set_num_threads(1);a.out.mkdir(exist_ok=False,parents=True)
    state=torch.load(a.origin/'u0_network.pt',map_location='cpu',weights_only=True)
    ck=torch.load(a.origin/'u0_checkpoint.pt',map_location='cpu',weights_only=False)
    assert ck['history_storage']=='q4_gp4' and ck['damage_history_storage']=='previous_accepted_nodal'
    assert ck['mesh_connectivity_arity']==4 and ck['history_driver_mode']=='current_active'
    for key in ['hist_fat','psi_plus_prev','psi_history_elem']:
        assert torch.count_nonzero(ck[key])==0, key
    with h5py.File(a.fem_initial) as h:
        canonical=np.array(h['node_coords']).T;cells=np.array(h['connectivity']).T.astype(int)-1
        d64=np.array(h['common/d']).ravel();free=np.array(h['free_dof_d']).ravel().astype(int)-1
        assert np.count_nonzero(h['common/u']) == np.count_nonzero(h['common/raw']) == 0
        history=np.array(h['common/history'])
        assert np.count_nonzero(history[:3]) == 0 and np.all(history[3] == 1)
        assert np.array_equal(np.array(h['common/lower']).ravel(), d64)
    with h5py.File(a.fem_state0) as h:
        assert np.array_equal(canonical,np.array(h['state0_node']).T)
        state0_error=float(np.max(abs(d64-np.array(h['state0_p_field']).ravel())))
        assert state0_error <= 1e-10, 'common initial does not reproduce original FEM state0'
    assert canonical.shape==(86756,2) and cells.shape==(86408,4)
    xy=torch.tensor(canonical,dtype=torch.float32);d0=torch.tensor(d64,dtype=torch.float32)
    fixed=torch.ones(len(xy),dtype=torch.bool);fixed[free]=False;assert fixed.sum()==251
    net=NeuralNet(2,3,8,400,'TrainableReLU',1.);net.load_state_dict(state);net.eval()
    with torch.inference_mode():raw=torch.cat([net(q)[:,2] for q in xy.split(1024)]).clone()
    s=NonsmoothSigmoid(2.,1e-3);legacy=s(raw)
    hist=ck['hist_alpha'].detach().clone()
    assert hist.shape==legacy.shape and float((hist-legacy).abs().max())<1e-5
    b=NodalDamageAlignment(xy,mode='hard_line',expected_crack_mask=fixed)
    c=NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d0,raw_reference=raw,expected_crack_mask=fixed)
    fields={'A_legacy':legacy,'B_hard_line':b(xy,raw,s),'C_FEM_initial':c(xy,raw,s)}
    histories={'A_legacy':hist,'B_hard_line':b.initial_history(hist),'C_FEM_initial':c.initial_history(hist)}
    assert torch.equal(fields['C_FEM_initial'],d0) and torch.equal(histories['C_FEM_initial'],d0)
    assert torch.equal(fields['B_hard_line'][~fixed],legacy[~fixed])
    assert all(bool((fields[k][fixed]==1).all()) for k in ['B_hard_line','C_FEM_initial'])
    r=raw.clone().requires_grad_(True);v=c(xy,r,s);g=torch.autograd.grad(v.sum(),r)[0]
    assert torch.count_nonzero(g[fixed])==0 and bool((g[~fixed]>0).all())
    # Arbitrary probe queries must use the native-Q4 reconstruction, not the map.
    yy=np.linspace(-.03,.03,1201);query=np.c_[np.zeros_like(yy),yy]
    probe=Probe(canonical,cells,query)
    profiles={'y':yy,'FEM_U0':probe.value(d64)}
    rows=[]
    for name,d in fields.items():
        dn=d.detach().numpy();profiles[name]=probe.value(dn)
        rows.append(dict(arm=name,initial_Linf_to_FEM_float32=float((d-d0).abs().max()),
                         line_min=float(d[fixed].min()),line_max=float(d[fixed].max()),
                         full_min=float(d.min()),full_max=float(d.max()),
                         history_initial_Linf_to_FEM_float32=float((histories[name]-d0).abs().max())))
    torch.save({'B':b.state_dict(),'C':c.state_dict()},a.out/'mapping_buffers.pt')
    np.savez_compressed(a.out/'initial_inputs.npz',node_coords=xy.numpy(),canonical_node_coords=canonical,
       connectivity=cells,FEM_initial_damage=d0.numpy(),PIDL_U0_history=hist.numpy(),raw_origin=raw.numpy(),crack_mask=fixed.numpy())
    np.savez_compressed(a.out/'initial_profiles.npz',**profiles)
    np.savez_compressed(a.out/'initial_fields.npz',**{k:v.detach().numpy() for k,v in fields.items()})
    result=dict(status='STATIC_ALIGNMENT_VERIFIED_NOT_TRAINED',origin=str(a.origin),FEM_initial=str(a.fem_initial),
       original_FEM_state0=str(a.fem_state0),common_vs_original_state0_max=state0_error,
       execution='CPU saved-network inference and elementwise mapping only',optimizer_updates=0,FEM_solves=0,history_commits=0,
       crack_line_nodes=int(fixed.sum()),nodes=len(xy),cells=len(cells),
       original_history_vs_CPU_output_max=float((hist-legacy).abs().max()),
       FEM_float64_to_float32_max=float(abs(d0.numpy().astype(float)-d64).max()),
       initial_free_raw_derivative_min=float(g[~fixed].min()),initial_free_raw_derivative_max=float(g[~fixed].max()),
       line_raw_derivative_max=float(g[fixed].abs().max()),
       caveat='C changes initial spatial representation and its tangent, not only optimizer initialization; soft tails and free-node healing remain',arms=rows)
    (a.out/'static_receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--origin',type=Path,required=True);p.add_argument('--fem-initial',type=Path,required=True);p.add_argument('--fem-state0',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
