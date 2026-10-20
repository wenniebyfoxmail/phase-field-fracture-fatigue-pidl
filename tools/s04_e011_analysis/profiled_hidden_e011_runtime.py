"""E011 existing-object runtime bridge, PREPARATION ONLY, no CLI or loader.

Never call on real objects without a separately approved, hash-bound producer
package and external watchdog. Importing does not import old E011 workers.
"""
from pathlib import Path
import hashlib
import numpy as np
import torch
from profiled_hidden_adapter import AdapterStop,E011Bridge,reprofile_check,probe_algebra
from profiled_hidden_kernel import conjugate_gradient,common_descent,limit_step,finite_trial_decision


class BudgetProxy:
    def __init__(self,legacy,guard):self.legacy=legacy;self.guard=guard
    def __getattr__(self,n):return getattr(self.legacy,n)
    def begin(self,role,**kw):
        self.guard.charge('energy_force_field');return self.legacy.begin(role,**kw)


class WorkProxy:
    """Charges old reviewed assembly/Newton helpers without modifying them."""
    def __init__(self,legacy,guard):self.legacy=legacy;self.guard=guard
    def __getattr__(self,n):return getattr(self.legacy,n)
    @property
    def assemblies(self):return self.legacy.assemblies
    @assemblies.setter
    def assemblies(self,n):
        if n!=self.legacy.assemblies+1:raise AdapterStop('invalid_assembly_increment')
        self.guard.charge('head_assembly');self.legacy.assemblies=n
    @property
    def solves(self):return self.legacy.solves
    @solves.setter
    def solves(self,n):
        if n!=self.legacy.solves+1:raise AdapterStop('invalid_solve_increment')
        self.guard.charge('head_factor')
        self.guard.charge('head_triangular_solve');self.guard.charge('head_triangular_solve');self.legacy.solves=n
    def check(self):self.guard.check();self.legacy.check()
    def product(self,role):self.guard.charge('explicit_head_products');self.legacy.product(role)


def binding(path):
    path=Path(path);h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=h.hexdigest())


def tensor_identity(state):
    h=hashlib.sha256()
    for name in sorted(state):
        value=state[name].detach().cpu().contiguous().numpy()
        h.update(name.encode());h.update(str(value.dtype).encode());h.update(str(value.shape).encode());h.update(value.tobytes())
    return h.hexdigest()


def candidate_identity(candidate):
    return dict(weights=tensor_identity(candidate['candidate_state']),
        phi=tensor_identity({'Phi':candidate['candidate_space']['phi']}),
        transform=hashlib.sha256(np.ascontiguousarray(candidate['candidate_space']['transform']).tobytes()).hexdigest(),
        q=hashlib.sha256(np.ascontiguousarray(candidate['q']).tobytes()).hexdigest())


class Runtime:
    """One frozen local point; all trial callbacks restore before returning.

    Existing E011 objects must already have passed source hashing/loading,
    native operator and triple saved-Phi readout admission in the producer.
    The future outer controller owns the separate phase hard deadlines.
    """
    def __init__(self,field,problem,space,budget,work,folder,guard,*,scales=None,helpers=None):
        self.guard=guard;self.folder=Path(folder);self.field=field;self.problem=problem;self.space=space
        # Lazy: no old worker import on module import or artificial helper tests.
        if helpers is None:import run_pidl_persisted_phi_hidden_newton as helpers
        self.h=helpers;self.budget=BudgetProxy(budget,guard);self.work=WorkProxy(work,guard)
        self.bridge=E011Bridge(field,problem,space,guard)
        if scales is not None:
            if scales.shape!=self.bridge.scales.shape or not bool(torch.isfinite(scales).all()) or bool((scales<=0).any()):raise AdapterStop('invalid_frozen_parameter_scaling')
            self.bridge.scales=scales.detach().clone()
        self.number=0;self.root_rank=space['transform'].shape[1];self.chart=None
        self.source_admitted=False;self.profile_verified=False;self.eligible_candidates={}
        self.folder.mkdir(parents=True,exist_ok=False)
    def form_chart(self):
        if not self.source_admitted:self.guard.stop('missing_triple_source_admission')
        self.bridge.startup()
        self.guard.charge('raw_feature_forward')
        with torch.no_grad():u,v,_=self.field.fieldCalculation(self.problem.x)
        reduced=self.h.ReducedElastic(self.problem,self.space['phi'],u,v)
        tangent=self.h.HiddenTangent(reduced,self.work)
        H,tr=tangent.matrix(np.zeros(2*self.root_rank))
        if bool((tr==0).any()):self.guard.stop('Amor_zero_trace_profile_not_differentiable')
        self.head_H=H.detach().cpu().numpy();self.chart=self.bridge.connect(self.head_H)
        self.point_q=self.bridge.q(self.bridge.zero).detach().cpu().numpy()
        self.root_E=float(self.chart.point.value.detach())
        self.root_Ru=float(torch.linalg.vector_norm(self.chart.point.force.detach()))
        np.savez_compressed(self.folder/'local_physical_point.npz',q=self.point_q,R=self.chart.array(self.chart.force),H=self.head_H,hidden_scaling=self.bridge.scales.cpu().numpy())
        projected=self.bridge.bt(self.bridge.zero,self.chart.force)
        self.h.dump(self.folder/'local_chart_admission.json',dict(E=self.root_E,Ru=self.root_Ru,
            actual_Phi_gradient_inf=float(projected.abs().max()),rank=self.root_rank,
            zero_trace_points=0,anchored_chart_is_not_actual_NN_certificate=True))
        if float(projected.abs().max())>1e-10:self.guard.stop('actual_saved_Phi_head_not_closed')
        return self.chart.algebra()
    def trial(self,delta):
        """Fresh full-current SVD, native head solve, actual NN replay, rollback.

        All native outputs are persisted by the reviewed helpers. This method
        does not accept or promote a method endpoint; one callback = one trial.
        """
        self.guard.check();self.number+=1;folder=self.folder/f'trial_{self.number:03d}';folder.mkdir()
        before=self.h.snapshot(self.field.net);flags=[p.requires_grad for p in self.field.net.parameters()]
        result=None
        try:
            state=self.bridge.parameter_state(torch.as_tensor(delta,device=self.bridge.zero.device,dtype=torch.float64))
            self.field.net.load_state_dict({n.removeprefix('net.'):p.detach() for n,p in state.items()})
            torch.save(self.h.snapshot(self.field.net),folder/'hidden_trial_network.pt')
            self.guard.charge('raw_feature_forward');self.guard.charge('svd')
            fresh=self.h.build_full_space(self.field,self.problem,self.work)
            self.h.persist_space(fresh,folder/'basis',self.field)
            if fresh['transform'].shape[1]!=self.root_rank:self.guard.stop('full_current_rank_changed')
            self.guard.charge('raw_feature_forward')
            correction,_,linear=self.h.correct_full_head(self.field,self.problem,fresh,self.work,self.budget,folder/'head',self.number)
            if correction['hard_failure']:self.guard.stop('native_head_'+correction['solver']['stop'])
            self.guard.charge('raw_feature_forward');self.guard.charge('hidden_vjp')
            obs,fields,_=self.h.persisted_readout(self.field,self.problem,np.eye(fresh['transform'].shape[0]),self.budget,'trial_'+str(self.number),fresh)
            realization=self.h.linear_realization_error(fields,linear)
            saved_state=self.h.snapshot(self.field.net)
            torch.save(saved_state,folder/'actual_candidate_network.pt')
            full=np.concatenate((fields['u'],fields['v']));free=self.problem.fu.detach().cpu().numpy()
            result=dict(q=full[free],E=obs['E_el'],Ru=obs['free_u_l2'],rank=fresh['transform'].shape[1],
                actual_nn=True,full_current_basis=True,persisted_actual_phi=True,frozen_state=False,fixed_state=False,rolled_back=False,
                head_gradient_inf=obs['reduced_gradient_inf'],realization_maxabs=realization,finite=bool(np.isfinite(full).all()),
                candidate_state=saved_state,candidate_space=fresh,folder=str(folder))
            # Frozen damage/history/B0/BC and damage output row stay exact even
            # while hidden and the two UV output rows legitimately move.
            for name,value in self.bridge.physics.items():
                if not torch.equal(getattr(self.problem,name),value):self.guard.stop('trial_frozen_physics_changed')
            for name,value in self.bridge.anchor.items():
                if not torch.equal(self.field.alpha_constraint.state_dict()[name],value):self.guard.stop('trial_B0_changed')
            for name in ['output_layer.weight','output_layer.bias']:
                if not torch.equal(saved_state[name][2:],before[name][2:]):self.guard.stop('trial_damage_output_row_changed')
            mask=np.ones(2*self.bridge.n,dtype=bool);mask[free]=False
            with torch.no_grad():source_full=self.bridge.q_full(self.bridge.zero).detach().cpu().numpy()
            # q_full uses captured source parameters, not the mutated live net.
            bc_error=float(np.max(abs(full[mask]-source_full[mask]))) if mask.any() else 0.
            if not np.isfinite(bc_error) or bc_error>1e-12:self.guard.stop('trial_original_UV_boundary_changed')
            result.update(frozen_state=True,fixed_state=True,boundary_maxabs=bc_error,
                actual_readout=binding(Path(self.budget.folder)/'readouts'/('trial_'+str(self.number)+'.npz')),
                actual_weights=binding(folder/'actual_candidate_network.pt'))
            self.h.dump(folder/'adapter_observables.json',{k:v for k,v in result.items() if k not in ['q','candidate_state','candidate_space']})
        except Exception as err:
            self.h.dump(folder/'adapter_failure.json',dict(type=type(err).__name__,message=str(err),trial=self.number))
            self.guard.stopped=True;raise
        finally:
            self.field.net.load_state_dict(before)
            for p,flag in zip(self.field.net.parameters(),flags):p.requires_grad_(flag)
            same=all(torch.equal(p,before[n]) for n,p in self.field.net.state_dict().items())
            if not same:self.guard.stop('trial_rollback_failed')
            self.bridge.verify_frozen()
        if result is None:raise AdapterStop('trial_no_actual_result')
        result['rolled_back']=True
        # Persist rollback proof only after checking source state; no false
        # early receipt can pass the mandatory finite-profile callback.
        self.h.dump(folder/'rollback.json',dict(rolled_back=True,source_network_unchanged=True))
        self.guard.check();self.eligible_candidates[id(result)]=candidate_identity(result);return result
    def verify_profile(self,algebra,directions):
        try:rows=reprofile_check(algebra,self.trial,directions,rank=self.root_rank)
        except Exception as err:self.guard.stop('profile_'+str(err))
        self.profile_verified=True;return rows
    def promote(self,accepted):
        # Caller must have used finite_trial_decision, after profile preflight.
        if not self.source_admitted or not self.profile_verified or id(accepted) not in self.eligible_candidates:self.guard.stop('promotion_missing_source_profile_or_trial_identity')
        if not accepted.get('rolled_back') or not accepted.get('actual_nn'):raise AdapterStop('promotion_missing_actual_receipt')
        status=finite_trial_decision(dict(E=self.root_E,Ru=self.root_Ru),accepted)
        if status!='accepted':raise AdapterStop('promotion_'+status)
        self.guard.check();before=self.h.snapshot(self.field.net)
        try:
            if candidate_identity(accepted)!=self.eligible_candidates[id(accepted)]:self.guard.stop('promotion_candidate_identity_changed')
            if binding(accepted['actual_weights']['path'])!=accepted['actual_weights']:self.guard.stop('promotion_weights_file_changed')
            if binding(accepted['actual_readout']['path'])!=accepted['actual_readout']:self.guard.stop('promotion_fields_file_changed')
            self.field.net.load_state_dict(accepted['candidate_state'])
            self.guard.charge('raw_feature_forward')
            with torch.no_grad():u,v,_=self.field.fieldCalculation(self.problem.x)
            actual=torch.cat((u,v))[self.problem.fu].cpu().numpy()
            if not np.isfinite(actual).all() or np.max(abs(actual-accepted['q']))>1e-12:self.guard.stop('promotion_actual_field_replay_mismatch')
            return accepted['candidate_space']
        except Exception:
            self.field.net.load_state_dict(before);self.guard.stopped=True;raise
    def close(self):
        if self.chart is not None:self.chart.point.close();self.chart=None


def candidate_direction(algebra,force,physical_mass,physical_radius,*,parameter_radius=.01,recorder=None):
    """Fixed policy, explicit CG and direction status; no optimizer fallback."""
    p=algebra.parameters;rng=np.random.default_rng(1);rayleigh=[]
    for _ in range(2):
        v=rng.choice([-1.,1.],size=p)/np.sqrt(p)
        z=algebra.z(v);rayleigh.append(float(z@algebra.k(z)))
    scale=max(rayleigh)
    if not np.isfinite(scale) or scale<=0:raise AdapterStop('no_positive_metric_scale')
    damping=.001*scale;ge,gr=algebra.gradients(force)
    if recorder is not None:recorder('profile_gradients',energy=ge,residual=gr)
    solve=lambda g:conjugate_gradient(lambda v:algebra.metric(v,damping),g,max_steps=64,relative_tolerance=1e-4)
    direction,info=common_descent(ge,gr,solve)
    if direction is None:raise AdapterStop(info['status'])
    direction,tr=limit_step(direction,algebra,physical_mass,physical_radius,parameter_radius)
    if recorder is not None:recorder('profile_direction',direction=direction,predicted_field=algebra.q(direction))
    return direction,dict(damping=damping,rayleigh=rayleigh,**info,trust_region=tr)


def one_macrostep(runtime,directions_for_profile,physical_mass,physical_radius):
    """One actual profile-verified step; no loop, launch or implicit retry."""
    try:
        algebra=runtime.form_chart()
        dot_checks,default_directions=probe_algebra(algebra,runtime.head_H,runtime.guard)
        runtime.h.dump(runtime.folder/'local_dot_checks.json',dict(rows=dot_checks))
        profile=runtime.verify_profile(algebra,default_directions if directions_for_profile is None else directions_for_profile)
        def record(name,**arrays):np.savez_compressed(runtime.folder/(name+'.npz'),**arrays)
        direction,info=candidate_direction(algebra,runtime.chart.array(runtime.chart.force),physical_mass,physical_radius,recorder=record)
        for alpha in [1.,.5,.25,.125]:
            candidate=runtime.trial(alpha*direction)
            status=finite_trial_decision(dict(E=runtime.root_E,Ru=runtime.root_Ru),candidate)
            runtime.h.dump(Path(candidate['folder'])/'candidate_decision.json',dict(alpha=alpha,status=status,direction=info))
            if status in ['rejected_contract','rejected_head_or_realization']:runtime.guard.stop('finite_candidate_'+status)
            if status=='accepted':return dict(status='accepted',space=runtime.promote(candidate),candidate=candidate,direction=info,profile_checks=profile)
        return dict(status='no_accepted_finite_step',profile_checks=profile,direction=info)
    except Exception:
        runtime.guard.stopped=True;raise
    finally:runtime.close()


def startup_checks(runtime,source_fields,source_energy=.005268400005223913):
    """On already hash-verified loaded objects: three actual-Phi readouts.

    No SVD/reconstruction at zero update. Caller must bind the six exact assets
    and the existing make_smooth(original)->load_state_dict(initial) sequence.
    This function is never invoked by importing this module.
    """
    bridge=runtime.bridge;bridge.startup();rows=[];vectors=[]
    for repeat in range(3):
        runtime.guard.charge('raw_feature_forward');runtime.guard.charge('hidden_vjp')
        obs,fields,g=runtime.h.persisted_readout(runtime.field,runtime.problem,np.eye(bridge.T.shape[0]),
            runtime.budget,'profile_source_'+str(repeat),runtime.space)
        error=max(float(np.max(abs(fields[k]-source_fields[k]))) for k in ['u','v','d'])
        row=dict(repeat=repeat,E=obs['E_el'],head_gradient_inf=obs['reduced_gradient_inf'],source_fields_maxabs=error,
            passed=bool(error<=1e-12 and abs(obs['E_el']-source_energy)<=1e-10 and obs['reduced_gradient_inf']<=1e-10))
        rows.append(row);vectors.append(np.asarray(g).copy())
        runtime.h.dump(runtime.folder/'source_repetitions.json',dict(rows=rows))
        bridge.verify_frozen()
        if not row['passed']:runtime.guard.stop('source_triple_readout_miss')
    runtime.h.dump(runtime.folder/'source_repetitions.json',dict(rows=rows,
        projected_vector_spread=max(float(np.max(abs(v-vectors[0]))) for v in vectors),
        spread_is_diagnostic_not_new_threshold=True))
    runtime.source_admitted=True
    return rows


def verify_source_assets(card,paths,guard):
    """Hash six old assets/code before loading; no authorization is inferred.

    Input paths may be fresh-root copies but contents must equal the exact old
    source assets. This helper does not load arrays/models or grant execution.
    """
    rows=[]
    for asset in card['input_bindings']:
        guard.check()
        try:actual=binding(paths[asset['role']])
        except Exception as err:guard.stop('source_asset_unavailable_'+type(err).__name__)
        guard.check()
        if actual['sha256']!=asset['sha256'] or actual['bytes']!=asset['bytes']:guard.stop('source_asset_mismatch_'+asset['role'])
        rows.append(dict(role=asset['role'],**actual))
    return rows
