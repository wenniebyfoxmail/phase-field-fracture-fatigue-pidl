"""Linux portability checks: manual bytes/mocks only, no fit/model/GPU/real GT."""
import copy,hashlib,importlib.util,io,json,os,signal,sys,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
HERE=Path(__file__).resolve().parents[2]/'scripts/pavetrack_qualified_spatial_selector';sys.path.insert(0,str(HERE))
import e029_support as c
import e029_guard as guard
import e029_migration as migration
import e029_linux_environment as environment
import e029_linux_process as managed
import e029_linux_bootstrap as bootstrap
import producer_taobo as wrapper
spec=importlib.util.spec_from_file_location('e029_linux_test_run',HERE/'run.py');run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)

class LinuxChecks(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()
    def test_frozen_science_equal(self):
        old,_=c.config();new,_=c.config('taobo')
        for k in ['locations','held_groups','excluded_locations','qualification_reused','primary_locations','arms','main','threshold','foreground_comparison','shift','gates','ridge','heads','policy','locality','primary','GT_access_contract','protocol','proposed_run_id','checkpoint','tile','counts']:self.assertEqual(new[k],old[k],k)
        self.assertIsNone(new['budget']['wall_seconds']);self.assertIsNone(new['budget']['total_task_wall_seconds']);self.assertIs(new['execution_enabled'],False)
        for k in ['RSS_bytes','GPU_allocated_bytes','GPU_reserved_bytes','output_bytes','archive_bytes']:self.assertIsNone(new['budget'][k])
    def test_no_wall_authority_strict(self):
        plan,_=c.config('taobo');a=dict(run_id='S01-E029-R001',reviewed_commit='a',source_manifest_sha256='b',execute_once=True,wall_seconds=None,GPU_uuid=plan['producer']['gpu_uuid'])
        run.authority(a,'b','a',plan);wrapper.authorization(a,plan,'a','b')
        for change in [dict(wall_seconds=3600),dict(wall_seconds=False),dict(GPU_uuid='other'),dict(execute_once=1),dict(extra=True)]:
            with self.assertRaises(PermissionError):run.authority(dict(a,**change),'b','a',plan)
            with self.assertRaises(PermissionError):wrapper.authorization(dict(a,**change),plan,'a','b')
    def test_windows_logical_identity_physical_resolver(self):
        cfg,_=c.config('taobo');rec=dict(image_id='image.jpg',prepared_image=cfg['logical_source_image_root']+'\\image.jpg')
        before=copy.deepcopy(rec);p=c.image_path(rec,cfg);self.assertEqual(p,Path(cfg['linux_paths']['images'])/'image.jpg');self.assertEqual(rec,before)
        for bad in ['..\\image.jpg','other.jpg','/etc/passwd']:
            with self.assertRaises(ValueError):c.image_path(dict(rec,prepared_image=bad),cfg)
    def test_worker_memory_no_proc_tree_scan_no_wall(self):
        cfg,_=c.config('taobo');cfg['budget']['RSS_bytes']=4*1024**3;g=guard.Guard(cfg,self.p,start=-10**12);g.self_only=True;g.process=Mock(pid=123);g.process.memory_info.return_value=Mock(rss=100,peak_wset=100);g.process.children.side_effect=AssertionError('global /proc traversal')
        g.check();g.process.children.assert_not_called()
        g.process.memory_info.return_value=Mock(rss=5*1024**3,peak_wset=5*1024**3)
        with self.assertRaises(MemoryError):g.check()
    def test_selected_GPU_other_jobs_allowed_only_own_card_free(self):
        cfg,_=c.config('taobo');uuid=cfg['producer']['gpu_uuid'];ps=Mock();ps.cpu_percent.return_value=10;ps.virtual_memory.return_value.available=16*1024**3;ps.disk_usage.return_value.free=64*1024**3
        inventory=f'5, {uuid}, NVIDIA GeForce RTX 4090, 24000, 0';other='GPU-OTHER, 42'
        with patch.object(environment,'command',side_effect=[inventory,other]):self.assertEqual(environment.admission(cfg,ps)['physical_GPU'][0],'5')
        for inv,compute in [(inventory,uuid+', 42'),(inventory[:-1]+'1',other),(inventory.replace(uuid,'other'),other)]:
            with patch.object(environment,'command',side_effect=[inv,compute]):
                with self.assertRaises((RuntimeError,ValueError)):environment.admission(cfg,ps)
        ps.cpu_percent.return_value=79
        with patch.object(environment,'command',side_effect=[inventory,other]):
            with self.assertRaises(RuntimeError):environment.admission(cfg,ps)
    def fixture(self):
        src=self.p/'a';src.write_bytes(b'GT_SENTINEL_MANUAL_BYTES');im=self.p/'b';im.write_bytes(b'NOT_REAL_RGB')
        rows=[dict(role=role,relative=name,source_windows=str(p),sha256=migration.sha(p),bytes=p.stat().st_size) for role,name,p in [('input','metadata.json',src),('image','images/a.jpg',im)]]
        cat=self.p/'private.json';cat.write_text(json.dumps(dict(protocol='S01-E029-taobo-private-v1',files=rows)));return cat
    def test_exact_private_round_trip_no_decoding(self):
        cat=self.fixture();a=self.p/'private.tar.gz';rec=migration.export(cat,a,1,1);dest=self.p/'received';migration.receive(a,dest,rec['catalogue_sha256'],1,1)
        self.assertEqual((dest/'metadata.json').read_bytes(),b'GT_SENTINEL_MANUAL_BYTES');self.assertEqual(rec['GT_decodes'],0)
        with self.assertRaises(FileExistsError):migration.export(cat,a,1,1)
        with self.assertRaises(FileExistsError):migration.receive(a,dest,rec['catalogue_sha256'],1,1)
    def test_private_changed_bytes_stops(self):
        cat=self.fixture();(self.p/'a').write_bytes(b'changed')
        with self.assertRaises(ValueError):migration.export(cat,self.p/'private.tar.gz',1,1)
        self.assertTrue((self.p/'private.tar.gz.part').exists())
    def test_private_extra_member_and_CRC_stops(self):
        cat=self.fixture();a=self.p/'private.tar.gz';rec=migration.export(cat,a,1,1)
        data=bytearray(a.read_bytes());data[-8]^=1;a.write_bytes(data)
        with self.assertRaises(Exception):migration.receive(a,self.p/'dest',rec['catalogue_sha256'],1,1)
        self.assertFalse((self.p/'dest').exists())
    def test_private_traversal_duplicate_reject(self):
        cat=self.fixture();v=json.loads(cat.read_text());v['files'][0]['relative']='../escape'
        with self.assertRaises(ValueError):migration.validate_catalogue(v,1,1)
        v['files'][0]['relative']=v['files'][1]['relative']
        with self.assertRaises(ValueError):migration.validate_catalogue(v,1,1)
    def test_python_source_links_rejected(self):
        p=self.p/'bad.tar'
        with tarfile.open(p,'w') as t:
            m=tarfile.TarInfo('Python-3.12.14/link');m.type=tarfile.SYMTYPE;m.linkname='/etc/passwd';t.addfile(m)
        with self.assertRaises(ValueError):bootstrap.source_extract(p,self.p/'extract',100)
    def test_artifact_wrong_origin_and_hash(self):
        spec={'origin_allowlist':['www.python.org']};rec=dict(url='https://evil.example/a',filename='a',sha256='0'*64)
        with self.assertRaises(ValueError):bootstrap.artifact(rec,self.p/'a',spec)
        response=io.BytesIO(b'manual');response.url='https://www.python.org/a'
        with patch.object(bootstrap.urllib.request,'urlopen',return_value=response):
            with self.assertRaises(ValueError):bootstrap.artifact(dict(rec,url=response.url),self.p/'a',spec)
    def process(self,pid=10,birth=1):
        p=Mock(pid=pid);p.create_time.return_value=birth;p.uids.return_value.real=os.getuid();p.cmdline.return_value=['python',str(self.p/'run')];p.cwd.return_value=str(self.p);p.parents.return_value=[Mock(pid=1)];p.children.return_value=[];p.status.return_value='running';return p
    def test_managed_identity_refuses_unowned_or_reused(self):
        p=self.process();saved=managed.identity(p);self.assertTrue(managed.matches(p,saved));p.create_time.return_value=2;self.assertFalse(managed.matches(p,saved));p.parents.return_value=[]
        with self.assertRaises(PermissionError):managed.capture(p,self.p/'run',1)
    def test_owned_terminate_no_foreign_signal(self):
        import psutil
        process=self.process();handle=Mock(pid=10)
        process.send_signal.side_effect=lambda sig:process.status.configure_mock(return_value=psutil.STATUS_ZOMBIE)
        with patch.object(os,'getpgid',return_value=10),patch.object(os,'getsid',return_value=10):
            managed.terminate_child(handle,self.p/'run',1,Mock(Process=Mock(return_value=process),NoSuchProcess=psutil.NoSuchProcess,STATUS_ZOMBIE=psutil.STATUS_ZOMBIE))
        process.send_signal.assert_called_once_with(signal.SIGTERM)
    def test_outer_persistence_failure_still_terminates(self):
        import e029_system_proc as psutil
        cfg,_=c.config('taobo');cfg['linux_paths']['root']=str(self.p);logs=self.p/'logs';logs.mkdir();child=Mock(pid=10);child.poll.return_value=None;proc=self.process();proc.send_signal.side_effect=lambda sig:proc.status.configure_mock(return_value=psutil.STATUS_ZOMBIE)
        with patch.object(wrapper.subprocess,'Popen',return_value=child),patch.object(wrapper,'write',side_effect=OSError('disk full')),patch.object(psutil,'Process',return_value=proc),patch.object(psutil,'process_iter',return_value=[proc]),patch.object(os,'getsid',return_value=10):
            with self.assertRaises(OSError):wrapper.invoke(['python',str(self.p/'run')],'mock',cfg,logs,{})
        proc.send_signal.assert_called_once_with(signal.SIGTERM)
    def test_runtime_spec_Linux_deps_hashes_and_no_install_on_import(self):
        spec=json.loads((c.DOC/'taobo_runtime_spec.json').read_text());names={r['name'].lower() for r in spec['wheels']}
        self.assertTrue({'torch','torchvision','nvidia-nccl-cu12','nvidia-cudnn-cu12','nvidia-cublas-cu12','triton'}<=names)
        self.assertTrue(all(len(r['sha256'])==64 and r['url'].startswith('https://') for r in spec['wheels']));self.assertEqual(spec['python']['version'],'3.12.14');self.assertNotIn('torch',sys.modules)
    def test_self_proc_and_font_capabilities_not_global(self):
        from e029_permissions import Files
        own=self.p/'proc/123/statm';other=self.p/'proc/456/statm';font=self.p/'runtime/font.ttf';caps=Files([own,font],[],[])
        self.assertTrue(caps.allow(own));self.assertTrue(caps.allow(font));self.assertFalse(caps.allow(other));self.assertFalse(caps.allow(self.p/'private/metadata.json'));self.assertFalse(caps.allow(self.p/'runtime/unlisted.py'))
    def test_clean_environment_ignores_inherited_injection(self):
        poison=dict(PATH='/evil',LD_PRELOAD='/evil.so',LD_LIBRARY_PATH='/evil',PYTHONPATH='/evil',PIP_INDEX_URL='https://evil',CFLAGS='-fplugin=evil',HOME='/evil')
        with patch.dict(os.environ,poison):env=wrapper.execution_environment(self.p)
        self.assertEqual(env['PATH'],'/usr/bin:/bin');self.assertEqual(env['CFLAGS'],'-O2');self.assertEqual(env['PIP_CONFIG_FILE'],'/dev/null')
        for key in ['LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH','PIP_INDEX_URL','HOME']:self.assertNotIn(key,env)
    def runtime_fixture(self):
        import e029_runtime_exec as seal
        root=self.p/'runtime';root.mkdir();f=root/'manual';f.write_bytes(b'manual sealed bytes');lock=self.p/'lock.json'
        lock.write_text(json.dumps(dict(state='built_from_frozen_artifacts',prefix=str(root),files={'manual':seal.sha(f)})))
        return seal,root,f,lock,seal.sha(lock)
    def test_runtime_trusted_seal_rejects_file_and_self_rehash(self):
        seal,root,f,lock,expected=self.runtime_fixture();seal.verify(lock,expected)
        f.write_bytes(b'changed')
        with self.assertRaises(ValueError):seal.verify(lock,expected)
        value=json.loads(lock.read_text());value['files']['manual']=seal.sha(f);lock.write_text(json.dumps(value))
        with self.assertRaises(ValueError):seal.verify(lock,expected)
    def test_runtime_parent_loss_and_extra_inventory_stop(self):
        seal,root,f,lock,expected=self.runtime_fixture()
        with patch.object(os,'getppid',return_value=2):
            with self.assertRaises(RuntimeError):seal.verify(lock,expected,parent=1)
        (root/'extra').write_bytes(b'extra')
        with self.assertRaises(ValueError):seal.verify(lock,expected)
    def test_lifeline_parent_birth_and_reparenting(self):
        import e029_parent_watch as watch
        ps=Mock();ps.Process.return_value.create_time.return_value=11
        with patch.object(os,'getppid',return_value=7):
            self.assertTrue(watch.parent_alive(7,11,ps));self.assertFalse(watch.parent_alive(7,12,ps))
        with patch.object(os,'getppid',return_value=1):self.assertFalse(watch.parent_alive(7,11,ps))
    def test_lifeline_receipt_failure_still_signals_only_owned_group(self):
        import e029_parent_watch as watch
        with patch.object(os,'getpid',return_value=7),patch.object(os,'getpgid',return_value=7),patch.object(os,'getsid',return_value=7),patch.object(Path,'write_text',side_effect=OSError('disk full')),patch.object(os,'write'),patch.object(signal,'signal'),patch.object(os,'killpg') as kill,patch.object(watch.time,'sleep'):
            watch.stop_group(self.p/'note','parent died')
        self.assertEqual(kill.call_args_list,[unittest.mock.call(7,signal.SIGTERM),unittest.mock.call(7,signal.SIGKILL)])
        with patch.object(os,'getpid',return_value=7),patch.object(os,'killpg') as kill:
            with self.assertRaises(PermissionError):watch.stop_group(self.p/'note','bad group',8)
            kill.assert_not_called()
    def test_lifeline_long_payload_parent_death(self):
        import e029_parent_watch as watch
        child=Mock();child.poll.return_value=None
        argv=['watch','--parent','9','--birth','11','--note',str(self.p/'note'),'--','compiler','manual']
        with patch.object(sys,'argv',argv),patch.object(os,'getpid',return_value=7),patch.object(os,'getsid',return_value=7),patch.object(os,'getpgid',return_value=7),patch.object(signal,'signal'),patch('e029_system_proc.Process') as proc,patch.object(watch,'parent_alive',side_effect=[True,False]),patch.object(watch.subprocess,'Popen',return_value=child) as popen,patch.object(watch,'stop_group',side_effect=RuntimeError('owned group stopped')) as stop:
            proc.return_value.create_time.return_value=10
            with self.assertRaisesRegex(RuntimeError,'owned group stopped'):watch.main()
            stop.assert_called_once();self.assertFalse(popen.call_args.kwargs['start_new_session'])
    def test_proc_stat_spaces_and_PID_reuse(self):
        import e029_system_proc as proc
        fields=['R','2','3','4']+['0']*15+['123','0','5']
        raw='7 (a tricky ) process) '+' '.join(fields)
        with patch.object(Path,'read_text',return_value=raw),patch.object(os,'sysconf',return_value=4096):
            self.assertEqual(proc.stat(7),dict(state='R',ppid=2,group=3,session=4,birth=123,rss=20480))
        with patch.object(proc,'stat',side_effect=[dict(birth=1),dict(birth=2)]):
            p=proc.Process(7)
            with self.assertRaises(proc.NoSuchProcess):p.create_time()
    def test_proc_cpu_guest_not_double_counted(self):
        import e029_system_proc as proc
        with patch.object(Path,'read_text',side_effect=['cpu 10 0 0 90 0 0 0 0 5 0','cpu 30 0 0 170 0 0 0 0 15 0']),patch.object(proc.time,'sleep'):
            self.assertEqual(proc.cpu_percent(),20.)
    def test_controller_chain_rejects_forged_or_reused_wrapper(self):
        import e029_system_proc as proc
        claim=dict(pid=9,wrapper_birth=100);ps=Mock();watch=Mock();watch.create_time.return_value=200;watch.ppid.return_value=9;outer=Mock();outer.create_time.return_value=100;ps.Process.side_effect=lambda pid:{7:watch,9:outer}[pid]
        with patch.object(os,'getppid',return_value=7):
            proc.approved_chain(claim,7,200,ps)
            outer.create_time.return_value=101
            with self.assertRaises(PermissionError):proc.approved_chain(claim,7,200,ps)
            outer.create_time.return_value=100;watch.ppid.return_value=8
            with self.assertRaises(PermissionError):proc.approved_chain(claim,7,200,ps)
        with patch.object(os,'getppid',return_value=1):
            with self.assertRaises(PermissionError):proc.approved_chain(claim,7,200,ps)
    def test_serial_install_and_explicit_no_source_bytecode(self):
        s=(HERE/'e029_linux_bootstrap.py').read_text()
        self.assertIn("['make','-j1','COMPILEALL_OPTS=-j1','install']",s)
        self.assertIn("'-I','-B'",s)
        self.assertIn('python3 -I -B ',(HERE/'producer_taobo.sh').read_text())
    def test_real_worker_entry_uses_controller_chain_without_approval_argument(self):
        from types import SimpleNamespace
        import e029_system_proc as proc
        cfg,base=c.config('taobo');args=SimpleNamespace(run=self.p/'run',request=self.p/'request',role='bank',fold=None,reviewed_commit='commit',approval_file=None)
        args.run.mkdir();approval=dict(run_id='S01-E029-R001',reviewed_commit='commit',source_manifest_sha256='manifest',execute_once=True,wall_seconds=None,GPU_uuid=cfg['producer']['gpu_uuid'])
        claim=dict(pid=9,wrapper_birth=100,commit='commit',manifest='manifest',approval_sha256='sha')
        launch=dict(controller_birth=200,lifeline_pid=8,lifeline_birth=150,approval_value=approval,approval_sha256='sha')
        req=dict(role='bank',fold=None,manifest='manifest',run_id='S01-E029-R001',input_freezes={});control=dict(controller_pid=7,controller_birth=200,expected=req)
        values={str(args.run/'launch.json'):launch,str(args.run/'control.json'):control,str(args.request):req,str(cfg['linux_paths']['launch_claim']):claim}
        processes={}
        for pid,birth,parent in [(7,200,8),(8,150,9),(9,100,1)]:
            processes[pid]=Mock();processes[pid].create_time.return_value=birth;processes[pid].ppid.return_value=parent
        live=Mock();live.parents.return_value=[Mock(pid=7),Mock(pid=8),Mock(pid=9)]
        with patch.dict(os.environ,dict(E029_PARENT_PID='7',E029_PARENT_BIRTH='200')),patch.object(os,'getppid',return_value=7),patch.object(proc,'Process',side_effect=lambda pid=None:processes[pid]),patch.object(c,'read',side_effect=lambda p:values[str(p)]),patch.object(c,'environment',return_value=Mock()),patch('psutil.Process',return_value=live),patch.object(run,'read_caps',side_effect=RuntimeError('reached capabilities before phase')):
            with self.assertRaisesRegex(RuntimeError,'reached capabilities before phase'):run.worker(args,cfg,base,{}, {},'manifest')
            processes[7].create_time.return_value=201
            with self.assertRaises(PermissionError):run.worker(args,cfg,base,{}, {},'manifest')
        self.assertNotIn('torch',sys.modules)
    def test_science_files_not_modified(self):
        # Reviewed read-only mathematical mechanism remains original, including fixed overlap.
        source=json.loads((c.DOC/'source_manifest.json').read_text())['files']
        for rel in source:
            if rel.startswith('scripts/') and 'pavetrack_qualified_spatial_selector/' not in rel:
                self.assertEqual(c.sha(c.ROOT/rel),source[rel],rel)
if __name__=='__main__':unittest.main()
