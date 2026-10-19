"""D013 fixed native-Q4 adapter. Imported safely; real assets load only explicitly."""
from pathlib import Path
import json
import numpy as np
from scipy.linalg.blas import dgemm
from s04_e024_field_budget import (REGIONS, GUARDS, InvalidEvidence, Metrics,
    Quadratics, finite, digest_array, squared)
from s04_e024_full_head import tangent_support
from s04_e024_weak_guard import Mechanics
from s04_e024_head_cone import elastic_driver


class FieldAdapter:
    """All physical arrays retain original domain weights and frozen damage."""
    def __init__(self,data,base,theta,phi,raw_forward,window,lower,upper,us,
                 gp_damage,gp_xy,integrity=lambda:None):
        self.data=data;self.base=base;self.theta=theta.copy();self.phi=phi
        self.us=abs(us);self.raw_forward=raw_forward;self.integrity=integrity
        self.window=window;self.lower=lower;self.upper=upper
        self.gp_damage=gp_damage;self.gp_xy=gp_xy
        if theta.size != 2*phi.shape[1]:raise InvalidEvidence('head/feature dimension')
        finite(theta,phi,base,window)
        # The unchanged original model's raw field, not a basis reconstruction, is centre.
        origin_uv=raw_forward(self.theta)
        self.mech=Mechanics(data['xy'],data['conn'],data['damage'],origin_uv)
        self.force_scale=self.us/data['energy_scale']
        self.node_weights={}
        mass=data['mass']/data['mass'].sum();bg=data['damage']<=.1
        self.node_masks=dict(full=np.ones(len(mass),bool),damage=~bg,background=bg,
                             inside_background=bg&(window>0))
        gd=gp_damage>.1;dist=np.maximum(lower-gp_xy,gp_xy-upper)
        self.gp_masks=dict(full=np.ones_like(gd),damage=gd,background=~gd,
                          inside_background=(~gd)&(dist<.02).all(2))
        self.node_weights={r:mass*self.node_masks[r] for r in REGIONS}
        det=np.stack([geo[1] for geo in self.mech.geo],axis=1)
        self.gp_weights={r:det*self.gp_masks[r] for r in REGIONS}
        self.origin=self.fields(origin_uv)
        self.reference=self.fields(data['equilibrated_uv'])
        self.metrics=Metrics(self.origin,self.reference,self.node_weights,self.gp_weights)
        self.bc=(data['xy'][:,1]==data['xy'][:,1].min())|(data['xy'][:,1]==data['xy'][:,1].max())
        self.fixed_digest={k:digest_array(data[k]) for k in ('xy','conn','damage','mass','equilibrated_uv')}
        for k in ('xy','conn','damage','mass','equilibrated_uv'):data[k].flags.writeable=False
        self.theta.flags.writeable=False;self.phi.flags.writeable=False
        for f in (self.origin,self.reference):
            for x in f.values():x.flags.writeable=False

    def fields(self,uv):
        e=self.mech.strains(uv);p,_=elastic_driver(self.mech,uv,self.gp_damage)
        force=(self.force_scale*self.mech.dual(self.mech.force(uv))).ravel()
        ex,ey,ga=np.moveaxis(e,-1,0);tr=ex+ey;mu=1/2.6;bulk=1/1.2
        psi=mu*(ex**2+ey**2-tr**2/3+ga**2/2)+.5*bulk*np.maximum(tr,0)**2
        g=(1-self.gp_damage)**2;vol=bulk*np.where(tr>=0,g,1.)*tr
        stress=np.stack([2*mu*g*(ex-tr/3)+vol,2*mu*g*(ey-tr/3)+vol,mu*g*ga],axis=-1)
        result=dict(uv=np.array(uv,copy=True),strain=e,driver=p,force=force,
                    psi_plus=psi,active_energy=g*psi,stress=stress)
        finite(*result.values());return result

    def realize(self,head):
        if head.dtype!=self.theta.dtype or head.shape!=self.theta.shape:
            raise InvalidEvidence('head is not producer-representable')
        return self.fields(self.raw_forward(head))

    def check_identity(self):self.integrity()

    def final_identity(self):
        self.check_identity()
        for k,h in self.fixed_digest.items():
            if digest_array(self.data[k])!=h:raise InvalidEvidence('frozen data drift: '+k)

    def check_realization(self,head,fields,metrics):
        uv=fields['uv'];origin=self.origin['uv']
        if not np.array_equal(uv[self.window==0],origin[self.window==0]):
            raise InvalidEvidence('window-exterior raw UV changed')
        if not np.array_equal(uv[self.bc],origin[self.bc]):raise InvalidEvidence('raw BC changed')
        delta=(head.astype(np.float64)-self.theta.astype(np.float64))
        affinity=origin+self.us*dgemm(1.,np.asarray(self.phi,order='F'),delta)
        from s04_e024_field_budget import ratio_norm
        discrepancy=[squared(uv-affinity,self.node_weights['full']),
            squared(fields['strain']-self.mech.strains(affinity),self.gp_weights['full'])]
        q=[ratio_norm(x,s) for x,s in zip(discrepancy,metrics.scales_sq[:2])]
        if max(q)>1e-8:raise InvalidEvidence('raw/affine field realization mismatch')
        return dict(mapping_discrepancy_ratios=q,outside_max_abs=0.,BC_max_abs=0.)

    def proxy(self,current,metrics,check=lambda:None):
        """17 compressed Grams. Never stores a domain-stacked GP/force Jacobian."""
        n=self.theta.size;pack=Quadratics.empty(n);pcols=self.phi.shape[1]
        for start in range(0,len(self.phi),256):
            check();sl=slice(start,start+256);a=self.us*self.phi[sl]
            j=np.zeros((len(a),2,n));j[:,0,0::2]=a;j[:,1,1::2]=a
            for r,region in enumerate(REGIONS):
                pack.add(r,current['uv'][sl]-metrics.reference['uv'][sl],j,self.node_weights[region][sl])
            pack.add(13,current['uv'][sl]-metrics.origin['uv'][sl],j,self.node_weights['full'][sl])
        _,stress=elastic_driver(self.mech,current['uv'],self.gp_damage)
        driver_index=[11,12,5,6]
        for gp,(grad,det,_) in enumerate(self.mech.geo):
            for start in range(0,len(self.mech.conn),128):
                check();sl=slice(start,start+128);conn=self.mech.conn[sl]
                d=self.us*np.einsum('ean,enp->eap',grad[sl],self.phi[conn])
                j=np.zeros((len(conn),3,n))
                j[:,0,0::2]=d[:,0];j[:,1,1::2]=d[:,1]
                j[:,2,0::2]=d[:,1];j[:,2,1::2]=d[:,0]
                jp=np.einsum('ea,eai->ei',stress[sl,gp],j)
                for r,region in enumerate(REGIONS):
                    w=self.gp_weights[region][sl,gp]
                    pack.add(7+r,current['strain'][sl,gp]-metrics.reference['strain'][sl,gp],j,w)
                    pack.add(driver_index[r],current['driver'][sl,gp]-metrics.reference['driver'][sl,gp],jp,w)
                pack.add(14,current['strain'][sl,gp]-metrics.origin['strain'][sl,gp],j,self.gp_weights['full'][sl,gp])
                pack.add(15,current['driver'][sl,gp]-metrics.origin['driver'][sl,gp],jp,self.gp_weights['full'][sl,gp])
        check()
        # Current branches are the only mutable mechanics linearization, never frozen physics data.
        self.mech.branches=current['strain'][...,:2].sum(2)>=0
        _,nodes,k=tangent_support(self.mech,self.phi)
        rows=np.flatnonzero(np.repeat(self.mech.free[nodes],2));local=self.phi[nodes]
        global_free=np.full(self.mech.n,-1,int);global_free[self.mech.free]=np.arange(self.mech.free.sum())
        indices=2*global_free[nodes[rows//2]]+rows%2
        for start in range(0,len(rows),256):
            check();rr=rows[start:start+256];idx=indices[start:start+256]
            j=np.empty((len(rr),n))
            j[:,0::2]=self.us*(k[rr][:,0::2]@local)
            j[:,1::2]=self.us*(k[rr][:,1::2]@local)
            j*=self.force_scale/np.sqrt(self.mech.mass[nodes[rr//2]])[:,None]
            one=np.ones(len(rr))
            pack.add(4,current['force'][idx],j,one,constant=False)
            pack.add(16,current['force'][idx]-metrics.origin['force'][idx],j,one,constant=False)
        # Whole-domain constants include all forces outside the Jacobian halo.
        pack.c[4]=float(np.sum(current['force']**2))
        pack.c[16]=float(np.sum((current['force']-metrics.origin['force'])**2))
        np.testing.assert_allclose(pack.c[:13],metrics.errors(current),rtol=1e-10,atol=1e-25)
        check();return pack

    def physical_report(self,fields):
        out=self.metrics.report(fields);extra={}
        for key in ('psi_plus','active_energy','stress'):
            extra[key]={r:dict(error_integral=squared(fields[key]-self.reference[key],self.gp_weights[r]),
                reference_integral=squared(self.reference[key],self.gp_weights[r])) for r in REGIONS}
        extra['branch_changed_GP_fraction']=float(np.mean((fields['strain'][...,:2].sum(2)>=0)!=(self.origin['strain'][...,:2].sum(2)>=0)))
        extra['unweighted_error_quantiles']={}
        for key,masks in [('uv',self.node_masks),('strain',self.gp_masks),('driver',self.gp_masks)]:
            error=fields[key]-self.reference[key]
            mag=np.sqrt(np.sum(error**2,axis=-1)) if key!='driver' else abs(error)
            extra['unweighted_error_quantiles'][key]={r:np.quantile(mag[m],[.5,.9,.99,1]).tolist() for r,m in masks.items()}
        return dict(**out,secondary=extra)


def load_real_adapter(project,state,check=lambda:None):
    """Scientific entry; caller must validate explicit approval before calling."""
    import torch
    from s04_e023_head_scale import physical_features
    from diagnose_s04_e023_endpoints import load_endpoint
    from diagnose_s04_e023_physical import observables
    from diagnose_s04_e023_terminal_head import sha,read
    from s04_e024_head_tail import HEAD_LOCKS
    from run_s04_e024_head_tail_screen import state_digest,US
    from s04_e018_global_local import compact_window
    from s04_e024_field_budget import STATES
    if state not in STATES:raise InvalidEvidence('unregistered state')
    check();torch.set_default_dtype(torch.float64);torch.set_num_threads(2)
    root=project/'local_archive/experiments';source=Path(__file__).resolve().parents[1]
    old=root/'S04-E019/producer_execution_v1/raw';e021=root/'S04-E021/producer_execution_v2/raw'
    e022=root/'S04-E022/producer_execution_v1/raw';e023=root/'S04-E023/producer_execution_v1/raw'
    model,data,base,saved,asset=load_endpoint(old,e021,e022,e023,state,'E023')
    model.requires_grad_(False)
    if any(p.device.type!='cpu' for p in model.parameters()):raise InvalidEvidence('CPU-only model')
    cp=e023/'runs'/HEAD_LOCKS[state]['run_id'];before={str(cp/n):sha(cp/n) for n in HEAD_LOCKS[state]['files']}
    original_digest=state_digest(model)
    theta=np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None]])
    phi=[];dtype=model.residual.output_layer.weight.dtype
    with torch.no_grad():
        for start in range(0,len(base),1024):
            check();x=torch.tensor(data['xy'][start:start+1024],dtype=dtype)
            phi.append((physical_features(model,x)*model.head_scale).numpy())
        window=compact_window(torch.tensor(data['xy'],dtype=dtype),model.lower,model.upper).numpy()[:,0]
    phi=np.concatenate(phi)
    def raw_forward(head):
        result=np.empty_like(base)
        with torch.no_grad():
            weight=torch.as_tensor(head[:-1].T.copy(),dtype=dtype);bias=torch.as_tensor(head[-1].copy(),dtype=dtype)
            for start in range(0,len(base),1024):
                check();sl=slice(start,start+1024);x=torch.tensor(data['xy'][sl],dtype=dtype)
                h=model.residual.encode((x-model.local_center)/model.local_scale)
                raw=torch.nn.functional.linear(h*model.head_scale[:-1],weight,bias*model.head_scale[-1])
                correction=(((x[:,1]+.5)*(.5-x[:,1]))[:,None]*compact_window(x,model.lower,model.upper))*raw
                result[sl]=base[sl]+correction.numpy()
        return result
    def integrity():
        if state_digest(model)!=original_digest or any(p.grad is not None or p.requires_grad for p in model.parameters()):
            raise InvalidEvidence('fixed model/gradNone drift')
    ref=observables(data,data['equilibrated_uv'])
    adapter=FieldAdapter(data,base,theta,phi,raw_forward,window,model.lower.numpy().copy(),model.upper.numpy().copy(),US,
                         ref['gp_damage'],ref['gp_xy'],integrity)
    adapter.realization_baseline_saved_max_gap=float(np.max(abs(adapter.origin['uv']-saved)))
    if adapter.realization_baseline_saved_max_gap>1e-12:raise InvalidEvidence('saved E023 baseline realization')
    np.testing.assert_allclose(adapter.reference['strain'],ref['strain'],rtol=0,atol=5e-10)
    np.testing.assert_allclose(adapter.reference['driver'],ref['elastic_damage_driver'],rtol=1e-10,atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(adapter.reference['force']),ref['rho_u'],rtol=1e-8,atol=1e-10)
    native_origin=observables(data,adapter.origin['uv'])
    np.testing.assert_allclose(np.linalg.norm(adapter.origin['force']),native_origin['rho_u'],rtol=1e-12,atol=0)
    np.testing.assert_allclose(adapter.origin['driver'],native_origin['elastic_damage_driver'],rtol=1e-10,atol=1e-12)
    del native_origin
    adapter.check_realization(theta,adapter.origin,adapter.metrics)
    # D012 is a historical comparator only. Its own archive and original head are pinned.
    d012=root/'S04-E024/full_head_attainable_v2';pin=read(source/'docs/research/S04/S04-E024/full_head_archive_v2.json')
    if sha(d012/'ARCHIVE_MANIFEST.json')!=pin['manifest_sha256']:raise InvalidEvidence('D012 archive pin')
    manifest=read(d012/'ARCHIVE_MANIFEST.json')['files'];ip=d012/'results'/f'{state}_full_head.npz'
    if sha(ip)!=manifest[str(ip.relative_to(d012))]['sha256']:raise InvalidEvidence('D012 head pin')
    with np.load(ip,allow_pickle=False) as z:
        np.testing.assert_array_equal(theta,z['original_coefficients']);adapter.d012_head=z['head_coefficients'].copy()
    adapter.assets=dict(state=state,**asset,original_files=before,model_digest=original_digest,
        reference_shape=list(data['equilibrated_uv'].shape),head_dtype=theta.dtype.str,
        d012_input_sha256={str(ip):sha(ip)},saved_vs_raw_origin_max_abs=adapter.realization_baseline_saved_max_gap,
        baseline='own unchanged E023 head, authoritative local raw reconstruction; native saved-field gap retained; not strict cross-platform admission',
        origin_field_sha256=adapter.metrics.centre_digest,guard_ceilings=adapter.metrics.ceilings.tolist(),budget_scales_squared=adapter.metrics.scales_sq.tolist())
    original_final=adapter.final_identity
    def final():
        original_final()
        if any(sha(Path(p))!=h for p,h in before.items()):raise InvalidEvidence('original checkpoint files changed')
    adapter.final_identity=final
    check();return adapter
