"""Artificial lifecycle fixtures only. No GPU query, child/model or arrays."""
import copy,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import control as c
import deadline_guard as dg
import launch
from telemetry import Reporter

class ControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.now=0.;self.clock=lambda:self.now
    def pre(self):return dict(completed=True,admitted=True,accepted_hidden_updates=0,root_state_restored=True)
    def test_preflight_scope_never_continues(self):
        ch=c.Chain('preflight_only',0,self.clock);ch.begin('preflight');ch.finish(self.pre())
        self.assertIn('NOT_SCIENTIFIC',ch.terminal())
        with self.assertRaises(RuntimeError):ch.begin('candidate')
    def test_full_chain_requires_all_phases(self):
        ch=c.Chain('conditional_full',0,self.clock)
        with self.assertRaises(RuntimeError):ch.begin('candidate')
        for n in c.PHASES:
            ch.begin(n);ch.finish(self.pre() if n=='preflight' else {'completed':True})
        self.assertEqual(ch.terminal(),'FULL_COMPARISON_COMPLETE')
    def test_missing_terminal(self):
        with self.assertRaises(RuntimeError):c.Chain('conditional_full',0,self.clock).terminal()
    def test_phase_cannot_borrow_next_budget(self):
        ch=c.Chain('conditional_full',0,self.clock);ch.begin('preflight');self.now=280
        with self.assertRaises(RuntimeError):ch.finish(self.pre())
        with self.assertRaises(RuntimeError):ch.begin('candidate')
    def test_preflight_rejects_update_or_bad_contract(self):
        for key,value in [('accepted_hidden_updates',1),('admitted',False),('root_state_restored',False),('completed',False)]:
            with self.subTest(key=key):
                ch=c.Chain('conditional_full',0,self.clock);ch.begin('preflight');r=self.pre();r[key]=value
                with self.assertRaises(RuntimeError):ch.finish(r)
    def test_receipt_io_is_inside_window(self):
        def save(*args):self.now=280
        with self.assertRaisesRegex(RuntimeError,'receipt IO'):
            c.drive('preflight_only',0,{'preflight':self.pre},Mock(),save,self.clock)
    def test_scope_invalid(self):
        for scope in [None,'full','resume','']:
            with self.assertRaises(ValueError):c.allowed_phases(scope)
    def test_exact_authority_and_one_family_claim(self):
        p=self.root/'authority';row=dict(approved_by='human',activate_closed_package=True,approval_ref='human-message',family=c.FAMILY,run_id='r1',package_sha256='pkg',scope='preflight_only')
        c.write_json(p,row);sha=c.digest(p)
        self.assertEqual(c.validate_authority(row,sha,p,{'run_id':'r1'},'pkg'),('preflight',))
        for key,value in [('approved_by',None),('activate_closed_package',False),('approval_ref',''),('family','different'),('run_id','r2'),('package_sha256','wrong')]:
            r={**row,key:value};c.write_json(p,r)
            with self.subTest(key=key),self.assertRaises(RuntimeError):c.validate_authority(r,c.digest(p),p,{'run_id':'r1'},'pkg')
        c.write_json(p,row)
        with self.assertRaises(RuntimeError):c.validate_authority(row,'wrong',p,{'run_id':'r1'},'pkg')
        claim=self.root/'claim';c.consume_claim(claim,sha,'r1')
        with self.assertRaises(FileExistsError):c.consume_claim(claim,sha,'different-run-id')
    def test_package_tamper_extra_symlink(self):
        code=self.root/'code';code.mkdir();p=code/'a.py';p.write_text('pass\n')
        m={'files':[dict(path='code/a.py',bytes=p.stat().st_size,sha256=c.digest(p))]};self.assertTrue(c.verify_package(self.root,m))
        q=code/'extra';q.write_text('x')
        with self.assertRaises(RuntimeError):c.verify_package(self.root,m)
        q.unlink();p.write_text('fail\n')
        with self.assertRaises(RuntimeError):c.verify_package(self.root,m)
        p.unlink();p.symlink_to(self.root/'external')
        with self.assertRaises(RuntimeError):c.verify_package(self.root,m)
    def test_seal_and_full_retrieval_including_postexit(self):
        roots={k:self.root/k for k in ['run','archive']}
        for p in roots.values():p.mkdir();(p/'a').write_text('artificial')
        post=roots['run']/'tail';post.write_text('old')
        dest=roots['run']/'export.json';m=c.seal_outputs(roots,dest,'r','STOPPED',(('run','tail'),))
        post.write_text('final');outer=dict(run_id='r',export_manifest_sha256=c.digest(dest),postexit_files=[dict(root='run',path='tail',bytes=post.stat().st_size,sha256=c.digest(post))])
        self.assertFalse(c.verify_retrieval(m,roots,outer)['scientific_success_inferred'])
        with self.assertRaises(RuntimeError):c.verify_retrieval(m,roots)
        with self.assertRaisesRegex(RuntimeError,'manifest SHA'):c.verify_retrieval(m,roots,{**outer,'export_manifest_sha256':'wrong'})
        post.write_text('corrupt')
        with self.assertRaises(RuntimeError):c.verify_retrieval(m,roots,outer)
    def test_retrieval_extra_and_payload_tamper(self):
        root=self.root/'run';root.mkdir();(root/'a').write_text('x');m=c.seal_outputs({'run':root},root/'manifest','r','STOP')
        (root/'b').write_text('x')
        with self.assertRaises(RuntimeError):c.verify_retrieval(m,{'run':root})
        (root/'b').unlink();(root/'a').write_text('y')
        with self.assertRaises(RuntimeError):c.verify_retrieval(m,{'run':root})
    def test_closed_or_foreign_group_never_signalled(self):
        child=Mock(pid=123);child.poll.return_value=0
        with patch.object(c.os,'killpg') as kill:c.stop_owned(child);kill.assert_not_called()
        child.poll.return_value=None
        with patch.object(c.os,'getpgid',return_value=999),patch.object(c.os,'killpg') as kill:
            with self.assertRaises(RuntimeError):c.stop_owned(child)
            kill.assert_not_called()
    def test_telemetry_peaks_and_invalid_raw_readings(self):
        limits=dict(host_RSS=100,GPU_allocated=100,GPU_reserved=100,fresh_root_outputs=10000)
        rss=[30];cuda=[40,50];r=Reporter(self.root/'t',[self.root],limits,rss=lambda:rss[0],clock=self.clock)
        boot=r.sample();c.validate_telemetry(boot,0,limits,allow_boot=True)
        with self.assertRaises(RuntimeError):c.validate_telemetry(boot,0,limits)
        r.cuda=lambda:tuple(cuda);r.sample();rss[0]=20;cuda[:]=[10,20];row=r.sample()
        self.assertEqual((row['peak_rss_bytes'],row['peak_cuda_allocated'],row['peak_cuda_reserved']),(30,40,50))
        for key,value in [('monotonic',-11),('peak_rss_bytes',101),('peak_cuda_reserved',101),('peak_cuda_allocated',float('nan')),('error','failed')]:
            bad={**row,key:value}
            with self.subTest(key=key),self.assertRaises(RuntimeError):c.validate_telemetry(bad,0,limits)
        cuda[0]=float('nan');self.assertEqual(r.sample()['cuda_state'],'failed')
    def test_external_missing_telemetry_stops(self):
        a=self.root/'archive';a.mkdir();limits=dict(host_RSS=100,GPU_allocated=100,GPU_reserved=100,fresh_root_outputs=1000)
        with patch.object(launch,'process_tree',return_value=0),patch.object(launch.time,'monotonic',return_value=6):
            with self.assertRaisesRegex(RuntimeError,'absent'):launch.resource_check(Mock(pid=123),self.root,a,{'resource_limits_bytes':limits},0)
    def test_gpu_foreign_capacity_uuid_and_exact_admission(self):
        card={'producer':dict(gpu_uuid='GPU-x',gpu_index=5)}
        def call(gpu,apps,allowed=()):
            with patch.object(launch,'command',side_effect=[gpu,apps]):return launch.gpu_snapshot(card,allowed)
        self.assertEqual(call('5,GPU-x,30000,0','')['uuid'],'GPU-x')
        for gpu,apps in [('5,GPU-x,100,0',''),('5,GPU-x,30000,20',''),('4,GPU-x,30000,0',''),('5,GPU-x,30000,0','999,GPU-x,1')]:
            with self.subTest(gpu=gpu,apps=apps),self.assertRaises(RuntimeError):call(gpu,apps)
        self.assertEqual(len(call('5,GPU-x,100,90','123,GPU-x,10',{123})['owned']),1)
    def test_ready_handshake_fail_closed(self):
        with patch.object(c.select,'select',return_value=([],[],[])):
            with self.assertRaises(RuntimeError):c.wait_guard_ready(0)

class FakeSocket:
    def __init__(self):self.messages=[]
    def setblocking(self,v):pass
    def recv(self,n):
        if not self.messages:raise BlockingIOError
        return json.dumps(self.messages.pop(0)).encode()
    def close(self):pass

class WatchdogTests(unittest.TestCase):
    def run_guard(self,events,phase=(10,),exit_alive=False):
        now=[0.];sock=FakeSocket();events=iter(events);killed=[]
        def select(read,*args):
            if read==[10]:return ([10] if not exit_alive else [],[],[])
            if read==[11]:return ([],[],[])
            t,msgs,ready=next(events);now[0]=t;sock.messages.extend(msgs);return ready,[],[]
        with tempfile.TemporaryDirectory() as d,patch.object(dg.sys,'platform','linux'),patch.object(dg.os,'pidfd_open',side_effect=[10,11],create=True),patch.object(dg.os,'close'),patch.object(dg.socket,'socket',return_value=sock),patch.object(dg.select,'select',side_effect=select),patch.object(dg.time,'monotonic',side_effect=lambda:now[0]),patch.object(dg.signal,'pidfd_send_signal',side_effect=lambda fd,s:killed.append((fd,s)),create=True):
            dg.guard_loop(100,200,99,100,10,Path(d)/'receipt',phase_seconds=phase)
            return json.loads((Path(d)/'receipt').read_text()),killed
    def start(self,n=1,t=0):return dict(event='step_start',step=n,started=t)
    def done(self,n=1,t=1):return dict(event='step_done',step=n,finished=t)
    def test_timely_complete_exit(self):
        r,k=self.run_guard([(1,[self.start(),self.done()],[10])]);self.assertIsNone(r['reason']);self.assertEqual(k,[])
    def test_missing_phase_cannot_exit_zero(self):
        r,k=self.run_guard([(1,[self.start(),self.done()],[10])],phase=(10,20));self.assertIn('incomplete',r['reason']);self.assertEqual(k,[])
    def test_early_exit_pending(self):
        r,k=self.run_guard([(1,[self.start()],[10])]);self.assertIn('incomplete',r['reason'])
    def test_late_done_no_budget_borrow(self):
        r,k=self.run_guard([(10,[self.start(),self.done(t=10)],[])],exit_alive=True);self.assertIn('late step',r['reason']);self.assertTrue(all(fd==10 for fd,s in k))
    def test_phase_gap_idle_ceiling(self):
        r,k=self.run_guard([(1,[self.start(),self.done()],[]),(10,[],[])],exit_alive=True);self.assertIn('terminal exit',r['reason'])
    def test_next_phase_after_prior_ceiling_rejected(self):
        r,k=self.run_guard([(1,[self.start(),self.done()],[]),(10,[self.start(2,10)],[])],phase=(10,20),exit_alive=True);self.assertIn('prior phase',r['reason'])
    def test_duplicate_jump_extra_phase(self):
        for msgs in [[self.start(),self.start()],[self.start(2)],[self.start(),self.done(),self.start(2,1)]]:
            with self.subTest(msgs=msgs):r,k=self.run_guard([(1,msgs,[])],exit_alive=True);self.assertIsNotNone(r['reason'])
    def test_supervisor_death_stops_only_bound_pidfd(self):
        r,k=self.run_guard([(1,[],[11])],exit_alive=True);self.assertEqual(r['reason'],'supervisor exited');self.assertTrue(all(fd==10 for fd,s in k))
    def test_malformed_message(self):
        r,k=self.run_guard([(1,[{'event':'bogus'}],[])],exit_alive=True);self.assertEqual(r['reason'],'unknown deadline event')


class ManagedTests(unittest.TestCase):
    def scenario(self,mode):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';root.mkdir();archive=Path(tmp)/'archive';archive.mkdir();(root/'code').mkdir();(root/'package_manifest.json').write_text('{}')
            state=dict(ready=False,admitted=False,opened=False,stopped=[]);realwrite=os.write
            card=dict(run_id='r',producer={'gpu_uuid':'GPU-fixture'})
            class Proc:
                def __init__(self,cmd,**kw):
                    self.guard='deadline_guard.py' in cmd[2];self.pid=222 if self.guard else 111;self.returncode=None
                    if not self.guard:state['gate']=int(kw['env']['E011_START_FD'])+1
                    else:
                        state['ready']=True;realwrite(kw['pass_fds'][-1],b'1')
                def poll(self):
                    if self.guard:return 0 if state['opened'] and mode!='admit_fail' else None
                    if state['opened']:
                        self.returncode=0
                        c.write_json(root/'deadline_guard.json',dict(reason=None,last_step=1))
                        if mode!='missing_terminal':c.write_json(archive/'worker_terminal.json',dict(status='PREFLIGHT_ONLY_COMPLETE_NOT_SCIENTIFIC_SUCCESS'))
                        return 0
                    return None
                def wait(self,timeout=None):self.returncode=0;return 0
            def write(fd,data):
                if fd==state.get('gate'):
                    assert state['ready'] and state['admitted'];state['opened']=True
                return realwrite(fd,data)
            def admit():
                self.assertTrue(state['ready']);self.assertFalse(state['opened'])
                if mode=='admit_fail':raise RuntimeError('foreign selected GPU')
                state['admitted']=True;return {'GPU':'artificial'}
            realready=c.wait_guard_ready
            def ready(fd):
                if mode=='no_ready':raise RuntimeError('fixture no ready')
                realready(fd)
            def stop(p):state['stopped'].append(p.pid)
            with patch.dict(os.environ,{'E011_GLOBAL_GUARD_FD':'999'}),patch.object(launch.subprocess,'Popen',side_effect=Proc),patch.object(launch.os,'write',side_effect=write),patch.object(launch,'wait_guard_ready',side_effect=ready),patch.object(launch,'stop_owned',side_effect=stop),patch.object(launch.time,'monotonic',return_value=0):
                if mode=='success':
                    r=launch.managed(root,archive,card,{}, {'scope':'preflight_only'},0,admit);self.assertTrue(r['gate_opened'])
                else:
                    with self.assertRaises((RuntimeError,FileNotFoundError)):launch.managed(root,archive,card,{}, {'scope':'preflight_only'},0,admit)
            self.assertIn(111,state['stopped']);self.assertTrue(set(state['stopped'])<={111,222})
            if mode in ['admit_fail','no_ready']:self.assertFalse(state['opened'])
            return state
    def test_ready_then_admit_then_release(self):self.scenario('success')
    def test_no_guard_ready_never_releases(self):self.scenario('no_ready')
    def test_foreign_gpu_never_releases(self):self.scenario('admit_fail')
    def test_zero_exit_without_terminal_is_failure(self):self.scenario('missing_terminal')


class AdmissionAmendmentTests(unittest.TestCase):
    def card(self):return dict(producer=dict(gpu_uuid='GPU-x',gpu_index=5),admission_revision=dict(required_initial_free_VRAM_bytes=12*1024**3,minimum_free_after_actual_preflight_bytes=3*1024**3))
    def snap(self,gpu,apps='',card=None):
        with patch.object(launch,'command',side_effect=[gpu,apps]):return launch.gpu_snapshot(card or self.card())
    def test_real_4090_capacity_accepts_revised_admission(self):
        r=self.snap('5,GPU-x,24077,0,24564');self.assertEqual(r['required_initial_free_bytes'],12*1024**3)
    def test_original_admission_impossible_on_4090(self):
        with self.assertRaisesRegex(RuntimeError,'exceeds physical'):self.snap('5,GPU-x,24077,0,24564',card={'producer':self.card()['producer']})
    def test_revised_insufficient_free_or_unknown_total_stops(self):
        for gpu in ['5,GPU-x,12287,0,24564','5,GPU-x,24077,0']:
            with self.subTest(gpu=gpu),self.assertRaises(RuntimeError):self.snap(gpu)
    def test_revised_does_not_admit_foreign_process(self):
        with self.assertRaisesRegex(RuntimeError,'foreign'):self.snap('5,GPU-x,24077,0,24564','111,GPU-x,1')
    def test_actual_preflight_requires_three_GiB_headroom(self):
        from science import verify_preflight_memory
        fake=Mock();fake.cuda.mem_get_info.return_value=(3*1024**3,24*1024**3)
        self.assertTrue(verify_preflight_memory(self.card(),fake)['amended_memory_check'])
        for free in [3*1024**3-1, -1, float('nan')]:
            fake.cuda.mem_get_info.return_value=(free,24*1024**3)
            with self.subTest(free=free),self.assertRaises(RuntimeError):verify_preflight_memory(self.card(),fake)

    def test_revised_authority_requires_explicit_first_stop_amendment(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'authority';card=self.card();card['run_id']='r';card['admission_revision'].update(prior_package_sha256='oldpkg',prior_stop_receipt_sha256='oldstop')
            row=dict(approved_by='human',activate_closed_package=True,approval_ref='new explicit approval',family=c.FAMILY,run_id='r',package_sha256='newpkg',scope='conditional_full')
            c.write_json(p,row)
            with self.assertRaisesRegex(RuntimeError,'first-stop amendment'):c.validate_authority(row,c.digest(p),p,card,'newpkg')
            row.update(amends_first_stop_package_sha256='oldpkg',amends_first_stop_receipt_sha256='oldstop');c.write_json(p,row)
            self.assertEqual(c.validate_authority(row,c.digest(p),p,card,'newpkg'),c.PHASES)


    def test_gpu_nonfinite_and_bad_ranges_fail_closed(self):
        for gpu in ['5,GPU-x,nan,0,24564','5,GPU-x,24077,nan,24564','5,GPU-x,24077,0,nan','5,GPU-x,24077,0,inf','5,GPU-x,-1,0,24564','5,GPU-x,25000,0,24564','5,GPU-x,24077,101,24564','5,GPU-x,0,0,0']:
            with self.subTest(gpu=gpu),self.assertRaisesRegex(RuntimeError,'telemetry'):self.snap(gpu)
    def test_failed_postpreflight_memory_is_recorded_before_stop(self):
        from science import verify_preflight_memory
        fake=Mock();rows=[];fake.cuda.mem_get_info.return_value=(2*1024**3,24*1024**3)
        with self.assertRaises(RuntimeError):verify_preflight_memory(self.card(),fake,rows.append)
        self.assertFalse(rows[-1]['passed']);self.assertEqual(rows[-1]['free_bytes'],2*1024**3)
        fake.cuda.mem_get_info.return_value=(float('nan'),24*1024**3)
        with self.assertRaises(RuntimeError):verify_preflight_memory(self.card(),fake,rows.append)
        self.assertFalse(rows[-1]['capacity_valid']);self.assertEqual(rows[-1]['free_bytes'],'nan')

if __name__=='__main__':unittest.main()
