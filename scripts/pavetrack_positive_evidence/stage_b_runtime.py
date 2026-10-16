"""Production-only torch bridge. Importing this module opens no model or image."""
import io,os,sys,hashlib,subprocess,json
from pathlib import Path

def production_environment(cfg):
    import socket
    if os.name!='nt' or socket.gethostname().upper()!=cfg['producer']['hostname']:raise PermissionError('approved Windows producer only')
    identity=subprocess.check_output(['whoami'],text=True).strip().lower()
    parts=lambda x:[v for v in x.lower().split(chr(92)) if v]
    if parts(identity)!=parts(cfg['producer']['account']) or sys.version.split()[0]!='3.12.14':raise PermissionError('account/Python runtime')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='1' or any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS']):raise PermissionError('frozen GPU/thread environment')
    if os.path.normcase(os.path.abspath(sys.executable))!=os.path.normcase(os.path.abspath(cfg['producer']['python'])):raise PermissionError('python executable')

def aggregate_memory(own_peak):
    import psutil
    parent=psutil.Process();total=own_peak()
    for child in parent.children(recursive=True):
        try:
            info=child.memory_info();total+=getattr(info,'peak_wset',info.rss)
        except psutil.NoSuchProcess:pass
    return total

def desktop_inventory(xml_text,baseline,file_sha):
    """Fail-closed exception for pinned desktop C+G contexts on this WDDM host."""
    import xml.etree.ElementTree as ET
    from pathlib import PureWindowsPath
    gpus=ET.fromstring(xml_text).findall('gpu')
    if len(gpus)!=1:raise ValueError('GPU XML inventory')
    gpu=gpus[0]
    if gpu.findtext('uuid')!=baseline['gpu_uuid'] or gpu.findtext('driver_model/current_dm')!='WDDM':raise ValueError('WDDM GPU identity')
    utilization=gpu.findtext('utilization/gpu_util') or ''
    if not utilization.strip().endswith('%'):raise ValueError('GPU utilization unavailable')
    value=float(utilization.strip()[:-1].strip())
    if not __import__('math').isfinite(value) or not 0<=value<=baseline['maximum_sampled_GPU_utilization_percent']:raise RuntimeError('GPU activity conflict')
    table={str(PureWindowsPath(p)).casefold():h for p,h in baseline['approved_desktop_executables'].items()}
    processes=gpu.find('processes')
    if processes is None or (processes.text or '').strip() not in {'','None'} or any(child.tag!='process_info' for child in processes):raise ValueError('GPU processes unavailable')
    rows=[];verified={}
    for entry in processes.findall('process_info'):
        path=entry.findtext('process_name') or '';kind=entry.findtext('type');pid=entry.findtext('pid');key=str(PureWindowsPath(path)).casefold()
        if kind!='C+G' or not pid or not pid.isdecimal() or key not in table:raise RuntimeError('unapproved GPU process')
        if key not in verified:verified[key]=file_sha(path)
        if verified[key]!=table[key]:raise ValueError('desktop executable identity')
        rows.append(dict(pid=int(pid),type=kind,path=path,sha256=verified[key]))
    return dict(gpu_uuid=baseline['gpu_uuid'],driver_model='WDDM',sampled_GPU_utilization_percent=value,processes=rows,scope='pinned desktop C+G snapshot; no future-idle guarantee')

class TorchBackend:
    def __init__(self,cfg,checkpoint,guard,validate_checkpoint):
        production_environment(cfg)
        import torch,torchvision
        from torchvision import models,transforms
        if torch.__version__!=cfg['producer']['torch'] or torchvision.__version__!=cfg['producer']['torchvision']:raise ValueError('torch runtime identity')
        text=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.free','--format=csv,noheader,nounits'],text=True)
        found=[line.split(',') for line in text.strip().splitlines() if line.split(',')[0].strip()=='1']
        if len(found)!=1:raise ValueError('physical GPU inventory')
        line=[s.strip() for s in found[0]]
        if line[1]!=cfg['producer']['gpu_uuid'] or line[2]!=cfg['producer']['gpu_name'] or float(line[3])<8192:raise ValueError('physical GPU identity/free memory')
        baseline_path=Path(__file__).resolve().parents[2]/'docs/research/S01/S01-E012/stage_B/gpu_desktop_baseline.json'
        baseline=json.loads(baseline_path.read_text(encoding='utf8'))
        if baseline['hostname']!=cfg['producer']['hostname'] or baseline['gpu_uuid']!=cfg['producer']['gpu_uuid']:raise ValueError('desktop baseline identity')
        def file_sha(path):
            digest=hashlib.sha256()
            with open(path,'rb') as src:
                while part:=src.read(1024*1024):digest.update(part);guard.check()
            return digest.hexdigest()
        desktop=desktop_inventory(subprocess.check_output(['nvidia-smi','-i','1','-q','-x'],text=True),baseline,file_sha)
        torch.set_num_threads(1);torch.set_float32_matmul_precision(cfg['scoring']['backend']['matmul_precision'])
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=False
        if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0)!=cfg['producer']['gpu_name']:raise ValueError('logical GPU mapping')
        guard.gpu=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0));guard.check()
        state=validate_checkpoint(checkpoint)['state_dict']
        self.model=models.mobilenet_v3_small(weights=None);self.model.classifier[-1]=torch.nn.Linear(self.model.classifier[-1].in_features,2);self.model.load_state_dict(state,strict=True);self.model.eval()
        # The same frozen checkpoint supplies the CPU head and GPU feature model.
        import copy
        self.head=copy.deepcopy(self.model.classifier).cpu().float().eval();self.model=self.model.to('cuda:0').float().eval()
        self.transform=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])]);self.torch=torch
        import PIL
        self.identity=dict(torch=torch.__version__,torchvision=torchvision.__version__,Pillow=PIL.__version__,desktop_baseline_sha256=hashlib.sha256(baseline_path.read_bytes()).hexdigest(),desktop_inventory=desktop,physical_GPU=line[:3],CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES'],logical_GPU=0,transform=repr(self.transform),dtype='float32',backends=cfg['scoring']['backend'])
        guard.gpu=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0));guard.check()
    def image(self,raw,record):
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as image:
            if image.size!=(record['width'],record['height']):raise ValueError('decoded dimensions')
            return image.convert('RGB')
    def features(self,image,rows):
        t=self.torch
        with t.inference_mode(),t.autocast('cuda',enabled=False):
            crops=[]
            for row in rows:
                crop=image.crop(tuple(row['crop_box_xyxy']))
                try:crops.append(self.transform(crop))
                finally:crop.close()
            x=t.stack(crops).to('cuda:0');z=self.model.avgpool(self.model.features(x)).flatten(1).cpu().numpy().copy()
        return z
    def probabilities(self,X):
        t=self.torch
        with t.inference_mode():return self.head(t.tensor(X,dtype=t.float32)).softmax(1)[:,1].tolist()
