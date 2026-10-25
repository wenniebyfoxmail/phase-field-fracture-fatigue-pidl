"""Taobo profile checks; no model construction, inference or installation on import."""
import hashlib,importlib.metadata,json,os,platform,pwd,socket,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
DOC=HERE.parents[1]/'docs/research/S01/S01-E029'
VERSIONS={'torch':'2.11.0+cu128','torchvision':'0.26.0+cu128','numpy':'2.5.2','psutil':'7.2.2','matplotlib':'3.11.2','Pillow':'12.3.0'}

def command(argv):return subprocess.check_output(argv,text=True,timeout=15).strip()
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def production_environment(cfg):
    p=cfg['producer'];root=Path(cfg['linux_paths']['runtime']).resolve()
    if sys.platform!='linux' or socket.gethostname()!=p['hostname'] or pwd.getpwuid(os.getuid()).pw_name!=p['account'] or platform.machine()!='x86_64':raise PermissionError('frozen Taobo host/account/architecture')
    if sys.version.split()[0]!='3.12.14' or Path(sys.executable).resolve()!=Path(p['python']).resolve() or not Path(sys.executable).resolve().is_relative_to(root):raise PermissionError('isolated Python executable')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!=str(p['gpu_physical_index']) or os.environ.get('PYTHONDONTWRITEBYTECODE')!='1' or os.environ.get('PYTHONNOUSERSITE')!='1' or os.environ.get('PYTHONPATH') or any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise PermissionError('frozen GPU/thread/import environment')
    spec=json.loads((DOC/'taobo_runtime_spec.json').read_text());lock=json.loads(Path(cfg['linux_paths']['runtime_lock']).read_text())
    if lock['spec_sha256']!=sha(DOC/'taobo_runtime_spec.json') or lock['prefix']!=str(root) or lock['state']!='built_from_frozen_artifacts':raise ValueError('runtime provenance')
    if not root.is_dir() or any(root.is_symlink() for _ in [0]):raise ValueError('runtime root')
    actual={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
    if set(actual)!=set(lock['files']):raise ValueError('runtime exact inventory')
    for rel,p in actual.items():
        if p.is_symlink() or sha(p)!=lock['files'][rel]:raise ValueError('runtime file identity')
    for name,version in VERSIONS.items():
        dist=importlib.metadata.distribution(name)
        if dist.version!=version or not Path(dist.locate_file('')).resolve().is_relative_to(root):raise ValueError('Linux distribution version/origin '+name)
    if spec['python']['version']!='3.12.14':raise ValueError('Python source version')

def worker_runtime_reads(cfg):
    # Runtime was independently inventoried before the role audit hook; exact files only.
    lock=json.loads(Path(cfg['linux_paths']['runtime_lock']).read_text());root=Path(lock['prefix'])
    return [root/rel for rel in lock['files']]

def admission(cfg,psutil_module=None):
    if psutil_module is None:
        import psutil
        ps=psutil
    else:ps=psutil_module
    p=cfg['producer'];a=cfg['admission']
    rows=[line.split(',') for line in command(['nvidia-smi','--query-gpu=index,uuid,name,memory.free,utilization.gpu','--format=csv,noheader,nounits']).splitlines()]
    rows=[[s.strip() for s in row] for row in rows];match=[r for r in rows if r[0]==str(p['gpu_physical_index'])]
    if len(match)!=1:raise ValueError('selected card missing')
    row=match[0]
    if row[1]!=p['gpu_uuid'] or row[2]!=p['gpu_name'] or float(row[3])<a['minimum_free_GPU_MiB'] or float(row[4])!=0:raise RuntimeError('selected GPU identity/free/utilization')
    compute=command(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'])
    if any(r.split(',')[0].strip()==p['gpu_uuid'] for r in compute.splitlines()):raise RuntimeError('selected GPU has compute; other cards untouched')
    cpu=ps.cpu_percent(interval=1)
    if cpu>=a['maximum_CPU_percent'] or ps.virtual_memory().available<a['minimum_free_RAM_bytes'] or ps.disk_usage(cfg['linux_paths']['root']).free<cfg['budget']['minimum_free_disk_bytes']:raise RuntimeError('shared host resources')
    return dict(physical_GPU=row,CPU_percent=cpu,other_GPU_jobs='left untouched')

def production_checks(cfg,guard,desktop_unused,sha_unused):
    production_environment(cfg);identity=admission(cfg)
    import torch,torchvision
    p=cfg['producer']
    if torch.__version__!=p['torch'] or torchvision.__version__!=p['torchvision'] or torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0)!=p['gpu_name']:raise ValueError('torch/device mapping')
    import uuid
    if uuid.UUID(str(torch.cuda.get_device_properties(0).uuid).removeprefix('GPU-'))!=uuid.UUID(p['gpu_uuid'].removeprefix('GPU-')):raise ValueError('logical UUID')
    torch.set_num_threads(1);torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    guard.gpu=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0));guard.check()
    return torch,dict(identity,hostname=socket.gethostname(),account=p['account'],pid=os.getpid(),CUDA_VISIBLE_DEVICES=str(p['gpu_physical_index']),logical_GPU=0,versions=VERSIONS,runtime_lock_sha256=sha(cfg['linux_paths']['runtime_lock']))


def prepare_fonts(cfg):
    # Data-free font discovery before the audit hook. Rendering uses only bundled fonts.
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import font_manager
    root=Path(cfg['linux_paths']['runtime']).resolve()
    fm=font_manager.fontManager
    fm.ttflist=[f for f in fm.ttflist if Path(f.fname).resolve().is_relative_to(root)]
    fm.afmlist=[f for f in fm.afmlist if Path(f.fname).resolve().is_relative_to(root)]
    if not any(f.name=='DejaVu Sans' for f in fm.ttflist):raise ValueError('bundled DejaVu font')
    matplotlib.rcParams['font.family']=['DejaVu Sans'];matplotlib.rcParams['font.sans-serif']=['DejaVu Sans']
