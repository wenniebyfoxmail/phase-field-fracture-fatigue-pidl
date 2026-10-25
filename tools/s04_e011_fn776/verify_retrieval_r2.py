"""Future report-copy verification only; static preparation never runs this."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

RUN = 'pf_s04e011_uvh_c1_fn776_r8_20261025'
CASE = Path('/Users/wenxiaofang/0 Research/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs') / RUN / 'authorized_execution'


def record(path):
    return json.loads(path.read_text())


def require_binding(value, binding, relative):
    assert value['contract_sha256'] == binding['semantic_sha256'], relative


def verify(case, code):
    source = record(code/'SOURCE_PROVENANCE.json')
    binding = source['contract_binding']
    contract = record(code/binding['path'])
    folder=case/'control_diagnostics'
    manifest=json.loads((folder/'manifest.stdout').read_text().splitlines()[-1])
    assert manifest['status']=='MANIFEST_OK'
    expected={row['path']:row for row in manifest['files']}
    assert len(expected)==len(manifest['files'])
    target=case/'retrieved'
    target.mkdir(exist_ok=False)
    seen=set()
    with tarfile.open(case/'retrieved.tar',mode='r:') as archive:
        for member in archive:
            path=PurePosixPath(member.name)
            assert member.isfile() and member.name in expected and member.name not in seen
            assert not path.is_absolute() and '..' not in path.parts and path.parts[0] in ('root','output')
            row=expected[member.name];assert member.size==row['bytes']
            output=target/member.name;output.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();count=0
            with archive.extractfile(member) as source,output.open('xb') as destination:
                for block in iter(lambda:source.read(1024**2),b''):
                    h.update(block);count+=len(block);destination.write(block)
            assert count==row['bytes'] and h.hexdigest()==row['sha256']
            seen.add(member.name)
    assert seen==set(expected)
    required_root = ('root/materialization_receipt.json', 'root/attempt_claim.json',
                     'root/launch_receipt.json')
    for relative in required_root:
        assert (target/relative).is_file(), 'missing root provenance record: '+relative
    materialization = record(target/'root/materialization_receipt.json')
    claim = record(target/'root/attempt_claim.json')
    launch = record(target/'root/launch_receipt.json')
    for relative, value in (('root/materialization_receipt.json', materialization),
                            ('root/attempt_claim.json', claim),
                            ('root/launch_receipt.json', launch)):
        require_binding(value, binding, relative)
    assert claim['source'] == launch['source'] == materialization['source']
    assert claim['run_id'] == launch['run_id'] == contract['run_id']
    assert claim['approval_ref'] == contract['control_plane']['card_id']
    guard_path = target/'output/guard_receipt.json'
    worker_path = target/'output/worker_receipt.json'
    output_members = {relative for relative in seen if relative.startswith('output/')}
    if output_members:
        assert guard_path.is_file() and worker_path.is_file(), 'partial output receipt chain'
        guard, worker = record(guard_path), record(worker_path)
        require_binding(guard, binding, 'output/guard_receipt.json')
        require_binding(worker, binding, 'output/worker_receipt.json')
        assert guard['run_id'] == worker['run_id'] == launch['run_id']
        assert guard['source'] == worker['code_commit'] == launch['source']
        assert guard['approval_ref'] == claim['approval_ref']
        assert worker['code_commit'] == launch['source']
        evidence_state = 'output_receipt_chain'
        worker_output_evidence_available = True
        terminal = None
    else:
        terminal_path = target/'root/operator_terminal.json'
        assert terminal_path.is_file(), 'missing terminal record for root-only archive'
        terminal = record(terminal_path)
        require_binding(terminal, binding, 'root/operator_terminal.json')
        assert terminal['retry_allowed'] is False and isinstance(terminal.get('error'), str)
        assert terminal['run_id'] == launch['run_id']
        assert terminal['source'] == launch['source']
        assert terminal['approval_ref'] == claim['approval_ref']
        assert terminal['output_claimed'] is False
        evidence_state = 'root_terminal_before_output'
        worker_output_evidence_available = False
    receipt=dict(status='RETRIEVAL_VERIFIED',files=len(seen),bytes=sum(r['bytes'] for r in expected.values()),
                 contract_binding=binding, evidence_state=evidence_state,
                 worker_output_evidence_available=worker_output_evidence_available,
                 terminal=terminal,
                 manifest_scope='producer files copied and size/hash verified; no numerical array decoding/recomputation')
    (folder/'retrieval_verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    code = Path(__file__).resolve().parents[2]
    print(json.dumps(verify(CASE, code)))


if __name__=='__main__':
    main()
