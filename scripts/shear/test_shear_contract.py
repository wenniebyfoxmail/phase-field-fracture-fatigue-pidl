"""Lightweight mechanics checks; no optimizer steps or training."""
import sys
import unittest
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/shear'),str(ROOT/'SENS_tensile'),str(ROOT/'source')]
from run_shear_pidl import split_quads
from field_computation import FieldComputation
from material_properties import MaterialProperties
from pff_model import PFFModel
from compute_energy import compute_energy


class ArbitraryRaw(torch.nn.Module):
    def forward(self,x):
        return torch.stack([3*x[:,0]+1,2*x[:,0]-7,torch.zeros_like(x[:,0])],dim=1)


class ShearContract(unittest.TestCase):
    def test_clamped_shear_edges_for_arbitrary_network(self):
        x=torch.tensor([[-.5,-.5],[.1,-.5],[.5,-.5],[-.5,.5],[.1,.5],[.5,.5]])
        f=FieldComputation(ArbitraryRaw(),torch.tensor([[-.5,.5],[-.5,.5]]),torch.tensor([.31]),torch.tensor([0.]))
        u,v,_=f.fieldCalculation(x)
        torch.testing.assert_close(u[:3],torch.zeros(3))
        torch.testing.assert_close(u[3:],torch.ones(3)*.31)
        torch.testing.assert_close(v,torch.zeros(6))

    def test_affine_shear_energy_and_direct_reaction(self):
        # Reversed node orientation must preserve positive integration area.
        xy=np.array([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]])
        for q in [np.array([[0,1,2,3]]),np.array([[3,2,1,0]])]:
            t,a=split_quads(xy,q)
            self.assertAlmostEqual(float(a.sum()),1.)
            x=torch.tensor(xy,dtype=torch.float64)
            conn=torch.tensor(t)
            area=torch.tensor(a)
            U=.1
            u=(U*(x[:,1]+.5)).requires_grad_(True)
            v=torch.zeros(4,dtype=torch.float64,requires_grad=True)
            alpha=torch.zeros(4,dtype=torch.float64)
            mat=MaterialProperties(1.,.3,1.,.01)
            pff=PFFModel('AT1','volumetric',torch.tensor(.005),residual_stiffness=torch.tensor(0.))
            eel,ed,eh=compute_energy(x,u,v,alpha,alpha,mat,pff,area,conn)
            self.assertAlmostEqual(float(eel),.5*mat.mat_mu*U**2,places=10)
            fu,_=torch.autograd.grad(eel,(u,v))
            self.assertAlmostEqual(float(fu[x[:,1]==.5].sum()),mat.mat_mu*U,places=10)
            self.assertAlmostEqual(float(fu[x[:,1]==-.5].sum()),-mat.mat_mu*U,places=10)
            self.assertEqual(float(ed+eh),0.)


if __name__=='__main__':
    unittest.main()
