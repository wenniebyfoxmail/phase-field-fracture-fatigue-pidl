"""Small cached-Q4 derivative contract; no optimizer or training loop."""
import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis'))
from run_pidl_block_diagnosis import LocalProblem
from compute_energy import compute_energy
from run_native_q4_direct_q4_damage import analytic_damage_gradient

def test_cached_native_q4_energy_and_damage_gradient():
 data=dict(nodes=np.array([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]]),cells=np.array([[0,1,2,3]]),
  u_fem=np.array([0.,.01,.02,0.]),v_fem=np.array([0.,0.,.12,.12]),d_fem=np.array([.1,.2,.25,.1]),
  pidl_hist_alpha_pre=np.array([.2,.25,.3,.15]),pidl_f_pre=np.array([[.3,.4,.5,.6]]),freeu=np.arange(8))
 p=LocalProblem(data,torch.device('cpu'));d=p.df.clone().requires_grad_(True);parts=p.parts(p.uf,p.vf,d)
 ref=compute_energy(p.x,p.uf,p.vf,d,p.hist,p.mat,p.model,p.area,p.cells,f_fatigue=p.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})
 torch.testing.assert_close(torch.stack(parts),torch.stack(ref),rtol=1e-13,atol=1e-13)
 ad=torch.autograd.grad(sum(parts),d)[0];analytic=analytic_damage_gradient(p.x,p.cells,p.uf,p.vf,d,p.hist,p.f,p.mat,p.model)
 torch.testing.assert_close(ad,analytic,rtol=1e-13,atol=1e-13)
 direction=torch.tensor([.3,-.4,.1,-.2],dtype=torch.float64);h=1e-7
 fd=(sum(p.parts(p.uf,p.vf,p.df+h*direction))-sum(p.parts(p.uf,p.vf,p.df-h*direction)))/(2*h)
 torch.testing.assert_close(fd,(ad*direction).sum(),rtol=1e-8,atol=1e-8)
 assert p.model.irrPenalty()==16875
