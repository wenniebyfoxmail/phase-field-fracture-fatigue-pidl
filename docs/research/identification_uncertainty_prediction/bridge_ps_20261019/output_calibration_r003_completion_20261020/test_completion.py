"""Artificial subset/full equivalence and rejecting invalid completion support."""
import unittest,tempfile,json,csv
from pathlib import Path
import numpy as np
import engine,evidence
from test_package import ArtificialData

class CompletionTests(unittest.TestCase):
 def test_subset_is_exact_full_outer_blocks_with_compact_anchors(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t)
   def run(name,selected):
    q=r/name;q.mkdir();d=ArtificialData();sink=evidence.DiskSink(q/'out',d)
    try:c=engine.run_comparison(d,sink,evidence.Audit(q),(1,2),outer_groups=selected)
    finally:sink.close()
    return q/'out',c
   full,fc=run('full',None);part,pc=run('part',['b','d'])
   self.assertEqual(pc,dict(predictor=32,residualizer=16,inner_rows=24,outer_rows=8,inner_scores=1080,outer_scores=56))
   def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
   for name in ['selections.jsonl','model_provenance.jsonl']:
    a=[v for v in lines(full/name) if v['outer'] in ('b','d')];self.assertEqual(a,lines(part/name))
   with (full/'outer_scores.csv').open() as f:a=[v for v in csv.DictReader(f) if v['group'] in ('b','d')]
   with (part/'outer_scores.csv').open() as f:self.assertEqual(a,list(csv.DictReader(f)))
   schema=json.loads((part/'array_schema.json').read_text());self.assertEqual(schema['anchor_cases'],[2,3,6,7]);self.assertEqual(schema['anchor_shape'][0],4)
   for i in (2,3,6,7):
    for h in (1,2):
     x=evidence.read_fields(full,i,h);y=evidence.read_fields(part,i,h)
     for a,b in zip(x[:3],y[:3]):np.testing.assert_array_equal(a,b)
   with self.assertRaises(ValueError):evidence.read_fields(part,0,1)
 def test_duplicate_unknown_unsorted_empty_outer_groups_rejected_before_outputs(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);data=ArtificialData()
   for selected in ([],['a','a'],['z'],['d','b']):
    sink=evidence.DiskSink(r/'out',data)
    with self.assertRaises(ValueError):engine.run_comparison(data,sink,evidence.Audit(r),(1,),outer_groups=selected)
    self.assertFalse((r/'out').exists());self.assertEqual(data.target_calls,[])
 def test_expected_remaining_counts_derived_from_frozen_text_metadata(self):
  # Metadata text only: never original scientific fields.
  labels=[c['group'] for c in json.loads(Path(__file__).with_name('frozen_cohort.json').read_text())['cases']]
  cfg=json.loads(Path(__file__).with_name('config.json').read_text());selected=cfg['outer_groups'];G=len(set(labels));n=len(labels)
  sets=len(selected)*2*G;inner=sum(n-labels.count(g) for g in selected)*2;outer=sum(g in selected for g in labels)*2
  self.assertEqual(cfg['expected_work'],dict(training_sets=sets,predictor=2*sets,residualizer=sets,inner_rows=inner,outer_rows=outer,inner_scores=45*inner,outer_scores=7*outer))


class ComponentVerificationTests(unittest.TestCase):
 def test_saved_component_recompute_and_corruption_rejected(self):
  from assemble_completion import verify_component
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d=ArtificialData();sink=evidence.DiskSink(r/'outputs',d)
   try:c=engine.run_comparison(d,sink,evidence.Audit(r),(1,2),outer_groups=['b','d'])
   finally:sink.close()
   co=[{'group':g,'center_row':d.centers[i]} for i,g in enumerate(d.groups)]
   scores,check,fields=verify_component(r,['b','d'],c,co,(1,2),1)
   self.assertEqual(len(scores),56);self.assertLess(check['max_native_difference'],1e-12)
   p=r/'outputs/selections.jsonl';lines=p.read_text().splitlines();z=json.loads(lines[0]);z['chosen_U_C_A'][0]=[2,2];lines[0]=json.dumps(z);p.write_text('\n'.join(lines)+'\n')
   with self.assertRaises(ValueError):verify_component(r,['b','d'],c,co,(1,2),1)
 def test_direct_human_authority_binds_only_four_groups(self):
  import package
  code=Path(__file__).parent;cfg=package.read(code/'config.json');digest=package.check(code);cs=package.sha(code/'config.json')
  a=dict(authority_kind='hq_exact_admission_and_run',authority_source_thread_id='01a10e77-8832-7371-b4cc-e5cbdadceced',human_approved=True,authority_basis='DIRECT_HUMAN',approval_text='artificial exact binding test; not execution authority',source_commit='a'*40,package_sha256=digest,config_sha256=cs,run_id=cfg['run_id'],run_root=cfg['run_root'],budget=cfg['approved_budget'],category_caps=cfg['category_caps'],scope='FOUR_GROUP_COMPLETION_OF_R002',allow_scientific_admission=True,allow_old_input_native_target_read=True,allow_456_solves_once=True,max_attempts=1,outer_groups=cfg['outer_groups'],prefix_binding_sha256=package.sha(code/'prefix_binding.json'))
  package.validate_authority(a,cfg,digest,cs)
  for k,v in [('outer_groups',[]),('allow_456_solves_once',False),('max_attempts',2),('prefix_binding_sha256','bad')]:
   bad={**a,k:v}
   with self.assertRaises(PermissionError):package.validate_authority(bad,cfg,digest,cs)


class AssemblyBoundaryTests(unittest.TestCase):
 def test_nan_and_inf_scores_and_means_rejected(self):
  from assemble_completion import verify_component
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d=ArtificialData();sink=evidence.DiskSink(r/'outputs',d)
   try:c=engine.run_comparison(d,sink,evidence.Audit(r),(1,2),outer_groups=['b','d'])
   finally:sink.close()
   co=[{'group':g,'center_row':d.centers[i]} for i,g in enumerate(d.groups)];p=r/'outputs/outer_scores.csv';original=p.read_text()
   for value in ('nan','inf','-inf'):
    lines=original.splitlines();row=lines[1].split(',');row[4]=value;lines[1]=','.join(row);p.write_text('\n'.join(lines)+'\n')
    with self.assertRaises(ValueError):verify_component(r,['b','d'],c,co,(1,2),1)
   p.write_text(original);p=r/'outputs/selections.jsonl';lines=p.read_text().splitlines();z=json.loads(lines[0]);z['candidate_group_mean_balanced'][0]=float('nan');lines[0]=json.dumps(z);p.write_text('\n'.join(lines)+'\n')
   with self.assertRaises(ValueError):verify_component(r,['b','d'],c,co,(1,2),1)
 def test_missing_retrieval_and_storage_budget_fail_closed(self):
  from assemble_completion import verify_retrieval,check_local_storage
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);root=r/'remote_snapshot/run';root.mkdir(parents=True)
   with self.assertRaises(FileNotFoundError):verify_retrieval(root)
   (r/'payload').write_bytes(b'1234');cfg={'local_storage_roots':[str(r)],'approved_budget':{'total_generated_bytes':3}}
   with self.assertRaises(ValueError):check_local_storage(cfg,reserve=0)
 def test_full_artificial_two_component_assembly_and_virtual_figure_decode(self):
  # Only source/prefix authority is simulated. Actual component verification,
  # retrieval hashes, lifecycle seals, counts, selectors, native fields and merge run.
  from unittest.mock import patch
  import assemble_completion as ac,package,tarfile
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d=ArtificialData();d.half_height=16
   old=r/'old';newcase=r/'new';new=newcase/'remote_snapshot/run';code=r/'code';code.mkdir();new.mkdir(parents=True);old.mkdir()
   def component(root,groups):
    sink=evidence.DiskSink(root/'outputs',d)
    try:counts=engine.run_comparison(d,sink,evidence.Audit(root),(10,40),outer_groups=groups)
    finally:sink.close()
    return counts
   oldcounts=component(old,['a','b']);newcounts=component(new,['c','d']);co=[{'group':g,'center_row':d.centers[i]} for i,g in enumerate(d.groups)]
   cfg={'outer_groups':['c','d'],'expected_work':{'training_sets':16,**newcounts},'H':[10,40],'local_storage_roots':[str(r)],'approved_budget':{'total_generated_bytes':1536*2**20}}
   (code/'config.json').write_text(json.dumps(cfg));(code/'frozen_cohort.json').write_text(json.dumps({'cases':co}));(code/'prefix_binding.json').write_text('{}')
   binding={'complete_groups':['a','b'],'counts':oldcounts}
   (new/'logs').mkdir();
   for n in ['launch.stderr','logs/controller.stderr','logs/worker.stderr']:(new/n).write_bytes(b'')
   for n,pid in [('logs/runtime_exit.json',3),('logs/controller_exit.json',2),('logs/watchdog_exit.json',1)]:evidence.write(new/n,{'status':'RETURNED_AND_EXIT_CALLBACKS_COMPLETE','pid':pid})
   evidence.write(new/'controller_receipt.json',{'status':'CANDIDATE_COMPLETE_REQUIRES_WATCHDOG','worker_pid':3})
   evidence.write(new/'watchdog_receipt.json',{'status':'COMPLETE_CONTROLLER_EXIT_VERIFIED','package_sha256':'artificial','controller_pid':2,'watchdog_pid':1})
   items=[{'path':str(p.relative_to(new/'outputs')),'bytes':p.stat().st_size,'sha256':package.sha(p)} for p in (new/'outputs').rglob('*') if p.is_file()]
   evidence.write(new/'outputs/receipt.json',{'counts':newcounts,'scope':'FOUR_OUTER_GROUPS_ONLY_NOT_FULL19','files_before_receipt':items})
   inventory={'files':{str(p.relative_to(new)):{'bytes':p.stat().st_size,'sha256':package.sha(p)} for p in new.rglob('*') if p.is_file()}}
   inv=new.parent/'retrieval_inventory.json';inv.write_text(json.dumps(inventory));archive=newcase/'snapshot.tar'
   with tarfile.open(archive,'w') as f:f.add(new,arcname='run')
   evidence.write(newcase/'retrieval_verification.json',{'status':'COMPLETE_SNAPSHOT_ALL_HASHES_VERIFIED','inventory_sha256':package.sha(inv),'snapshot_path':str(archive),'snapshot_bytes':archive.stat().st_size,'snapshot_sha256':package.sha(archive)})
   with patch.object(ac.prefix_binding,'verify_root',return_value=binding),patch.object(ac.package,'check',return_value='artificial'):
    info=ac.assemble(code,old,new,r/'assembled',render=False)
   self.assertEqual(len(info['paired']),8);self.assertEqual(info['counts']['outer_scores'],112)
   for i in range(8):
    source=old if d.groups[i] in ('a','b') else new
    for h in (10,40):
     a=evidence.read_fields(r/'assembled',i,h);b=evidence.read_fields(source/'outputs',i,h)
     for x,y in zip(a[:3],b[:3]):np.testing.assert_array_equal(x,y)
   # Decode virtual field source used by the real figure renderer; no fits/forwards.
   import figures
   figures.render(r/'assembled')
   self.assertEqual(len(list((r/'assembled').glob('0*.png'))),3)
   inv.write_text('{}')
   with self.assertRaises(ValueError):ac.verify_retrieval(new)

if __name__=='__main__':unittest.main()
