"""Extract existing s3/s4 history states; read-only commands, no solve or training."""
from pathlib import Path
import base64,concurrent.futures,shlex,subprocess

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT=ROOT/'local_archive/report_ch4_fatigue_fields_20261015/raw'
OUT.mkdir(parents=True,exist_ok=True)

PIDL=r'''
from pathlib import Path
import numpy as np,torch,sys,json,io
torch.set_num_threads(1)
root=Path('/mnt/data2/drtao/pidl_archives/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z')
arrays={};records=[]
for arm in ('q4','t3'):
 paths=list(root.glob('*_'+arm+'_production_*'));assert len(paths)==1
 p=paths[0]
 settings=(p/'model_settings.txt').read_text();assert 'previous_accepted_nodal' in settings
 arrays['settings_'+arm]=np.array(settings)
 for c in (20,60,83):
  j=5*c-1
  diag=p/'element_diagnostics_probe_driver'/f'element_fields_cycle_{j:04d}.npz'
  zz=np.load(diag,allow_pickle=False)
  for s,step in ((3,j-1),(4,j)):
   path=p/'best_models'/f'checkpoint_step_{step}.pt'
   z=torch.load(path,map_location='cpu',weights_only=False,mmap=True)
   assert z['history_storage']==('q4_gp4' if arm=='q4' else 'tri3_gp3')
   h=z['hist_fat'];f=torch.ones_like(h);mask=h>.5;f[mask]=(1/(h[mask]+.5)).pow(2)
   arrays[f'{arm}_c{c}_s{s}_H']=h.numpy().copy()
   arrays[f'{arm}_c{c}_s{s}_F']=f.numpy().copy()
   st=path.stat();row={'arm':arm,'cycle':c,'substep':s,'global_step':step,'path':str(path),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'history_storage':z['history_storage'],'gauss_order':z['gauss_order'],'damage_history_storage':z['damage_history_storage'],'timing':'checkpoint after history refresh'}
   if s==4:
    dh=float(np.max(np.abs(h.numpy()-zz['hist_fat_gp'])));df=float(np.max(np.abs(f.numpy()-zz['f_fatigue_gp'])))
    assert dh==0 and df<3e-7,(arm,c,dh,df)
    arrays[f'{arm}_c{c}_s4_F']=zz['f_fatigue_gp'].copy()
    arrays[f'{arm}_c{c}_centers']=np.column_stack([zz['elem_x'],zz['elem_y']])
    arrays[f'{arm}_c{c}_areas']=zz['area_elem'].copy()
    row.update({'export_path':str(diag),'checkpoint_vs_export_history_maxabs':dh,'recomputed_vs_saved_f_maxabs':df,'f_source':'actual post-refresh diagnostic GP export'})
   else:row['f_source']='recomputed from the preceding accepted history with production float32 law'
   records.append(row)
  print(arm,c,'s3/s4 existing history read',file=sys.stderr,flush=True)
arrays['receipts_json']=np.array(json.dumps(records))
b=io.BytesIO();np.savez_compressed(b,**arrays);sys.stdout.buffer.write(b.getvalue())
'''

FEM=r'''
base='C:\Users\xw436\OneDrive - University of Cambridge\griphfith\S04_E011_raw_outputs_ad749c8_20261005_backup_20261015';
for aa={'Q4','T3'}
 arm=aa{1};folder=fullfile(base,['S04_E011_FEM_' arm '_C120'],'request28_post_commit');
 for c=[20 60 83]
  for sub=[3 4]
   path=fullfile(folder,sprintf('c%04d_s%03d_post_commit.mat',c,sub));
   a=load(path,'request28_snapshot');q=a.request28_snapshot;
   assert(q.cycle==c && q.substep==sub && q.damage_committed && q.history_committed);
   info=dir(path);m=struct('arm',arm,'cycle',c,'substep',sub,'path',path,'bytes',info.bytes,'datenum',info.datenum,'load_factor',q.load_factor,'state_timing',q.state_timing,'num_gauss_points',q.num_gauss_points,'history_committed',q.history_committed);
   fprintf('META|%s\n',jsonencode(m));
   names={'H','F'};values={q.alpha_bar_gp,q.f_alpha_gp};
   if c==20 && sub==4
    names=[names {'coords','cells'}];values=[values {double(q.node_coords),double(q.connectivity)}];
   end
   for k=1:numel(names)
    v=double(values{k});assert(all(isfinite(v),'all'));
    stream=java.io.ByteArrayOutputStream();gz=java.util.zip.GZIPOutputStream(stream);
    raw=typecast(v(:),'int8');gz.write(raw,0,numel(raw));gz.close();
    packed=typecast(stream.toByteArray(),'uint8');encoded=matlab.net.base64encode(packed);
    fprintf('PACK|%s|%d|%d|%s|%d|%d|%s\n',arm,c,sub,names{k},size(v,1),size(v,2),encoded);
   end
  end
 end
end
fprintf('FEM_HISTORY_READ_COMPLETE\n');
'''

def read_pidl():
    cmd='python3 -c '+shlex.quote(PIDL)
    with (OUT/'pidl_history.npz.partial').open('wb') as o,(OUT/'pidl_reader.stderr').open('wb') as e:
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','gpu-taobo',cmd],stdout=o,stderr=e,timeout=900)
    if p.returncode:raise RuntimeError(f'PIDL reader exit {p.returncode}')
    (OUT/'pidl_history.npz.partial').rename(OUT/'pidl_history.npz')
    print('PIDL history extraction complete',flush=True)

def read_fem():
    m="eval(native2unicode(matlab.net.base64decode('"+base64.b64encode(FEM.encode()).decode()+"'),'UTF-8'))"
    exe=r'C:\Program Files\MATLAB\R2025b\bin\matlab.exe'
    ps=f"$ErrorActionPreference='Stop'; & '{exe}' -singleCompThread -batch \"{m}\"; exit $LASTEXITCODE"
    cmd='powershell -NoProfile -EncodedCommand '+base64.b64encode(ps.encode('utf-16le')).decode()
    with (OUT/'fem_history.stdout.partial').open('wb') as o,(OUT/'fem_reader.stderr').open('wb') as e:
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','citpc12-ssh',cmd],stdout=o,stderr=e,timeout=900)
    if p.returncode:raise RuntimeError(f'FEM reader exit {p.returncode}')
    assert b'FEM_HISTORY_READ_COMPLETE' in (OUT/'fem_history.stdout.partial').read_bytes()
    (OUT/'fem_history.stdout.partial').rename(OUT/'fem_history.stdout')
    print('FEM post-commit history extraction complete',flush=True)

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fs=[ex.submit(read_pidl),ex.submit(read_fem)]
        for f in concurrent.futures.as_completed(fs):f.result()
