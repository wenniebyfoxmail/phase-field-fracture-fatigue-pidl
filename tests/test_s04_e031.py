import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import s04_e031 as m
import s04_e027 as old


class HeadTests(unittest.TestCase):
    def test_seven_gradient_certificate_and_conflict(self):
        g=np.column_stack((np.ones(7),np.arange(7)-3))
        direction,q,info=m.common_descent(g)
        self.assertTrue(info['resolved_strict']);self.assertTrue(np.all(g@direction<0))
        direction,q,info=m.common_descent(np.vstack((np.eye(3),-np.eye(3),[1,1,1])))
        self.assertFalse(info['resolved_strict']);self.assertTrue(np.array_equal(direction,np.zeros(3)))

    def test_original_head_forward_and_frozen_damage(self):
        torch.manual_seed(1);model=old.NeuralNet(2,3,2,4,'TrainableReLU',1.).double()
        xy=torch.tensor([[-.2,-.25],[.2,-.25],[.2,.25],[-.2,.25]],dtype=torch.float64);p=SimpleNamespace(xy=xy)
        h=model.encode(xy).detach();theta=m.head_state(model).requires_grad_(True);d=torch.tensor([0.,.2,.5,1.],dtype=torch.float64)
        q=m.fields(theta,h,p,d);self.assertTrue(torch.allclose(q[:,:2],old.fields(model,xy)[:,:2],atol=1e-14,rtol=1e-14))
        gd=torch.autograd.grad(q[:,2].sum(),theta,retain_graph=True)[0]
        self.assertTrue(torch.equal(gd,torch.zeros_like(gd)))
        gu=torch.autograd.grad(q[:,:2].square().sum(),theta)[0];self.assertGreater(float(gu.norm()),0)
        changed=m.fields(theta.detach()+.001,h,p,d)
        self.assertTrue(torch.equal(changed[:,2],d));self.assertFalse(torch.equal(changed[:,:2],q[:,:2]))

    def test_exact_uv_curvature_and_finite_guard(self):
        e=np.array([[1.,2.],[2.,1.]])
        velocity=-3*e;fraction,terms=m.uv_safe_fraction(e,velocity,{'full':np.ones(2),'Z':np.array([1.,0.])})
        self.assertAlmostEqual(fraction,1/3)
        self.assertLess(np.sum((e+fraction*velocity)**2),np.sum(e**2))
        base={k:1. for k in m.METRICS};candidate={k:.9 for k in m.METRICS}
        self.assertTrue(m.admit_candidate(candidate,base,.01)[0])
        candidate['force_squared']=1.0001;self.assertFalse(m.admit_candidate(candidate,base,.01)[0])
        self.assertFalse(m.admit_candidate(base,base,.0201)[0])

    def test_native_q4_seven_head_metric_gradients_match_fd(self):
        xy=np.array([[-.2,-.02],[.2,-.02],[.2,.02],[-.2,.02]])
        ref=np.column_stack((.001*xy[:,0],old.US*(xy[:,1]+.5),np.full(4,.3)))
        p=old.Problem(dict(xy=xy,conn=np.array([[0,1,2,3]]),ref=ref,previous=np.full(4,.1),f=np.ones((1,4)),free_u=np.arange(8),free_d=np.arange(4)))
        features=p.xy.clone();damage=torch.full((4,),.2,dtype=torch.float64)
        theta=torch.tensor([[.1,.02,.03],[.02,.1,-.03]],dtype=torch.float64,requires_grad=True)
        reference=p.parts(*p.ref.unbind(1));q=m.fields(theta,features,p,damage)
        norm=float(p.force(q).detach().norm());values=m.metric_values(p,q,reference,norm,True)
        direction=torch.tensor([[.2,-.3,.1],[-.1,.4,.3]],dtype=torch.float64)
        eps=1e-6
        for name in m.METRICS:
            derivative=float((torch.autograd.grad(values[name],theta,retain_graph=True)[0]*direction).sum())
            plus=(theta.detach()+eps*direction).requires_grad_(True);minus=(theta.detach()-eps*direction).requires_grad_(True)
            vp=m.metric_values(p,m.fields(plus,features,p,damage),reference,norm,False)[name]
            vm=m.metric_values(p,m.fields(minus,features,p,damage),reference,norm,False)[name]
            finite_difference=float((vp-vm).detach())/(2*eps)
            self.assertAlmostEqual(derivative,finite_difference,delta=1e-6*max(1,abs(derivative)))


if __name__=='__main__':unittest.main()
