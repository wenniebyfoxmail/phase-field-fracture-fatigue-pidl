"""Local hand-built/mock path checks only: no fit, model, private GT or OOF run."""
import copy,hashlib,importlib.util,json,os,subprocess,sys,tarfile,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch,Mock
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'scripts/pavetrack_qualified_spatial_selector';sys.path.insert(0,str(HERE))
import e029_support as c
import e029_inputs as inputs
import e029_phases as phases
import e029_permissions as permissions
spec=importlib.util.spec_from_file_location('e029_controller',HERE/'run.py');run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
spec=importlib.util.spec_from_file_location('e029_pack',HERE/'pack.py');pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
spec=importlib.util.spec_from_file_location('e029_receive',HERE/'receive.py');receive=importlib.util.module_from_spec(spec);spec.loader.exec_module(receive)

class ProductionChecks(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_no_torch_import(self):self.assertNotIn('torch',sys.modules)
    def test_package_disabled(self):
        plan,legacy=c.config();self.assertIs(plan['execution_enabled'],False);self.assertEqual(plan['budget']['total_task_wall_seconds'],3600);self.assertEqual(plan['budget']['wall_seconds']+plan['budget']['packaging_reserve_seconds'],3600)
    def test_authority_must_be_exact(self):
        plan,_=c.config();good=dict(run_id='S01-E029-R001',reviewed_commit='abc',source_manifest_sha256='def',execute_once=True,wall_seconds=3600,GPU_uuid=plan['producer']['gpu_uuid'])
        run.authority(good,'def','abc',plan)
        for change in [dict(execute_once=False),dict(reviewed_commit='other'),dict(wall_seconds=3601),dict(run_id='S01-E028-R002'),dict(extra='GT')]:
            with self.assertRaises(PermissionError):run.authority(dict(good,**change),'def','abc',plan)
    def test_phase_order_no_retry(self):
        done=[]
        for role,k in run.ORDER:done=run.transition(done,role,k)
        self.assertEqual(len(done),10)
        for d,r,k in [([], 'fit',0),(done,'bank',None),([('bank',None)],'evaluate',None)]:
            with self.assertRaises(PermissionError):run.transition(d,r,k)
    def test_request_fold_arm_cache_identity(self):
        q=dict(role='fit',fold=0,manifest='abc',run_id='S01-E029-R001',input_freezes={});permissions.request(q,'fit',0)
        for change in [dict(fold=1),dict(fold=True),dict(run_id='R002'),dict(targets=[])]:
            with self.assertRaises(ValueError):permissions.request(dict(q,**change),'fit',0)
    def test_numeric_export_drops_GT_and_policies(self):
        heads={n:dict(coefficients=[0],columns=[],verified=True,target='GT_SENTINEL',strata=[dict(GT='secret')]) for n in ['Q','N','A']}
        exported=c.numeric_model(dict(heads=heads,threshold='abstain',targets=['secret'],policies=['secret']))
        self.assertEqual(set(exported),{'heads','threshold'});self.assertNotIn('secret',json.dumps(exported));self.assertNotIn('GT_SENTINEL',json.dumps(exported))
    def test_inference_payload_rejects_cross_fold_and_GT(self):
        v=dict(heads={n:dict(coefficients=[0],columns=[],verified=True) for n in ['Q','N','A']},threshold='abstain',fold=0,arm='aligned',held_locations=['24'],source_digest='x')
        permissions.inference_payload(v,0,'aligned',['24'],'x')
        for change in [dict(fold=1),dict(arm='half_shift'),dict(source_digest='other'),dict(targets=['GT_SENTINEL'])]:
            with self.assertRaises(ValueError):permissions.inference_payload(dict(v,**change),0,'aligned',['24'],'x')
    def test_fit_member_capability(self):
        for k in range(3):
            members=inputs.members('fit',k);self.assertEqual(len(members),3)
            self.assertTrue(all(str(k) in n for n in members));self.assertNotIn('supervision_fold_'+str((k+1)%3)+'.json',members)
        for role in ['held','spatial','evaluate']:
            with self.assertRaises(PermissionError):inputs.members(role,0)
    def test_zip_other_fold_sentinel_never_decoded(self):
        z=self.p/'synthetic.zip';raw={n:b'{"ok":true}' for n in inputs.members('fit',0)};raw['supervision_fold_1.json']=b'GT_SENTINEL_NOT_JSON'
        with zipfile.ZipFile(z,'w') as t:
            for n,b in raw.items():t.writestr(n,b)
        lock=dict(source_files={n:hashlib.sha256(b).hexdigest() for n,b in raw.items()})
        selected=inputs.zip_values(z,lock,'fit',0);self.assertEqual(set(selected),inputs.members('fit',0));self.assertTrue(all(json.loads(v)=={'ok':True} for v in selected.values()))
        with self.assertRaises(PermissionError):inputs.zip_values(z,lock,'held',0)
    def test_scoped_metadata_ignores_held_sentinel(self):
        metadata=self.p/'synthetic_metadata.json'
        # Only allowed row is decoded; other location payload is deliberately not a GT schema.
        metadata.write_text(json.dumps(dict(records=[dict(image_id='a',reid='fit',split='train',width=1920,height=1080,crack_boxes_xyxy=[]),dict(image_id='b',reid='held',crack_boxes_xyxy='GT_SENTINEL')])))
        seen=[]
        def decoder(original):
            def call(span,*args,**kw):
                value=original(span,*args,**kw)
                if isinstance(value,dict):seen.append(value.get('image_id'))
                if isinstance(value,dict) and value.get('reid')=='held':raise AssertionError('held GT decoded')
                return value
            return call
        got=inputs.targets(metadata,['fit'],{'a':'fit','b':'held'},Mock(check=lambda:None),decoder);self.assertEqual(got,{'a':[]});self.assertNotIn('b',seen)
    def test_held_file_capabilities_deny_labels_and_other_fold(self):
        paths={'metadata':str(self.p/'GT.json'),'E017_zip':str(self.p/'labels.zip')};local,extra=run.read_caps('held',0,self.p,paths)
        caps=permissions.Files(local+extra,[self.p/'held_0'],[HERE])
        self.assertFalse(caps.allow(paths['metadata']));self.assertFalse(caps.allow(paths['E017_zip']))
        self.assertFalse(caps.allow(self.p/'fit_1/aligned_inference.json'));self.assertFalse(caps.allow(self.p/'fit_0/aligned_FIT.json'))
        self.assertTrue(caps.allow(self.p/'fit_0/aligned_inference.json'))
    def test_real_audit_hook_blocks_sentinel_read(self):
        good=self.p/'numeric.json';bad=self.p/'GT_SENTINEL.json';good.write_text('{}');bad.write_text('secret')
        code="import sys;sys.path.insert(0,sys.argv[1]);from e029_permissions import Files;f=Files([sys.argv[2]],[],[sys.base_prefix]);sys.addaudithook(f.hook);assert open(sys.argv[2]).read()=='{}';\ntry:open(sys.argv[3]).read()\nexcept PermissionError:pass\nelse:raise AssertionError('GT leaked')"
        r=subprocess.run([sys.executable,'-c',code,str(HERE),str(good),str(bad)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
    def test_freeze_tamper_rehash_cannot_rescue(self):
        f=self.p/'numeric.json';f.write_text('{}');trusted=run.barrier(self.p,['numeric.json'],'models_freeze');run.verify_barrier(self.p,'models_freeze',trusted)
        f.write_text('{"changed":1}')
        with self.assertRaises(ValueError):run.verify_barrier(self.p,'models_freeze',trusted)
        run.barrier(self.p,['numeric.json'],'models_freeze')
        with self.assertRaises(ValueError):run.verify_barrier(self.p,'models_freeze',trusted)
    def test_mock_held_has_no_GT_or_fit_calls(self):
        plan,cfg=c.config();r=self.p;model=dict(heads={n:dict(coefficients=[0],columns=[],verified=True) for n in ['Q','N','A']},threshold='abstain',fold=0,held_locations=cfg['held_groups'][0],source_digest='digest')
        c.write(r/'bank/bank.json',dict(originals=[],candidates=[],image_locations={},images={},contexts=[],original_digest='x'));c.write(r/'spatial/descriptors.json',[])
        for arm in c.adapter.ARMS:c.write(r/f'fit_0/{arm}_inference.json',dict(model,arm=arm))
        b1=dict(model,arm='saved_E018_geometry');c.write(r/'bank/B1.json',dict(models=[b1],folds=[dict(source_keys=[],rows=[],features_and_predictions=[])]))
        out=r/'held_0';out.mkdir()
        with patch.object(c,'context',return_value=({},[])),patch.object(c,'prediction_rows',return_value=[]),patch.object(c,'choose',return_value=([],[])),patch.object(c.learning,'fit',side_effect=AssertionError('fit called')),patch.object(inputs,'targets',side_effect=AssertionError('GT called')),patch.object(inputs,'zip_values',side_effect=AssertionError('label ZIP called')):
            phases.held({},dict(bundle_identity='digest'),plan,cfg,r,out,Mock(take=lambda *a:None),0)
        self.assertTrue((out/'aligned.json').exists());self.assertTrue((out/'saved_E018_geometry.json').exists())
    def test_fit_label_permutation_does_not_reach_inference_export(self):
        # Mock coefficients, never fit: GT placement cannot survive strict export schema.
        model=dict(heads={n:dict(coefficients=[.1],columns=[],verified=True,labels=[1,0]) for n in ['Q','N','A']},threshold=0)
        a=c.numeric_model(model)
        for h in model['heads'].values():h['labels'].reverse()
        self.assertEqual(a,c.numeric_model(model))
    def test_pack_receive_success_and_stopped_both_no_scores(self):
        for state in ['completed','stopped']:
            base=self.p/state;base.mkdir();r=base/'run';r.mkdir();logs=base/'logs';logs.mkdir();c.write(r/'status.json',dict(state=state,science=None));m=base/'manifest.json';m.write_text('{}')
            archive=base/'fixed.tar.gz';rec=pack.pack(r,logs,m,archive,time.monotonic()+10)
            got=receive.receive(archive,base/'received',rec['sha256'],rec['bytes']);self.assertEqual(got['retrieval'],'verified');self.assertEqual(json.loads((base/'received/run/status.json').read_text())['science'],None)
    def test_reception_rejects_unsafe_tar(self):
        import io
        archive=self.p/'bad.tar.gz'
        with tarfile.open(archive,'w:gz') as t:
            raw=b'x';info=tarfile.TarInfo('../outside');info.size=1;t.addfile(info,io.BytesIO(raw))
        with self.assertRaises(ValueError):receive.receive(archive,self.p/'receive',receive.sha(archive),archive.stat().st_size)
    def test_pack_does_not_overwrite_or_retry(self):
        r=self.p/'r';r.mkdir();logs=self.p/'l';logs.mkdir();m=self.p/'m';m.write_text('{}');out=self.p/'p.tar.gz';out.write_bytes(b'prior')
        with self.assertRaises(FileExistsError):pack.pack(r,logs,m,out,time.monotonic()+10)
        self.assertEqual(out.read_bytes(),b'prior')
    def test_utility_decision_positive_tie_negative_and_old_loss(self):
        def table(s,m=0,b=0,lost=0):
            v={a:dict(net_GT=n,lost_old=0) for a,n in [('E003',0),('saved_E018_geometry',b),('aligned',s),('half_shift',m)]}
            return dict(pooled9=v,pooled12=dict(v,aligned=dict(net_GT=s,lost_old=lost)))
        self.assertEqual(phases.utility_decision(table(1))['scientific_verdict'],'supports')
        for t in [table(0),table(-1),table(1,1),table(2,0,2),table(1,lost=1)]:self.assertEqual(phases.utility_decision(t)['scientific_verdict'],'negative')
    def test_strict_inventory_rejects_missing_or_extra_science(self):
        out=self.p/'fit';out.mkdir()
        wanted={'resource.json',*[a+s for a in c.adapter.ARMS for s in ['_FIT.json','_inference.json']]}
        for name in wanted:(out/name).write_text('{}')
        self.assertEqual(run.phase_inventory(out,'fit',0),wanted)
        (out/'hidden_GT.json').write_text('{}')
        with self.assertRaises(ValueError):run.phase_inventory(out,'fit',0)
    def test_model_manifest_and_arm_are_part_of_cache_key(self):
        base=dict(heads={n:dict(coefficients=[0],columns=[],verified=True) for n in ['Q','N','A']},threshold='abstain',fold=1,arm='half_shift',held_locations=['95'],source_digest='sourceA')
        permissions.inference_payload(base,1,'half_shift',['95'],'sourceA')
        for f,a,sites,d in [(0,'half_shift',['95'],'sourceA'),(1,'aligned',['95'],'sourceA'),(1,'half_shift',['24'],'sourceA'),(1,'half_shift',['95'],'sourceB')]:
            with self.assertRaises(ValueError):permissions.inference_payload(base,f,a,sites,d)
    def test_pack_hard_deadline_no_retry(self):
        r=self.p/'r';r.mkdir();(r/'saved.json').write_text('{}');logs=self.p/'l';logs.mkdir();m=self.p/'m';m.write_text('{}')
        with self.assertRaises(TimeoutError):pack.pack(r,logs,m,self.p/'p.tar.gz',time.monotonic()-1)
        self.assertTrue((self.p/'p.tar.gz.part').exists());self.assertFalse((self.p/'p.tar.gz').exists())
    def test_corrupt_archive_crc_rejected_before_extract(self):
        r=self.p/'r';r.mkdir();logs=self.p/'l';logs.mkdir();m=self.p/'m';m.write_text('{}');a=self.p/'p.tar.gz';rec=pack.pack(r,logs,m,a,time.monotonic()+10)
        b=bytearray(a.read_bytes());b[-8]^=1;a.write_bytes(b)
        with self.assertRaises(Exception):receive.receive(a,self.p/'received',receive.sha(a),a.stat().st_size)
        self.assertFalse((self.p/'received').exists())
    def test_owned_tree_cleanup_never_kills_reused_PID(self):
        import psutil
        parent=Mock(pid=11);childproc=Mock(pid=77);childproc.parents.return_value=[parent];childproc.cmdline.return_value=['python',str(self.p)];childproc.create_time.return_value=1.;grand=Mock(pid=78);grand.create_time.return_value=2.;childproc.children.return_value=[grand]
        reused=Mock(pid=78);reused.create_time.return_value=3.;handle=Mock(pid=77)
        def process(pid):
            if pid==77:
                if not hasattr(process,'seen'):process.seen=True;return childproc
                raise psutil.NoSuchProcess(pid)
            return reused
        with patch.object(psutil,'Process',side_effect=process),patch.object(run.subprocess,'run') as kill:
            run.terminate_owned(handle,self.p,11)
        self.assertEqual(kill.call_args.args[0],['taskkill.exe','/PID','77','/T','/F']);self.assertEqual(kill.call_count,1)
    def test_cleanup_refuses_unowned_process(self):
        import psutil
        process=Mock();process.parents.return_value=[]
        with patch.object(psutil,'Process',return_value=process),patch.object(run.subprocess,'run') as kill:
            with self.assertRaises(RuntimeError):run.terminate_owned(Mock(pid=77),self.p,11)
        kill.assert_not_called()
    def test_managed_wrapper_is_own_tree_only(self):
        text=(HERE/'producer.ps1').read_text();self.assertIn('CreationDate',text);self.assertIn('WaitForExit(100)',text);self.assertIn('taskkill.exe /PID $key /T /F',text);self.assertNotIn('Stop-Process -Name',text);self.assertIn('3480',text);self.assertIn("'package' 3600",text)
    def test_counts_no_hidden_new_native_replay(self):
        plan,_=c.config();counts=plan['counts'];self.assertEqual(counts['native_tiles'],497*40);self.assertEqual(counts['reused_contexts']+counts['new_contexts'],31156);self.assertEqual(counts['linear_solves'],18);self.assertEqual(counts['case_captures'],6)
if __name__=='__main__':unittest.main()
