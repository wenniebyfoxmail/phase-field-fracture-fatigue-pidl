import importlib.util
from pathlib import Path
import unittest
import torch
p=Path(__file__).resolve().parents[1]/'source/primal_dual_safeguards.py'
s=importlib.util.spec_from_file_location('safeguards',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Base:
    PFF_model='AT1'
class Safeguards(unittest.TestCase):
    def test_extension_values_and_right_derivative(self):
        d=torch.tensor([-2.,0.,.2,1.,2.],requires_grad=True)
        w,_,_=m.PositiveAT1Extension(Base()).damageFun(d)
        self.assertTrue(torch.equal(w,torch.tensor([0.,0.,.2,1.,2.])))
        self.assertTrue(torch.equal(torch.autograd.grad(w.sum(),d)[0],torch.tensor([0.,1.,1.,1.,1.])))
    def test_equal_bound_elimination_only(self):
        x=torch.tensor([.1,.4],requires_grad=True);h=torch.tensor([1.,.99999])
        y=m.eliminate_fully_broken(x,h)
        self.assertTrue(torch.equal(y,torch.tensor([1.,.4])))
        self.assertTrue(torch.equal(torch.autograd.grad(y.sum(),x)[0],torch.tensor([0.,1.])))
    def test_backtrack_and_state_scaling(self):
        p=torch.tensor([1.],requires_grad=True);o=torch.optim.Rprop([p],lr=2.,step_sizes=(1e-10,50))
        (p.square().sum()).backward()
        def f():
            if float(p)<=0:raise FloatingPointError('outside domain')
            return p.square().sum()
        r=m.safeguarded_rprop([p],o,f,1.,lambda:None)
        self.assertEqual(r['backtracks'],2);self.assertAlmostEqual(float(p),.5)
        self.assertAlmostEqual(float(o.state[p]['step_size']),.5)
    def test_exhaustion_restores_optimizer_and_parameters(self):
        p=torch.tensor([1.],requires_grad=True);o=torch.optim.Rprop([p],lr=.1)
        p.square().sum().backward()
        with self.assertRaises(m.SearchFailure) as ctx:
            m.safeguarded_rprop([p],o,lambda:2.,1.,lambda:None,max_backtracks=2)
        self.assertEqual(float(p),1.);self.assertEqual(len(o.state),0)
        self.assertEqual(ctx.exception.context['evaluations'],3)
    def test_deadline_restores_proposal(self):
        p=torch.tensor([1.],requires_grad=True);o=torch.optim.Rprop([p],lr=.1);p.square().sum().backward()
        def timeout():raise TimeoutError()
        with self.assertRaises(TimeoutError):m.safeguarded_rprop([p],o,lambda:0.,1.,timeout)
        self.assertEqual(float(p),1.);self.assertEqual(len(o.state),0)
if __name__=='__main__':unittest.main()
