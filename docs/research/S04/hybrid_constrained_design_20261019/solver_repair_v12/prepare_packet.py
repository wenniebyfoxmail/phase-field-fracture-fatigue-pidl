"""Local disabled-template preparation only; no network, science or activation."""
from pathlib import Path
import hashlib,io,json,subprocess,tarfile
HERE=Path(__file__).resolve().parent;CODE=HERE.parents[4]
LOCAL=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v12_20261021')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,allow_nan=False).encode()).hexdigest()

def prepare():
    card=json.loads((HERE/'execution_card.json').read_text())
    if card['execution_enabled']is not False or card['execution_authority']is not None:raise RuntimeError('preparation never activates card')
    old=json.loads((HERE.parent/'solver_repair_v11/source_manifest.json').read_text())
    paths=[x for x in old['files']if x.startswith('source/')]
    paths+=['source/hybrid_box_krylov.py','tools/hybrid_producer_worker.py','tools/hybrid_deadline_guard.py','tools/run_hybrid_producer.py','tools/run_hybrid_cpu_v12_budgeted.py','tools/preflight_hybrid_cpu_v12.py','tools/receive_hybrid_cpu_v12.py']
    paths+=[str((HERE/x).relative_to(CODE))for x in ['plan.md','authority.json','retained_deps_manifest.json']]
    files={x:sha(CODE/x)for x in sorted(set(paths))};artifact=canonical(files)
    if not(HERE/'execution_review.json').exists():
        card['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=CODE,text=True).strip()
        (HERE/'execution_card.json').write_text(json.dumps(card,indent=2,ensure_ascii=False)+'\n')
        package=dict(source_commit=card['source_commit'],artifact_id=artifact,files=files)
        (HERE/'source_manifest.json').write_text(json.dumps(package,indent=2)+'\n')
        print(json.dumps(dict(status='disabled_template_awaiting_review',artifact_id=artifact,template_id=canonical(card),card_sha256=sha(HERE/'execution_card.json'),files=len(files))))
        return
    package=json.loads((HERE/'source_manifest.json').read_text());review=json.loads((HERE/'execution_review.json').read_text())
    if package!=dict(source_commit=card['source_commit'],artifact_id=artifact,files=files):raise RuntimeError('reviewed source immutable')
    if review['verdict']!='CODE_TEMPLATE_REVIEW_PASS_ONLY'or review['artifact_id']!=artifact or review['template_id']!=canonical(card):raise RuntimeError('reviewed template immutable')
    data={n:(HERE/n).read_bytes()for n in ['execution_card.json','source_manifest.json','execution_review.json']}
    data.update({'code/'+x:(CODE/x).read_bytes()for x in files});buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz')as t:
        for n,v in data.items():
            item=tarfile.TarInfo(n);item.size=len(v);item.mtime=0;t.addfile(item,io.BytesIO(v))
    payload=buf.getvalue()
    if len(payload)>2*2**20 or sum(map(len,data.values()))>4*2**20:raise RuntimeError('code/control package exceeds cap')
    LOCAL.mkdir(exist_ok=True,parents=True);(LOCAL/'disabled_code_control.tar.gz').write_bytes(payload)
    print(json.dumps(dict(status='REVIEWED_DISABLED_NOT_FOR_DISPATCH',artifact_id=artifact,template_id=canonical(card),bundle_sha256=hashlib.sha256(payload).hexdigest(),bundle_bytes=len(payload))))
if __name__=='__main__':prepare()
