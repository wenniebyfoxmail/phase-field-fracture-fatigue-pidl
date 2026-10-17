"""Meaningful nonidentity-D function/gradient and no-mutation checks on a tiny model."""
import sys
from pathlib import Path
import unittest
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from diagnose_s04_e023_endpoints import measure_dual
from diagnose_s04_e021_endpoints import measure
from s04_e018_global_local import compact_window
from s04_e019_frozen_residual import state_digest
class Act(torch.nn.Module):
 def __init__(self):super().__init__();self.coeff=torch.nn.Parameter(torch.tensor(-.7))
 def forward(self,x):return torch.nn.functional.leaky_relu(self.coeff*x,.01)
class Residual(torch.nn.Module):
 def __init__(self):
  super().__init__();self.input_layer=torch.nn.Linear(2,3);self.hidden_layers=torch.nn.ModuleList([torch.nn.Linear(3,3)]);self.activations=torch.nn.ModuleList([Act(),Act()]);self.output_layer=torch.nn.Linear(3,2)
class Tiny(torch.nn.Module):
 def __init__(self,scale):
  super().__init__();self.residual=Residual()
  for n,v in dict(lower=[-.1,-.1],upper=[.1,.1],local_center=[0.,0.],local_scale=[.2,.2]).items():self.register_buffer(n,torch.tensor(v))
  self.register_buffer('head_scale',torch.tensor(scale))
 def correction_physical(self,xy):
  z=(xy-self.local_center)/self.local_scale
  for layer,act in zip([self.residual.input_layer,*self.residual.hidden_layers],self.residual.activations):z=act(layer(z))
  raw=torch.nn.functional.linear(z*self.head_scale[:-1],self.residual.output_layer.weight,self.residual.output_layer.bias*self.head_scale[-1])
  return ((xy[:,1]+.5)*(.5-xy[:,1]))[:,None]*compact_window(xy,self.lower,self.upper)*raw
class Tests(unittest.TestCase):
 def setUp(self):torch.set_default_dtype(torch.float64);torch.set_num_threads(2);torch.manual_seed(7)
 def data(self,m):
  xy=np.array([[0.,0.],[.05,.04],[-.05,-.04],[.09,.08],[.3,.3],[-.3,-.3]])
  base=np.zeros((6,2));target=np.array([[.003,-.004],[-.002,.003],[.001,.002],[.002,-.002],[.001,.001],[-.002,.001]])
  saved=m.correction_physical(torch.tensor(xy)).detach().numpy()
  return dict(xy=xy,mass=np.array([1.,2.,1.,3.,1.,2.]),damage=np.array([.5,.3,0.,0.,0.,0.]),equilibrated_uv=target),base,saved
 def test_nonidentity_scale_matches_equivalent_physical_model(self):
  scaled=Tiny([.2,3.,11.,7.]);physical=Tiny([1.,1.,1.,1.]);physical.load_state_dict(scaled.state_dict())
  with torch.no_grad():physical.residual.output_layer.weight.mul_(scaled.head_scale[:-1]);physical.residual.output_layer.bias.mul_(scaled.head_scale[-1]);physical.head_scale.fill_(1.)
  data,base,saved=self.data(scaled);before=state_digest(scaled)
  a=measure_dual(scaled,data,base,saved,2);b=measure_dual(physical,data,base,saved,3)
  for x,y in zip([r for r in a['head'] if r['coordinate']=='physical'],[r for r in b['head'] if r['coordinate']=='physical']):
   for k in ('loss_contribution','gradient_norm','scaled_normal_residual'):
    if x[k] is None:self.assertIsNone(y[k])
    else:np.testing.assert_allclose(x[k],y[k],rtol=1e-10,atol=1e-12)
  self.assertEqual(state_digest(scaled),before);self.assertTrue(all(p.grad is None for p in scaled.parameters()));self.assertEqual(a['parameter_updates'],0)
  self.assertTrue(any(abs(x['gradient_norm']-y['gradient_norm'])>1e-8 for x,y in zip([r for r in a['head'] if r['coordinate']=='physical'],[r for r in a['head'] if r['coordinate']=='actual'])))
 def test_identity_reproduces_original_measure(self):
  m=Tiny([1.,1.,1.,1.]);data,base,saved=self.data(m);a=measure_dual(m,data,base,saved,2);b=measure(m,data,base,saved,2)
  for x,y in zip([r for r in a['head'] if r['coordinate']=='physical'],b['head']):
   for k in ('loss_contribution','gradient_norm','scaled_normal_residual'):
    if x[k] is None:self.assertIsNone(y[k])
    else:np.testing.assert_allclose(x[k],y[k],rtol=1e-12,atol=1e-14)
  for x,y in zip([r for r in a['gradients'] if r['coordinate']=='actual'],b['gradients']):
   for k in ('full_norm','damage_norm','inside_background_norm'):np.testing.assert_allclose(x[k],y[k],rtol=1e-12,atol=1e-14)
if __name__=='__main__':unittest.main()
