"""Read existing production files; never start a solve or modify a producer file."""
from pathlib import Path
import base64
import concurrent.futures
import json
import shlex
import subprocess

ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT = ROOT / 'local_archive/report_ch4_revision_20261015/raw'
OUT.mkdir(parents=True, exist_ok=True)

PIDL = r'''
from pathlib import Path
import numpy as np,torch,sys,json,io,hashlib
torch.set_num_threads(1)
root=Path('/mnt/data2/drtao/pidl_archives/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z')
arrays={}; receipts={}
for arm in ('q4','t3'):
 paths=list(root.glob('*_'+arm+'_production_*')); assert len(paths)==1
 p=paths[0]; snap=np.load(p/'alpha_snapshots/alpha_cycle_0000.npy',allow_pickle=False)
 arrays['coords_'+arm]=snap[:,:2]; arrays['snapshot_initial_'+arm]=snap[:,2]
 states=[];records=[];checks=[]
 for cycle in range(0,121):
  step=0 if cycle==0 else 5*cycle-1
  f=p/'best_models'/f'checkpoint_step_{step}.pt'
  z=torch.load(f,map_location='cpu',weights_only=False,mmap=True)
  assert z['damage_history_storage']=='previous_accepted_nodal'
  d=z['hist_alpha'].numpy().reshape(-1).copy()
  assert d.shape==(86756,) and np.isfinite(d).all()
  states.append(d)
  sf=p/'alpha_snapshots'/f'alpha_cycle_{step:04d}.npy'
  if sf.exists():
   ss=np.load(sf,allow_pickle=False); delta=float(np.max(np.abs(ss[:,2]-d)))
   assert delta==0.0,(arm,step,delta)
   assert np.array_equal(ss[:,:2],snap[:,:2]);checks.append(step)
  if cycle==0:
   arrays['initial_hist_fat_'+arm]=z['hist_fat'].numpy()
   arrays['initial_previous_active_'+arm]=z['psi_plus_prev'].numpy()
   receipts[arm]={'archive':str(p),'initial_checkpoint_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'settings':(p/'model_settings.txt').read_text()}
  st=f.stat(); records.append({'cycle':cycle,'step':step,'path':str(f),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns})
  if cycle%20==0: print(arm,cycle,'stored nodal damage read',file=sys.stderr,flush=True)
 arrays['damage_'+arm]=np.stack(states)
 receipts[arm]['sources']=records; receipts[arm]['snapshot_exact_match_steps']=checks
arrays['receipt_json']=np.array(json.dumps(receipts))
b=io.BytesIO();np.savez_compressed(b,**arrays);sys.stdout.buffer.write(b.getvalue())
'''

FEM = r'''
base='C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\production_outputs';
for aa={'Q4','T3'}
 arm=aa{1}; folder=fullfile(base,['S04_E011_FEM_' arm '_C120']);
 a=load(fullfile(folder,'state0_analysis.mat'));
 disp(['INITIAL_KEYS_' arm '=' strjoin(fieldnames(a),',')]);
 d=double(a.state0_p_field(:)); xy=double(a.state0_node);
 assert(numel(d)==86756 && all(isfinite(d)));
 fprintf('INITIAL_DAMAGE_%s=%s\n',arm,matlab.net.base64encode(typecast(d,'uint8')));
 fprintf('INITIAL_COORDS_%s=%s\n',arm,matlab.net.base64encode(typecast(xy(:),'uint8')));
 m=load(fullfile(folder,'initial_state_metadata.mat'),'initial_state_metadata');
 fprintf('METADATA_%s=%s\n',arm,jsonencode(m.initial_state_metadata));
 mask=xy(:,1)>.48;
 for c=1:120
  p=fullfile(folder,'native_gp_staging',sprintf('cycle_%04d_peak_%s.mat',c,lower(arm)));
  d=double(h5read(p,'/converged_peak_solution/d'));d=d(:);
  assert(numel(d)==86756 && all(isfinite(d)));
  info=dir(p); n=sum(d(mask)>.95);
  fprintf('EVENT,%s,%d,%d,%.17g,%.17g,%d,%.17g\n',arm,c,n,min(d),max(d),info.bytes,info.datenum);
 end
end
fprintf('FEM_READ_COMPLETE\n');
'''

def collect_pidl():
    command='python3 -c '+shlex.quote(PIDL)
    with (OUT/'pidl_all_peaks.npz.partial').open('wb') as o,(OUT/'pidl_read.stderr').open('wb') as e:
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','gpu-taobo',command],stdout=o,stderr=e,timeout=1800)
    if p.returncode: raise RuntimeError(f'PIDL read exit {p.returncode}')
    (OUT/'pidl_all_peaks.npz.partial').rename(OUT/'pidl_all_peaks.npz')
    print('PIDL read complete',flush=True)

def collect_fem():
    encoded=base64.b64encode(FEM.encode()).decode()
    matlab="eval(native2unicode(matlab.net.base64decode('"+encoded+"'),'UTF-8'))"
    exe=r'C:\Program Files\MATLAB\R2025b\bin\matlab.exe'
    ps=f"$ErrorActionPreference='Stop'; & '{exe}' -singleCompThread -batch \"{matlab}\"; exit $LASTEXITCODE"
    command='powershell -NoProfile -EncodedCommand '+base64.b64encode(ps.encode('utf-16le')).decode()
    with (OUT/'fem_read.stdout.partial').open('wb') as o,(OUT/'fem_read.stderr').open('wb') as e:
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','citpc12-ssh',command],stdout=o,stderr=e,timeout=1800)
    if p.returncode: raise RuntimeError(f'FEM read exit {p.returncode}')
    data=(OUT/'fem_read.stdout.partial').read_bytes()
    if b'FEM_READ_COMPLETE' not in data: raise RuntimeError('FEM read lacks completion marker')
    (OUT/'fem_read.stdout.partial').rename(OUT/'fem_read.stdout')
    print('FEM read complete',flush=True)

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fs=[ex.submit(collect_pidl),ex.submit(collect_fem)]
        for f in concurrent.futures.as_completed(fs): f.result()
