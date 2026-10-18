import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import s04_e027 as old
import s04_e030 as m


class FixedUVTests(unittest.TestCase):
    def fixture(self):
        xy=torch.tensor([[-.2,-.25],[.2,-.25],[.2,.25],[-.2,.25]],dtype=torch.float64)
        model=torch.nn.Linear(2,3,dtype=torch.float64)
        with torch.no_grad():
            model.weight.copy_(torch.tensor([[.2,.3],[-.1,.4],[.1,-.3]],dtype=torch.float64));model.bias.copy_(torch.tensor([.1,.2,.3],dtype=torch.float64))
        legacy=old.fields(model,xy);p=SimpleNamespace(xy=xy)
        raw=model(xy)[:,2];lower=torch.zeros(4,dtype=torch.float64);fixed=torch.zeros(4,dtype=torch.bool)
        mapper=m.BoundedIncrement(xy,lower,fixed,raw,torch.full_like(raw,.1))
        uv=m.FixedDisplacement(xy,legacy[:,:2]);return model,p,mapper,uv

    def test_shared_parameter_change_preserves_physical_uv_and_strain(self):
        model,p,mapper,uv=self.fixture();q0=m.fields(model,p,mapper,uv).detach()
        conn=torch.tensor([[0,1,2,3]],dtype=torch.long);N,B,w=old.q4_shape_data(p.xy,conn)
        g0=old.q4_gradient(q0[:,1],conn,B)
        with torch.no_grad():model.weight.add_(.25);model.bias.add_(.1)
        q=m.fields(model,p,mapper,uv);m.assert_fixed_uv(q,uv)
        self.assertTrue(torch.equal(q[:,:2],q0[:,:2]))
        self.assertTrue(torch.equal(old.q4_gradient(q[:,1],conn,B),g0))
        self.assertFalse(torch.equal(q[:,2],q0[:,2]))

    def test_damage_gradient_exists_uv_gradient_is_zero(self):
        model,p,mapper,uv=self.fixture();q=m.fields(model,p,mapper,uv)
        target=q.detach().clone();target[:,2]+=.1;target[:,:2]+=.1
        loss=(q-target).square().sum();loss.backward()
        self.assertTrue(torch.equal(model.weight.grad[:2],torch.zeros_like(model.weight.grad[:2])))
        self.assertGreater(float(model.weight.grad[2].norm()),0)
        self.assertFalse(uv.physical_uv.requires_grad)

    def test_frozen_buffer_identity_and_checkpoint(self):
        model,p,mapper,uv=self.fixture();self.assertEqual(list(uv.parameters()),[])
        original=uv.physical_uv.clone();q=uv(p.xy)
        self.assertTrue(torch.equal(q,original))
        state=uv.state_dict();uv.load_state_dict(state)
        bad=dict(state);bad['_extra_state']={'origin':'FEM'}
        with self.assertRaises(ValueError):uv.load_state_dict(bad)

    def test_node_order_and_nonfinite_rejection(self):
        model,p,mapper,uv=self.fixture()
        with self.assertRaises(ValueError):uv(p.xy.flip(0))
        bad=uv.physical_uv.clone();bad[0,0]=float('nan')
        with self.assertRaises(ValueError):m.FixedDisplacement(p.xy,bad)


if __name__=='__main__':unittest.main()
