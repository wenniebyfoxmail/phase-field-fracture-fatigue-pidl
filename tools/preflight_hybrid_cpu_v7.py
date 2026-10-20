"""Single read-only <=20s producer admission; stdlib, no scientific arrays."""
import hashlib,json,os,pwd,socket,time
from pathlib import Path


def main():
    start=time.perf_counter();old=Path('/mnt/data2/drtao/wennie/pf_hybrid_solver_v6_20261020_r3')
    root=Path('/mnt/data2/drtao/wennie/pf_hybrid_solver_v7_20261020_r4')
    archive=Path('/mnt/data2/drtao/pidl_archives')/root.name
    if socket.gethostname()!='GPUServer8' or os.geteuid()!=pwd.getpwnam('drtao').pw_uid:raise RuntimeError('wrong producer')
    if not os.path.ismount('/mnt/data2') or root.exists() or archive.exists():raise RuntimeError('mount/fresh identity unavailable')
    for p in [old/'inputs',old/'deps',root.parent,archive.parent]:
        if not p.is_dir() or any(x.is_symlink() for x in [p,*p.parents]):raise RuntimeError('source/path unavailable or symlink')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    mf=old/'inputs/inputs.json'
    if sha(mf)!='51776e2ebb9642a2f6805a87e34842d608f44624b0d0fb06aa4b0792e95f4c1c':raise RuntimeError('old input manifest differs')
    manifest=json.loads(mf.read_text());assets=[]
    for name,want in manifest['assets'].items():
        rel=Path(name);p=old/'inputs'/rel
        if rel.is_absolute() or '..' in rel.parts or p.is_symlink() or sha(p)!=want:raise RuntimeError('old asset differs')
        assets.append(dict(name=name,sha256=want,bytes=p.stat().st_size))
    terminal=json.loads((old/'terminal.json').read_text())
    if terminal['status']!='failed':raise RuntimeError('R3 terminal changed')
    pids=[]
    for name in ['launch_reservation.json','launch_receipt.json','monitor.json']:
        r=json.loads((old/name).read_text());pid=r.get('pid')
        if pid and (Path('/proc')/str(pid)).exists():
            command=(Path('/proc')/str(pid)/'cmdline').read_bytes()
            if str(old).encode() in command:raise RuntimeError('attributable R3 process still alive')
        pids.append(pid)
    mem=dict(x.split(':',1) for x in Path('/proc/meminfo').read_text().splitlines())
    available=int(mem['MemAvailable'].split()[0])*1024;disk=os.statvfs('/mnt/data2')
    free=disk.f_bavail*disk.f_frsize;affinity=sorted(os.sched_getaffinity(0))
    if available<32*2**30 or free<16*2**30 or len(affinity)<4:raise RuntimeError('CPU/memory/disk admission failed')
    retained=json.loads((old/'stage_receipt.json').read_text())
    deps={x['target'][5:]:x['sha256'] for x in retained['inventory'] if x['target'].startswith('deps/')}
    if hashlib.sha256(json.dumps(deps,sort_keys=True,allow_nan=False).encode()).hexdigest()!='1fbb703c25235550f2137dbab0eb0a114ca8a5777b4b55ac8d33ce90023d1f77':raise RuntimeError('retained dependency manifest differs')
    for name,want in deps.items():
        p=old/'deps'/name
        if any(x.is_symlink() for x in [p,*p.parents]) or sha(p)!=want:raise RuntimeError('retained dependency file differs')
    for name in ['osqp','osqp-1.0.4.dist-info']:
        if not (old/'deps'/name).is_dir():raise RuntimeError('retained OSQP missing')
    print(json.dumps(dict(passed=True,hostname=socket.gethostname(),account=pwd.getpwuid(os.geteuid()).pw_name,
        epoch=time.time(),wall_seconds=time.perf_counter()-start,assets=assets,
        R3_status=terminal['status'],R3_attributable_pids_not_alive=pids,
        capacity=dict(available_ram_bytes=available,free_disk_bytes=free,cpu_affinity_count=len(affinity),load_average=os.getloadavg()),
        inputs_read_only=str(old/'inputs'),deps_read_only=str(old/'deps'),
        GPU_queries=0,scientific_array_decodes=0,scientific_imports=0,writes=0)),flush=True)


if __name__=='__main__':main()
