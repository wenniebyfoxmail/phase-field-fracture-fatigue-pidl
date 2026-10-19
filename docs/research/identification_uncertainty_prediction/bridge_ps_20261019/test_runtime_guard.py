"""Only hand-written scripts, temporary CSV and artificial child processes; no scientific I/O."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest,threading
import runtime_guard as guard
import supervise,time

PACKAGE=Path(__file__).resolve().parent

class LifetimeGuardTests(unittest.TestCase):
 def execute(self,body,guarded=True,before=None):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);logs=root/'logs';logs.mkdir();(root/'fixture.csv').write_text('a,b\n1,2\n')
   target=root/'fixture.py';target.write_text("from pathlib import Path\nimport os,sys,json,warnings,gc,atexit\nr=Path(os.environ['GUARD_FIXTURE_ROOT'])\n"+body)
   if before:before(root)
   cmd=[sys.executable,str(PACKAGE/'runtime_guard.py'),'--root',str(root),'--target',str(target)] if guarded else [sys.executable,str(target)]
   env=os.environ.copy();env['GUARD_FIXTURE_ROOT']=str(root)
   with (logs/'stdout').open('wb') as out,(logs/'worker.stderr').open('wb') as err:
    p=subprocess.Popen(cmd,env=env,stdout=out,stderr=err,start_new_session=True)
    expired=[]
    def timeout():
     expired.append(True)
     if p.poll() is None:p.kill()
    timer=threading.Timer(8,timeout);timer.start()
    try:
     peak,reason=supervise.monitor_child(p,root,time.monotonic())
     if p.poll() is None and reason:p.terminate()
     p.wait(timeout=8)
    finally:
     timer.cancel()
     if p.poll() is None:p.kill();p.wait()
    self.assertFalse(expired,'artificial fixture timed out')
   reason=reason or guard.child_failure(root,p.pid,p.returncode,require_clean=True)
   # The real controller raises on this same reason; this artificial controller has no science paths.
   decision={'status':'STOPPED_NO_RETRY' if reason else 'COMPLETE','reason':reason,'exit_code':1 if reason else 0}
   (root/'artificial_controller_receipt.json').write_text(json.dumps(decision))
   result=dict(rc=p.returncode,reason=reason,decision=decision,stderr=(logs/'worker.stderr').read_text(),events=(logs/'runtime_fatal.jsonl').read_text() if (logs/'runtime_fatal.jsonl').is_file() else '',seal=(logs/'runtime_exit.json').exists(),candidate=(root/'candidate.json').read_text() if (root/'candidate.json').exists() else '',controller=json.loads((root/'controller_receipt.json').read_text()) if (root/'controller_receipt.json').exists() else None,controller_event=(logs/'controller_fatal.jsonl').read_text() if (logs/'controller_fatal.jsonl').is_file() else '')
   if os.environ.get('GUARD_FIXTURE_AUDIT_DIR'):
    audit=Path(os.environ['GUARD_FIXTURE_AUDIT_DIR']);audit.mkdir(parents=True,exist_ok=True)
    (audit/(self._testMethodName+'.json')).write_text(json.dumps({'scope':'HAND_AUTHORED_ARTIFICIAL_SUBPROCESS_ONLY','result':result},indent=2)+'\n')
   return result
 def failed(self,x,event=None):
  self.assertEqual(x['decision']['status'],'STOPPED_NO_RETRY');self.assertNotEqual(x['decision']['exit_code'],0)
  if event:self.assertIn(event,x['events']);self.assertNotEqual(x['rc'],0)
 def test_original_leaked_csv_reproduces_exit_zero_unraisable_gap(self):
  x=self.execute("warnings.simplefilter('error')\nimport csv\nrows=list(csv.DictReader((r/'fixture.csv').open()))\n",False)
  self.assertEqual(x['rc'],0);self.assertIn('ResourceWarning',x['stderr']);self.assertIn('Exception ignored',x['stderr'])
 def test_guarded_original_csv_leak_is_durable_and_nonzero(self):
  self.failed(self.execute("import csv\nrows=list(csv.DictReader((r/'fixture.csv').open()))\n"),'ResourceWarning')
 def test_actual_score_reader_closes_csv_and_completes_cleanly(self):
  x=self.execute(f"sys.path.insert(0,{str(PACKAGE)!r})\nfrom verify import read_score_rows\nassert read_score_rows(r/'fixture.csv')==[{{'a':'1','b':'2'}}]\ngc.collect()\n")
  self.assertEqual(x['rc'],0);self.assertIsNone(x['reason']);self.assertTrue(x['seal']);self.assertFalse(x['stderr']);self.assertFalse(x['events'])
 def test_destructor_exception_is_durable_and_nonzero(self):
  self.failed(self.execute("class Bad:\n def __del__(self):raise RuntimeError('fixture destructor')\nBad()\n"),'RuntimeError')
 def test_cyclic_destructor_warning_collected_after_target_return(self):
  self.failed(self.execute("class Bad:\n def __del__(self):warnings.warn('fixture cyclic warning',ResourceWarning)\nb=Bad();b.cycle=b\ndel b\n"),'ResourceWarning')
 def test_atexit_warning_after_normal_return_stops(self):
  self.failed(self.execute("atexit.register(lambda:warnings.warn('fixture exit warning',ResourceWarning))\n"),'ResourceWarning')
 def test_atexit_exception_after_normal_return_stops(self):
  self.failed(self.execute("def fail():raise RuntimeError('fixture exit exception')\natexit.register(fail)\n"),'RuntimeError')
 def test_late_module_finalizer_cannot_authorise_complete(self):
  x=self.execute("import builtins\nclass Bad:\n def __del__(self,_warn=warnings.warn,_kind=ResourceWarning):_warn('fixture shutdown',_kind)\nbuiltins._guard_fixture_late=Bad()\n")
  self.failed(x);self.assertTrue(x['events'] or x['stderr'])
 def test_warning_after_candidate_receipt_cannot_authorise_complete(self):
  x=self.execute("(r/'candidate.json').write_text(json.dumps({'status':'CANDIDATE_COMPLETE_REQUIRES_CONTROLLER'}))\natexit.register(lambda:warnings.warn('after candidate',ResourceWarning))\n")
  self.failed(x,'ResourceWarning');self.assertIn('CANDIDATE_COMPLETE',x['candidate'])
 def test_warning_during_candidate_serialisation_cannot_authorise_complete(self):
  x=self.execute("class Bad:\n def __str__(self):warnings.warn('during candidate',ResourceWarning);return 'unused'\n(r/'candidate.json').write_text(json.dumps({'value':Bad()},default=str))\n")
  self.failed(x);self.assertNotEqual(x['rc'],0);self.assertIn('ResourceWarning',x['stderr'])
 def test_stderr_fallback_rejects_replaced_unraisable_hook(self):
  x=self.execute("sys.unraisablehook=sys.__unraisablehook__\nclass Bad:\n def __del__(self):raise RuntimeError('fallback fixture')\nBad()\n")
  self.assertEqual(x['rc'],0);self.assertTrue(x['seal']);self.assertIn('Exception ignored',x['stderr']);self.failed(x)
 def test_emitted_warning_stderr_is_not_filtered_or_exempted(self):
  x=self.execute("warnings.simplefilter('always')\nwarnings.warn('emitted fixture warning',UserWarning)\n")
  self.assertEqual(x['rc'],0);self.assertIn('UserWarning',x['stderr']);self.failed(x)
 def test_fatal_evidence_write_failure_still_exits_nonzero(self):
  x=self.execute("class Bad:\n def __del__(self):raise RuntimeError('fixture')\nBad()\n",before=lambda r:(r/'logs/runtime_fatal.jsonl.partial').mkdir())
  self.failed(x);self.assertNotEqual(x['rc'],0);self.assertIn('RUNTIME_FATAL_EVIDENCE_WRITE_FAILED',x['stderr'])
 def test_reentrant_exception_formatting_cannot_deadlock_guard(self):
  x=self.execute("class Nested:\n def __del__(self):raise RuntimeError('nested')\nclass OddError(Exception):\n def __str__(self):Nested();return 'outer'\nclass Bad:\n def __del__(self):raise OddError()\nBad()\n")
  self.failed(x);self.assertNotEqual(x['rc'],0);self.assertIn('RUNTIME_FATAL_REENTRANT',x['stderr'])
 def test_uncaught_thread_exception_is_fatal(self):
  self.failed(self.execute("import threading\ndef fail():raise RuntimeError('fixture thread')\nt=threading.Thread(target=fail);t.start();t.join()\n"),'thread_exception')
 def test_missing_clean_exit_seal_rejected_even_exit_zero(self):
  x=self.execute("os._exit(0)\n")
  self.assertEqual(x['rc'],0);self.failed(x);self.assertEqual(x['reason'],'runtime_clean_exit_evidence_missing')
 def test_guard_rejects_running_child_or_stale_clean_pid(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'logs').mkdir();(p/'logs/worker.stderr').write_bytes(b'');(p/'logs/runtime_exit.json').write_text(json.dumps({'status':'RETURNED_AND_EXIT_CALLBACKS_COMPLETE','pid':12}))
   self.assertEqual(guard.child_failure(p,12,None,require_clean=True),'worker_not_exited')
   self.assertEqual(guard.child_failure(p,13,0,require_clean=True),'runtime_clean_exit_identity')
 def controller_fixture(self,body):
  prefix=f"sys.path.insert(0,{str(PACKAGE)!r})\nimport time\nfrom supervise import install_controller_guard\ninstall_controller_guard(r,'fixture-digest','fixture-start',time.monotonic(),{{'child':None}})\n"
  return self.execute(prefix+body,guarded=False)
 def test_controller_warning_after_complete_receipt_rejects_and_exits(self):
  x=self.controller_fixture("(r/'controller_receipt.json').write_text(json.dumps({'status':'COMPLETE'}))\natexit.register(lambda:warnings.warn('controller after receipt',ResourceWarning))\n")
  self.assertEqual(x['rc'],86);self.assertEqual(x['controller']['status'],'STOPPED_NO_RETRY');self.assertIn('ResourceWarning',x['controller_event'])
 def test_controller_late_finalizer_rejects_prior_complete(self):
  x=self.controller_fixture("(r/'controller_receipt.json').write_text(json.dumps({'status':'COMPLETE'}))\nimport builtins\nclass Bad:\n def __del__(self,_warn=warnings.warn,_kind=ResourceWarning):_warn('controller shutdown',_kind)\nbuiltins._guard_fixture_controller=Bad()\n")
  self.assertEqual(x['rc'],86);self.assertEqual(x['controller']['status'],'STOPPED_NO_RETRY');self.assertIn('ResourceWarning',x['controller_event'])
 def test_controller_finalizer_during_receipt_open_rejects(self):
  x=self.controller_fixture("with (r/'controller_receipt.json').open('w') as f:\n f.write(json.dumps({'status':'COMPLETE'}))\n class Bad:\n  def __del__(self):raise RuntimeError('during controller receipt')\n Bad()\n")
  self.assertEqual(x['rc'],86);self.assertEqual(x['controller']['status'],'STOPPED_NO_RETRY');self.assertIn('RuntimeError',x['controller_event'])
 def test_controller_clean_completion_not_changed(self):
  x=self.controller_fixture("(r/'controller_receipt.json').write_text(json.dumps({'status':'COMPLETE'}))\n")
  self.assertEqual(x['rc'],0);self.assertEqual(x['controller']['status'],'COMPLETE');self.assertFalse(x['controller_event']);self.assertFalse(x['stderr'])
 def test_plain_clean_completion_is_accepted_without_stderr(self):
  x=self.execute("(r/'candidate.json').write_text(json.dumps({'status':'CANDIDATE_COMPLETE_REQUIRES_CONTROLLER'}))\n")
  self.assertEqual(x['decision']['status'],'COMPLETE');self.assertEqual(x['rc'],0);self.assertTrue(x['seal'])

if __name__=='__main__':unittest.main()
