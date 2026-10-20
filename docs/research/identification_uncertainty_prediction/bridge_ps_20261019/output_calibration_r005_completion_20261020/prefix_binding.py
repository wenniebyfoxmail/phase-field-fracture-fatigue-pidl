"""Hash-bind the immutable stopped prefix. No source native data, fitting or mutation."""
from pathlib import Path
import json
import package

def verify_root(code,root):
 binding=package.read(Path(code)/'prefix_binding.json');root=Path(root)
 if root.is_symlink():raise ValueError('prefix root symlink')
 for name,item in binding['files'].items():
  p=root/name
  if p.is_symlink() or p.stat().st_size!=item['bytes'] or package.sha(p)!=item['sha256']:raise ValueError('prefix binding changed: '+name)
 if package.read(root/'outputs/progress.json')!=binding['counts']:raise ValueError('prefix checkpoint changed')
 lock=package.check(root/'code')
 if lock!=binding['package_sha256']:raise ValueError('prefix package identity')
 oldcfg=package.read(root/'code/config.json');newcfg=package.read(Path(code)/'config.json')
 for key in ('predictor_alpha','input_residualizer_alpha','H','channels','candidate_counts','primary','dependencies','cases','groups'):
  if oldcfg[key]!=newcfg[key]:raise ValueError('scientific configuration changed '+key)
 labels=[c['group'] for c in package.read(root/'code/frozen_cohort.json')['cases']]
 if sorted(binding['complete_groups']+binding['missing_groups'])!=sorted(set(labels)):raise ValueError('prefix complement not full cohort')
 if set(binding['complete_groups'])&set(binding['missing_groups']) or newcfg['outer_groups']!=binding['missing_groups']:raise ValueError('prefix overlap/complement')
 return binding

def verify(code,cfg,audit):
 audit.enter('immutable_prefix_identity_before_any_fit')
 b=verify_root(code,package.read(Path(code)/'prefix_binding.json')['remote_root'])
 package.write(audit.root/'prefix_identity_verified.json',{'status':'HASH_BOUND_PREFIX_VERIFIED_READ_ONLY','run_id':b['run_id'],'files_verified':len(b['files']),'counts':b['counts'],'complete_groups':b['complete_groups'],'missing_groups':b['missing_groups']})
 return b
