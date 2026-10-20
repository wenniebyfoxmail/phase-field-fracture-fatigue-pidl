"""One fresh, bounded producer staging action; no science imports or execution.

Executed via reviewed stdin under external timeout. Standard library only.
Copies exact retained input files and OSQP only; never installs or retries.
"""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import socket
import subprocess
import time

RUN_ID = 'pf_hybrid_complete_20261020_r2'
ROOT = Path('/mnt/data2/drtao/wennie') / RUN_ID
ARCHIVE = Path('/mnt/data2/drtao/pidl_archives') / RUN_ID
OLD = Path('/mnt/data2/drtao/wennie/pf_hybrid_full_20261019_r1')
INPUT_SHA = '51776e2ebb9642a2f6805a87e34842d608f44624b0d0fb06aa4b0792e95f4c1c'
GPU_UUID = 'GPU-5622bd47-1050-3003-246d-3cabe2b4791b'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def plain(path):
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise RuntimeError('symlink in selected path: ' + str(path))


def main():
    tick = time.perf_counter()
    if socket.gethostname() != 'GPUServer8' or os.geteuid() != __import__('pwd').getpwnam('drtao').pw_uid:
        raise RuntimeError('producer identity differs')
    if not os.path.ismount('/mnt/data2'):
        raise RuntimeError('canonical data2 mount unavailable')
    for p in [ROOT.parent, ARCHIVE.parent, OLD/'inputs', OLD/'deps']:
        plain(p)
        if not p.is_dir():
            raise RuntimeError('required parent/source missing')
    if ROOT.exists() or ARCHIVE.exists():
        raise RuntimeError('fresh roots required; no retry')
    disk = shutil.disk_usage('/mnt/data2')
    mem = dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = int(mem['MemAvailable'].split()[0])*1024
    if disk.free < 256*2**30 or available < 64*2**30 or len(os.sched_getaffinity(0)) < 16:
        raise RuntimeError('capacity below existing complete comparison allowance')
    gpu = subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=3)
    rows = [[v.strip() for v in l.split(',')] for l in gpu.splitlines()]
    selected = next(r for r in rows if r[1] == GPU_UUID)
    if selected[0] != '5' or float(selected[2]) > 64 or float(selected[4]) > 5:
        raise RuntimeError('selected GPU occupied/changed; no wait/rebinding')
    df = subprocess.check_output(['df','-h','/','/mnt/data2','/mnt/data3'],text=True,timeout=3)
    manifest_path = OLD/'inputs/inputs.json'
    plain(manifest_path)
    if digest(manifest_path) != INPUT_SHA:
        raise RuntimeError('retained input manifest differs')
    manifest = json.loads(manifest_path.read_text())
    inventory = []
    selected_files = [(manifest_path, Path('inputs/inputs.json'), INPUT_SHA)]
    for rel, expected in manifest['assets'].items():
        rel = Path(rel)
        if rel.is_absolute() or '..' in rel.parts:
            raise RuntimeError('nonlocal asset')
        selected_files.append((OLD/'inputs'/rel, Path('inputs')/rel, expected))
    if len(selected_files) != 8:
        raise RuntimeError('input asset count differs')
    for name in ['osqp','osqp-1.0.4.dist-info','osqp.libs']:
        tree = OLD/'deps'/name
        if not tree.exists():
            if name == 'osqp.libs':
                continue
            raise RuntimeError('required OSQP source missing: '+name)
        plain(tree)
        for base, dirs, files in os.walk(tree, followlinks=False):
            for child in dirs+files:
                plain(Path(base)/child)
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for filename in files:
                if filename.endswith('.pyc'):
                    continue
                src = Path(base)/filename
                selected_files.append((src, Path('deps')/src.relative_to(OLD/'deps'), None))
    if len(selected_files) > 1024 or sum(p.stat().st_size for p,_,_ in selected_files) > 160*2**20:
        raise RuntimeError('bounded staging file/byte cap exceeded')
    for src, rel, expected in selected_files:
        plain(src)
        found = digest(src)
        if expected is not None and expected != found:
            raise RuntimeError('retained input asset differs')
        inventory.append(dict(source=str(src), target=str(rel), bytes=src.stat().st_size, sha256=found))
    ROOT.mkdir(exist_ok=False)
    (ROOT/'stage_reservation.json').write_text(json.dumps(dict(run_id=RUN_ID, state='reserved', no_retry=True)))
    for item in inventory:
        target = ROOT/item['target']
        target.parent.mkdir(parents=True, exist_ok=True)
        with Path(item['source']).open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst, length=1024*1024)
        if digest(target) != item['sha256']:
            raise RuntimeError('staged copy differs')
    cpu = resource.getrusage(resource.RUSAGE_SELF)
    record = dict(passed=True, hostname=socket.gethostname(), run_id=RUN_ID,
                  run_root=str(ROOT), archive_root=str(ARCHIVE), archive_created=False,
                  inventory=inventory, copied_bytes=sum(i['bytes'] for i in inventory),
                  capacity=dict(free_disk_bytes=disk.free, available_ram_bytes=available,
                                affinity_count=len(os.sched_getaffinity(0)), load_average=os.getloadavg(),
                                selected_gpu=selected, df=df),
                  wall_seconds=time.perf_counter()-tick, cpu_seconds=cpu.ru_utime+cpu.ru_stime,
                  gpu_seconds=0., numerical_seconds=0., scientific_imports=[],
                  scientific_arrays_decoded=False, installs=0, retries=0,
                  scope='staging only, not runtime admission or numerical execution')
    (ROOT/'stage_receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
