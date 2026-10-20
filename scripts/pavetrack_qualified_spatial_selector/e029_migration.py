"""Exact private byte migration. Only catalogue metadata is decoded; no GT/model/RGB."""
import argparse,gzip,hashlib,io,json,os,tarfile
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def name_ok(name):
    return isinstance(name,str) and name and not name.startswith('/') and '\\' not in name and '..' not in Path(name).parts and ':' not in name

def validate_catalogue(value,expected_inputs=11,expected_images=497):
    if set(value)!={'protocol','files'} or value['protocol']!='S01-E029-taobo-private-v1':raise ValueError('private catalogue schema')
    rows=value['files']
    if len(rows)!=expected_inputs+expected_images or len({r['relative'] for r in rows})!=len(rows):raise ValueError('private inventory')
    if sum(r['role']=='input' for r in rows)!=expected_inputs or sum(r['role']=='image' for r in rows)!=expected_images:raise ValueError('private role counts')
    for r in rows:
        if set(r)!={'role','relative','source_windows','sha256','bytes'} or not name_ok(r['relative']) or len(r['sha256'])!=64:raise ValueError('private record')
    return rows

def export(catalogue,archive,expected_inputs=11,expected_images=497):
    value=json.loads(catalogue.read_text());rows=validate_catalogue(value,expected_inputs,expected_images)
    if archive.exists() or Path(str(archive)+'.part').exists():raise FileExistsError('no private export overwrite/retry')
    part=Path(str(archive)+'.part');total=0
    with tarfile.open(part,'w:gz') as t:
        for row in rows:
            p=Path(row['source_windows'])
            if p.is_symlink() or not p.is_file():raise ValueError('ordinary pinned input')
            size=p.stat().st_size;total+=size
            if size>256*1024**2 or total>4*1024**3 or row['bytes'] is not None and size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('private source identity')
            t.add(p,arcname=row['relative'],recursive=False)
        raw=catalogue.read_bytes();info=tarfile.TarInfo('private_catalogue.json');info.size=len(raw);t.addfile(info,io.BytesIO(raw))
    part.rename(archive);receipt=dict(bytes=archive.stat().st_size,sha256=sha(archive),files=len(rows)+1,catalogue_sha256=sha(catalogue),model_calls=0,RGB_decodes=0,GT_decodes=0)
    Path(str(archive)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def receive(archive,root,expected_catalogue_sha,expected_inputs=11,expected_images=497):
    if root.exists():raise FileExistsError('fresh private destination')
    with gzip.open(archive,'rb') as f:
        n=0
        for b in iter(lambda:f.read(1024**2),b''):
            n+=len(b)
            if n>4*1024**3+1024**2:raise ValueError('private gzip raw cap')
    with tarfile.open(archive,'r:gz') as t:
        infos=t.getmembers();names=[m.name for m in infos]
        if len(names)!=len(set(names)) or any(not m.isfile() or not name_ok(m.name) for m in infos):raise ValueError('unsafe private archive')
        raw=t.extractfile('private_catalogue.json').read(2*1024**2)
        if hashlib.sha256(raw).hexdigest()!=expected_catalogue_sha:raise ValueError('private catalogue binding')
        rows=validate_catalogue(json.loads(raw),expected_inputs,expected_images);expected={r['relative']:r for r in rows}
        if set(names)!=set(expected)|{'private_catalogue.json'} or sum(m.size for m in infos)>4*1024**3:raise ValueError('private archive inventory/size')
        root.mkdir(parents=True,exist_ok=False)
        for m in infos:
            dest=root/m.name;dest.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();n=0
            with t.extractfile(m) as src,dest.open('xb') as out:
                for b in iter(lambda:src.read(1024**2),b''):out.write(b);h.update(b);n+=len(b)
            if m.name!='private_catalogue.json':
                r=expected[m.name]
                if n!=m.size or h.hexdigest()!=r['sha256'] or r['bytes'] is not None and n!=r['bytes']:raise ValueError('private received identity')
    return dict(files=len(names),catalogue_sha256=expected_catalogue_sha,GT_decodes=0,RGB_decodes=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['export','receive']);p.add_argument('--catalogue',type=Path);p.add_argument('--archive',type=Path,required=True);p.add_argument('--root',type=Path);p.add_argument('--approval',type=Path,required=True);p.add_argument('--reviewed-commit',required=True);p.add_argument('--server-receipt',type=Path);p.add_argument('--catalogue-sha256',required=True);a=p.parse_args()
    doc=Path(__file__).resolve().parents[2]/'docs/research/S01/S01-E029'
    approval=json.loads(a.approval.read_text());mp=doc/'taobo_source_manifest.json'
    expected=dict(run_id='S01-E029-R001',reviewed_commit=a.reviewed_commit,source_manifest_sha256=sha(mp),execute_once=True,wall_seconds=None,GPU_uuid='GPU-5622bd47-1050-3003-246d-3cabe2b4791b')
    if approval!=expected or type(approval.get('execute_once')) is not bool or approval.get('wall_seconds') is not None:raise PermissionError('exact byte migration approval required')
    root=doc.parents[3]
    for rel,h in json.loads(mp.read_text())['files'].items():
        if sha(root/rel)!=h:raise ValueError('migration source binding')
    lock=json.loads((doc/'taobo_transfer_lock.json').read_text())
    if a.catalogue_sha256!=lock['catalogue_sha256']:raise ValueError('exact frozen catalogue')
    if a.operation=='export':
        if os.name!='nt' or sha(a.catalogue)!=a.catalogue_sha256:raise PermissionError('Windows byte export only')
        export(a.catalogue,a.archive)
    else:
        cfg=json.loads((doc/'taobo_run_config.json').read_text())
        if a.root!=Path(cfg['linux_paths']['private']):raise ValueError('exact private destination')
        if a.server_receipt is None:raise ValueError('private exact export receipt required')
        receipt=json.loads(a.server_receipt.read_text())
        if a.archive.stat().st_size!=receipt['bytes'] or sha(a.archive)!=receipt['sha256'] or receipt['catalogue_sha256']!=a.catalogue_sha256:raise ValueError('private export archive binding')
        receive(a.archive,a.root,a.catalogue_sha256)
