"""Tiny algebra fixtures; never load a trained network or research fields."""
import numpy as np
from analyze_pidl_hidden_directions import Operator,decompose,diagonal_statistics,signed_localization,transition


def fixture(d=None):
    p=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
    z=dict(nodes=p,cells=np.array([[0,1,2,3]]),d_fem=np.array([.2,.3,.4,.5]) if d is None else d,freeu=np.arange(8))
    op=Operator(z);q=np.r_[-.2*p[:,0],.1*p[:,1]];v=np.r_[.4*p[:,0],.03*p[:,1]]
    return op,q,v


def test_energy_gradient_and_action():
    op,q,v=fixture();s=op.evaluate(q);k,_=op.action(s,v)
    h=1e-6;p=op.evaluate(q+h*v);m=op.evaluate(q-h*v)
    assert abs((p['E']-m['E'])/(2*h)-s['R']@v)<1e-10
    assert np.max(np.abs((p['R']-m['R'])/(2*h)-k))<1e-10


def test_piecewise_exact_integral_crosses_trace_branch():
    op,q,v=fixture();s=op.evaluate(q);end=op.evaluate(q+v);c,secant=op.integrated_curvature(s,v)
    assert np.any((s['tr']>=0)!=(end['tr']>=0))
    assert abs(end['E']-s['E']-s['R']@v-c)<1e-14
    assert np.max(np.abs(end['R']-s['R']-secant))<1e-14


def test_exact_integral_reverse_crossing():
    op,q,v=fixture();s=op.evaluate(q+v);end=op.evaluate(q);c,secant=op.integrated_curvature(s,-v)
    assert abs(end['E']-s['E']+s['R']@v-c)<1e-14
    assert np.max(np.abs(end['R']-s['R']-secant))<1e-14


def test_diagonal_matches_matrix_actions():
    op,q,v=fixture();s=op.evaluate(q);h=np.stack([op.action(s,x)[0] for x in np.eye(8)],axis=1)
    assert np.max(np.abs(h-h.T))<1e-14
    assert np.max(np.abs(np.diag(h)-op.diagonal(s)))<1e-14
    assert np.linalg.eigvalsh(h).min()>-1e-13


def test_zero_trace_one_sided_policy():
    op,q,v=fixture();q=np.zeros(8);s=op.evaluate(q)
    for direction in [v,-v]:
        k,_=op.action(s,direction,True);z=op.evaluate(q+1e-5*direction)
        assert np.max(np.abs((z['R']-s['R'])/1e-5-k))<1e-13
        c,sec=op.integrated_curvature(s,direction)
        end=op.evaluate(q+direction)
        assert abs(end['E']-c)<1e-14
        assert np.max(np.abs(end['R']-sec))<1e-14


def test_zero_degradation_diagonal_no_floor():
    op,q,v=fixture(np.ones(4));op.g[:]=0  # exact-zero algebra fixture, independent of interpolation roundoff
    s=op.evaluate(q+v)
    assert np.array_equal(op.diagonal(s),np.zeros(8))


def test_tiny_positive_diagonal_is_not_floored():
    op,q,v=fixture();op.g[:]=1e-30;s=op.evaluate(q+v)
    assert 0<op.diagonal(s).max()<1e-29


def test_squared_difference_exact_with_weights():
    a=np.array([1.,2.,4.]);b=np.array([4.,-1.,2.]);w=np.array([.1,.3,.2])
    r=decompose(a,b,w)
    assert abs(r['closure_error'])<1e-14


def test_zero_diagonal_and_zero_residual_statistics_are_explicit():
    z=diagonal_statistics(np.zeros(3),np.zeros(3))
    assert z['positive_diagonal_percentiles'] is None
    assert z['zero_diagonal_residual_squared_share'] is None
    assert z['undefined_reason']=='zero_residual'
    z=diagonal_statistics(np.zeros(3),np.array([1.,0.,0.]))
    assert z['zero_diagonal_residual_squared_share']==1
    assert z['undefined_reason']=='no_positive_diagonal'


def test_signed_increment_localization_closes_and_empty_sign_is_null():
    d=np.array([2.,-1.,0.]);xy=np.array([[0.,0.],[1.,0.],[2.,0.]])
    r=signed_localization(d,xy)
    assert r['signed_total']==1 and r['positive']['magnitude']==2 and r['negative']['magnitude']==1
    assert r['positive']['centroid']==[0.,0.] and r['negative']['centroid']==[1.,0.]
    assert signed_localization(np.zeros(3),xy)['positive']['centroid'] is None


def test_merit_derivative_factor_and_energy_components():
    op,q,v=fixture();a=op.evaluate(q);b=op.evaluate(q+.01*v);ref=op.evaluate(.5*q)
    row=transition(op,a,b,ref,'toy_net')
    eps=1e-6;z=op.evaluate(q+eps*(b['q']-q))
    fd=(np.sum(op.w*(z['active']-ref['active'])**2)-np.sum(op.w*(a['active']-ref['active'])**2))/eps
    assert abs(fd-row['active_squared_error_forward_directional'])<1e-10
    fdR=(np.dot(z['rf'],z['rf'])-np.dot(a['rf'],a['rf']))/(2*eps)
    assert abs(fdR-row['residual_half_squared_merit_forward_directional'])<1e-10
    assert abs(a['energy_component_closure_error'])<1e-14
    assert abs(row['energy_component_change_closure_error'])<1e-14


def test_field_budget_preserves_count(tmp_path):
    op,q,v=fixture();op.audit_out=tmp_path;op.cap=1;op.evaluate(q)
    import pytest,json
    with pytest.raises(RuntimeError,match='saved_array_budget_exhausted'):op.evaluate(q)
    assert json.loads((tmp_path/'work_partial.json').read_text())['field_evaluations']==1
