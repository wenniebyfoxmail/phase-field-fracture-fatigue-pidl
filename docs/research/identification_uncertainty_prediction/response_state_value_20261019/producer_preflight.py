from pathlib import Path
import hashlib,json,sys,time,os
root=Path('/mnt/data2/drtao/wennie/IU-RESPONSE-STATE-20261019-R002');sys.path.insert(0,str(root/'code'))
import runner
started=time.time();manifest=json.loads((root/'input_transfer_manifest.json').read_text());data=Path('/mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/inputs/mendeley')
for row in manifest:
 p=data/row['relative_path'];assert p.stat().st_size==row['bytes'],str(p)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],str(p)
cfg=json.loads((root/'code/config.producer.json').read_text());m,frames,cand=runner.build_manifest(cfg)
assert m['cases']==json.loads(Path('/mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/outputs/manifest.json').read_text())['cases']
assert len(m['cases'])==1144 and len({c['group'] for c in m['cases']})==19
import torch,numpy as np
import subprocess
subprocess.run([sys.executable,'-m','unittest','discover','-s',str(root/'code'),'-p','test_*.py'],check=True)
loader=runner.Loader(data);seen=set();checks=[]
for c in m['cases']:
 if c['group'] in seen:continue
 seen.add(c['group']);row=frames[(c['group'],c['origin_stage'])];field=loader.get(row)
 original=loader.cache[data/'pt_extracted'/row['pt_member']][row['list_index']]
 assert original.dtype==torch.float32,('Unexpected source dtype; conversion needs review',original.dtype)
 direct=runner.state_features(field,cand[(c['group'],row['stage'])],'rich_set',-1,0.)
 base=runner.state_features(field,cand[(c['group'],row['stage'])],'rich',0,0.)
 cached=runner.scenario_from_point(base,cand[(c['group'],row['stage'])],'rich_set',-1,0.)
 np.testing.assert_array_equal(direct,cached)
 checks.append({'group':c['group'],'stage':row['stage'],'shape':list(field.shape),'dtype':str(original.dtype)})
report={'status':'PREFLIGHT_COMPLETE_NO_FIT','verified_files':len(manifest),'verified_bytes':sum(x['bytes'] for x in manifest),'groups':19,'origins':len(m['cases']),'horizon_cases':2*len(m['cases']),'tensor_checks':checks,'elapsed_seconds':time.time()-started}
(root/'producer_preflight.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='tensor_checks'}),flush=True)
