"""Artificial observations/native arrays ONLY; exercises the actual nested code and writer."""
import unittest,tempfile,json,csv,subprocess,sys,inspect,logging,os
from pathlib import Path
from unittest.mock import patch
import numpy as np
import engine as e
import evidence as ev
import producer_data as pd
import package
import figures

class ArtificialData:
 coarse_side=2;native_side=4;half_height=1;identity={'kind':'ARTIFICIAL_ONLY'}
 def __init__(self,poison_group=None):
  self.groups=[g for g in ('a','b','c','d') for _ in (0,1)];self.centers=[2]*8;self.poison=poison_group;self.target_calls=[]
 def observations(self,ids,H):
  i=np.asarray(ids,dtype=float);return np.c_[i/10,(i%2)-.5],np.c_[i*i/70+H*.01,np.sin(i)]
 def current(self,i):return (np.arange(32,dtype=np.float32).reshape(2,4,4)/10+np.float32(i))
 def field(self,i,H):
  delta=np.asarray([.01*(i+1)*H,.02*(i%3+1)*H],dtype=np.float32)[:,None,None]+np.arange(16,dtype=np.float32).reshape(1,4,4)*np.float32(.001*H)
  return self.current(i)+delta+(np.float32(9.) if self.groups[i]==self.poison else np.float32(0.))
 def training_targets(self,ids,fold):
  fold.validate(self.groups)
  if tuple(ids)!=fold.train:raise ValueError('train target leak')
  self.target_calls.append(('train',fold.outer,fold.inner,tuple(ids)))
  d=[self.field(i,fold.horizon)-self.current(i) for i in ids]
  return np.asarray([e.base.pool(x,2).ravel() for x in d]),np.asarray([abs(x).mean((1,2)) for x in d]),ids
 def evaluation_target(self,i,fold):
  fold.validate(self.groups)
  if i not in fold.query:raise ValueError('eval target leak')
  self.target_calls.append(('eval',fold.outer,fold.inner,i));return self.field(i,fold.horizon)

class RecordingSink(ev.DiskSink):
 def outer(self,*args):
  fold,i=args[:2];self.saved=getattr(self,'saved',{});self.saved[i,fold.horizon]=args[6].copy()
  return super().outer(*args)

class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.audit=ev.Audit(self.root)
  self.previous=np.seterr(all='raise')
 def tearDown(self):np.seterr(**self.previous);self.temp.cleanup()
 def run_toy(self,data=None,name='out'):
  data=data or ArtificialData();sink=RecordingSink(self.root/name,data)
  try:counts=e.run_comparison(data,sink,self.audit,(1,2))
  finally:sink.close()
  return data,sink,counts
 def test_real_nested_path_counts_streams_and_native_reconstruction(self):
  data,sink,counts=self.run_toy();self.assertEqual(counts,{'predictor':64,'residualizer':32,'inner_rows':48,'outer_rows':16,'inner_scores':2160,'outer_scores':112})
  self.assertEqual(sink.i,48);self.assertEqual(sink.o,16)
  saved=json.loads((sink.root/'group_horizon_results.json').read_text());self.assertEqual(len(saved['paired']),8)
  schema=json.loads((sink.root/'array_schema.json').read_text());self.assertEqual((sink.root/'inner_losses.f64').stat().st_size,48*45*3*8)
  for case,H in ((0,1),(7,2)):
   fields,target,anchor,entry=ev.read_fields(sink.root,case,H);np.testing.assert_array_equal(fields,sink.saved[case,H])
   scores=e.native_losses(fields,target,np.asarray(entry['normalizer']),2,1)
   for j,p in enumerate(fields):np.testing.assert_allclose(scores[j],np.asarray(e.base.score(p,target,2,np.asarray(entry['normalizer']),1))[[0,3,4]],rtol=0,atol=1e-14)
  with (sink.root/'outer_scores.csv').open() as f:self.assertEqual(len(list(csv.DictReader(f))),112)
 def test_outer_target_poison_cannot_change_outer_a_models_or_selector(self):
  _,s1,_=self.run_toy(name='clean');_,s2,_=self.run_toy(ArtificialData('a'),'poison')
  def rows(sink):
   with (sink.root/'model_provenance.jsonl').open() as f:return [json.loads(x) for x in f if json.loads(x)['outer']=='a']
  self.assertEqual(rows(s1),rows(s2));self.assertEqual(s1.selections['a',1],s2.selections['a',1]);self.assertEqual(s1.selections['a',2],s2.selections['a',2])
 def test_fold_rejects_outer_or_query_training_before_target_access(self):
  data=ArtificialData();bad=e.Fold('a','b',tuple(range(8)),(2,3),1);counts={'predictor':0,'residualizer':0}
  with self.assertRaises(ValueError):e.fit_pair(data,bad,counts,self.audit)
  self.assertEqual(data.target_calls,[]);self.assertEqual(sum(counts.values()),0)
  with self.assertRaises(ValueError):e.Fold('unknown','b',(0,1,4,5,6,7),(2,3),1).validate(data.groups)
  with self.assertRaises(ValueError):e.Fold('a','a',(2,3,4,5,6,7),(0,1),1).validate(data.groups)
 def test_target_provenance_and_fixed_alpha(self):
  data=ArtificialData();fold=e.Fold('a','b',(4,5,6,7),(2,3),1)
  with self.assertRaises(ValueError):data.training_targets((0,1),fold)
  counts={'predictor':0,'residualizer':0};m=e.fit_pair(data,fold,counts,self.audit)
  np.testing.assert_array_equal(m.normalizer,np.maximum(data.training_targets(fold.train,fold)[1].mean(0),1e-6));self.assertEqual(m.provenance['normalizer_train_ids'],list(fold.train))
  self.assertEqual(m.provenance['alpha'],10.);self.assertEqual(counts,{'predictor':2,'residualizer':1})
  with self.assertRaises(ValueError):e.ridge(np.ones((4,2)),np.ones((4,2)),['c','c','d','d'],alpha=.1)
  self.assertNotIn('target',inspect.signature(e.predict_pair).parameters)
  with self.assertRaises(TypeError):e.predict_pair(m,None,None,None,None,2,target=np.zeros(1))
 def test_candidate_selection_ties_and_degeneracy(self):
  self.assertEqual((len(e.U),len(e.C),len(e.A),len(e.PAIRS)),(25,27,25,45))
  losses={w:1. for w in e.PAIRS};self.assertEqual(e.select(losses,e.C),(0.,0.))
  losses[(1.,0.)]=0.;self.assertEqual(e.select(losses,e.C),(1.,0.));self.assertEqual(e.select(losses,e.A),(1.,0.))
  pc=np.zeros((2,4,4));ph=np.ones((2,4,4));np.testing.assert_array_equal(e.blend(pc,ph,[(.3,0.),(.3,1.)])[0],e.blend(pc,ph,[(.3,0.),(.3,1.)])[1])
  out=e.blend(pc,ph,[(0.,0.),(1.,1.)]);np.testing.assert_array_equal(out[0],pc);np.testing.assert_array_equal(out[1],ph)
 def test_nonfinite_first_stop_preserves_case_and_does_not_overwrite(self):
  data=ArtificialData();original=data.evaluation_target
  def bad(i,fold):x=original(i,fold).copy();x[0,0,0]=np.nan;return x
  data.evaluation_target=bad;sink=ev.DiskSink(self.root/'bad',data)
  try:
   with self.assertRaises(ValueError):e.run_comparison(data,sink,self.audit,(1,))
  finally:sink.close()
  raw=(self.root/'first_failure.json').read_bytes();record=json.loads(raw);self.assertEqual(record['context']['stage'],'inner_query');self.assertIn('case',record['context']);self.assertFalse((sink.root/'group_horizon_results.json').exists())
  self.audit.fail(RuntimeError('second'));self.assertEqual(raw,(self.root/'first_failure.json').read_bytes())
 def test_existing_output_and_receipt_never_overwritten(self):
  (self.root/'existing').mkdir();sentinel=self.root/'existing/sentinel';sentinel.write_text('old')
  sink=ev.DiskSink(self.root/'existing',ArtificialData())
  with self.assertRaises(FileExistsError):e.run_comparison(sink.data,sink,self.audit,(1,))
  self.assertEqual(sentinel.read_text(),'old')
  ev.write(self.root/'receipt.json',{'old':True},True)
  with self.assertRaises(FileExistsError):ev.write(self.root/'receipt.json',{'new':True},True)
  self.assertEqual(json.loads((self.root/'receipt.json').read_text()),{'old':True})
 def test_full_geometry_is_derived_not_fixture_filled(self):
  p=e.work_plan(19,1144,2);self.assertEqual((p['predictor'],p['residualizer'],p['inner_scores'],p['outer_scores']),(1444,722,1853280,16016))
  self.assertGreater(2*(41184*45*3*8+2288*2*512*8),100*2**20)
 def test_font_policy_accepts_exact_dependency_log_only(self):
  handler=figures.FontCacheLog(self.root/'font.log');record=logging.LogRecord('matplotlib.font_manager',logging.WARNING,'',0,'Matplotlib is building the font cache; this may take a moment.',(),None);handler.emit(record)
  self.assertIn('font cache',(self.root/'font.log').read_text())
  record.msg='unexpected dependency warning'
  with self.assertRaises(RuntimeError):handler.emit(record)
 def test_budget_boundaries_and_size_race(self):
  import supervise
  self.assertEqual(package.budget_reason(1201,0,0,0,0),'wall_budget');self.assertEqual(package.budget_reason(1,2*2**30+1,0,0,0),'rss_budget');self.assertEqual(package.budget_reason(1,0,1536*2**20+1,0,0),'total_storage_budget');self.assertEqual(package.budget_reason(1,0,0,700*2**20+1,0),'archive_budget')
  class Missing:
   def stat(self):raise FileNotFoundError()
  with patch.object(Path,'rglob',return_value=iter([Missing()])):self.assertEqual(supervise.size(self.root),0)
  class Denied:
   def stat(self):raise PermissionError()
  with patch.object(Path,'rglob',return_value=iter([Denied()])):
   with self.assertRaises(PermissionError):supervise.size(self.root)


class LifecycleTests(unittest.TestCase):
 def test_actual_guard_child_exit_and_first_fatal_lifetime(self):
  import runtime_guard
  guard=Path(runtime_guard.__file__)
  fixtures={'clean':'x=1\n',
   'warning':"import warnings\nwarnings.warn('artificial scientific warning')\n",
   'destructor':"class Broken:\n def __del__(self):raise RuntimeError('artificial destructor')\nx=Broken()\ndel x\n",
   'atexit':"import atexit\ndef bad():raise RuntimeError('artificial exit callback')\natexit.register(bad)\n"}
  for label,code in fixtures.items():
   with self.subTest(label=label),tempfile.TemporaryDirectory() as t:
    r=Path(t);(r/'logs').mkdir();script=r/'artificial.py';script.write_text(code)
    p=subprocess.run([sys.executable,str(guard),'--root',str(r),'--target',str(script)],capture_output=True,timeout=10)
    (r/'logs/worker.stderr').write_bytes(p.stderr)
    if label=='clean':self.assertEqual(p.returncode,0);self.assertIsNone(runtime_guard.child_failure(r,json.loads((r/'logs/runtime_exit.json').read_text())['pid'],0,require_clean=True))
    else:
     self.assertNotEqual(p.returncode,0);self.assertIsNotNone(runtime_guard.child_failure(r,0,p.returncode,require_clean=True))
     if label!='warning':self.assertTrue((r/'logs/runtime_fatal.jsonl').exists())
     else:self.assertIn(b'artificial scientific warning',p.stderr)
 def test_real_monitor_budget_first_stop_without_scientific_child(self):
  import supervise
  class ArtificialChild:
   pid=987654321
   def poll(self):return None
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);(r/'logs').mkdir();(r/'logs/worker.stderr').write_bytes(b'')
   with patch.object(supervise.time,'monotonic',return_value=1201):
    peak,reason=supervise.monitor_child(ArtificialChild(),r,0)
   self.assertEqual(reason,'wall_budget')
   (r/'logs/worker.stderr').write_bytes(b'artificial stderr')
   peak,reason=supervise.monitor_child(ArtificialChild(),r,0);self.assertEqual(reason,'worker_stderr_nonempty')
 def test_three_actual_artificial_figures_and_sidecars(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);audit=ev.Audit(r);sink=ev.DiskSink(r/'out',ArtificialData())
   try:e.run_comparison(sink.data,sink,audit,(1,2))
   finally:sink.close()
   # The renderer is isolated to a fresh artificial cache before first import.
   env=os.environ.copy();env.update(MPLCONFIGDIR=str(r/'font_cache'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
   script="import warnings;warnings.simplefilter('error');from figures import render;render("+repr(str(r/'out'))+")"
   p=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).parent,env=env,capture_output=True,timeout=30)
   self.assertEqual(p.returncode,0,p.stderr.decode());self.assertEqual(p.stderr,b'')
   self.assertEqual(len(list((r/'out').glob('0*.png'))),3)
   for image in (r/'out').glob('0*.png'):self.assertTrue(image.with_suffix('.md').is_file())
   dependency=json.loads((r/'out/plot_dependency.json').read_text());self.assertEqual(dependency['backend'].lower(),'agg')


class DisabledTests(unittest.TestCase):
 def test_sealed_cli_default_denial_before_scientific_open(self):
  code=Path(__file__).parent.resolve()
  for entry in ('worker.py','supervise.py','launch.py'):
   script="""import sys,runpy
from pathlib import Path
def forbid(event,args):
 if event=='open' and isinstance(args[0],str) and (args[0].endswith(('.pt','.npz','.csv')) or '/inputs/mendeley/' in args[0]):raise AssertionError('SCIENTIFIC_OPEN_FORBIDDEN')
sys.addaudithook(forbid)
target=sys.argv[1]
sys.argv=[target]
runpy.run_path(target,run_name='__main__')
"""
   result=subprocess.run([sys.executable,'-c',script,str(code/entry)],cwd=code,capture_output=True,timeout=10)
   self.assertNotEqual(result.returncode,0);self.assertIn(b'Exact execution authority absent',result.stderr);self.assertNotIn(b'SCIENTIFIC_OPEN_FORBIDDEN',result.stderr)

class ResourceTests(unittest.TestCase):
 def test_actual_category_scan_includes_copies_and_temporary(self):
  import resource_contract as r
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'outputs').mkdir();(root/'tmp').mkdir()
   (root/'outputs/inner_losses.f64').write_bytes(b'1234');(root/'results.tar.partial').write_bytes(b'12345');(root/'tmp/owned').write_bytes(b'12')
   counts=r.storage(root);self.assertEqual((counts['raw_arrays'],counts['archive'],counts['temporary']),(4,5,2));self.assertEqual(sum(counts.values()),11)
   self.assertEqual(r.storage_reason(root,{'archive':4}),'storage_category_archive');self.assertIsNone(r.storage_reason(root,{'archive':5}))

class WholeLifecycleTests(unittest.TestCase):
 def test_real_controller_final_hash_timeout_and_exception(self):
  import watchdog as w,time
  code=Path(__file__).parent.resolve()
  for failure in ('sleep','exception'):
   with self.subTest(failure=failure),tempfile.TemporaryDirectory() as t:
    root=Path(t);(root/'logs').mkdir();(root/'payload.bin').write_bytes(b'artificial-final-payload')
    script="""import sys,time
from pathlib import Path
import supervise
root=Path(sys.argv[1])
def injected_hash(path):
 if Path(path).name=='payload.bin':
  if sys.argv[2]=='sleep':time.sleep(5)
  else:raise RuntimeError('artificial final controller hash failure')
 return 'artificial-hash-for-non-scientific-fixture'
supervise.contract.sha=injected_hash
supervise.finalize_delivery(root)
"""
    with (root/'logs/controller.stderr').open('xb') as err:
     child=subprocess.Popen([sys.executable,'-c',script,str(root),failure],cwd=code,stderr=err,stdout=subprocess.DEVNULL,start_new_session=True)
     try:
      result=w.watch_process(child,root,time.monotonic(),wall=.4 if failure=='sleep' else 3,sampler=lambda pg:(0,[]),interval=.02)
      self.assertIsNotNone(result['reason'])
      if failure=='sleep':self.assertEqual(result['reason'],'whole_lifecycle_wall_deadline')
      else:self.assertIn(result['reason'],('controller.stderr_nonempty','controller_exit_nonzero'))
      w.stop_group(child);self.assertIsNotNone(child.poll())
      w.first_stop(root,result['reason'],{'scope':'ARTIFICIAL_FINAL_CONTROLLER_IO'});before=(root/'watchdog_first_stop.json').read_bytes();w.first_stop(root,'second',{});self.assertEqual(before,(root/'watchdog_first_stop.json').read_bytes())
      self.assertFalse((root/'delivery_manifest.json').exists())
     finally:
      if child.poll() is None:w.stop_group(child)
 def test_combined_memory_includes_controller_worker_helper_and_monitor(self):
  import watchdog as w
  def r(pid,pg,sid,rss,hwm):return dict(pid=pid,pgid=pg,sid=sid,rss=rss,hwm=hwm,start_ticks=1)
  records=[r(1,9,9,10,15),r(2,20,20,30,40),r(3,20,20,50,60),r(4,20,20,5,8),r(5,88,88,10000,10000)]
  value,owned=w.combined_memory(records,20,1);self.assertEqual(value,123);self.assertEqual({x['pid'] for x in owned},{1,2,3,4})
 def test_outer_monitor_counts_all_archive_copies_and_combined_memory(self):
  import watchdog as w,time
  from unittest.mock import patch
  class Child:
   pid=987654321
   def poll(self):return None
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'logs').mkdir();(root/'results.tar').write_bytes(b'123');(root/'results.tar.partial').write_bytes(b'456')
   with patch.dict(w.storage_reason.__globals__['LIMITS'],{'archive':5}):
    r=w.watch_process(Child(),root,time.monotonic(),wall=1,sampler=lambda pg:(0,[]),interval=.01)
   self.assertEqual(r['reason'],'storage_category_archive')
   r=w.watch_process(Child(),root,time.monotonic(),wall=1,rss_cap=100,sampler=lambda pg:(101,[]),interval=.01);self.assertEqual(r['reason'],'combined_process_rss_budget')
 def test_posix_alarm_interrupts_actual_blocking_final_io_wait(self):
  import watchdog as w,signal,time
  previous=signal.getsignal(signal.SIGALRM)
  try:
   w.arm_deadline(.05);start=time.monotonic()
   with self.assertRaises(w.DeadlineExceeded):time.sleep(1)
   self.assertLess(time.monotonic()-start,.5)
  finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
 def test_worker_controller_seals_are_separate_and_late_exception_stops(self):
  code=Path(__file__).parent.resolve()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'logs').mkdir()
   script="""import sys
from pathlib import Path
from runtime_guard import install
root=Path(sys.argv[1]);flag=install(root,event_name='controller_fatal.jsonl',seal_name='controller_exit.json');flag[0]=True
"""
   p=subprocess.run([sys.executable,'-c',script,str(root)],cwd=code,capture_output=True,timeout=10)
   self.assertEqual(p.returncode,0,p.stderr);self.assertTrue((root/'logs/controller_exit.json').exists());self.assertFalse((root/'logs/runtime_exit.json').exists())
 def test_actual_controller_late_exit_failure_rejects_candidate(self):
  code=Path(__file__).parent.resolve()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'logs').mkdir()
   script="""import sys,atexit,time
from pathlib import Path
import supervise
root=Path(sys.argv[1]);flag=supervise.install_controller_guard(root,'ARTIFICIAL','ARTIFICIAL',time.monotonic(),{'child':None})
supervise.contract.write(root/'controller_receipt.json',{'status':'CANDIDATE_COMPLETE_REQUIRES_WATCHDOG'})
def broken():raise RuntimeError('artificial late controller callback')
atexit.register(broken);flag[0]=True
"""
   result=subprocess.run([sys.executable,'-c',script,str(root)],cwd=code,capture_output=True,timeout=10)
   self.assertNotEqual(result.returncode,0);self.assertTrue((root/'logs/controller_fatal.jsonl').exists())
   self.assertEqual(json.loads((root/'controller_receipt.json').read_text())['status'],'STOPPED_NO_RETRY')
 def test_resource_only_decision_cannot_authorize_execution(self):
  code=Path(__file__).parent
  cfg=json.loads((code/'config.json').read_text());decision=json.loads((code/'resource_decision.json').read_text())
  with self.assertRaises(PermissionError):package.validate_authority(decision,cfg,'artificial-digest','artificial-config')
  self.assertFalse(cfg['execution_authority_granted']);self.assertEqual(cfg['run_id'],'IU-OUTPUT-CALIBRATION-C27A25-20261020-R001')




class CleanupRaceTests(unittest.TestCase):
 def test_reaped_child_never_signals_a_stale_group(self):
  import watchdog as w
  class Reaped:
   pid=987654321
   def poll(self):return 1
   def wait(self,timeout):return 1
  with patch.object(w.os,'killpg',side_effect=AssertionError('stale group must not be signalled')):w.stop_group(Reaped())
 def test_signal_denial_for_live_child_is_not_hidden(self):
  import watchdog as w
  class Live:
   pid=987654321
   def poll(self):return None
   def wait(self,timeout):raise subprocess.TimeoutExpired('ARTIFICIAL',timeout)
  with patch.object(w.os,'killpg',side_effect=PermissionError('ARTIFICIAL_DENIAL')):
   with self.assertRaises(PermissionError):w.stop_group(Live())

class InterruptedCleanupTests(unittest.TestCase):
 def member(self,pid=42,start=17,pgid=41,state='S'):
  return dict(pid=pid,start_ticks=start,pgid=pgid,sid=pgid,state=state,rss=12,hwm=20)
 def test_interrupted_monitor_retains_observed_identity(self):
  import watchdog as w,time
  class Child:
   pid=41
   def poll(self):return None
  for error in (RuntimeError('artificial storage failure'),w.DeadlineExceeded('artificial deadline')):
   with self.subTest(error=type(error).__name__),tempfile.TemporaryDirectory() as t:
    state={};member=self.member()
    with patch.object(w,'storage_reason',side_effect=error):
     with self.assertRaises(type(error)):w.watch_process(Child(),t,time.monotonic(),sampler=lambda pg:(20,[member]),state=state)
    self.assertEqual(state['members'],[member]);self.assertEqual(state['peak_combined_hwm_bytes'],20)
    self.assertGreater(state['last_observation_monotonic'],0)
 def test_reaped_controller_known_worker_is_killed_and_verified(self):
  import watchdog as w
  class Reaped:
   pid=41
   def poll(self):return 0
   def wait(self,timeout):return 0
  member=self.member();snapshots=iter([[member],[],[]])
  with patch.object(w.os,'killpg') as kill:
   result=w.stop_group(Reaped(),[member],records_provider=lambda:next(snapshots))
  kill.assert_called_once_with(41,w.signal.SIGKILL)
  self.assertTrue(result['known_descendants_verified']);self.assertEqual(result['verified_identity_count'],1)
 def test_surviving_known_worker_never_claims_cleanup(self):
  import watchdog as w
  class Reaped:
   pid=41
   def poll(self):return 0
   def wait(self,timeout):return 0
  member=self.member()
  with patch.object(w.os,'killpg') as kill:
   with self.assertRaisesRegex(RuntimeError,'still active'):w.stop_group(Reaped(),[member],records_provider=lambda:[member],cleanup_timeout=0)
  kill.assert_called_once_with(41,w.signal.SIGKILL)
 def test_reused_group_without_retained_identity_is_not_signalled(self):
  import watchdog as w
  class Reaped:
   pid=41
   def poll(self):return 0
   def wait(self,timeout):return 0
  with patch.object(w.os,'killpg',side_effect=AssertionError('unowned group')):
   with self.assertRaisesRegex(RuntimeError,'unverified'):w.stop_group(Reaped(),[self.member(start=17)],records_provider=lambda:[self.member(start=99)])
 def test_deadline_and_actual_exit_seal_have_comparable_clocks(self):
  import watchdog as w,time
  start_m=time.monotonic();start_u=time.time();event=w.DeadlineExceeded('artificial');cleanup_m=time.monotonic();cleanup_u=time.time()
  self.assertLessEqual(start_m,event.trigger_monotonic);self.assertLessEqual(event.trigger_monotonic,cleanup_m)
  self.assertLessEqual(start_u,event.trigger_unix);self.assertLessEqual(event.trigger_unix,cleanup_u)
  code=Path(__file__).parent.resolve()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'logs').mkdir()
   script="from runtime_guard import install; import sys; f=install(sys.argv[1],seal_name='watchdog_exit.json'); f[0]=True"
   p=subprocess.run([sys.executable,'-c',script,t],cwd=code,capture_output=True,timeout=10)
   self.assertEqual(p.returncode,0,p.stderr);seal=json.loads((root/'logs/watchdog_exit.json').read_text())
   self.assertLessEqual(cleanup_m,seal['time_monotonic']);self.assertLessEqual(cleanup_u,seal['time_unix'])

if __name__=='__main__':unittest.main()
