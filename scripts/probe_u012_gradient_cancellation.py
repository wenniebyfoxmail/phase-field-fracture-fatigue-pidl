"""Zero-update gradient-vector audit of standard U0.12 archived final states."""
import argparse
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile')]
from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from compute_energy import compute_energy
from fatigue_history import compute_fatigue_degrad

STEPS=(4,5,199,200,409,410,439,440,444,445,447)

def norm(v): return float(np.linalg.norm(v))
def cosine(a,b):
    den=norm(a)*norm(b)
    return float(np.dot(a,b)/den) if den else None

def stats(vectors):
    e,d,h,f,p,r,a=vectors
    dh=d+h
    ideal=p+r
    opposite=(p!=0)&(a!=0)&(np.signbit(p)!=np.signbit(a))
    ideal_opposite=(p!=0)&(ideal!=0)&(np.signbit(p)!=np.signbit(ideal))
    wake=(p==0)&(a!=0)
    zeroed=(p!=0)&(a==0)
    return dict(parameter_count=len(p),
        norms=dict(zip(['elastic','dissipation','irreversibility','physical_energy_only','net_log_energy','regularizer','net_total'],map(norm,vectors))),
        cos_dissipation_irr=cosine(d,h),
        norm_dissipation_plus_irr=norm(dh),
        dh_residual_fraction=norm(dh)/(norm(d)+norm(h)),
        cos_physical_energy_vs_penalty=cosine(f,h),
        cos_physical_energy_vs_net_log_energy=cosine(f,p),
        cos_physical_energy_vs_total=cosine(f,a),
        decomposition_vs_direct_net_l2=norm(e+d+h-p),
        decomposition_vs_direct_net_relative=norm(e+d+h-p)/max(norm(p),1e-300),
        direct_total_vs_analytic_add_l2=norm(a-ideal),
        direct_total_vs_analytic_add_sign_count=int(np.count_nonzero(np.sign(a)!=np.sign(ideal))),
        regularizer_opposite_count=int(opposite.sum()),
        regularizer_opposite_fraction_all=float(opposite.mean()),
        regularizer_opposite_fraction_nonzero=float(opposite.sum()/max(np.count_nonzero(p),1)),
        ideal_opposite_count=int(ideal_opposite.sum()),
        physical_zero_count=int(np.count_nonzero(p==0)),
        regularizer_zero_to_nonzero_count=int(wake.sum()),
        regularizer_nonzero_to_zero_count=int(zeroed.sum()),
        total_sign_change_count=int(np.count_nonzero(np.sign(p)!=np.sign(a))),
        physical_scaled_slope_along_negative_total_gradient=float(-np.dot(f,a)),
        penalty_scaled_slope_along_negative_total_gradient=float(-np.dot(h,a)),
        physical_scaled_slope_along_negative_total_sign=float(-np.dot(f,np.sign(a))),
        penalty_scaled_slope_along_negative_total_sign=float(-np.dot(h,np.sign(a))))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--commit',required=True)
    args=ap.parse_args()
    assert torch.cuda.is_available(),'GPU-only zero-update probe'
    args.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    torch.set_num_threads(4)
    ext=torch.tensor([[-.5,.5],[-.5,.5]],device='cuda')
    pff,mat,net=construct_model(
        dict(PFF_model='AT1',se_split='volumetric',tol_ir=5e-3,residual_stiffness=0.),
        dict(mat_E=1.,mat_nu=.3,w1=1.,l0=.01),
        dict(hidden_layers=8,neurons=400,seed=1,activation='TrainableReLU',init_coeff=1.,compile=False),ext,'cuda')
    field=FieldComputation(net,ext,torch.tensor(0.,device='cuda'),torch.tensor([np.pi/2],device='cuda'),l0=.01)
    inp,conn,area,_=prep_input_data(mat,pff,dict(x_init=[-.5],y_init=[0],L_crack=[.5],angle_crack=[0]),dict(gradient_type='numerical'),str(ROOT/'SENS_tensile/meshed_geom_fem_soft_hist0.msh'),'cuda')
    assert inp.shape==(45591,2) and conn.shape==(90000,3)
    named=list(net.named_parameters());params=[p for _,p in named]
    groups={name:dict(start=sum(p.numel() for _,p in named[:i]),count=p.numel()) for i,(name,_) in enumerate(named)}
    best=args.baseline/'best_models'
    archived=np.load(best/'energy_gradient_terms_vs_cycle.npy')
    results=[]
    for j in STEPS:
        assert time.monotonic()-started<180,'Zero-step audit time cap'
        net.load_state_dict(torch.load(best/f'trained_1NN_{j}.pt',map_location='cuda',weights_only=False),strict=True)
        # Energies were logged BEFORE the j history refresh. Use j-1 history.
        checkpoint=torch.load(best/f'checkpoint_step_{j-1}.pt',map_location='cuda',weights_only=False)
        assert checkpoint['history_driver_mode']=='current_active' and not checkpoint['lagged_stiffness_enabled']
        history=checkpoint['hist_alpha'].detach()
        fatigue=compute_fatigue_degrad(checkpoint['hist_fat'].detach(),dict(loading_type='cyclic',accum_type='carrara',degrad_type='asymptotic',alpha_T=.5))
        field.lmbda=torch.tensor(.12*[.25,.5,.75,1.,0.][(j-1)%5],device='cuda')
        u,v,d=field.fieldCalculation(inp)
        terms=compute_energy(inp,u,v,d,history,mat,pff,area,conn,fatigue,irreversibility_penalty_cfg=dict(enable=True,mode='fem_gp_tri3'))
        values=np.array([float(x.detach()) for x in terms])
        reference=archived[j,1:4]
        error=np.max(np.abs(values-reference)/np.maximum(np.abs(reference),1e-30))
        assert error<2e-6,(j,values,reference,error)
        total=sum(terms);loge=torch.log10(total)
        coefficient=(1/(math.log(10)*total)).detach()
        reg=1e-5*sum(p.square().sum() for n,p in named if 'weight' in n)
        def grad(scalar,retain=True):
            gs=torch.autograd.grad(scalar,params,allow_unused=True,retain_graph=retain)
            return np.concatenate([(torch.zeros_like(p) if g is None else g).detach().cpu().numpy().ravel() for p,g in zip(params,gs)]).astype(np.float64)
        e,g_d,h=[grad(term*coefficient) for term in terms]
        f=grad((terms[0]+terms[1])*coefficient)
        p=grad(loge)
        a=grad(loge+reg,False)
        r=np.concatenate([(2e-5*x.detach() if 'weight' in n else torch.zeros_like(x)).cpu().numpy().ravel() for n,x in named]).astype(np.float64)
        vectors=(e,g_d,h,f,p,r,a)
        row=dict(step=j,cycle=(j-1)//5+1,substep=(j-1)%5+1,energies=values.tolist(),replay_energy_max_relerr=float(error),**stats(vectors))
        row['per_tensor']={}
        for name,g in groups.items():
            sl=slice(g['start'],g['start']+g['count'])
            row['per_tensor'][name]=stats(tuple(x[sl] for x in vectors))
        np.savez_compressed(args.output/f'vectors_step{j:03d}.npz',**dict(zip(['elastic','dissipation','irr','physical','net_logE','reg','net_total'],[x.astype(np.float32) for x in vectors])))
        results.append(row)
        (args.output/'results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k!='per_tensor'}),flush=True)
    receipt=dict(commit=args.commit,baseline=str(args.baseline),torch=torch.__version__,device=torch.cuda.get_device_name(0),steps=STEPS,elapsed_seconds=time.monotonic()-started,optimizer_updates=0,history_commits=0,parameter_groups=groups,
        scope='Archived final states with previous-step histories; fixed-state gradient directions only. No optimizer state in archive. Unit sign direction is fresh-RPROP proxy, not the archived adaptive update.',
        physical_slope_note='physical refers to Eel+Ed. Scaled derivatives use common positive 1/(ln(10)*S), so their signs equal raw energy directional derivative signs.')
    (args.output/'completed.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
