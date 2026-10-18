import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import s04_e032 as m

class JointHeadTests(unittest.TestCase):
 def test_saved_span_is_complete_and_fixed(self):
  gradients=np.zeros((7,802));gradients[:,:7]=np.eye(7)
  basis,info=m.frozen_basis(gradients)
  self.assertEqual(info['dimension'],7)
  self.assertTrue(np.allclose(np.einsum('ij,kj->ik',basis,basis),np.eye(7)))
  self.assertTrue(np.allclose(np.einsum('ij,jk->ik',np.einsum('ik,jk->ij',gradients,basis),basis),gradients))
  with self.assertRaises(ValueError):m.frozen_basis(np.zeros((7,802)))
 def test_exact_uv_plane_quadratic_and_jacobian(self):
  rng=np.random.default_rng(1);error=rng.normal(size=(5,2));vel=rng.normal(size=(3,5,2))
  weights={'UV_global':np.arange(1,6.),'UV_Z':np.array([1.,1.,0.,0.,0.])}
  terms=m.uv_quadratics(error,vel,weights);z=np.array([.1,-.2,.3])
  for name,w in weights.items():
   changed=error+np.einsum('i,ina->na',z,vel)
   expected=np.einsum('n,na,na->',w,changed,changed)/np.einsum('n,na,na->',w,error,error)
   self.assertAlmostEqual(m.quadratic_value(z,terms[name]),expected,places=13)
   grad=2*terms[name]['b']+2*np.einsum('ij,j->i',terms[name]['q'],z)
   for i in range(3):
    d=np.eye(3)[i]*1e-6;fd=(m.quadratic_value(z+d,terms[name])-m.quadratic_value(z-d,terms[name]))/2e-6
    self.assertAlmostEqual(fd,grad[i],delta=1e-9)
 def test_joint_coefficients_improve_proxy_with_cone_and_radius(self):
  g=np.ones((7,1));baseline={n:1. for n in m.METRICS}
  terms={n:dict(b=np.array([.1]),q=np.array([[.01]])) for n in ['UV_global','UV_Z']}
  z,info=m.joint_coefficients(g,baseline,terms,np.array([-.1]),1.)
  self.assertTrue(info['success']);self.assertLess(info['epigraph'],info['seed_epigraph'])
  self.assertAlmostEqual(z[0],-1.,places=8);self.assertGreaterEqual(info['minimum_constraint'],-1e-10)
  self.assertLessEqual(info['iterations'],100)
  self.assertLessEqual(len(info['coefficient_iterations']),100)
 def test_proxy_rejects_bad_schema_and_infeasible_seed(self):
  g=np.ones((7,1));baseline={n:1. for n in m.METRICS}
  terms={n:dict(b=np.array([.1]),q=np.array([[.01]])) for n in ['UV_global','UV_Z']}
  with self.assertRaises(ValueError):m.joint_coefficients(g,baseline,terms,np.array([.1]),1.)
  g[0]=0
  with self.assertRaises(ValueError):m.joint_coefficients(g,baseline,terms,np.array([-.1]),1.)

if __name__=='__main__':unittest.main()
