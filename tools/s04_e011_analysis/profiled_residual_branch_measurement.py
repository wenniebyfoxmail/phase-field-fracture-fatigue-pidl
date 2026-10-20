"""Four fixed-chart mechanism controls, no NN installation or optimization.
All expensive actions are counted. Pure helpers also support artificial fixtures.
"""
from pathlib import Path
import json,time,gc
import numpy as np


def residual_target(gradient,target):return np.asarray(gradient)-np.asarray(target)


def comparison(Q,plus,minus,h):
    fd=(plus-minus)/(2*h);difference=Q-fd
    scale=max(float(np.linalg.norm(Q)),float(np.linalg.norm(fd)),np.finfo(float).tiny)
    tol=1e-10+1e-4*scale
    return dict(error_L2=float(np.linalg.norm(difference)),scale=scale,tolerance=tol,
                ratio=float(np.linalg.norm(difference))/tol,passed=bool(np.linalg.norm(difference)<=tol)),fd,difference


def inverse_bound(H,X):
    """Norm bound for exact stored H if the rounded residual enclosure is <1.
    This is NOT a native nonlinear root/force arithmetic certificate.
    """
    n=len(H);eps=np.finfo(float).eps;gamma=(n+2)*eps/(1-(n+2)*eps)
    residual=np.eye(n)-H@X
    enclosure=np.abs(residual)+gamma*(np.abs(H)@np.abs(X)+np.eye(n))
    eta=float(np.max(np.sum(enclosure,axis=1)))*(1+gamma)
    xinf=float(np.max(np.sum(abs(X),axis=1)))*(1+gamma)
    xone=float(np.max(np.sum(abs(X),axis=0)))*(1+gamma)
    # H/X numerically symmetric, but use both 1 and inf norms explicitly.
    eta1=float(np.max(np.sum(enclosure,axis=0)))*(1+gamma)
    valid=max(eta,eta1)<1
    upper=(xinf*xone/((1-eta)*(1-eta1)))**.5 if valid else None
    return dict(stored_matrix_inverse_norm2_upper=upper,residual_inf_upper=eta,residual_one_upper=eta1,
        matrix_bound_available=valid,rounding_model='IEEE binary64 standard gamma_n matmul and norm-sum enclosure, no overflow/underflow assumed',
        finite_root_bound=False,native_force_roundoff_bound=False)


def persist_arm_result(archive,label,row,writer):
    """Each arm gets one immutable receipt; the final aggregate is written once."""
    if label not in ['native_constant','native_zero','frozen_constant','frozen_zero']:raise ValueError('unknown_arm')
    writer(Path(archive)/(label+'_result.json'),row)


class LinearJournal:
    """Immutable begin/end receipts; finally index survives partial completion."""
    def __init__(self,archive,writer):self.archive=Path(archive);self.writer=writer;self.started=[];self.finished=[]
    def begin(self,role):
        key=f'{len(self.started)+1:04d}';self.started.append(key)
        self.writer(self.archive/('linear_'+key+'_start.json'),dict(id=key,role=role))
        return key
    def finish(self,key,summary):
        self.writer(self.archive/('linear_'+key+'_end.json'),dict(id=key,**summary));self.finished.append(key)
    def index(self,error):
        self.writer(self.archive/'linear_solve_index.json',dict(started=self.started,finished=self.finished,
            incomplete=[k for k in self.started if k not in self.finished],primary_error=error))


class Meter:
    def __init__(self,guard,combined=500):self.guard=guard;self.combined=combined
    def action(self,kind):
        self.guard.charge(kind)
        if kind in ['energy_force_field','native_tangent','frozen_tangent']:
            if sum(self.guard.counts.get(k,0) for k in ['energy_force_field','native_tangent','frozen_tangent'])>self.combined:self.guard.stop(f'combined_field_K_{self.combined}')


def _run(card,root,archive,reporter,started,context):
    import torch
    from profiled_hidden_adapter import Guard,E011Bridge
    from profiled_hidden_e011_runtime import verify_source_assets,tensor_identity
    from profiled_hidden_receipts import atomic_json
    import run_pidl_persisted_phi_hidden_newton as base
    from run_pidl_head_newton import assemble_blocks
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise RuntimeError('one CUDA device required')
    import ctypes,uuid
    lib=ctypes.CDLL('libcuda.so.1');dev=ctypes.c_int();raw=(ctypes.c_ubyte*16)()
    if lib.cuInit(0) or lib.cuDeviceGet(ctypes.byref(dev),0) or lib.cuDeviceGetUuid_v2(ctypes.byref(raw),dev):raise RuntimeError('CUDA UUID query')
    actual='GPU-'+str(uuid.UUID(bytes=bytes(raw)))
    if actual!=card['producer']['gpu_uuid']:raise RuntimeError('CUDA UUID mismatch')
    torch.cuda.init();device=torch.device('cuda:0')
    import resource,os,sys
    atomic_json(archive/'runtime_versions.json',dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,GPU_UUID=actual,
        CPU_affinity=sorted(os.sched_getaffinity(0)),RLIMIT_AS=resource.getrlimit(resource.RLIMIT_AS),AS_inherited_unchanged=True))
    reporter.cuda=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0))
    caps={k:v for k,v in card['work_caps'].items() if v>0}
    completion=card.get('mode')=='frozen_completion_only'
    guard=Guard(caps,float(card['measurement_seconds']),memory=reporter.ratio,max_bytes=1.);guard.start=started
    meter=Meter(guard,250 if completion else 500);context['guard']=guard;context['journal']=LinearJournal(archive,atomic_json)
    if completion:
        verified=[]
        from profiled_hidden_e011_runtime import binding
        for item in card['reuse_bindings']:
            guard.check();actual_item=binding(item['source'])
            if actual_item['sha256']!=item['sha256'] or actual_item['bytes']!=item['bytes']:raise RuntimeError('old_cache_binding_mismatch_'+item['role'])
            verified.append(dict(role=item['role'],**actual_item))
        reuse={x['role']:Path(x['source']) for x in card['reuse_bindings']}
        for item in card['operator_bindings']:
            got=binding(root/'code'/item['path'])
            if got['sha256']!=item['sha256'] or got['bytes']!=item['bytes']:raise RuntimeError('operator_version_not_same_'+item['path'])
        atomic_json(archive/'native_reuse_inventory.json',[x for x in verified if x['role'].startswith('native:')])
        atomic_json(archive/'reuse_hash_verification.json',verified)
        for scope_role in ['old_native_source_card','energy_reference_card']:
            old_scope=json.loads(reuse[scope_role].read_text())
            if [(x['role'],x['bytes'],x['sha256']) for x in old_scope['input_bindings']]!=[(x['role'],x['bytes'],x['sha256']) for x in card['input_bindings']]:raise RuntimeError('old_source_state_scope_mismatch_'+scope_role)
        old_runtime=json.loads(reuse['old_runtime'].read_text())
        if torch.__version__!=old_runtime['torch'] or np.__version__!=old_runtime['numpy']:raise RuntimeError('cache_runtime_version_mismatch')
    inputs=root/'inputs';inputs.mkdir();paths={r['role']:r['source'] for r in card['input_bindings']}
    atomic_json(archive/'source_assets.json',verify_source_assets(card,paths,guard))
    # Only existing remote inputs are reused. Keep each immutable source binding.
    z=dict(np.load(paths['input'],allow_pickle=False));p=base.LocalProblem(z,device)
    original=torch.load(paths['original_model'],map_location=device,weights_only=True)
    initial=torch.load(paths['initial_model'],map_location=device,weights_only=True)
    meter.action('raw_feature_forward');field=base.make_smooth(original,p);field.net.load_state_dict(initial);field.net.requires_grad_(False)
    source_id=tensor_identity(field.net.state_dict());physical={n:getattr(p,n).clone() for n in ['df','hist','f']}
    head=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).cpu().numpy()
    space=base.load_actual_space(paths['source_phi'],paths['source_transform'],head,device,p.n)
    class CaptureBridge(E011Bridge):
        def features(self,xi):
            if getattr(self,'capture_source',False):
                if not hasattr(self,'captured_source_features'):
                    self.captured_source_features=super().features(xi).detach()
                return self.captured_source_features
            return super().features(xi)
    bridge=CaptureBridge(field,p,space,guard);context['bridge']=bridge;bridge.capture_source=True;bridge.startup()
    v=np.random.default_rng(173).normal(size=bridge.zero.numel());v/=np.linalg.norm(v);h=1e-6
    def save(name,array):
        guard.check();path=archive/(name+'.npy');path.parent.mkdir(parents=True,exist_ok=True)
        if torch.is_tensor(array):array=array.detach().cpu().numpy()
        if np.asarray(array).dtype.kind in 'fc' and not np.isfinite(array).all():raise RuntimeError('nonfinite_saved_'+name)
        with path.open('xb') as stream:np.save(stream,array,allow_pickle=False)
    save('direction',v);save('scales',bridge.scales);save('free_dofs',p.fu);save('transform',bridge.T)
    if completion:
        for role,value in [('direction',v),('scales',bridge.scales.cpu().numpy()),('free_dofs',p.fu.cpu().numpy()),('transform',bridge.T.cpu().numpy())]:
            if not np.array_equal(np.load(reuse[role],allow_pickle=False),value):raise RuntimeError('common_'+role+'_not_exact')
    cache={}
    # Exactly three cache captures. startup raw0 is reused for source design.
    for label,step in [('source',0.),('plus',h),('minus',-h)]:
        bridge.capture_source=(label=='source')
        with torch.no_grad():
            f=bridge.features(torch.as_tensor(step*v,device=device));design=bridge.load*bridge.bubble[:,None]*torch.cat((f,torch.ones((p.n,1),device=device,dtype=torch.float64)),dim=1)
            phi=bridge.phi+(design-bridge.raw0)@bridge.T
            rawhead=f@bridge.head[:,:-1].T+bridge.head[:,-1]
            u=(bridge.bubble*rawhead[:,0]+(p.x[:,-1]-bridge.y0)/(bridge.yL-bridge.y0)*torch.cos(bridge.angle))*bridge.load
            vv=(bridge.bubble*rawhead[:,1]+(p.x[:,-1]-bridge.y0)/(bridge.yL-bridge.y0)*torch.sin(bridge.angle))*bridge.load
            q=torch.cat((u,vv))
            if completion:
                oldphi=torch.as_tensor(np.load(reuse[label+'_phi'],allow_pickle=False),device=device)
                oldq=torch.as_tensor(np.load(reuse[label+'_qraw'],allow_pickle=False),device=device)
                same=dict(phi=torch.equal(phi,oldphi),qraw=torch.equal(q,oldq))
                atomic_json(archive/(label+'_derived_cache_identity.json'),same)
                if not all(same.values()):raise RuntimeError('derived_cache_not_bit_exact_'+label)
                phi,q=oldphi,oldq
            cache[label]=(phi,q)
            save('shared/'+label+'_phi',phi);save('shared/'+label+'_qraw',q)
            del f,design,rawhead,u,vv
    bridge.capture_source=False;del bridge.captured_source_features
    q0=cache['source'][1];n=p.n;r=space['transform'].shape[1];heads=2*r;free=p.fu
    if r!=386 or not torch.equal(cache['source'][0],bridge.phi):raise RuntimeError('rank_or_actual_Phi_anchor')
    with torch.no_grad():
        tr0=p.grad(q0[:n])[:,:,0]+p.grad(q0[n:])[:,:,1]
        if bool((tr0==0).any()):raise RuntimeError('source_zero_trace')
        dg=torch.einsum('gi,ei->eg',p.N,p.df[p.cells]);degrade=p.model.Edegrade(dg)[0]
    save('shared/source_trace_sign',torch.sign(tr0).to(torch.int8))
    if completion:
        if not np.array_equal(np.load(reuse['source_trace'],allow_pickle=False),torch.sign(tr0).to(torch.int8).cpu().numpy()):raise RuntimeError('source_branch_labels_not_exact')
        if not np.array_equal(np.load(reuse['old_native_q0'],allow_pickle=False),q0[free].cpu().numpy()):raise RuntimeError('native_energy_reference_q0_not_exact')
    source_fields=dict(np.load(paths['source_fields'],allow_pickle=False))
    source_full=np.concatenate((source_fields['u'],source_fields['v']))
    source_error=float(np.max(abs(q0.cpu().numpy()-source_full)))
    if source_error>1e-12:raise RuntimeError('source_field_identity')
    prescribed=torch.ones(2*n,device=device,dtype=torch.bool);prescribed[free]=False
    for side,(ph,qr) in cache.items():
        if float((qr[prescribed]-q0[prescribed]).abs().max())>1e-12:raise RuntimeError('original_boundary_cache')
        if float(torch.cat((ph,ph),dim=0)[prescribed].abs().max())>1e-12:raise RuntimeError('B_changes_boundary')
    atomic_json(archive/'source_and_boundary_identity.json',dict(source_fields_maxabs=source_error,rank=r,source_phi_exact=True,cache_boundary_fixed=True))
    native_parts=p.parts
    def frozen_parts(u,vv,d):
        # Fixed source sign on the complete full field, including original lift.
        gu,gv=p.grad(u),p.grad(vv);xx,yy=gu[:,:,0],gv[:,:,1];xy=.5*(gu[:,:,1]+gv[:,:,0]);tr=xx+yy
        dev=(xx-tr/3).square()+(yy-tr/3).square()+(tr/3).square()+2*xy.square()
        bulk=p.mat.mat_lmbda+2/3*p.mat.mat_mu
        coefficient=torch.where(tr0>0,degrade,torch.ones_like(degrade))
        energy=(p.w*(.5*bulk*coefficient*tr.square()+p.mat.mat_mu*degrade*dev)).sum()
        return energy,energy*0,energy*0
    def energy(q,branch):
        if completion and branch!='frozen':raise RuntimeError('native_recomputation_forbidden')
        meter.action('energy_force_field')
        return (native_parts if branch=='native' else frozen_parts)(q[:n],q[n:],p.df)[0]
    def trace(q):
        meter.action('energy_force_field') # saved field/strain operation also counted
        with torch.no_grad():return p.grad(q[:n])[:,:,0]+p.grad(q[n:])[:,:,1]
    def bfull(phi,zz):
        a=phi@zz.reshape(2,r).T;return torch.cat((a[:,0],a[:,1]))
    free_mask=torch.zeros(2*n,device=device,dtype=torch.float64);free_mask[free]=1
    def project(phi,force):
        force=force*free_mask
        return torch.cat((phi.T@force[:n],phi.T@force[n:]))
    class Basis:
        def __init__(self,phi):
            self.phi=phi;self.gx=torch.empty((4*len(p.cells),r),device=device,dtype=torch.float64);self.gy=torch.empty_like(self.gx)
            with torch.no_grad():
                for st in range(0,len(p.cells),1024):
                    guard.check();en=min(st+1024,len(p.cells));local=phi[p.cells[st:en]];grad=torch.einsum('egki,eir->egkr',p.B[st:en],local)
                    self.gx[4*st:4*en]=grad[:,:,0].reshape(-1,r);self.gy[4*st:4*en]=grad[:,:,1].reshape(-1,r)
        def matrix(self,q,branch):
            if completion and branch!='frozen':raise RuntimeError('native_assembly_forbidden')
            meter.action('head_assembly')
            tr=trace(q) if branch=='native' else tr0
            H,asym=assemble_blocks(self.gx,self.gy,p.w.reshape(-1),degrade.reshape(-1),tr.reshape(-1))
            if not torch.isfinite(H).all():raise RuntimeError('nonfinite_H')
            return H
    solve_log=[];journal=context['journal']
    def factor(H):
        meter.action('head_factor');L,info=torch.linalg.cholesky_ex(H,check_errors=False)
        if int(info):raise RuntimeError('head_not_SPD')
        return L
    def solve(H,L,rhs):
        meter.action('head_triangular_solve');meter.action('head_triangular_solve')
        key=journal.begin('head_vector_solve')
        for name,value in [('H',H),('factor',L),('rhs',rhs)]:save('linear/'+key+'_'+name,value)
        x=torch.cholesky_solve(rhs[:,None],L).squeeze(1)
        res=H@x-rhs;rel=float(torch.linalg.vector_norm(res)/max(float(torch.linalg.vector_norm(rhs)),np.finfo(float).tiny))
        for name,value in [('solution',x),('residual',res)]:save('linear/'+key+'_'+name,value)
        journal.finish(key,dict(relative_residual=rel,rhs_L2=float(torch.linalg.vector_norm(rhs)),solution_L2=float(torch.linalg.vector_norm(x))))
        if not torch.isfinite(x).all() or rel>1e-6:raise RuntimeError('linear_solve_failure')
        solve_log.append(dict(relative_residual=rel,rhs_L2=float(torch.linalg.vector_norm(rhs)),solution_L2=float(torch.linalg.vector_norm(x))))
        return x
    def evaluate(phi,qraw,zz,target,branch):
        zz=zz.detach().clone().requires_grad_(True);q=qraw+bfull(phi,zz);value=energy(q,branch);objective=value-target@zz
        g=torch.autograd.grad(objective,zz)[0]
        if not all(bool(torch.isfinite(t).all()) for t in [value,objective,g,q]):raise RuntimeError('nonfinite_head_evaluation')
        return dict(z=zz.detach(),q=q.detach(),value=float(value.detach()),objective=float(objective.detach()),defect=g.detach())
    internal=1e-13
    def newton(phi,qraw,target,branch,basis,initial_z,label):
        last=evaluate(phi,qraw,initial_z,target,branch);accepted=[];status='max10'
        for k in range(10):
            guard.check()
            if float(last['defect'].abs().max())<=internal:status='internal_target';break
            H=basis.matrix(last['q'],branch);L=factor(H);direction=-solve(H,L,last['defect']);slope=float(last['defect']@direction)
            if slope>=0:raise RuntimeError('non_descent_head')
            ok=False
            for line in range(32):
                alpha=2.**(-line);trial=evaluate(phi,qraw,last['z']+alpha*direction,target,branch)
                roundoff=32*np.finfo(float).eps*max(abs(last['objective']),abs(trial['objective']),1e-30)
                if trial['objective']<=last['objective']+1e-4*alpha*slope+roundoff:
                    last=trial;accepted.append(dict(k=k,alpha=alpha,defect_inf=float(last['defect'].abs().max())));ok=True;break
            if not ok:status='line_search_unresolved';break
        if float(last['defect'].abs().max())<=internal:status='internal_target'
        # A finite inability to make the forward bound small is an observation.
        if max(float(last['defect'].abs().max()),float((last['defect']+target).abs().max()))>1e-10:raise RuntimeError('original_head_defect_or_physical_gradient_contract')
        atomic_json(archive/(label+'_solver.json'),dict(status=status,accepted=accepted,internal_fixed=internal,original_defect_limit=1e-10,
            target_is_physical_zero=bool((target==0).all()),physical_gradient_inf=float((last['defect']+target).abs().max()),target_defect_inf=float(last['defect'].abs().max())))
        return last
    results=[];source_data={};endpoint_data={};native_source_reference=None
    for branch in (['frozen'] if completion else ['native','frozen']):
        phi,qraw=cache['source'];basis=Basis(phi)
        qleaf=qraw.detach().clone().requires_grad_(True);e=energy(qleaf,branch);R=torch.autograd.grad(e,qleaf)[0].detach();g0=project(phi,R).detach()
        save(branch+'/g0',g0);save(branch+'/R0',R)
        if branch=='native':native_source_reference=(float(e.detach()),R.detach().cpu().numpy())
        else:
            if completion:
                old_ref=json.loads(reuse['old_native_energy'].read_text())
                native_source_reference=(old_ref['E'],np.load(reuse['native_R0'],allow_pickle=False))
            errs=dict(energy_abs=abs(float(e.detach())-native_source_reference[0]),force_maxabs=float(np.max(abs(R.detach().cpu().numpy()-native_source_reference[1]))))
            if completion:errs['same_coordinate_g0_maxabs']=float(np.max(abs(g0.cpu().numpy()-np.load(reuse['native_g0'],allow_pickle=False))))
            atomic_json(archive/'frozen_source_equivalence.json',errs)
            if errs['energy_abs']>1e-12 or errs['force_maxabs']>1e-10 or errs.get('same_coordinate_g0_maxabs',0)>1e-10:raise RuntimeError('frozen_source_E_R_mismatch')
        for kind in ['constant','zero']:
            label=branch+'_'+kind;target=g0.clone() if kind=='constant' else torch.zeros_like(g0)
            src=newton(phi,qraw,target,branch,basis,torch.zeros(heads,device=device,dtype=torch.float64),label+'_source')
            H=basis.matrix(src['q'],branch);L=factor(H)
            if float((src['q'][prescribed]-q0[prescribed]).abs().max())>1e-12:raise RuntimeError('source_root_boundary')
            source_data[label]=dict(branch=branch,kind=kind,target=target,source=src,H=H.detach().clone(),L=L.detach().clone())
            save(label+'/source_z',src['z']);save(label+'/source_q',src['q']);save(label+'/target',target)
        del basis,qleaf,e,R;gc.collect();torch.cuda.empty_cache()
        for kind in ['constant','zero']:
            label=branch+'_'+kind;data=source_data[label];src=data['source'];zstar=src['z'].detach();H,L=data['H'],data['L']
            source_trace=trace(src['q'])
            save(label+'/source_trace',torch.sign(source_trace).to(torch.int8))
            if branch=='native' and bool((source_trace==0).any()):raise RuntimeError('reanchored_native_source_zero_trace')
            del source_trace
            # Full chain J includes B'(xi) zstar; zstar fixed for partial xi.
            def qanchor(xi):
                # One shared feature graph; do not create two full NN JVP graphs.
                f=bridge.features(xi)
                design=bridge.load*bridge.bubble[:,None]*torch.cat((f,torch.ones((n,1),device=device,dtype=torch.float64)),dim=1)
                moving=bridge.phi+(design-bridge.raw0)@bridge.T
                raw=f@bridge.head[:,:-1].T+bridge.head[:,-1]
                uu=(bridge.bubble*raw[:,0]+(p.x[:,-1]-bridge.y0)/(bridge.yL-bridge.y0)*torch.cos(bridge.angle))*bridge.load
                vv=(bridge.bubble*raw[:,1]+(p.x[:,-1]-bridge.y0)/(bridge.yL-bridge.y0)*torch.sin(bridge.angle))*bridge.load
                return torch.cat((uu,vv))+bfull(moving,zstar)
            meter.action('hidden_jvp');anchor_value,J=torch.autograd.functional.jvp(qanchor,bridge.zero,torch.as_tensor(v,device=device),strict=True)
            save(label+'/source_AD_primal',anchor_value)
            anchor_error=float((anchor_value.detach()-src['q']).abs().max())
            atomic_json(archive/(label+'_source_AD_identity.json'),dict(maxabs=anchor_error))
            if anchor_error>1e-12:raise RuntimeError('source_AD_primal_mismatch')
            J=J.detach();del anchor_value
            qleaf=src['q'].detach().clone().requires_grad_(True);e=energy(qleaf,branch);R=torch.autograd.grad(e,qleaf,create_graph=True)[0]
            meter.action('frozen_tangent' if completion else 'native_tangent');KJ=torch.autograd.grad(R,qleaf,grad_outputs=J)[0].detach()
            Rdet=R.detach()
            meter.action('hidden_jvp')
            C=torch.autograd.functional.jvp(lambda xi:project(bridge.moving_phi(xi),Rdet),bridge.zero,torch.as_tensor(v,device=device),strict=True)[1].detach()
            U=project(phi,KJ)+C;hd=solve(H,L,U);Q=(J-bfull(phi,hd))[free];meter.action('Qv')
            bth=project(phi,KJ);save(label+'/Jv',J[free]);save(label+'/Cv',C);save(label+'/KJv',KJ[free]);save(label+'/BTKJv',bth);save(label+'/U',U);save(label+'/head_response',hd);save(label+'/Qv',Q);save(label+'/H',H);save(label+'/factor',L);save(label+'/source_R',Rdet);save(label+'/source_defect',src['defect'])
            data['Q']=Q.detach().cpu().numpy();del qleaf,e,R,Rdet,J,KJ,C,U,hd,Q,bth;gc.collect();torch.cuda.empty_cache()
        for side in ['plus','minus']:
            phi,qraw=cache[side];basis=Basis(phi)
            for kind in ['constant','zero']:
                label=branch+'_'+kind;data=source_data[label];last=newton(phi,qraw,data['target'],branch,basis,data['source']['z'],label+'_'+side)
                if float((last['q'][prescribed]-q0[prescribed]).abs().max())>1e-12:raise RuntimeError('side_root_boundary')
                HH=basis.matrix(last['q'],branch);LL=factor(HH)
                qleaf=last['q'].detach().clone().requires_grad_(True);ee=energy(qleaf,branch);force=torch.autograd.grad(ee,qleaf)[0].detach()
                direct=project(phi,force)-data['target']
                save(label+'/'+side+'_q',last['q']);save(label+'/'+side+'_z',last['z']);save(label+'/'+side+'_defect',last['defect']);save(label+'/'+side+'_direct_defect',direct);save(label+'/'+side+'_R',force);save(label+'/'+side+'_H',HH);save(label+'/'+side+'_factor',LL)
                if max(float(direct.abs().max()),float((direct+data['target']).abs().max()))>1e-10:raise RuntimeError('direct_projected_head_contract')
                save(label+'/'+side+'_trace',torch.sign(trace(last['q'])).to(torch.int8))
                # Local linear head-defect displacement, not nonlinear root certificate.
                correction=solve(HH,LL,direct);field_correction=bfull(phi,correction)[free]
                save(label+'/'+side+'_linear_defect_field',field_correction)
                # Inverse of stored H with residual enclosure, no SVD.
                meter.action('head_triangular_solve');meter.action('head_triangular_solve')
                ikey=journal.begin('head_inverse_columns')
                identity=torch.eye(heads,device=device,dtype=torch.float64)
                for name,value in [('H',HH),('factor',LL),('rhs',identity)]:save('linear/'+ikey+'_'+name,value)
                inv=torch.cholesky_solve(identity,LL);inverse_residual=HH@inv-identity
                save('linear/'+ikey+'_solution',inv);save('linear/'+ikey+'_residual',inverse_residual)
                journal.finish(ikey,dict(residual_inf=float(inverse_residual.abs().sum(1).max())))
                hb=inverse_bound(HH.cpu().numpy(),inv.cpu().numpy())
                # B Gram in free coordinates, no mass weighting.
                meter.action('explicit_head_products');mask=torch.zeros(2*n,device=device,dtype=torch.float64);mask[free]=1
                gram_u=phi.T@(mask[:n,None]*phi);gram_v=phi.T@(mask[n:,None]*phi)
                gamma=(n+2)*np.finfo(float).eps/(1-(n+2)*np.finfo(float).eps)
                # Conservative absolute-product enclosure for rounded Gram.
                gram_abs_u=phi.abs().T@(mask[:n,None]*phi.abs());gram_abs_v=phi.abs().T@(mask[n:,None]*phi.abs())
                bnorm=float(torch.sqrt(torch.maximum((gram_u.abs()+gamma*gram_abs_u).sum(1).max(),(gram_v.abs()+gamma*gram_abs_v).sum(1).max())*(1+gamma)))
                save(label+'/'+side+'_Hinv',inv);save(label+'/'+side+'_Gram_u',gram_u);save(label+'/'+side+'_Gram_v',gram_v)
                # Projection summation error conditional on exact saved nodal R.
                projabs=project(phi.abs(),force.abs());proj_round=gamma*projabs
                amplification=None if hb['stored_matrix_inverse_norm2_upper'] is None else bnorm*hb['stored_matrix_inverse_norm2_upper']
                estimate=None if amplification is None else amplification*float(torch.linalg.vector_norm(direct.abs()+proj_round))
                hb.update(B_norm2_upper=bnorm,local_defect_field_L2=float(torch.linalg.vector_norm(field_correction)),linear_forward_upper_conditional_saved_R=estimate,
                    nodal_force_arithmetic_bound_available=False,native_global_strong_convexity_bound_available=False,
                    full_forward_bound_trusted=False,quadratic_control=bool(completion),reason=('Frozen quadratic control: stored-matrix/Gram bounds only; force and assembly arithmetic enclosures incomplete.' if completion else 'Stored-matrix/Gram enclosures only. Native force arithmetic and nonlinear path strong-convexity bounds not established; never use as full certificate.'))
                atomic_json(archive/(label+'_'+side+'_forward.json'),hb)
                endpoint_data[label,side]=dict(q=last['q'][free].cpu().numpy(),local=float(torch.linalg.vector_norm(field_correction)),bound=estimate,trusted=False)
                del qleaf,ee,force,HH,LL,correction,field_correction,inv,gram_u,gram_v,gram_abs_u,gram_abs_v,projabs,proj_round,last
            del basis;gc.collect();torch.cuda.empty_cache()
        for kind in ['constant','zero']:
            label=branch+'_'+kind;data=source_data[label];row,fd,diff=comparison(data['Q'],endpoint_data[label,'plus']['q'],endpoint_data[label,'minus']['q'],h)
            local=(endpoint_data[label,'plus']['local']+endpoint_data[label,'minus']['local'])/(2*h)
            row.update(arm=label,internal_head_tol=internal,source_z_L2=float(torch.linalg.vector_norm(data['source']['z'])),
                source_defect_inf=float(data['source']['defect'].abs().max()),source_physical_gradient_inf=float((data['source']['defect']+data['target']).abs().max()),
                side_linear_defect_FD_triangle=local,full_forward_bound_trusted=False,causal_verdict='numerically_unresolved_even_if_FD_passes')
            save(label+'/FD',fd);save(label+'/difference',diff);results.append(row);persist_arm_result(archive,label,row,atomic_json)
            del data['H'],data['L'];gc.collect();torch.cuda.empty_cache()
    bridge.verify_frozen()
    if tensor_identity(field.net.state_dict())!=source_id:raise RuntimeError('source_weights_changed')
    for name,value in physical.items():
        if not torch.equal(getattr(p,name),value):raise RuntimeError('physical_state_changed')
    atomic_json(archive/'linear_solve_records.json',solve_log)
    result=dict(status='FROZEN_PAIR_COMPLETE_NO_OPTIMIZATION' if completion else 'FOUR_ARM_COMPLETE_NO_OPTIMIZATION',arms=results,counts=dict(guard.counts,svd=0),scientific_elapsed_seconds=time.monotonic()-started,
        original_head_limit=1e-10,internal_head_tol=internal,FD_abs=1e-10,FD_rel=1e-4,h=h,source_identity=source_id,rank=r,
        reused_native_run=card.get('reused_native_run'),original_boundary_fixed=True,source_restored=True,all_arms_are_chart_controls=True,optimization_updates=0,history_commits=0,rollout=0,
        full_forward_bound_trusted=False,causal_decision='unresolved_without_full_forward_error_control')
    atomic_json(archive/'measurement_result.json',result);return result


def run(card,root,archive,reporter,started):
    """Persist final counts/state even at first failure; never retry/recompute."""
    from profiled_hidden_receipts import atomic_json,note_record_failure
    context={};primary=None;completed=False
    try:
        result=_run(card,root,archive,reporter,started,context);completed=True;return result
    except BaseException as err:
        primary=err;raise
    finally:
        state_ok=None;state_error=None;state_exception=None
        if 'bridge' in context:
            try:context['bridge'].verify_frozen();state_ok=True
            except BaseException as err:
                state_ok=False;state_error=str(err);state_exception=err
                if primary is not None:note_record_failure(primary,err)
        row=dict(completed=bool(completed and state_ok is not False),source_network_B0_physics_unchanged=state_ok,state_error=state_error,
            primary_error=None if primary is None else dict(type=type(primary).__name__,message=str(primary)),
            counts=dict(context['guard'].counts,svd=0) if 'guard' in context else {},
            elapsed_seconds=time.monotonic()-started,optimization_updates=0,history_commits=0,rollout=0)
        if 'journal' in context:
            try:context['journal'].index(row['primary_error'] or state_error)
            except BaseException as err:
                earlier=primary if primary is not None else state_exception
                if earlier is not None:note_record_failure(earlier,err)
                else:state_exception=err
                row['completed']=False;row['linear_index_error']=dict(type=type(err).__name__,message=str(err))
        try:atomic_json(archive/'measurement_terminal.json',row)
        except BaseException as err:
            earlier=primary if primary is not None else state_exception
            if earlier is not None:note_record_failure(earlier,err)
            else:raise

        if state_exception is not None and primary is None:raise state_exception
