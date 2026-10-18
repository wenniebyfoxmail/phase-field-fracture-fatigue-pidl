import sys,unittest
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import s04_e027 as old
import s04_e033 as m

class FullHeadTests(unittest.TestCase):
 def test_eleven_row_certificate_zero_and_guard(self):
  gradients=np.column_stack((np.eye(11),np.ones(11)*.2));calls=[]
  direction,q,info=m.common_descent(gradients,lambda:calls.append(1))
  a=gradients/np.linalg.norm(gradients,axis=1)[:,None]
  self.assertTrue(info['resolved_strict']);self.assertEqual(len(calls),2**11-1)
  self.assertLess(np.einsum('ij,j->i',a,direction).max(),0)
  gradients[3]=0
  d,q,info=m.common_descent(gradients)
  self.assertFalse(info['resolved_strict']);self.assertTrue(np.array_equal(d,np.zeros(12)))
 def test_single_axis_enrichment_exact_and_no_forcing(self):
  basis=np.zeros((7,2,401));basis.reshape(7,-1)[:,:7]=np.eye(7)
  direction=np.zeros(802);direction[0]=.6;direction[7]=.8
  new,coords,info=m.enrich_one_axis(basis,direction.reshape(2,401))
  self.assertTrue(info['eligible']);self.assertTrue(np.array_equal(new[:7],basis))
  self.assertTrue(np.allclose(np.einsum('i,ijk->jk',coords,new),direction.reshape(2,401),atol=1e-14))
  new,coords,info=m.enrich_one_axis(basis,basis[0]);self.assertFalse(info['eligible']);self.assertIsNone(new)
 def test_all_six_component_quadratics_and_seed(self):
  rng=np.random.default_rng(2);error=rng.normal(size=(5,2));vel=rng.normal(size=(3,5,2));vel[0]=-3*error
  weights={'UV_global':np.arange(1,6.),'UV_Z':np.array([1.,1.,0.,0.,0.])}
  terms=m.component_quadratics(error,vel,weights);z=np.array([.1,-.2,.3])
  changed=error+np.einsum('i,ina->na',z,vel)
  for name in m.UV_TERMS:
   channel,region=name.split('_');w=weights['UV_'+region]
   selected=[0,1] if channel=='UV' else [0] if channel=='u' else [1]
   before=np.sum(w[:,None]*error[:,selected]**2);after=np.sum(w[:,None]*changed[:,selected]**2)
   self.assertAlmostEqual(m.previous.quadratic_value(z,terms[name]),after/before,places=12)
  fraction,details=m.curvature_seed(terms,np.array([1.,0.,0.]))
  self.assertAlmostEqual(fraction,1/3);self.assertEqual(set(details),set(m.UV_TERMS))
 def test_eleven_native_metric_gradients_match_fd(self):
  xy=np.array([[-.2,-.02],[.2,-.02],[.2,.02],[-.2,.02]])
  ref=np.column_stack((.001*xy[:,0],old.US*(xy[:,1]+.5),np.full(4,.3)))
  p=old.Problem(dict(xy=xy,conn=np.array([[0,1,2,3]]),ref=ref,previous=np.full(4,.1),f=np.ones((1,4)),free_u=np.arange(8),free_d=np.arange(4)))
  theta=torch.tensor([[.1,.02,.03],[.02,.1,-.03]],dtype=torch.float64,requires_grad=True)
  features=p.xy.clone();damage=torch.full((4,),.2,dtype=torch.float64)
  reference=p.parts(*p.ref.unbind(1));q=m.fields(theta,features,p,damage)
  norm=float(p.force(q).detach().norm());values=m.metric_values(p,q,reference,norm,True)
  self.assertEqual(tuple(values),m.METRICS)
  for region in ['global','Z']:
   self.assertAlmostEqual(float(values['UV_'+region].detach()),float((values['u_'+region]+values['v_'+region]).detach()),places=14)
  direction=torch.tensor([[.2,-.3,.1],[-.1,.4,.3]],dtype=torch.float64);eps=1e-6
  for name in m.METRICS:
   actual=float((torch.autograd.grad(values[name],theta,retain_graph=True)[0]*direction).sum())
   vp=m.metric_values(p,m.fields((theta.detach()+eps*direction).requires_grad_(True),features,p,damage),reference,norm,False)[name]
   vm=m.metric_values(p,m.fields((theta.detach()-eps*direction).requires_grad_(True),features,p,damage),reference,norm,False)[name]
   self.assertAlmostEqual(actual,float((vp-vm).detach())/(2*eps),delta=1e-6*max(1,abs(actual)))
 def test_joint_proxy_and_reject_individual_u_regression(self):
  terms={n:dict(b=np.array([.1]),q=np.array([[.01]])) for n in m.UV_TERMS}
  baseline={n:1. for n in m.METRICS}
  z,info=m.joint_coefficients(np.ones((11,1)),baseline,terms,np.array([-.1]),1.)
  self.assertTrue(info['success']);self.assertAlmostEqual(z[0],-1.,places=8)
  candidate={n:.9 for n in m.METRICS};self.assertTrue(m.admit_candidate(candidate,baseline,.001)[0])
  candidate['u_global']=1.0001
  ok,reasons=m.admit_candidate(candidate,baseline,.001);self.assertFalse(ok);self.assertIn('u_global',reasons)

if __name__=='__main__':unittest.main()
