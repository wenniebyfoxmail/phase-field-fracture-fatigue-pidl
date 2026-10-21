"""One small code/control bundle; retained private R3 data never transferred."""
import hashlib,io,json,os,pwd,socket,subprocess,sys,tarfile,time
from pathlib import Path

ROOT=Path('/mnt/data2/drtao/wennie/pf_hybrid_solver_v11_20261021_r8')
ARCHIVE=Path('/mnt/data2/drtao/pidl_archives')/ROOT.name
OLD_DEPS=Path('/mnt/data2/drtao/wennie/pf_hybrid_solver_v6_20261020_r3/deps')
sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    start=time.perf_counter()
    if socket.gethostname()!='GPUServer8' or os.geteuid()!=pwd.getpwnam('drtao').pw_uid:raise RuntimeError('wrong producer')
    if not os.path.ismount('/mnt/data2') or ROOT.exists() or ARCHIVE.exists():raise RuntimeError('fresh roots required; inspect unknown launch')
    if any(p.is_symlink() for p in [ROOT.parent,*ROOT.parents,ARCHIVE.parent,*ARCHIVE.parents]):raise RuntimeError('symlink in root')
    payload=sys.stdin.buffer.read(2*2**20+1)
    if len(payload)>2*2**20 or sha(payload)!=sys.argv[1]:raise RuntimeError('bundle digest/size differs')
    files={}
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as tar:
        members=tar.getmembers()
        if len(members)>128 or sum(x.size for x in members)>4*2**20:raise RuntimeError('expanded code cap')
        for item in members:
            p=Path(item.name)
            if not item.isfile() or p.is_absolute() or '..' in p.parts or item.name in files:raise RuntimeError('nonregular/nonlocal bundle')
            files[item.name]=tar.extractfile(item).read()
    package=json.loads(files['source_manifest.json']);card=json.loads(files['execution_card.json']);review=json.loads(files['execution_review.json'])
    artifact=sha(json.dumps(package['files'],sort_keys=True,allow_nan=False).encode())
    if package['artifact_id']!=artifact:raise RuntimeError('artifact differs')
    names={'source_manifest.json','execution_card.json','execution_review.json'}|{'code/'+p for p in package['files']}
    if set(files)!=names:raise RuntimeError('closed code bundle differs')
    for rel,want in package['files'].items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts or sha(files['code/'+rel])!=want:raise RuntimeError('source differs')
        if rel.endswith('.py'):compile(files['code/'+rel],rel,'exec')
    if (review.get('verdict')!='REVIEW_PASS' or review['artifact_id']!=artifact
            or review['card_sha256']!=sha(files['execution_card.json'])
            or card['run_root']!=str(ROOT) or card['archive_root']!=str(ARCHIVE)
            or card['execution_enabled'] is not True):raise RuntimeError('exact review/card differs')
    ROOT.mkdir(exist_ok=False)
    with (ROOT/'dispatch_reservation.json').open('x') as f:
        json.dump(dict(bundle_sha256=sys.argv[1],epoch=time.time(),no_retry=True),f);f.flush();os.fsync(f.fileno())
    for rel,data in files.items():
        p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    # Copy only the98 already-approved public OSQP source/binary files on the
    # same server. Old R3 caches are neither imported, copied nor modified.
    dep_path=card['retained_deps_manifest']
    dep_data=files['code/'+dep_path]
    if sha(dep_data)!=card['retained_deps_manifest_sha256']:raise RuntimeError('dependency manifest binding differs')
    retained=json.loads(dep_data)['files'];copied=0
    old=OLD_DEPS
    for name,want in retained.items():
        rel=Path(name);source=old/rel;target=ROOT/'deps'/rel
        if (rel.is_absolute() or '..' in rel.parts or '__pycache__' in rel.parts
                or rel.suffix=='.pyc' or any(p.is_symlink() for p in [source,*source.parents])):
            raise RuntimeError('invalid retained OSQP source')
        data=source.read_bytes();copied+=len(data)
        if copied>2**20 or sha(data)!=want:raise RuntimeError('retained OSQP source differs/over cap')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
    if time.perf_counter()-start>12:raise RuntimeError('dispatch preparation deadline; no spawn')
    env=dict(os.environ);env['CUDA_VISIBLE_DEVICES']='';env['PYTHONDONTWRITEBYTECODE']='1'
    cmd=['/usr/bin/python3','-B',str(ROOT/'code/tools/run_hybrid_cpu_v11_budgeted.py'),'--launch']
    result=subprocess.check_output(cmd,cwd=ROOT/'code',env=env,timeout=5,text=True)
    record=dict(state='dispatched',launch=json.loads(result),wall_seconds=time.perf_counter()-start,
        bundle_sha256=sys.argv[1],artifact_id=artifact,code_only_no_private_data=True,
        same_host_retained_OSQP_copied_bytes=copied)
    (ROOT/'dispatch_receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)


if __name__=='__main__':main()
