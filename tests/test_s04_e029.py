"""Pure deterministic gradient-flow fixtures; no optimizer or training loop."""
import copy
from pathlib import Path
import sys
import unittest
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import s04_e028 as old
import s04_e029 as m


def fixture():
    xy=torch.tensor([[0.,0.],[.1,0.],[.2,0.],[.3,0.]],dtype=torch.float64)
    lo=torch.tensor([1.,.2,0.,.9],dtype=torch.float64)
    fixed=torch.tensor([True,False,False,False])
    origin=torch.tensor([3.,-5.,-5.,2.],dtype=torch.float64)
    seed=torch.tensor([1.,.2,0.,1.],dtype=torch.float64)
    return xy,lo,fixed,origin,seed,m.BoundedIncrement(xy,lo,fixed,origin,seed)


class Tests(unittest.TestCase):
    def test_seed_change_bounded_and_physical(self):
        xy,lo,fixed,origin,seed,mapper=fixture()
        q=mapper(xy,origin)
        self.assertLessEqual(float((q-seed).abs().max()),m.EPS+1e-15)
        self.assertTrue(bool(((q>=lo)&(q<=1)).all()));self.assertEqual(float(q[0]),1.)

    def test_true_derivative_matches_autograd_and_difference(self):
        xy,lo,fixed,origin,seed,mapper=fixture()
        for delta in [0.,-5.,-50.,5.,50.]:
            r=(origin+delta).requires_grad_(True)
            q=mapper(xy,r);g=torch.autograd.grad(q.sum(),r)[0]
            self.assertEqual(float(g[0]),0.)
            self.assertTrue(bool((g[1:]>0).all()))
            p=torch.sigmoid(mapper.seed_logit+torch.asinh(r.detach()-origin))
            expected=(1-lo)*p*(1-p)/torch.hypot(torch.ones_like(origin),r.detach()-origin)
            torch.testing.assert_close(g,expected,atol=1e-16,rtol=1e-10)
            eps=1e-4
            fd=(mapper(xy,r.detach()+eps)-mapper(xy,r.detach()-eps))/(2*eps)
            torch.testing.assert_close(g,fd,atol=2e-12,rtol=1e-4)

    def test_positive_increment_has_descent_signal(self):
        xy,lo,fixed,origin,seed,mapper=fixture()
        r=origin.clone().requires_grad_(True)
        desired=torch.tensor([1.,.4,.3,.99],dtype=torch.float64)
        q=mapper(xy,r);loss=(q[1:3]-desired[1:3]).square().sum()
        g=torch.autograd.grad(loss,r)[0]
        self.assertTrue(bool((g[1:3]<0).all()))
        moved=mapper(xy,origin+1e-3)
        self.assertLess(float((moved[1:3]-desired[1:3]).square().sum()),float(loss.detach()))

    def test_removes_observed_flat_lower_region(self):
        xy,lo,fixed,origin,seed,mapper=fixture()
        raw=origin.clone().requires_grad_(True)
        candidate=torch.where(raw< -2,.001*(raw+2),raw/4+.5)
        legacy=old.project_damage(candidate,lo,fixed)
        g_old=torch.autograd.grad(legacy.sum(),raw)[0]
        g_new=torch.autograd.grad(mapper(xy,raw).sum(),raw)[0]
        self.assertEqual(float(g_old[1]),0.);self.assertGreater(float(g_new[1]),0.)

    def test_no_parameters_or_source_alias_and_state_identity(self):
        xy,lo,fixed,origin,seed,mapper=fixture()
        self.assertEqual(len(list(mapper.parameters())),0)
        state=copy.deepcopy(mapper.state_dict());other=fixture()[-1];other.load_state_dict(state)
        torch.testing.assert_close(mapper(xy,origin),other(xy,origin),rtol=0,atol=0)
        oldbuf=mapper.raw_origin.clone();origin.add_(2)
        self.assertTrue(torch.equal(mapper.raw_origin,oldbuf))
        state['_extra_state']['relative_transform']='straight_through'
        with self.assertRaises(ValueError):other.load_state_dict(state)

    def test_wrong_nodes_and_nonfinite_rejected(self):
        xy,lo,fixed,origin,seed,mapper=fixture()
        with self.assertRaises(ValueError):mapper(xy.flip(0),origin)
        bad=origin.clone();bad[1]=float('inf')
        with self.assertRaises(ValueError):mapper(xy,bad)

    def test_real_fixture_parameter_gradient_and_uv_parity(self):
        from types import SimpleNamespace
        import s04_e027 as legacy
        xy,lo,fixed,_,_,_=fixture()
        torch.manual_seed(1);model=torch.nn.Linear(2,3).double()
        with torch.no_grad():
            raw_origin=model(xy)[:,2];oldq=legacy.fields(model,xy)
            seed=old.project_damage(oldq[:,2],lo,fixed)
        mapper=m.BoundedIncrement(xy,lo,fixed,raw_origin,seed)
        q=m.fields(model,SimpleNamespace(xy=xy),mapper)
        torch.testing.assert_close(q[:,:2],legacy.fields(model,xy)[:,:2],rtol=0,atol=0)
        g=torch.autograd.grad(q[:,2].sum(),model.bias)[0]
        self.assertGreater(float(g[2]),0.)
        self.assertEqual(float(g[0]),0.);self.assertEqual(float(g[1]),0.)

    def test_numerically_all_zero_flow_refused(self):
        xy,lo,fixed,origin,seed,mapper=fixture()
        with self.assertRaises(ValueError):mapper(xy,torch.full_like(origin,1e100))


if __name__=='__main__':unittest.main()
