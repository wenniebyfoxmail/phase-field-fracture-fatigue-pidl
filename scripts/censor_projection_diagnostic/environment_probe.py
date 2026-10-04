"""Condor-only CUDA runtime probe; no PIDL optimizer or training loop."""
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

from windows_runtime import configure
configure()

out = Path('output')
out.mkdir(exist_ok=True)
receipt = {'run_id': os.environ['CENSOR_RUN_ID'], 'kind': 'tooling-only', 'training': False,
           'pid': os.getpid(), 'host': platform.node(), 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
(out/'execution.json').write_text(json.dumps(receipt, indent=2))
for key, name in [('_CONDOR_JOB_AD', 'job.ad'), ('_CONDOR_MACHINE_AD', 'machine.ad')]:
    path = os.environ.get(key)
    if not path:
        raise RuntimeError('Probe requires a Condor allocation')
    (out/name).write_bytes(Path(path).read_bytes())
machine = (out/'machine.ad').read_text()
m = re.search(r'^AssignedGPUs\s*=\s*"(GPU-[a-fA-F0-9-]+)"\s*$', machine, re.M)
if not m:
    raise RuntimeError('Expected exactly one GPU UUID assigned by Condor')
receipt['original_cuda_visible_devices'] = os.environ.get('CUDA_VISIBLE_DEVICES')
os.environ['CUDA_VISIBLE_DEVICES'] = m.group(1)
receipt['assigned_gpu'] = m.group(1)
import torch

torch.set_num_threads(1)
receipt.update(torch=torch.__version__, cuda_runtime=torch.version.cuda, cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'])
if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
    raise RuntimeError('Assigned GPU is not uniquely visible to CUDA')
prop = torch.cuda.get_device_properties(0)
receipt.update(gpu_name=prop.name, gpu_uuid=str(prop.uuid), capability=[prop.major, prop.minor], gpu_memory=prop.total_memory)
if not str(prop.uuid).lower().removeprefix('gpu-').startswith(m.group(1).lower().removeprefix('gpu-')):
    raise RuntimeError('CUDA UUID differs from scheduler allocation')
x = torch.tensor([1., 2., 3.], device='cuda', requires_grad=True)
y = x.square().sum()
y.backward()
torch.cuda.synchronize()
if not torch.equal(x.grad, torch.tensor([2., 4., 6.], device='cuda')):
    raise RuntimeError('CUDA autograd probe failed')
receipt['cuda_autograd'] = 'PASS'
result = subprocess.run([sys.executable, '-c', "from windows_runtime import configure; configure(); import torch; torch.set_num_threads(1); import pytest,sys; sys.exit(pytest.main(['-q','code/tests/test_native_q4_quadrature.py','code/tests/test_native_q4_history.py']))"], capture_output=True, text=True)
(out/'unit_tests.txt').write_text(result.stdout+result.stderr)
receipt.update(unit_test_exit=result.returncode, finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
receipt['status'] = 'PASS' if result.returncode == 0 else 'FAIL'
(out/'execution.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2), flush=True)
sys.exit(result.returncode)
