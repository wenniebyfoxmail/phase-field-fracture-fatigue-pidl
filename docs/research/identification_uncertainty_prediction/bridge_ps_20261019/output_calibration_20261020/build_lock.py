"""Source/metadata-text hashing only. Never parses scientific cohort cases or arrays."""
from pathlib import Path
import hashlib,json

def main():
 root=Path(__file__).resolve().parent
 names=sorted(p.name for p in root.iterdir() if p.is_file() and p.suffix in ('.py','.json','.md','.txt') and p.name not in ('package_lock.json','preparation_receipt.json'))
 lock={'protocol':'FIXED_ALPHA_OUTPUT_CALIBRATION_DISABLED_V1','accepted_design_commit':'fe54ab36df890551f13e0e515ab50c2ad69c97c8','files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},'reuse':['r002_base.py byte-identical base target/native metric and bounded loader','legacy_state.py byte-identical origin feature construction only','runtime_guard.py byte-identical reviewed lifetime guard'],'scientific_access_or_run_authority':False}
 (root/'package_lock.json').write_text(json.dumps(lock,sort_keys=True,indent=2)+'\n')
 print(hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(',',':')).encode()).hexdigest())
if __name__=='__main__':main()
