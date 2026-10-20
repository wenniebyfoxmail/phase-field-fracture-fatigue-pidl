"""Unexecuted E011 adapter. No loader, CLI, model factory or launch side effect.

An anchored local proposal is NOT a certified real-network profile. An actual
full-current reprofile callback is mandatory before a direction can be used.
Only supplied existing objects are connected. Tests supply artificial objects.
"""
from __future__ import annotations
import time
import numpy as np
import torch
from profiled_hidden_kernel import Profiled, strict_spd_solver
from profiled_hidden_receipts import trial_metadata, note_record_failure


class AdapterStop(RuntimeError):
    pass


def check_tensor(x,shape=None):
    if not isinstance(x,torch.Tensor) or x.dtype!=torch.float64 or (shape is not None and tuple(x.shape)!=tuple(shape)) or not bool(torch.isfinite(x).all()):
        raise AdapterStop('tensor_shape_dtype_or_nonfinite')
    return x


class Guard:
    """In-process checks only; does not replace an external hard watchdog."""
    def __init__(self,caps,seconds,*,clock=time.monotonic,memory=None,max_bytes=None):
        if not np.isfinite(seconds) or seconds<=0:raise AdapterStop('invalid_time_budget')
        if memory is not None and (max_bytes is None or not np.isfinite(max_bytes) or max_bytes<=0):raise AdapterStop('invalid_memory_bound')
        if any(isinstance(v,bool) or not isinstance(v,int) or v<1 for v in caps.values()):raise AdapterStop('invalid_work_budget')
        self.caps=dict(caps);self.counts={k:0 for k in caps};self.seconds=seconds
        self.clock=clock;self.start=clock();self.memory=memory;self.max_bytes=max_bytes;self.events=[];self.stopped=False
    def stop(self,reason):
        self.stopped=True;self.events.append(dict(stop=reason,counts=dict(self.counts)));raise AdapterStop(reason)
    def check(self):
        if self.stopped:raise AdapterStop('guard_already_stopped')
        elapsed=self.clock()-self.start
        if not np.isfinite(elapsed) or elapsed<0 or elapsed>=self.seconds:self.stop('wall_deadline')
        if self.memory is not None:
            used=self.memory()
            if not np.isfinite(used) or used<0 or used>self.max_bytes:self.stop('memory_limit')
    def charge(self,kind):
        self.check()
        if kind not in self.caps:self.stop('undeclared_work_'+kind)
        if self.counts[kind]>=self.caps[kind]:self.stop('work_limit_'+kind)
        self.counts[kind]+=1
    def invoke(self,kind,fun):
        self.charge(kind)
        try:out=fun()
        except Exception as err:self.stop('callback_'+kind+'_'+type(err).__name__)
        self.check();return out


class EnergyPoint:
    """Frozen free-DOF energy graph, reused for K actions, explicitly released."""
    def __init__(self,q,energy,guard):
        self.guard=guard;self.q=check_tensor(q).detach().clone().requires_grad_(True)
        def build():
            value=check_tensor(energy(self.q),())
            force=check_tensor(torch.autograd.grad(value,self.q,create_graph=True,allow_unused=False)[0],self.q.shape)
            return value,force
        self.value,self.force=guard.invoke('energy_force_field',build)
    def k(self,v):
        check_tensor(v,self.q.shape)
        def action():return check_tensor(torch.autograd.grad(self.force,self.q,grad_outputs=v,retain_graph=True,allow_unused=False)[0],self.q.shape).detach()
        return self.guard.invoke('native_tangent',action)
    def close(self):
        self.q=None;self.value=None;self.force=None


class AutogradChart:
    """q(xi,0) and B(xi)z from the SAME basepoint; C uses detached R.

    q_fn contains the current raw head. Do not add B' z again to J at z=0.
    There is no cached hidden graph and no allow_unused/zero-fill fallback.
    """
    def __init__(self,xi,q_fn,b_fn,bt_fn,point,head_matrix,guard):
        self.xi=check_tensor(xi).detach().clone();self.q_fn=q_fn;self.b_fn=b_fn;self.bt_fn=bt_fn
        self.point=point;self.guard=guard;self.force=point.force.detach().clone()
        h=np.asarray(head_matrix,dtype=np.float64)
        if h.ndim!=2 or h.shape[0]!=h.shape[1] or not np.isfinite(h).all():raise AdapterStop('invalid_head_matrix')
        self.heads=len(h);self.fields=self.force.numel();self.parameters=self.xi.numel()
        self.guard.charge('head_factor')
        try:self.solve_head=strict_spd_solver(h)
        except (ValueError,np.linalg.LinAlgError) as err:self.guard.stop('head_factor_'+type(err).__name__)
    def tensor(self,x):return torch.as_tensor(x,dtype=torch.float64,device=self.xi.device)
    def array(self,x):return check_tensor(x).detach().cpu().numpy().copy()
    def j(self,v):
        return self.guard.invoke('hidden_jvp',lambda:torch.autograd.functional.jvp(self.q_fn,self.xi,self.tensor(v),strict=True)[1])
    def jt(self,w):
        def action():
            xi=self.xi.detach().clone().requires_grad_(True);q=self.q_fn(xi)
            return torch.autograd.grad(q,xi,grad_outputs=self.tensor(w),allow_unused=False)[0]
        return self.guard.invoke('hidden_vjp',action)
    def c(self,v):
        return self.guard.invoke('C',lambda:torch.autograd.functional.jvp(lambda x:self.bt_fn(x,self.force),self.xi,self.tensor(v),strict=True)[1])
    def ct(self,z):
        def action():
            xi=self.xi.detach().clone().requires_grad_(True);contraction=self.bt_fn(xi,self.force)
            return torch.autograd.grad(contraction,xi,grad_outputs=self.tensor(z),allow_unused=False)[0]
        return self.guard.invoke('CT',action)
    def solve(self,rhs):
        self.guard.charge('head_triangular_solve');self.guard.charge('head_triangular_solve')
        try:result=self.solve_head(rhs)
        except Exception as err:self.guard.stop('head_solve_'+type(err).__name__)
        return result
    def algebra(self):
        a=lambda fn:lambda v:self.array(fn(v))
        return Profiled(self.parameters,self.fields,self.heads,a(self.j),a(self.jt),
            a(lambda z:self.b_fn(self.xi,self.tensor(z))),a(lambda w:self.bt_fn(self.xi,self.tensor(w))),
            a(lambda v:self.point.k(self.tensor(v))),a(lambda v:self.point.k(self.tensor(v))),
            a(self.c),a(self.ct),self.solve)


class _Encode(torch.nn.Module):
    def __init__(self,net):super().__init__();self.net=net
    def forward(self,x):return self.net.encode(x)


class E011Bridge:
    """Uses existing net.encode and fieldCalculation, never instantiates a net.

    Fixed local T, exact saved Phi at the source; moving raw design is NOT
    detached. q_real uses the current raw UV head and original UV formula.
    Startup compares that formula with the existing fieldCalculation method.
    """
    def __init__(self,field,problem,space,guard):
        self.guard=guard;self.field=field;self.problem=problem;self.space=space
        self.physics={n:getattr(problem,n).detach().clone() for n in ['df','hist','f']}
        self.anchor={n:p.detach().clone() for n,p in field.alpha_constraint.state_dict().items()} if hasattr(field,'alpha_constraint') else {}
        flags=['williams_enabled','ansatz_enabled','exact_bc_enabled','symmetry_prior','local_patch_enabled']
        if any(getattr(field,n,False) for n in flags):raise AdapterStop('unsupported_UV_parameterization')
        if hasattr(field.net,'_orig_mod'):raise AdapterStop('compiled_network_not_supported')
        if list(field.net.named_buffers()):raise AdapterStop('mutable_network_buffers_not_supported')
        self.module=_Encode(field.net);self.state={n:p.detach().clone() for n,p in self.module.state_dict().items()}
        self.names=[n for n,_ in self.module.named_parameters() if not n.startswith('net.output_layer.')]
        if not self.names:raise AdapterStop('missing_hidden_parameters')
        self.x=check_tensor(problem.x);self.n=len(self.x);self.free=problem.fu.detach().clone()
        if self.free.ndim!=1 or self.free.dtype!=torch.long or len(torch.unique(self.free))!=len(self.free) or len(self.free)==0 or int(self.free.min())<0 or int(self.free.max())>=2*self.n:raise AdapterStop('invalid_free_DOF')
        self.head=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).detach().clone()
        self.T=check_tensor(torch.as_tensor(space['transform'],device=self.x.device,dtype=torch.float64)).detach().clone()
        self.phi=check_tensor(space['phi'],(self.n,self.T.shape[1])).detach().clone()
        if self.T.shape[0]!=self.head.shape[1]:raise AdapterStop('head_transform_shape')
        scales=[];self.slices={};offset=0
        for name in self.names:
            p=check_tensor(self.state[name]);n=p.numel();s=max(float(torch.sqrt(torch.mean(p.square()))),1e-3)*np.sqrt(n)
            if not np.isfinite(s):raise AdapterStop('parameter_scale_nonfinite')
            self.slices[name]=slice(offset,offset+n);scales.append(torch.full((n,),s,device=p.device,dtype=p.dtype));offset+=n
        self.scales=torch.cat(scales);self.zero=torch.zeros(offset,dtype=torch.float64,device=self.x.device)
        self.y0=field.domain_extrema[1,0].detach().clone();self.yL=field.domain_extrema[1,1].detach().clone()
        self.load=field.lmbda.detach().clone().reshape(());self.angle=field.theta.detach().clone().reshape(())
        if float(self.yL-self.y0)<=0:raise AdapterStop('invalid_original_boundary')
        self.bubble=(self.x[:,-1]-self.y0)*(self.yL-self.x[:,-1]);self.lift=(self.x[:,-1]-self.y0)/(self.yL-self.y0)*self.load
        self.raw0=None
    def parameter_state(self,xi):
        check_tensor(xi,self.zero.shape);result=dict(self.state)
        for n in self.names:result[n]=self.state[n]+(self.scales[self.slices[n]]*xi[self.slices[n]]).reshape(self.state[n].shape)
        return result
    def features(self,xi):
        return self.guard.invoke('raw_feature_forward',lambda:check_tensor(torch.func.functional_call(self.module,self.parameter_state(xi),(self.x,),strict=True)))
    def raw_design(self,xi):
        f=self.features(xi);check_tensor(f,(self.n,self.head.shape[1]-1))
        return self.load*self.bubble[:,None]*torch.cat((f,torch.ones((self.n,1),device=f.device,dtype=f.dtype)),dim=1)
    def q_full(self,xi):
        # Keep original UV arithmetic order (bubble*raw + lift/load)*load.
        f=self.features(xi);raw=f@self.head[:,:-1].T+self.head[:,-1]
        u=(self.bubble*raw[:,0]+(self.x[:,-1]-self.y0)/(self.yL-self.y0)*torch.cos(self.angle))*self.load
        v=(self.bubble*raw[:,1]+(self.x[:,-1]-self.y0)/(self.yL-self.y0)*torch.sin(self.angle))*self.load
        return torch.cat((u,v))
    def q(self,xi):return self.q_full(xi)[self.free]
    def moving_phi(self,xi):
        if self.raw0 is None:raise AdapterStop('startup_not_completed')
        return self.phi+(self.raw_design(xi)-self.raw0)@self.T
    def b(self,xi,z):
        inc=self.moving_phi(xi)@z.reshape(2,-1).T
        return torch.cat((inc[:,0],inc[:,1]))[self.free]
    def bt(self,xi,w):
        full=torch.zeros(2*self.n,dtype=torch.float64,device=w.device).scatter(0,self.free,w)
        p=self.moving_phi(xi);return torch.cat((p.T@full[:self.n],p.T@full[self.n:]))
    def startup(self):
        self.guard.charge('energy_force_field');self.guard.charge('raw_feature_forward')
        with torch.no_grad():
            u,v,_=self.field.fieldCalculation(self.x);actual=torch.cat((u,v));ours=self.q_full(self.zero)
            if float((actual-ours).abs().max())>1e-12:self.guard.stop('original_UV_formula_mismatch')
            self.raw0=self.raw_design(self.zero).detach().clone()
            if not torch.equal(self.moving_phi(self.zero),self.phi):self.guard.stop('initial_saved_Phi_not_reused')
            # B must be zero on prescribed DOF; reactions must not enter BT.
            fullphi=torch.cat((self.phi,self.phi),dim=0);mask=torch.ones(2*self.n,dtype=torch.bool,device=self.x.device);mask[self.free]=False
            if bool(mask.any()) and float(fullphi[mask].abs().max())>1e-12:self.guard.stop('basis_changes_prescribed_UV')
        self.verify_frozen();self.guard.check()
    def verify_frozen(self):
        if any(not torch.equal(p,self.state[n]) for n,p in self.module.state_dict().items()):self.guard.stop('source_network_mutated')
        if any(not torch.equal(getattr(self.problem,n),p) for n,p in self.physics.items()):self.guard.stop('frozen_physics_mutated')
        if self.anchor and any(not torch.equal(self.field.alpha_constraint.state_dict()[n],p) for n,p in self.anchor.items()):self.guard.stop('B0_anchor_mutated')
        if not torch.equal(self.field.lmbda.reshape(()),self.load) or not torch.equal(self.field.theta.reshape(()),self.angle):self.guard.stop('UV_loading_mutated')
        if not torch.equal(self.field.domain_extrema[1,0],self.y0) or not torch.equal(self.field.domain_extrema[1,1],self.yL):self.guard.stop('UV_domain_mutated')
    def energy_point(self):
        qfull=self.q_full(self.zero).detach();p=self.problem
        with torch.no_grad():
            tr=p.grad(qfull[:self.n])[:,:,0]+p.grad(qfull[self.n:])[:,:,1]
            if bool((tr==0).any()):self.guard.stop('Amor_zero_trace_profile_not_differentiable')
        def energy(q):
            full=qfull.scatter(0,self.free,q);return p.parts(full[:self.n],full[self.n:],p.df)[0]
        return EnergyPoint(qfull[self.free],energy,self.guard)
    def connect(self,head_hessian):
        self.guard.check()
        if self.raw0 is None:raise AdapterStop('startup_not_completed')
        if tuple(head_hessian.shape)!=(2*self.T.shape[1],2*self.T.shape[1]):raise AdapterStop('H_does_not_match_actual_Phi')
        point=self.energy_point()
        try:return AutogradChart(self.zero,self.q,self.b,self.bt,point,head_hessian,self.guard)
        except Exception:
            point.close();raise


def reprofile_check(algebra,reprofile,directions,*,rank,eps=1e-6,relative=1e-4,absolute=1e-10,recorder=None):
    """Same actual-profile gate; observe raw sides and comparison BEFORE stops.

    Recording performs no additional model, AD, basis or solver evaluations.
    The recorder is mandatory in Runtime; optional for legacy artificial callers.
    """
    def emit(event,data=None,arrays=None):
        if recorder is not None:recorder(event,data,arrays)
    rows=[];position={}
    try:
        emit('check_start',dict(rank=rank,eps=eps,relative=relative,absolute=absolute,
            fields=algebra.fields,parameters=algebra.parameters,norm='unweighted Euclidean L2 of free DOFs; original free index order'))
        if reprofile is None:raise AdapterStop('missing_real_full_reprofile_hook')
        if not np.isfinite([eps,relative,absolute]).all() or min(eps,relative,absolute)<=0:raise AdapterStop('invalid_reprofile_tolerances')
        def checked(delta,side):
            position['side']=side
            emit('side_start',dict(position),{'delta':delta})
            out=reprofile(delta)
            # Raw callback arrays and all saved solver/rollback references precede
            # contract validation. No coercion changes the old validation order.
            emit('side_returned',{**position,**trial_metadata(out)},{'q_raw':out.get('q')})
            for key in ['actual_nn','full_current_basis','persisted_actual_phi','frozen_state','rolled_back']:
                if out.get(key) is not True:raise AdapterStop('unverified_reprofile_'+key)
            if out.get('rank')!=rank:raise AdapterStop('reprofile_rank_changed')
            for key in ['head_gradient_inf','realization_maxabs']:
                value=out.get(key)
                if value is None or not np.isfinite(value) or value<0 or value>1e-10:raise AdapterStop('reprofile_'+key)
            q=np.asarray(out['q'],dtype=float)
            if q.shape!=(algebra.fields,) or not np.isfinite(q).all():raise AdapterStop('invalid_actual_reprofile_fields')
            emit('side_validated',dict(position))
            return q
        for index,direction in enumerate(directions):
            position={'direction':index};v=np.asarray(direction,dtype=float)
            emit('direction',dict(position),{'v':v})
            predicted=algebra.q(v)
            emit('prediction',dict(position),{'Qv':predicted})
            for h in [eps,eps/2]:
                position={'direction':index,'h':h}
                plus=checked(h*v,'plus');minus=checked(-h*v,'minus')
                fd=(plus-minus)/(2*h)
                error=float(np.linalg.norm(predicted-fd));scale=max(float(np.linalg.norm(predicted)),float(np.linalg.norm(fd)))
                rows.append(dict(h=h,error=error,scale=scale))
                emit('comparison',dict(direction=index,h=h,error=error,scale=scale,
                    tolerance=absolute+relative*scale,predicted_norm=float(np.linalg.norm(predicted)),FD_norm=float(np.linalg.norm(fd)),
                    norm='unweighted Euclidean L2 of free DOFs; original free index order'),
                    {'FD':fd,'difference':predicted-fd})
                if error>absolute+relative*scale:raise AdapterStop('actual_full_profile_derivative_mismatch')
        if not rows:raise AdapterStop('missing_reprofile_directions')
        emit('check_passed',dict(rows=rows))
        return rows
    except Exception as err:
        try:emit('check_failed',dict(position=position,type=type(err).__name__,message=str(err)))
        except Exception as recording_error:note_record_failure(err,recording_error)
        raise


def probe_algebra(algebra,H,guard,*,seed=173):
    """Two fixed artificial-direction dot checks on the supplied runtime map.

    These check the implemented local chart only; full reprofile FD remains
    mandatory and independent. No new solves/truncation are used to repair it.
    """
    rng=np.random.default_rng(seed);rows=[];directions=[]
    for _ in range(2):
        v=rng.normal(size=algebra.parameters);v/=np.linalg.norm(v)
        w=rng.normal(size=algebra.fields);w/=np.linalg.norm(w)
        z=rng.normal(size=algebra.heads);z/=np.linalg.norm(z);directions.append(v)
        for name,f,ft,right in [('J',algebra.j,algebra.jt,w),('C',algebra.c,algebra.ct,z),
                                 ('U',algebra.u,algebra.ut,z),('Q',algebra.q,algebra.qt,w),('Z',algebra.z,algebra.zt,w)]:
            left=float(f(v)@right);adjoint=float(v@ft(right));error=abs(left-adjoint)
            rows.append(dict(kind=name,error=error,scale=max(abs(left),abs(adjoint))))
            if not np.isfinite([left,adjoint]).all() or error>1e-10+1e-6*max(abs(left),abs(adjoint)):guard.stop('local_adjoint_'+name)
        hz=np.asarray(H)@z;bkb=algebra.bt(algebra.k(algebra.b(z)))
        error=float(np.linalg.norm(hz-bkb));scale=max(float(np.linalg.norm(hz)),float(np.linalg.norm(bkb)))
        rows.append(dict(kind='native_H_vs_BtKB',error=error,scale=scale))
        if not np.isfinite([error,scale]).all() or error>1e-10+1e-6*scale:guard.stop('local_head_tangent_mismatch')
    return rows,directions
