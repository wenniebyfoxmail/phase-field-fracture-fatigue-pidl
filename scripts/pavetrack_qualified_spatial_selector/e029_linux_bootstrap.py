"""Approved task-only source-built Linux runtime. No fitting/model/GT access."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tarfile,urllib.parse,urllib.request
from pathlib import Path
DOC=Path(__file__).resolve().parents[2]/'docs/research/S01/S01-E029'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def artifact(rec,dest,spec):
    def valid(url):
        p=urllib.parse.urlsplit(url)
        return p.scheme=='https' and p.hostname in spec['origin_allowlist'] and not p.username and not p.password
    if not valid(rec['url']) or Path(rec['filename']).name!=rec['filename']:raise ValueError('artifact URL/name')
    if dest.exists():raise FileExistsError('no download overwrite')
    n=0;h=hashlib.sha256()
    with urllib.request.urlopen(rec['url'],timeout=60) as src,dest.open('xb') as out:
        if not valid(src.url):raise ValueError('unapproved redirect')
        for b in iter(lambda:src.read(1024**2),b''):
            out.write(b);h.update(b);n+=len(b)
            if n>2*1024**3:raise ValueError('single artifact cap')
    if h.hexdigest()!=rec['sha256'] or rec.get('bytes') is not None and n!=rec['bytes']:raise ValueError('artifact identity')
    return n

def source_extract(archive,out,limit):
    out.mkdir(exist_ok=False);total=0
    with tarfile.open(archive) as t:
        seen=set()
        for m in t:
            n=m.name
            if n in seen or n.startswith('/') or '\\' in n or '..' in Path(n).parts or not (m.isfile() or m.isdir()) or Path(n).parts[0]!='Python-3.12.14':raise ValueError('unsafe Python source member')
            seen.add(n);total+=m.size
            if total>limit:raise ValueError('source extraction cap')
            p=out/n
            if m.isdir():p.mkdir(parents=True,exist_ok=True)
            else:
                p.parent.mkdir(parents=True,exist_ok=True)
                with t.extractfile(m) as src,p.open('xb') as dest:shutil.copyfileobj(src,dest,1024**2)
                p.chmod(m.mode & 0o755)

def run(argv,cwd=None):
    # Outer owned-session supervisor controls RSS, signals and no-retry.
    subprocess.run(argv,cwd=cwd,check=True)

def build(cfg):
    spec_path=DOC/'taobo_runtime_spec.json';spec=json.loads(spec_path.read_text());lp=cfg['linux_paths'];prefix=Path(lp['runtime']);base=Path(lp['root']);work=base/'runtime_build';cache=base/'runtime_artifacts'
    if sys.platform!='linux' or prefix.exists() or work.exists() or cache.exists() or Path(lp['runtime_lock']).exists():raise PermissionError('fresh Linux task runtime only')
    if shutil.disk_usage(base).free<spec['minimum_free_disk_bytes']:raise ValueError('runtime disk space')
    work.mkdir();cache.mkdir();total=artifact(spec['python'],cache/spec['python']['filename'],spec)
    for rec in spec['wheels']:
        total+=artifact(rec,cache/rec['filename'],spec)
        if total>spec['download_limit_bytes']:raise ValueError('runtime artifact aggregate cap')
    source_extract(cache/spec['python']['filename'],work/'src',spec['source_extract_limit_bytes']);src=work/'src/Python-3.12.14';target=str(prefix)
    run([str(src/'configure'),'--prefix='+target,'--with-ensurepip=install'],src);run(['make','-j1'],src);run(['make','install'],src)
    exe=prefix/'bin/python3.12'
    run([str(exe),'-I','-m','pip','install','--prefix='+target,'--disable-pip-version-check','--no-index','--no-deps','--no-cache-dir',*[str(cache/r['filename']) for r in spec['wheels']]])
    # Materialise only internal file symlinks so an exact runtime read inventory is sufficient.
    for p in sorted(prefix.rglob('*')):
        if p.is_symlink():
            resolved=p.resolve(strict=True)
            if not resolved.is_relative_to(prefix) or not resolved.is_file():raise ValueError('external/directory runtime symlink')
            raw=resolved.read_bytes();mode=resolved.stat().st_mode;p.unlink();p.write_bytes(raw);p.chmod(mode & 0o777)
    files={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()}
    lock=dict(state='built_from_frozen_artifacts',prefix=str(prefix.resolve()),spec_sha256=sha(spec_path),files=files,artifacts={r['filename']:r['sha256'] for r in [spec['python'],*spec['wheels']]},Python_build='configure --prefix TASK; make -j1; make install',model_calls=0,GT_decodes=0)
    Path(lp['runtime_lock']).write_text(json.dumps(lock,indent=2)+'\n')
    run([str(exe),'-I','-c',"import json,sys,importlib.metadata as m;print(json.dumps({'python':sys.version,'versions':{n:m.version(n) for n in ['torch','torchvision','numpy','psutil','matplotlib','Pillow']}}))"])
    return lock

if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import e029_system_proc as proc
    cfg=json.loads((DOC/'taobo_run_config.json').read_text());lp=cfg['linux_paths'];approval=json.loads(Path(lp['approval']).read_text());claim=json.loads(Path(lp['launch_claim']).read_text())
    expected=dict(run_id='S01-E029-R001',reviewed_commit=claim['commit'],source_manifest_sha256=claim['manifest'],execute_once=True,wall_seconds=None,GPU_uuid=cfg['producer']['gpu_uuid'])
    parent=proc.Process(os.getppid())
    if parent.ppid()!=claim['pid'] or parent.create_time()!=int(os.environ.get('E029_PARENT_BIRTH','-1')) or proc.Process(claim['pid']).create_time()!=claim['wrapper_birth']:raise PermissionError('bootstrap lifeline/wrapper birth chain')
    if os.getppid()==claim['pid']:raise PermissionError('bootstrap requires independent stage lifeline')
    if approval!=expected or type(approval.get('execute_once')) is not bool or approval.get('wall_seconds') is not None or claim['approval_sha256']!=sha(Path(lp['approval'])) or os.getppid()!=int(os.environ.get('E029_PARENT_PID','-1')):raise PermissionError('bootstrap only in exact approved wrapper lifecycle')
    build(cfg)
