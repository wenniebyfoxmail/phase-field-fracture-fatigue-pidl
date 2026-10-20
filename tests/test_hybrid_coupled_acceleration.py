"""Artificial algebraic maps/Q4 only. No project arrays, profile or producer."""
from dataclasses import replace,asdict
from types import SimpleNamespace
import json
import numpy as np
import pytest
from hybrid_coupled_acceleration import CouplingSettings,ProjectedAnderson,joint_merit
from hybrid_incremental import solve_step,StepFailure,NativeQ4Backend
from hybrid_work_trace import PersistentWorkTrace
from test_hybrid_incremental import AlgebraicBackend,state,settings,one_element


def solve(backend=None,**kwargs):
    return solve_step(backend or AlgebraicBackend(),state(),np.array([0]),np.array([0.]),next_load_id='artificial',
                      settings=kwargs.pop('settings',settings()),coupling=kwargs.pop('coupling',CouplingSettings(mode='projected_anderson')),**kwargs)


def test_acceleration_reaches_same_fresh_fixed_point_within_shared_map_budget():
    old=state();before=old.fingerprint()
    with pytest.raises(StepFailure,match='iteration cap'):solve(coupling=CouplingSettings(),settings=settings(max_outer=8))
    p=solve(settings=settings(max_outer=8));plain=solve(coupling=CouplingSettings())
    assert p.certificate['outer']<plain.certificate['outer'] and p.certificate['outer']<=8
    assert p.certificate['coupling_work']['proposals']>=1 and p.certificate['coupling_work']['kept_accelerated_maps']>=1
    assert np.max(abs(p.state.damage-plain.state.damage))<3e-7 and np.max(abs(p.state.damage-.4))<1e-8
    assert p.certificate['damage']['kkt_scaled_inf']<=1e-7 and old.fingerprint()==before
    assert np.allclose(p.state.accumulated,(1-p.state.damage[0])**2*p.state.damage[0])
    assert sum(w['kind']=='fresh_final_force' for w in p.work)==p.certificate['outer']


def test_projection_uses_original_lower_and_only_stable_free_nodes():
    lo=np.array([1.,.2,0.,0.]);a=ProjectedAnderson(lo,np.array([1,0,0,0],bool),np.ones(4),1e-10,CouplingSettings(mode='projected_anderson'))
    a.add(np.array([1.,.5,0.,1.]),np.array([1.,.35,0.,1.]))
    a.add(np.array([1.,.35,0.,1.]),np.array([1.,.425,.1,.9]))
    candidate,meta=a.propose()
    assert candidate is not None and meta['stable_free_nodes']==1
    assert lo[1]<=candidate[1]<.425 and candidate[0]==1. and np.array_equal(candidate[2:],[.1,.9])
    p=solve(classical_initial=np.full(4,.8))
    assert np.all(p.state.damage<.8) and np.all(p.state.damage>=state().damage)


class CachedAlgebraic(NativeQ4Backend,AlgebraicBackend):
    """Not a project FEM: symbolic u=d map with a fake cache checkpoint."""
    def __init__(self):
        from native_q4_damage_qp import gauss_interpolation_matrix
        self.kin=one_element();self.gp=gauss_interpolation_matrix(self.kin);self.crack=np.zeros(4,bool)
        self.mechanics_workspace=SimpleNamespace(factor_key=None,factor=None);self.cache_calls=[]
    validate_state=AlgebraicBackend.validate_state
    trial=AlgebraicBackend.trial
    damage_problem=AlgebraicBackend.damage_problem
    force_audit=AlgebraicBackend.force_audit
    def mechanics(self,d,dofs,values,settings,initial_u=None):
        self.cache_calls.append((float(d[0]),self.mechanics_workspace.factor_key))
        self.mechanics_workspace.factor_key=float(d[0]);self.mechanics_workspace.factor=object()
        return np.repeat(d,2),dict(iterations=1)


def test_bad_trial_restores_full_baseline_d_u_and_cache(monkeypatch):
    count=[0];real=ProjectedAnderson.propose
    def bad(self):
        if len(self.history)>=2 and count[0]==0:
            count[0]+=1;self.proposals+=1;return np.full(4,.95),dict(reason='injected_bad_feasible_guess')
        return real(self)
    monkeypatch.setattr(ProjectedAnderson,'propose',bad)
    b=CachedAlgebraic();records=[];p=solve(b,iteration_observer=records.append)
    reject=next(x for x in records if not x['kept_as_iteration_point']);baseline=records[reject['baseline_outer']-1]
    following=records[reject['outer']]
    assert reject['rejection_reason']=='joint_merit_guard'
    assert reject['restored_baseline_damage_id']==baseline['output_damage_id']==following['input_damage_id']
    assert reject['restored_baseline_u_id']==baseline['output_equilibrated_u_id']==following['mechanical_warm_start_u_id']
    assert p.certificate['coupling_work']['rejections']==1 and p.certificate['coupling_work']['proposals']==1
    assert any(abs(d-.35)<1e-9 and abs(cache-.3)<1e-9 for d,cache in b.cache_calls if cache is not None)
    assert np.allclose(p.state.accumulated,(1-p.state.damage[0])**2*p.state.damage[0])


def test_real_trial_numerical_failure_is_not_swallowed(monkeypatch):
    def bad(self):
        if len(self.history)>=2:return np.full(4,.95),dict(reason='injected')
        return None,dict(reason='history')
    monkeypatch.setattr(ProjectedAnderson,'propose',bad)
    class Broken(CachedAlgebraic):
        def mechanics(self,d,*args,**kwargs):
            if d[0]>.9:raise RuntimeError('original pivot failure')
            return super().mechanics(d,*args,**kwargs)
    rows=[]
    with pytest.raises(StepFailure,match='original pivot failure'):solve(Broken(),iteration_observer=rows.append)
    assert len(rows)==2 and not any(x['passed_physical'] for x in rows)


def test_merit_keeps_global_l2_fatigue_and_nonfinite_predicates():
    d=dict(primal_inf=0.,kkt_scaled_inf=0.,projected_inf=0.,kkt_l2=0.)
    f=dict(force_inf=0.,force_scaled=0.,force_l2=0.,boundary_inf=0.)
    assert joint_merit(d,f,0.,settings())==0.
    assert joint_merit(dict(d,kkt_l2=8e-6),f,0.,settings())>1.
    assert joint_merit(d,f,2e-8,settings())>1.
    with pytest.raises(RuntimeError,match='nonfinite'):joint_merit(d,dict(f,force_l2=np.nan),0.,settings())
    with pytest.raises(RuntimeError,match='nonfinite'):joint_merit(d,dict(f,force_inf=np.nan),0.,settings())


def test_degenerate_history_and_algebraic_guards_skip_without_physical_trials():
    policy=CouplingSettings(mode='projected_anderson');a=ProjectedAnderson(np.zeros(4),np.zeros(4,bool),np.ones(4),1e-10,policy)
    assert a.propose()[0] is None
    a.add(np.full(4,.2),np.full(4,.3));a.add(np.full(4,.2),np.full(4,.3))
    assert a.propose()[1]['reason']=='zero_secant_information' and a.proposals==0
    b=ProjectedAnderson(np.zeros(4),np.zeros(4,bool),np.ones(4),1e-10,replace(policy,coefficient_l1_cap=1.))
    b.add(np.zeros(4),np.full(4,.2));b.add(np.full(4,.2),np.full(4,.3))
    assert b.propose()[1]['reason']=='coefficient_guard'
    c=ProjectedAnderson(np.zeros(4),np.zeros(4,bool),np.ones(4),1e-10,replace(policy,trust_factor=.01))
    c.add(np.zeros(4),np.full(4,.2));c.add(np.full(4,.2),np.full(4,.3))
    assert c.propose()[1]['reason']=='trust_guard'
    z=ProjectedAnderson(np.zeros(4),np.zeros(4,bool),np.ones(4),1e-10,policy)
    z.add(np.zeros(4),np.zeros(4));z.add(np.zeros(4),np.zeros(4))
    assert z.propose()[1]['reason']=='no_stable_free_nodes'


def test_iteration_evidence_persists_fresh_scalars_and_failure_stays_fatal(tmp_path,monkeypatch):
    import hybrid_work_trace as t
    trace=PersistentWorkTrace(tmp_path/'work_trace.jsonl','unit',1)
    p=solve(work_observer=trace.call,iteration_observer=trace.record_iteration)
    rows=[json.loads(x) for x in (tmp_path/'iterations.jsonl').read_text().splitlines()]
    assert len(rows)==p.certificate['outer'] and rows[-1]['passed_physical']
    assert all('damage' in x and 'force' in x and 'active_counts' in x for x in rows)
    original=t.append_event
    def fail(path,value):
        if str(path).endswith('iterations.jsonl'):raise OSError('iteration disk failure')
        return original(path,value)
    monkeypatch.setattr(t,'append_event',fail)
    with pytest.raises(StepFailure,match='durable joint iteration evidence failed'):solve(iteration_observer=trace.record_iteration)


def test_iteration_logging_cannot_extend120_seconds(monkeypatch):
    import hybrid_incremental as i
    now=[0.];monkeypatch.setattr(i,'perf_counter',lambda:now[0])
    def evidence(row):now[0]=121.
    with pytest.raises(StepFailure,match='wall cap'):solve(iteration_observer=evidence)


def test_policy_provenance_is_shared_and_mixed_labels_are_rejected():
    from hybrid_producer_worker import coupling_identity,verify_label_coupling
    from run_hybrid_producer import validate_card
    from test_hybrid_producer import card
    c=card();c['coupling']=asdict(CouplingSettings(mode='projected_anderson'));validate_card(c)
    identity=coupling_identity(c)
    verify_label_coupling(dict(coupling_policy_id=identity,certificate=dict(coupling_policy_id=identity)),identity)
    with pytest.raises(RuntimeError,match='policy differs'):verify_label_coupling(dict(coupling_policy_id='old',certificate={}),identity)
    c['phases'][-1]['coupling']={}
    with pytest.raises(ValueError,match='shared coupling'):validate_card(c)


def test_fatigue_feedback_is_rebuilt_from_old_and_passes_original_consistency():
    from hybrid_history import trial_history
    class Feedback(AlgebraicBackend):
        def trial(self,old,u,d):
            psi=np.full((1,4),u[0]);q=trial_history(old,np.full((1,4),d[0]),psi,alpha_t=.01,power=2.)
            return psi,q
        def damage_problem(self,psi,f,old):
            from hybrid_damage import NodalQP
            from scipy import sparse
            target=.2+.2*psi[0,0]+.02*f[0,0]
            return NodalQP(sparse.eye(4,format='csc'),np.full(4,-target),old.damage,np.ones(4),str(target))
    p=solve(Feedback());plain=solve(Feedback(),coupling=CouplingSettings())
    assert np.all(p.state.fatigue<1.) and p.certificate['fatigue_residual']<=settings().fatigue_tolerance
    assert np.max(abs(p.state.damage-plain.state.damage))<3e-7
    assert np.allclose(p.state.accumulated,(1-p.state.damage[0])**2*p.state.damage[0])


def test_failed_past_costs_are_charged_once_without_becoming_admission(tmp_path):
    from run_hybrid_producer import initial_totals
    from hybrid_inputs import sha256
    from hybrid_producer_common import write_json
    from test_hybrid_producer import card
    f=tmp_path/'frozen.json';write_json(f,dict(passed=False,w=617.,c=572.,g=0.,n=340.))
    c=card();c['prior_costs']=[dict(source=f.name,sha256=sha256(f),lineage=['R1','V01','V02'],cost_only_not_admission=True,
                                metrics=dict(wall_seconds=['w'],cpu_seconds=['c'],gpu_seconds=['g'],numerical_seconds=['n']))]
    t=initial_totals(c,1000.,tmp_path)
    assert t['wall_seconds']==617. and t['start_monotonic']==383. and t['shared_analysis_seconds']==277.
    assert t['pre_execution_cost']['cost_only_not_admission'] is True and t['phases']=={}
    c['prior_costs']*=2
    with pytest.raises(RuntimeError,match='overlapping'):initial_totals(c,1000.,tmp_path)
    c['prior_costs']=c['prior_costs'][:1];f.write_text('{}')
    with pytest.raises(RuntimeError,match='source differs'):initial_totals(c,1000.,tmp_path)


def test_already_accepted_native_one_q4_never_wastes_accelerated_map():
    fields=[]
    for mode in ('none','projected_anderson'):
        b=NativeQ4Backend(one_element(),np.array([1,0,0,0],bool),length_scale=.1,alpha_t=1e6)
        old=replace(state(np.array([1.,0,0,0])),mesh_id=b.mesh_id,physics_id=b.physics_id)
        p=solve_step(b,old,np.array([0,1,3,5,7]),np.array([0.,0,0,.2,.2]),next_load_id='artificial_Q4',settings=settings(),coupling=CouplingSettings(mode=mode))
        assert p.certificate['outer']==1 and p.certificate['coupling_work']['proposals']==0
        assert p.certificate['damage']['primal_inf']<=settings().bound_tolerance and p.certificate['mechanics']['force_l2']<=1e-8
        fields.append(p.state.fingerprint())
    assert fields[0]==fields[1]


def test_regularized_condition_guard_rejects_unreliable_secant_window():
    p=CouplingSettings(mode='projected_anderson',condition_cap=1.)
    a=ProjectedAnderson(np.zeros(4),np.zeros(4,bool),np.ones(4),1e-10,p)
    a.add(np.array([.1,.2,.1,.2]),np.array([.2,.3,.2,.3]))
    a.add(np.array([.2,.3,.2,.3]),np.array([.3,.35,.3,.35]))
    a.add(np.array([.3,.35,.3,.35]),np.array([.375,.4,.375,.4]))
    candidate,why=a.propose()
    assert candidate is None and why['reason']=='regularized_condition_guard' and a.proposals==0
