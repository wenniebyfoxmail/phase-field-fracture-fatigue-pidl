"""E028-owned GPU0 placement checks; historical producer modules stay frozen."""
import json,os,socket,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GPU_UUID='GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7'


def placement(cfg):
    p=cfg['producer']
    if (p['hostname'],p['gpu_physical_index'],p['gpu_logical_index'],p['CUDA_VISIBLE_DEVICES'],p['gpu_uuid'],p['fallback'])!=('D-26-09',0,0,'0',GPU_UUID,False):raise PermissionError('frozen E028 GPU0 placement')
    return p


def production_environment(cfg):
    p=placement(cfg)
    if os.name!='nt' or socket.gethostname().upper()!=p['hostname']:raise PermissionError('approved Windows producer only')
    identity=subprocess.check_output(['whoami'],text=True).strip().lower()
    parts=lambda x:[v for v in x.lower().split(chr(92)) if v]
    if parts(identity)!=parts(p['account']) or sys.version.split()[0]!='3.12.14':raise PermissionError('account/Python runtime')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='0' or any(os.environ.get(k)!='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']):raise PermissionError('frozen GPU/thread environment')
    lock=json.loads((ROOT/'docs/research/S01/S01-E028/runtime_lock.json').read_text())
    if os.environ.get('PYTHONPATH')!=lock['overlay'] or os.environ.get('PYTHONDONTWRITEBYTECODE')!='1':raise PermissionError('isolated Pillow runtime environment')
    if os.path.normcase(os.path.abspath(sys.executable))!=os.path.normcase(os.path.abspath(p['python'])):raise PermissionError('python executable')


def verify_overlay(overlay,files):
    import hashlib
    overlay=Path(overlay)
    actual={p.relative_to(overlay).as_posix():p for p in overlay.rglob('*') if p.is_file()}
    if set(actual)!=set(files):raise ValueError('Pillow overlay exact inventory')
    for n,p in actual.items():
        if hashlib.sha256(p.read_bytes()).hexdigest()!=files[n]:raise ValueError('Pillow overlay binary identity')
    return len(actual)


def verify_pillow():
    lock=json.loads((ROOT/'docs/research/S01/S01-E028/runtime_lock.json').read_text());overlay=Path(lock['overlay'])
    count=verify_overlay(overlay,lock['files'])
    import PIL
    if PIL.__version__!=lock['version'] or Path(PIL.__file__).resolve()!= (overlay/'PIL/__init__.py').resolve():raise ValueError('Pillow version/origin')
    from PIL import Image,ImageDraw
    if Path(Image.__file__).resolve()!=(overlay/'PIL/Image.py').resolve() or Path(Image.core.__file__).resolve().parent!=(overlay/'PIL').resolve():raise ValueError('Pillow native origin')
    # Cheap, data-free exercise of the raster and image codec before producer use.
    import io
    im=Image.new('L',(8,8));ImageDraw.Draw(im).polygon([(1,1),(4,1),(4,4),(1,4)],fill=1)
    if sum(im.tobytes())!=16:raise ValueError('Pillow polygon sanity')
    data=io.BytesIO();im.save(data,format='PNG');data.seek(0)
    with Image.open(data) as reopened:
        if reopened.tobytes()!=im.tobytes():raise ValueError('Pillow codec sanity')
    return dict(version=PIL.__version__,origin=PIL.__file__,files=count)


def physical_gpu(info,cfg):
    p=placement(cfg)
    found=[[s.strip() for s in line.split(',')] for line in info.splitlines() if line.split(',')[0].strip()=='0']
    if len(found)!=1:raise ValueError('physical GPU0 inventory')
    gpu=found[0]
    if len(gpu)!=4 or gpu[1]!=p['gpu_uuid'] or gpu[2]!=p['gpu_name'] or not __import__('math').isfinite(float(gpu[3])) or float(gpu[3])<8192:raise ValueError('GPU identity/free memory')
    return gpu


def logical_gpu(torch,cfg):
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0)!=cfg['producer']['gpu_name']:raise ValueError('logical GPU mapping')
    raw=getattr(torch.cuda.get_device_properties(0),'uuid',None)
    try:actual=uuid.UUID(str(raw).removeprefix('GPU-'))
    except (ValueError,TypeError,AttributeError) as exc:raise ValueError('logical GPU UUID unavailable') from exc
    if actual!=uuid.UUID(placement(cfg)['gpu_uuid'].removeprefix('GPU-')):raise ValueError('logical GPU UUID mapping')


def production_checks(cfg,guard,desktop_inventory,sha):
    production_environment(cfg)
    ps_script="Get-CimInstance Win32_Process|Where-Object {$_.Name -like 'python*'}|Select-Object ProcessId,CommandLine|ConvertTo-Json -Compress"
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps_script],text=True).strip()
    rows=[] if not raw else json.loads(raw);rows=rows if isinstance(rows,list) else [rows]
    import psutil
    allowed={os.getpid(),*[p.pid for p in psutil.Process().parents() if p.name().lower().startswith('python')]}
    if any(row['ProcessId'] not in allowed for row in rows):raise RuntimeError('shared Python compute conflict')
    baseline_path=ROOT/'docs/research/S01/S01-E028/gpu_desktop_baseline.json'
    baseline=json.loads(baseline_path.read_text())
    if baseline['hostname']!=cfg['producer']['hostname'] or baseline['gpu_uuid']!=GPU_UUID:raise ValueError('desktop baseline identity')
    desktop=desktop_inventory(subprocess.check_output(['nvidia-smi','-i','0','-q','-x'],text=True),baseline,sha)
    gpu=physical_gpu(subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.free','--format=csv,noheader,nounits'],text=True),cfg)
    import torch,torchvision
    if torch.__version__!=cfg['producer']['torch'] or torchvision.__version__!=cfg['producer']['torchvision']:raise ValueError('torch runtime')
    torch.set_num_threads(1);torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    logical_gpu(torch,cfg)
    guard.gpu=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0));guard.check()
    return torch,dict(hostname=socket.gethostname(),account=subprocess.check_output(['whoami'],text=True).strip(),pid=os.getpid(),torch=torch.__version__,torchvision=torchvision.__version__,physical_GPU=gpu,CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES'],logical_GPU=0,desktop_baseline_sha256=sha(baseline_path),desktop=desktop)
