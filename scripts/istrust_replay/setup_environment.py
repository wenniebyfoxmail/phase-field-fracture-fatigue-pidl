"""Task-local environment preparation only. Does not access images or initialize CUDA."""
from pathlib import Path
import json,os,subprocess,sys,time
root=Path(sys.argv[1]).resolve()
assert root == Path('/mnt/data2/drtao/wennie/S02-E007-R001')
env=os.environ.copy()
env.update(TMPDIR=str(root/'tmp'),PIP_CACHE_DIR=str(root/'pip_cache'),CUDA_VISIBLE_DEVICES='',PIP_DISABLE_PIP_VERSION_CHECK='1')
for key in ['TMPDIR','PIP_CACHE_DIR']:Path(env[key]).mkdir(exist_ok=False)
venv=root/'venv'
commands=[
 ['/usr/bin/python3','-m','venv',str(venv)],
 [str(venv/'bin/python'),'-m','pip','install','--retries','0','--timeout','30','torch==1.13.1+cu116','torchvision==0.14.1+cu116','--extra-index-url','https://download.pytorch.org/whl/cu116'],
 [str(venv/'bin/python'),'-m','pip','install','--retries','0','--timeout','30','-r',str(Path(__file__).with_name('requirements.txt'))],
 [str(venv/'bin/python'),'-m','pip','freeze']]
try:
 for cmd in commands:
  print(json.dumps({'command':cmd}),flush=True)
  subprocess.run(cmd,check=True,env=env,timeout=1800)
 (root/'environment_ready.json').write_text(json.dumps({'ready':True,'python':str(venv/'bin/python'),'model_execution':False})+'\n')
except BaseException as e:
 (root/'environment_first_stop.json').write_text(json.dumps({'first_stop':repr(e),'automatic_retry':False})+'\n')
 raise
