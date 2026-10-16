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
        active=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
        if any(cfg['producer']['gpu_uuid'] in row for row in active.splitlines()):raise RuntimeError('GPU compute conflict')
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
        self.identity=dict(torch=torch.__version__,torchvision=torchvision.__version__,Pillow=PIL.__version__,physical_GPU=line[:3],CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES'],logical_GPU=0,transform=repr(self.transform),dtype='float32',backends=cfg['scoring']['backend'])
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
