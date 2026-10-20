"""Offline verification of copies, never a network transfer/retry tool."""
import argparse,json
from pathlib import Path
from control import verify_retrieval,write_json

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--run-copy',type=Path,required=True);p.add_argument('--archive-copy',type=Path,required=True);p.add_argument('--outer-return',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args();m=json.loads(a.manifest.read_text());outer=json.loads(a.outer_return.read_text())
    from control import digest
    if digest(a.manifest)!=outer['export_manifest_sha256']:raise RuntimeError('producer-return manifest SHA differs')
    r=verify_retrieval(m,{'run':a.run_copy,'archive':a.archive_copy},outer)
    r['producer_status']=outer['status'];r['scientific_success_inferred']=False
    # Put verification receipt outside copied roots so exact coverage remains
    # checkable without ignoring arbitrary extra files.
    if any(root.resolve() in a.receipt.resolve().parents for root in [a.run_copy,a.archive_copy]):raise RuntimeError('verification receipt must be outside verified roots')
    write_json(a.receipt,r);print(json.dumps(r,indent=2))
