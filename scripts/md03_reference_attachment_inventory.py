"""Authorised MD03 two ZIP downloads + Fig.7; file lists, no model execution."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
WORK = ROOT/'.codex/worktrees/crackmnist-tokenizer-mvp'
OUT = ROOT/'local_archive/experiments/S03-E049-MD03/reference_attachment_check_20261020/R001'
META = ROOT/'local_archive/open_data/s03_independent_sequence_metadata_20261018'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    receipt = dict(started_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
                   scope='two ZIPs and Fig7 only; no new TIFFs/recognition/forecast', downloads=[])
    sources = json.loads((META/'wv7hvgg8c7_root_files.json').read_text())
    assert len(sources)==2
    specs = [dict(filename=r['filename'], url=r['content_details']['download_url'],
                  expected_bytes=r['size'], expected_sha256=r['content_details']['sha256_hash']) for r in sources]
    specs.append(dict(filename='author_Fig7.jpg', url='https://ars.els-cdn.com/content/image/1-s2.0-S026412752030719X-gr7_lrg.jpg'))
    for s in specs:
        result = dict(s)
        try:
            request = urllib.request.Request(s['url'],headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=35) as response:
                payload=response.read(5_000_001)
                assert len(payload)<=5_000_000
                result.update(final_url=response.url,content_type=response.headers.get('Content-Type'))
            if 'expected_sha256' in s:
                assert len(payload)==s['expected_bytes'] and sha(payload)==s['expected_sha256']
            else:
                assert payload[:2]==b'\xff\xd8', 'Figure response is not JPEG'
            (OUT/s['filename']).write_bytes(payload)
            result.update(status='verified_download',bytes=len(payload),sha256=sha(payload))
            if s['filename'].endswith('.zip'):
                with zipfile.ZipFile(OUT/s['filename']) as z:
                    result['members']=[dict(name=i.filename,bytes=i.file_size,compressed_bytes=i.compress_size,
                                            is_dir=i.is_dir(),crc=i.CRC) for i in z.infolist()]
                    assert len(result['members'])<1000
                    assert sum(i['bytes'] for i in result['members'])<100_000_000
                    result['zip_crc_check']=z.testzip()
                    assert result['zip_crc_check'] is None
        except Exception as e:
            result.update(status='failed',error=repr(e))
        receipt['downloads'].append(result)
        (OUT/'download_and_members.json').write_text(json.dumps(receipt,indent=2))
    receipt.update(ended_utc=datetime.now(timezone.utc).isoformat())
    (OUT/'download_and_members.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
