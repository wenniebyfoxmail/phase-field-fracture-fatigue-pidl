"""Bounded fixed success/stop package; no model/GT decoding or network."""
import argparse,hashlib,io,json,os,tarfile,time
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()

def pack(run,logs,manifest,output,deadline):
    if output.exists() or output.with_suffix(output.suffix+'.part').exists():raise FileExistsError('fresh fixed package only')
    files={}
    for prefix,root in [('run',run),('wrapper',logs)]:
        if root.exists():
            for p in sorted(root.rglob('*')):
                if p.is_symlink():raise ValueError('symlink rejected')
                if p.is_file():files[prefix+'/'+p.relative_to(root).as_posix()]=p
    files['source_manifest.json']=manifest
    if sum(p.stat().st_size for p in files.values())>2*1024**3:raise ValueError('raw package cap')
    records={name:dict(bytes=p.stat().st_size,sha256=sha(p)) for name,p in files.items()}
    temp=output.with_suffix(output.suffix+'.part')
    with tarfile.open(temp,'w:gz') as t:
        for name,p in files.items():
            if time.monotonic()>deadline:raise TimeoutError('fixed package deadline')
            t.add(p,arcname=name,recursive=False)
            if temp.stat().st_size>2*1024**3:raise ValueError('archive cap')
        raw=json.dumps(dict(files=records),sort_keys=True).encode();info=tarfile.TarInfo('file_manifest.json');info.size=len(raw);t.addfile(info,io.BytesIO(raw))
    if temp.stat().st_size>2*1024**3 or time.monotonic()>deadline:raise RuntimeError('fixed package cap/deadline')
    temp.rename(output);receipt=dict(archive=str(output),bytes=output.stat().st_size,sha256=sha(output),files=len(files)+1,run_state='see run/status.json or wrapper failure record; no missing score filled with zero')
    output.with_suffix(output.suffix+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['run','logs','manifest','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--seconds',type=float,required=True);a=p.parse_args()
    pack(a.run,a.logs,a.manifest,a.output,time.monotonic()+a.seconds)
