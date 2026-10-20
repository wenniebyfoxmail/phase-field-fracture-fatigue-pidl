"""Task-local environment preparation only; no image reads, model code or CUDA init."""
from pathlib import Path
import json,os,subprocess,sys,hashlib
root=Path(sys.argv[1]).resolve()
assert root == Path('/mnt/data2/drtao/wennie/S02-E007-R001')
env=os.environ.copy()
env.update(TMPDIR=str(root/'tmp_bootstrap'),PIP_CACHE_DIR=str(root/'pip_cache_bootstrap'),CUDA_VISIBLE_DEVICES='',PIP_DISABLE_PIP_VERSION_CHECK='1')
for key in ['TMPDIR','PIP_CACHE_DIR']:Path(env[key]).mkdir(exist_ok=False)
venv=root/'venv_replay'
bootstrap=root/'get-pip.py'
commands=[
 ['/usr/bin/python3','-m','venv','--without-pip',str(venv)],
 ['curl','-sS','--fail','--retry','0','--max-time','120','-o',str(bootstrap),'https://bootstrap.pypa.io/get-pip.py'],
 [str(venv/'bin/python'),str(bootstrap),'pip==23.2.1','setuptools==68.2.2','wheel==0.41.2','--retries','0','--timeout','30'],
 [str(venv/'bin/python'),'-m','pip','install','--retries','0','--timeout','30','torch==1.13.1+cu116','torchvision==0.14.1+cu116','--extra-index-url','https://download.pytorch.org/whl/cu116'],
 [str(venv/'bin/python'),'-m','pip','install','--retries','0','--timeout','30','-r',str(Path(__file__).with_name('requirements.txt'))],
 [str(venv/'bin/python'),'-m','pip','freeze']]
try:
 for cmd in commands:
  print(json.dumps({'command':cmd}),flush=True)
  subprocess.run(cmd,check=True,env=env,timeout=1800)
 receipt={'ready':True,'python':str(venv/'bin/python'),'model_execution':False,'bootstrap_url':'https://bootstrap.pypa.io/get-pip.py','bootstrap_sha256':hashlib.sha256(bootstrap.read_bytes()).hexdigest(),'prior_ensurepip_failure_preserved':True}
 (root/'environment_replay_ready.json').write_text(json.dumps(receipt,indent=2)+'\n')
except BaseException as e:
 (root/'environment_bootstrap_first_stop.json').write_text(json.dumps({'first_stop':repr(e),'automatic_retry':False})+'\n')
 raise
