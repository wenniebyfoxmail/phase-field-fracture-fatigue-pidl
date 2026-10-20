"""ARTIFICIAL ONLY. No real model, arrays, loading, producer or FEM solve."""
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from profiled_hidden_adapter import (AdapterStop,Guard,EnergyPoint,AutogradChart,E011Bridge,reprofile_check,probe_algebra)


def guard(**overrides):
    caps={n:1000 for n in ['energy_force_field','native_tangent','hidden_jvp','hidden_vjp','C','CT','head_factor','head_triangular_solve','raw_feature_forward','svd']}
    caps.update(overrides);return Guard(caps,10.)


def moving_adapter(t=.4,shift=0.):
    g=guard();xi=torch.tensor([t],dtype=torch.float64);a=-t/(2+t*t);K=torch.diag(torch.tensor([2.,1.],dtype=torch.float64))
    def q(x):return torch.stack((torch.ones_like(x[0])*a,1+x[0]*a))
    def b(x,z):return torch.stack((z[0],(x[0]+shift)*z[0]))
    def bt(x,w):return (w[0]+(x[0]+shift)*w[1]).reshape(1)
    point=EnergyPoint(q(xi),lambda v:.5*v@K@v,g)
    H=np.array([[2+(t+shift)**2]])
    chart=AutogradChart(xi,q,b,bt,point,H,g)
    return chart,chart.algebra(),g


def actual_profile(theta):return np.array([-theta/(2+theta**2),2/(2+theta**2)])


def receipt(q,**kw):
    return dict(q=q,actual_nn=True,full_current_basis=True,persisted_actual_phi=True,frozen_state=True,rolled_back=True,rank=1,
                head_gradient_inf=1e-12,realization_maxabs=1e-12,**kw)


def test_moving_C_profile_jvp_vjp_and_actual_hook():
    chart,p,g=moving_adapter();v=np.array([.7]);w=np.array([.1,-.3]);h=1e-6
    fd=(actual_profile(.4+h*.7)-actual_profile(.4-h*.7))/(2*h)
    assert np.linalg.norm(p.q(v)-fd)<1e-9
    assert abs(p.q(v)@w-v@p.qt(w))<1e-14
    assert abs(p.c(v)[0])>.1 and abs(p.ct(np.ones(1))[0])>.1
    rows=reprofile_check(p,lambda d:receipt(actual_profile(.4+d[0])),[v],rank=1)
    assert len(rows)==2 and g.counts['hidden_jvp']>0 and g.counts['C']>0
    chart.point.close();assert chart.point.q is None


def test_anchored_graph_self_consistency_does_not_pass_wrong_actual_profile():
    _,p,g=moving_adapter(shift=.01)
    v=np.array([1.]);w=np.array([.4,.8]);assert abs(p.q(v)@w-v@p.qt(w))<1e-14
    with pytest.raises(AdapterStop,match='actual_full_profile_derivative_mismatch'):
        reprofile_check(p,lambda d:receipt(actual_profile(.4+d[0])),[v],rank=1)


@pytest.mark.parametrize('change,reason',[
    ({'rank':2},'rank_changed'),({'head_gradient_inf':1.1e-10},'head_gradient'),
    ({'realization_maxabs':1.1e-10},'realization'),({'full_current_basis':False},'full_current_basis'),
    ({'persisted_actual_phi':False},'persisted_actual_phi'),({'rolled_back':False},'rolled_back'),
    ({'q':np.array([np.nan,1.])},'fields')])
def test_reprofile_receipt_first_stops(change,reason):
    _,p,_=moving_adapter()
    with pytest.raises(AdapterStop,match=reason):
        reprofile_check(p,lambda d:{**receipt(actual_profile(.4+d[0])),**change},[np.ones(1)],rank=1)


def test_missing_hook_and_missing_direction_never_admit():
    _,p,_=moving_adapter()
    with pytest.raises(AdapterStop,match='missing_real'):reprofile_check(p,None,[np.ones(1)],rank=1)
    with pytest.raises(AdapterStop,match='missing_reprofile_directions'):reprofile_check(p,lambda d:None,[],rank=1)


def test_detached_hidden_graph_or_unsupported_double_backward_stops():
    c,p,g=moving_adapter();c.q_fn=lambda x:x.detach()*0+torch.tensor([1.,2.],dtype=torch.float64)
    with pytest.raises(AdapterStop,match='callback_hidden_jvp'):p.j(np.ones(1))
    assert g.stopped
    c,p,g=moving_adapter();c.bt_fn=lambda x,w:(x.detach()*0+1.)
    with pytest.raises(AdapterStop,match='callback_C'):p.c(np.ones(1))
    assert g.stopped


def test_head_degeneracy_and_solve_residual_first_stop():
    c,_,g=moving_adapter()
    with pytest.raises(AdapterStop,match='head_factor'):AutogradChart(c.xi,c.q_fn,c.b_fn,c.bt_fn,c.point,np.zeros((1,1)),g)
    assert g.stopped
    c,p,g=moving_adapter();c.solve_head=lambda x:(_ for _ in ()).throw(ValueError('bad solve'))
    with pytest.raises(AdapterStop,match='head_solve'):p.solve(np.ones(1))


def test_guard_count_wall_memory_and_callback_latch():
    g=guard(hidden_jvp=1);g.charge('hidden_jvp')
    with pytest.raises(AdapterStop,match='work_limit'):g.charge('hidden_jvp')
    with pytest.raises(AdapterStop,match='already_stopped'):g.check()
    ticks=[0.];g=Guard({'x':2},1.,clock=lambda:ticks[0]);ticks[0]=1.
    with pytest.raises(AdapterStop,match='wall_deadline'):g.check()
    g=Guard({'x':2},1.,memory=lambda:11,max_bytes=10)
    with pytest.raises(AdapterStop,match='memory_limit'):g.check()
    g=Guard({'x':2},1.)
    with pytest.raises(AdapterStop,match='callback_x'):g.invoke('x',lambda:1/0)
    assert g.stopped


class MockEncode(torch.nn.Module):
    """Two-coordinate polynomial callable; NOT source.NeuralNet or training."""
    def __init__(self):
        super().__init__();self.coeff=torch.nn.Parameter(torch.tensor([.3,.7],dtype=torch.float64))
        self.output_layer=torch.nn.Linear(2,3,dtype=torch.float64)
        with torch.no_grad():
            self.output_layer.weight.copy_(torch.tensor([[.1,.2],[.3,-.1],[.4,.5]],dtype=torch.float64))
            self.output_layer.bias.copy_(torch.tensor([.2,.1,.3],dtype=torch.float64))
    def encode(self,x):return torch.stack((self.coeff[0]*x[:,0]**2+self.coeff[1],self.coeff[1]*x[:,0]+self.coeff[0]**2),dim=1)
    def forward(self,x):return self.output_layer(self.encode(x))


def mock_bridge():
    net=MockEncode();x=torch.tensor([[-.4,-.5],[-.2,-.1],[.1,.2],[.4,.5]],dtype=torch.float64)
    load=torch.tensor([.11999988],dtype=torch.float64);angle=torch.tensor([np.pi/2],dtype=torch.float64)
    field=SimpleNamespace(net=net,domain_extrema=torch.tensor([[-.5,.5],[-.5,.5]],dtype=torch.float64),lmbda=load,theta=angle)
    def fieldcalc(x):
        raw=net(x);b=(x[:,1]+.5)*(.5-x[:,1]);lift=x[:,1]+.5
        return ((b*raw[:,0]+lift*torch.cos(angle))*load,(b*raw[:,1]+lift*torch.sin(angle))*load,raw[:,2])
    field.fieldCalculation=fieldcalc
    p=SimpleNamespace(x=x,fu=torch.tensor([1,2,5,6]),df=torch.zeros(4,dtype=torch.float64),hist=torch.zeros(4,dtype=torch.float64),f=torch.ones(4,dtype=torch.float64))
    T=np.array([[1.],[.2],[.1]])
    with torch.no_grad():raw=load*((x[:,1]+.5)*(.5-x[:,1]))[:,None]*torch.cat((net.encode(x),torch.ones(4,1,dtype=torch.float64)),dim=1)
    phi=raw@torch.as_tensor(T);phi=phi.clone();phi[1,0]+=1e-9
    b=E011Bridge(field,p,dict(transform=T,phi=phi),guard());b.startup();return b


def test_existing_object_functional_bridge_keeps_Phi_and_frozen_source():
    b=mock_bridge();before={n:p.clone() for n,p in b.field.net.state_dict().items()}
    assert torch.equal(b.moving_phi(b.zero),b.phi)
    v=torch.ones_like(b.zero);j=torch.autograd.functional.jvp(b.q,b.zero,v,strict=True)[1]
    eps=1e-6;fd=(b.q(b.zero+eps*v)-b.q(b.zero-eps*v))/(2*eps)
    assert torch.linalg.vector_norm(j-fd)<1e-9 and torch.linalg.vector_norm(j)>0
    z=torch.tensor([.4,-.3],dtype=torch.float64);w=torch.tensor([.2,.4,.1,-.2],dtype=torch.float64)
    assert abs(float(b.b(b.zero,z)@w-z@b.bt(b.zero,w)))<1e-14
    hidden=b.zero.clone().requires_grad_(True);cb=b.bt(hidden,w);C=torch.autograd.grad(cb,hidden,torch.ones_like(cb))[0]
    assert float(torch.linalg.vector_norm(C))>0
    # Nonzero anchored head increment must not be silently called actual NN.
    theta=b.zero+.002*v;local=b.q_full(theta)
    inc=b.moving_phi(theta)@z.reshape(2,1).T;pred=local+torch.cat((inc[:,0],inc[:,1]))
    rawinc=(b.raw_design(theta)@b.T)@z.reshape(2,1).T;real=local+torch.cat((rawinc[:,0],rawinc[:,1]))
    assert float((pred-real).abs().max())>1e-10
    b.verify_frozen();assert all(torch.equal(p,before[n]) for n,p in b.field.net.state_dict().items())
    boundary=torch.tensor([0,3,4,7]);assert torch.equal(b.q_full(theta)[boundary],b.q_full(b.zero)[boundary])


def test_source_mutation_and_wrong_boundary_are_not_silent():
    b=mock_bridge()
    with torch.no_grad():b.field.net.coeff.add_(.1)
    with pytest.raises(AdapterStop,match='source_network_mutated'):b.verify_frozen()
    b=mock_bridge();b.raw0=None;b.field.fieldCalculation=lambda x:(torch.ones(4,dtype=torch.float64),torch.ones(4,dtype=torch.float64),torch.zeros(4,dtype=torch.float64))
    with pytest.raises(AdapterStop,match='UV_formula_mismatch'):b.startup()


def test_local_algebra_probe_cannot_replace_actual_profile_hook():
    c,p,g=moving_adapter();rows,directions=probe_algebra(p,np.array([[2+.4**2]]),g)
    assert len(rows)==12 and len(directions)==2
    with pytest.raises(AdapterStop,match='missing_real'):reprofile_check(p,None,directions,rank=1)


def test_frozen_physics_and_invalid_memory_contracts_stop():
    b=mock_bridge();b.problem.df[0]=.1
    with pytest.raises(AdapterStop,match='frozen_physics'):b.verify_frozen()
    with pytest.raises(AdapterStop,match='invalid_memory_bound'):Guard({'x':1},1.,memory=lambda:1,max_bytes=np.nan)


def test_head_H_is_independently_checked_against_native_free_tangent():
    c,p,g=moving_adapter()
    with pytest.raises(AdapterStop,match='head_tangent_mismatch'):probe_algebra(p,np.array([[999.]]),g)
