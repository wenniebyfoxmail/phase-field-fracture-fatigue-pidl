"""Synthetic CPU forward/static checks only; no backward or optimizer.step."""
import ast,copy,math,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np,torch
from core import UNet,loss_fn,crop_plan,crop_arrays,error,scores,risk_curve,validation,check_time,BudgetExpired
from tiling import reconstruct
from data_lock import validate,canonical,PINNED,PROVENANCE
import runner
class Checks(unittest.TestCase):
 def test_model(self):
  torch.set_num_threads(1);m=UNet().eval()
  with torch.no_grad():y=m(torch.zeros(1,3,32,48))
  self.assertEqual(tuple(y.shape),(1,1,32,48));self.assertTrue(torch.isfinite(y).all())
  self.assertEqual(sum(isinstance(x,torch.nn.Conv2d) for x in m.modules()),19)
  self.assertFalse(any(isinstance(x,(torch.nn.BatchNorm2d,torch.nn.Dropout)) for x in m.modules()))
 def test_padding_loss(self):
  z=torch.zeros(1,1,2,2);t=torch.zeros_like(z);v=torch.tensor([[[[1.,0.],[0.,0.]]]])
  expected=.5*math.log(2)+.5*(1-1/1.5)
  self.assertAlmostEqual(loss_fn(z,t,v).item(),expected,places=6)
  z[0,0,1,1]=100;t[0,0,1,1]=1
  self.assertAlmostEqual(loss_fn(z,t,v).item(),expected,places=6)
 def test_crop_plan(self):
  rows=[{'id':'b','role':'train','source':'METU','shape':[600,700]},{'id':'a','role':'train','source':'METU','shape':[20,30]}]
  a=crop_plan(rows,np.random.default_rng(20261009));b=crop_plan(rows[::-1],np.random.default_rng(20261009));self.assertEqual(a,b);self.assertEqual(len(a),8)
  with self.assertRaises(ValueError):crop_plan([dict(rows[0],role='internal_test')],np.random.default_rng(0))
  x,y,v=crop_arrays(np.full((20,30,3),255,np.uint8),np.zeros((20,30),bool),0,0)
  self.assertEqual(v.sum(),600);self.assertTrue((x==1).all());self.assertEqual(y.sum(),0)
 def test_geometry(self):
  rng=np.random.default_rng(1)
  for h,w in [(1,1),(200,310),(448,448),(449,451),(673,897)]:
   a=rng.random((h,w,3));self.assertTrue(np.allclose(reconstruct(a,lambda x:x[:,:,0]),a[:,:,0]))
 def test_metrics(self):
  self.assertEqual(error(np.zeros((2,2)),np.zeros((2,2),bool)),0)
  self.assertEqual(error(np.ones((2,2)),np.zeros((2,2),bool)),1)
  self.assertEqual(error(np.full((1,1),.5),np.ones((1,1),bool)),0)
  self.assertEqual(scores(np.array([0.,1.])),(0.,0.));self.assertAlmostEqual(scores(np.array([.5]))[1],math.log(2))
  rows=[{'id':'a','error':0.,'U':0.},{'id':'b','error':1.,'U':1.}]
  self.assertEqual(np.mean([r['risk'] for r in risk_curve(rows,'U')]),.25)
 def test_roles(self):
  rows=[]
  for (source,i),(role,group) in canonical().items():
   image=('rgb/' if source=='METU' else 'images/')+i+'.png';mask=('BW/' if source=='METU' else 'labels/')+i+'.png'
   rows.append(dict(id=i,source=source,role=role,group=group,image=image,mask=mask,image_sha256=source+i))
  meta={'provenance':PROVENANCE,'contract_sha256':PINNED['CODE_CONTRACT_R1.md'],'roles_sha256':{n:PINNED[n] for n in ['metu_group_split_r1.csv','buildcrack_external_role_r1.csv']}}
  validate(dict(meta,rows=rows),{},False)
  for field,value in [('id','UNKNOWN'),('role','unknown'),('image','../escape'),('image','rgb/unknown.png')]:
   bad=copy.deepcopy(rows);bad[0][field]=value
   with self.assertRaises(ValueError):validate(dict(meta,rows=bad),{},False)
  with self.assertRaises(ValueError):validate(dict(meta,rows=rows,contract_sha256='bad'),{},False)
  bad=copy.deepcopy(rows);a=next(r for r in bad if r['role']=='train');v=next(r for r in bad if r['role']=='validation');v['image_sha256']=a['image_sha256']
  with self.assertRaises(ValueError):validate(dict(meta,rows=bad),{},False)
 def test_checkpoint_tie(self):
  from core import better
  self.assertFalse(better(.2,.2));self.assertTrue(better(.199999999,.2))
  with self.assertRaises(ValueError):better(float('nan'),.2)
 def test_final_has_no_optimizer(self):
  tree=ast.parse(Path('core.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='final_evaluate')
  self.assertNotIn('optim',ast.unparse(fn));self.assertNotIn('backward',ast.unparse(fn))
 def test_gates(self):
  with patch('runner.platform.system',return_value='Darwin'):
   with self.assertRaises(RuntimeError):runner.gate({},'/nonexistent')
  approval={'execute':True,'producer_alias':'gpu-server','experiment_id':'HQ-PUBLIC-REF-001','user_authorization_reference':'chat 2026-10-09','hostname':'D-26-09','code_snapshot':'snapshot','data_lock_sha256':'lock','environment':{'frozen':True},'output_root':'C:/Users/xw436/jobs'}
  with patch.dict('runner.os.environ',{'CUDA_VISIBLE_DEVICES':'0','CUBLAS_WORKSPACE_CONFIG':':4096:8'},clear=True), patch('runner.platform.system',return_value='Windows'), patch('runner.torch.cuda.is_available',return_value=True), patch('runner.socket.gethostname',return_value='D-26-09'), patch('runner.snapshot',return_value='snapshot'), patch('runner.sha',return_value='lock'), patch('runner.environment',return_value={'frozen':True}):
   runner.gate(approval,'lock.json')
   with self.assertRaises(RuntimeError):runner.gate(dict(approval,producer_alias='taobo'),'lock.json')
  with self.assertRaises(BudgetExpired):check_time(-1)
  with self.assertRaises(ValueError):validation(None,[{'source':'BuildCrack','role':'validation'}],{},None,0)
if __name__=='__main__':unittest.main(verbosity=2)
