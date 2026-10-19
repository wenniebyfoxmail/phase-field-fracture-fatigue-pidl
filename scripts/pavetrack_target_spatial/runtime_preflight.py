"""Data-free complete library/device preflight; no model, annotations or source RGB."""
import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('e028_runtime_check',Path(__file__).with_name('environment.py'));env=importlib.util.module_from_spec(spec);spec.loader.exec_module(env)
cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text())
env.production_environment(cfg);pillow=env.verify_pillow()
import torch,torchvision,numpy,psutil,matplotlib
expected=dict(torch=cfg['producer']['torch'],torchvision=cfg['producer']['torchvision'],numpy='2.5.2',psutil='7.2.2',matplotlib='3.11.2')
observed={name:module.__version__ for name,module in [('torch',torch),('torchvision',torchvision),('numpy',numpy),('psutil',psutil),('matplotlib',matplotlib)]}
if observed!=expected:raise ValueError('complete software preflight')
env.logical_gpu(torch,cfg)
print(json.dumps(dict(state='runtime_preflight_passed',python=sys.version.split()[0],Pillow=pillow,versions=observed,logical_uuid=str(torch.cuda.get_device_properties(0).uuid),forwards=0,source_decodes=0,reference_decodes=0)))
