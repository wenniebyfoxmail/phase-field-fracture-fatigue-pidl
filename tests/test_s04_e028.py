"""Finite fixture checks only; no optimizer step, model checkpoint or GPU."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
import s04_e027 as old
import s04_e028 as m
from test_s04_e027 import fixture


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): torch.set_num_threads(1)

    def test_forward_bounds_and_fixed_gradient(self):
        raw=torch.tensor([-.2,.4,1.2,.3,1.],dtype=torch.float64,requires_grad=True)
        lower=torch.tensor([0.,.2,.8,1.,1.],dtype=torch.float64)
        fixed=torch.tensor([False,False,False,True,False])
        d=m.project_damage(raw,lower,fixed)
        torch.testing.assert_close(d,torch.tensor([0.,.4,1.,1.,1.],dtype=torch.float64))
        g=torch.autograd.grad(d.sum(),raw)[0]
        torch.testing.assert_close(g,torch.tensor([0.,1.,0.,0.,0.],dtype=torch.float64))

    def test_nonfinite_cannot_be_hidden_by_clamp(self):
        with self.assertRaises(ValueError):
            m.project_damage(torch.tensor([float('inf')]),torch.zeros(1),torch.zeros(1,dtype=torch.bool))

    def test_q4_bounds_are_preserved(self):
        a=fixture();p=old.Problem(a)
        d=m.project_damage(p.ref[:,2]*3-.6,p.previous,torch.zeros(16,dtype=torch.bool))
        gp=old.q4_interpolate(d,p.conn,p.N)
        self.assertGreaterEqual(float((gp-p.old_gp).min()),-1e-14)
        self.assertLessEqual(float(gp.max()),1.)

    def test_active_zero_and_nodal_derivative(self):
        p=old.Problem(fixture());q=p.ref.clone().requires_grad_(True)
        self.assertEqual(float(m.active_loss(p,q).detach()),0.)
        q=(p.ref+.002*torch.arange(16)[:,None]).requires_grad_(True)
        loss=m.active_loss(p,q);grad=torch.autograd.grad(loss,q)[0]
        for i,j in [(5,0),(10,1),(6,2)]:
            hi,lo=q.detach().clone(),q.detach().clone();eps=1e-7
            hi[i,j]+=eps;lo[i,j]-=eps
            fd=float((m.active_loss(p,hi)-m.active_loss(p,lo))/(2*eps))
            self.assertAlmostEqual(float(grad[i,j]),fd,delta=1e-5*max(1,abs(fd)))

    def test_norm_cap_and_zero_cases(self):
        for b,a in [(1.,4000.),(1.,.01),(0.,1.),(1.,0.)]:
            w=m.capped_weight(torch.tensor(b),torch.tensor(a))
            self.assertLessEqual(float(w*a),.25*b+1e-8)
            self.assertTrue(0<=float(w)<=1)
            self.assertFalse(w.requires_grad)

    def test_reference_lower_is_not_silently_target(self):
        p=old.Problem(fixture())
        with self.assertRaises(ValueError):m.validate_current_lower(p)

    def test_complete_objective_no_update_and_parameter_cap(self):
        torch.manual_seed(1)
        p=old.Problem(fixture())
        model=torch.nn.Sequential(torch.nn.Linear(2,6),torch.nn.Tanh(),torch.nn.Linear(6,3)).double()
        before=[x.detach().clone() for x in model.parameters()]
        rng=torch.Generator().manual_seed(1);ids=p.sample(rng);rng_before=rng.get_state().clone()
        q=old.fields(model,p.xy)
        lu,ld=p.supervised_components(q,ids)
        b,logb=m.objective(p,model,q,ids,False)
        r,logr=m.objective(p,model,q,ids,True)
        torch.testing.assert_close(b,lu+ld)
        torch.testing.assert_close(r,b+logr['active_weight']*m.active_loss(p,q))
        self.assertEqual(logb['active_weight'],0.)
        gs=m.vector_gradient(lu+ld,tuple(model.parameters()))
        ga=m.vector_gradient(m.active_loss(p,q),tuple(model.parameters()))
        gb=m.vector_gradient(b,tuple(model.parameters()))
        gr=m.vector_gradient(r,tuple(model.parameters()))
        for s,a,base,repair in zip(gs,ga,gb,gr):
            torch.testing.assert_close(base,s)
            torch.testing.assert_close(repair,s+logr['active_weight']*a)
        self.assertLessEqual(logr['weighted_active_grad'],.25*logr['grad_supervision']+1e-12)
        self.assertTrue(torch.equal(rng_before,rng.get_state()))
        for x,y in zip(before,model.parameters()):torch.testing.assert_close(x,y,rtol=0,atol=0)

    def test_mac_execute_refused_before_io(self):
        sys.path.insert(0,str(ROOT/'SENS_tensile'))
        from run_s04_e028 import admit
        with patch('run_s04_e028.platform.system',return_value='Darwin'):
            with self.assertRaises(PermissionError):admit({}, {}, Path('/nonexistent/E028'))

    def test_actual_gpu_identity_rejection_without_gpu(self):
        sys.path.insert(0,str(ROOT/'SENS_tensile'))
        from run_s04_e028 import device_admission
        grant={'cuda_visible_devices':'5','gpu_uuid':'GPU-expected'}
        with patch.dict('os.environ',{'CUDA_VISIBLE_DEVICES':'5'}),patch('run_s04_e028.torch.cuda.is_available',return_value=True),patch('run_s04_e028.torch.cuda.device_count',return_value=2),patch('run_s04_e028.subprocess.check_output') as query:
            with self.assertRaises(PermissionError):device_admission(grant)
            query.assert_not_called()
        with patch.dict('os.environ',{'CUDA_VISIBLE_DEVICES':'5'}),patch('run_s04_e028.torch.cuda.is_available',return_value=True),patch('run_s04_e028.torch.cuda.device_count',return_value=1),patch('run_s04_e028.subprocess.check_output',return_value='GPU-other\n'):
            with self.assertRaises(PermissionError):device_admission(grant)
        with patch.dict('os.environ',{'CUDA_VISIBLE_DEVICES':'5'}),patch('run_s04_e028.torch.cuda.is_available',return_value=True),patch('run_s04_e028.torch.cuda.device_count',return_value=1),patch('run_s04_e028.subprocess.check_output',return_value='GPU-expected\n'):
            self.assertEqual(device_admission(grant),'GPU-expected')


if __name__=='__main__': unittest.main()
