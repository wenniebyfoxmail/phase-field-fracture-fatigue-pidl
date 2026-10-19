"""Future report-copy verification only; static preparation never runs this."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

RUN = 'pf_s04e011_uvh_c1_fn776_r2_20261019'
CASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs') / RUN / 'authorized_execution'


def main():
    folder=CASE/'control_diagnostics'
    manifest=json.loads((folder/'manifest.stdout').read_text().splitlines()[-1])
    assert manifest['status']=='MANIFEST_OK'
    expected={row['path']:row for row in manifest['files']}
    assert len(expected)==len(manifest['files']) and sum(row['bytes'] for row in expected.values())<100*1024**2
    target=CASE/'retrieved'
    target.mkdir(exist_ok=False)
    seen=set()
    with tarfile.open(CASE/'retrieved.tar',mode='r:') as archive:
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
    receipt=dict(status='RETRIEVAL_VERIFIED',files=len(seen),bytes=sum(r['bytes'] for r in expected.values()),
                 manifest_scope='producer files copied and size/hash verified; no numerical array decoding/recomputation')
    (folder/'retrieval_verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
