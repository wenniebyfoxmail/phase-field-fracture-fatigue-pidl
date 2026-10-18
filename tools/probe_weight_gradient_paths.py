"""Producer no-step arithmetic controls on the original saved C GPU bundle."""
import argparse,json,os,sys,time
from pathlib import Path
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile'),str(ROOT/'tools')]
from run_loss_weight_pair import make_field
from run_physical_symmetry_pilot import dump
from nodal_damage_alignment import NodalDamageAlignment
from material_properties import MaterialProperties
from pff_model import PFFModel
from compute_energy import compute_energy
from q4_quadrature import q4_shape_data
from loss_weight_diagnostics import flatten_grad,flatten_vjp,norm


def compare(a,b):
    diff=a-b;limits=1e-6+1e-4*b.abs()
    return dict(Linf=float(diff.abs().max()),L2=norm(diff),relative_L2=norm(diff)/norm(b) if norm(b) else None,
        failing=int((diff.abs()>limits).sum()),max_tolerance_ratio=float((diff.abs()/limits).max()),bitwise_equal=bool(torch.equal(a,b)))


def main(a):
    started=time.monotonic()
    assert torch.cuda.is_available() and os.environ.get('CUDA_VISIBLE_DEVICES') is not None
    r=json.loads(a.recipe.read_text());assert r['GPU']==os.environ['CUDA_VISIBLE_DEVICES']
    assert json.loads((ROOT/'RUN_PROVENANCE.json').read_text())['commit']==r['commit']
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(1)
    device=torch.device('cuda:0');torch.cuda.set_device(device)
    torch.cuda.set_per_process_memory_fraction(22*1024**3/torch.cuda.get_device_properties(0).total_memory)
    assert Path(r['initial_inputs']).stat().st_size==3271767
    assert a.bundle.stat().st_size==6333769 and a.saved_vectors.stat().st_size==27008473
    z=np.load(r['initial_inputs']);x=torch.tensor(z['node_coords'],device=device)
    cells=torch.tensor(z['connectivity'],device=device,dtype=torch.long);d0=torch.tensor(z['FEM_initial_damage'],device=device)
    assert x.shape==(86756,2) and cells.shape==(86408,4) and x.dtype==torch.float32
    bundle=torch.load(a.bundle,map_location=device,weights_only=False)
    adapter=NodalDamageAlignment(x,mode='fem_initial',initial_damage=d0,raw_reference=torch.zeros_like(d0))
    adapter.load_state_dict(bundle['mapper']);field=make_field(bundle['network'],device,adapter)
    frozen={k:v.clone() for k,v in adapter.named_buffers()};state={k:v.clone() for k,v in field.net.state_dict().items()}
    params=list(field.net.parameters());capture={}
    def raw_hook(m,i,o):capture['raw']=o
    def layer_hook(m,i,o):capture['X']=i[0];capture['affine']=o
    handles=[field.net.register_forward_hook(raw_hook),field.net.hidden_layers[3].register_forward_hook(layer_hook)]
    u,v,d=field.fieldCalculation(x)
    for h in handles:h.remove()
    assert torch.equal(d,d0)
    _,_,w=q4_shape_data(x,cells)
    ee=compute_energy(x,u,v,d,d0,MaterialProperties(1.,.3,1.,.01),PFFModel('AT1','volumetric',.005,residual_stiffness=0.),
        w.sum(1),cells,f_fatigue=1.,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4','spatial_integration':'native_q4_gp4'})
    reg=sum(p.square().sum() for name,p in field.net.named_parameters() if 'weight' in name)
    raw={k:flatten_grad(e,params) for k,e in zip(['Eel','Ed','Eh','R'],(*ee,reg))}
    saved=torch.load(a.saved_vectors,map_location=device,weights_only=False)
    assert float(ee[2])==0 and torch.count_nonzero(raw['Eh'])==0
    result=dict(commit=r['commit'],GPU=r['GPU'],torch=torch.__version__,dtype=str(x.dtype),
        initial_C_exact=True,optimizer_updates=0,history_commits=0,FEM_solves=0,
        finite_guard='allclose atol1e-6 rtol1e-4 unchanged',
        allow_tf32=torch.backends.cuda.matmul.allow_tf32,autocast=torch.is_autocast_enabled(),
        source_bundle=str(a.bundle),source_vectors=str(a.saved_vectors),rows=[])
    for beta in [1.,25.]:
        total=ee[0]+ee[1]+beta*ee[2];coeff=1/(np.log(10.)*total.detach())
        seeds=(coeff,coeff,beta*coeff,torch.full_like(reg,1e-5))
        loss=torch.log10(total)+1e-5*reg
        direct=flatten_grad(loss,params);repeat=flatten_grad(loss,params)
        joint=flatten_vjp((*ee,reg),params,seeds)
        presplit=sum(flatten_vjp((e,),params,(s,)) for e,s in zip((*ee,reg),seeds))
        post=sum(raw[k]*s for k,s in zip(raw,seeds))
        rawout=capture['raw'];gout=torch.autograd.grad(loss,rawout,retain_graph=True)[0].detach()
        # Collapse at the actual NN output, traversing the NN reverse graph once.
        via_raw=flatten_vjp((rawout,reg),params,(gout,seeds[-1]))
        row=dict(beta=beta,energy=float(total.detach()),direct_repeat=compare(repeat,direct),joint_manual_VJP=compare(joint,direct),
            prescaled_separate_VJPs=compare(presplit,direct),postscaled_parameter_sum=compare(post,direct),
            single_NN_VJP_from_actual_output_adjoint=compare(via_raw,direct))
        if beta==1:
            row['saved_original_direct']=compare(direct,saved['direct'])
            row['saved_original_postsum']=compare(post,saved['expected'])
            row['saved_raw_components_bitwise_equal']={k:bool(torch.equal(raw[k],saved[k])) for k in raw}
            mask=(saved['expected']-saved['direct']).abs()>1e-6+1e-4*saved['direct'].abs()
            assert int(mask.sum())==9 and torch.equal(direct,saved['direct']) and torch.equal(post,saved['expected']), 'original path did not reproduce; do not infer cause'
            row['old_failing_indices']=torch.nonzero(mask).flatten().cpu().tolist()
            row['old_failing_values']={k:value[mask].cpu().tolist() for k,value in [('post',post),('direct',direct),('joint',joint),('presplit',presplit)]}
            # Fixed affine backward: same float32 X and component adjoints;
            # only where scaling/addition happens around GEMM changes.
            da=[torch.autograd.grad(e,capture['affine'],retain_graph=True)[0].detach() for e in ee[:2]]
            X=capture['X'].detach();c=coeff.detach()
            mm_post=(da[0].T@X)*c+(da[1].T@X)*c
            mm_pre=(da[0]*c+da[1]*c).T@X
            xd=X.double();a0,a1=da[0].double(),da[1].double();cd=c.double()
            mm_post64=(a0.T@xd)*cd+(a1.T@xd)*cd
            mm_pre64=(a0*cd+a1*cd).T@xd
            row['fixed_hidden3_GEMM_order_control']=dict(float32=compare(mm_post,mm_pre),float64=compare(mm_post64,mm_pre64),
                scope='same saved float32 forward X/component adjoints and coefficient; local affine VJP arithmetic only; not a full-NN float64 reference')
            del da,X,xd,a0,a1,mm_post64,mm_pre64,mm_post,mm_pre
        result['rows'].append(row)
        dump(a.out/'arithmetic_controls.json',result)
        assert row['direct_repeat']['bitwise_equal'],'same-path nonrepeatability needs separate diagnosis'
        assert row['joint_manual_VJP']['failing']==0,'candidate fix fails unchanged tolerance'
        if time.monotonic()-started>165:raise RuntimeError('diagnostic time cap')
    assert all(torch.equal(v,state[k]) for k,v in field.net.state_dict().items())
    assert all(torch.equal(v,frozen[k]) for k,v in adapter.named_buffers())
    result.update(elapsed_seconds=time.monotonic()-started,network_buffers_unchanged=True,status='completed_no_step_arithmetic_controls')
    dump(a.out/'complete.json',result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--saved-vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:main(a)
    except BaseException as exc:
        if a.out.is_dir():dump(a.out/'terminal_failure.json',dict(error=type(exc).__name__,message=str(exc)))
        raise
