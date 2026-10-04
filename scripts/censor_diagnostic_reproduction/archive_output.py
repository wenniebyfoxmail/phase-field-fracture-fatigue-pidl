"""Create a checksummed output bundle after Condor exit and retrieval."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parent
output=root/'output'
execution=json.loads((output/'execution.json').read_text())
if execution.get('execution_status')!='succeeded':raise RuntimeError('Numerical execution not complete')
files=list(output.rglob('*'))
files += list(root.glob('condor-*.*'))
for old in ('output-attempt52','output-attempt53'):
 files += list((root/old).rglob('*'))
files=[p for p in files if p.is_file()]
manifest={'execution':execution,'files':[{'path':str(p.relative_to(root)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(root/'output_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(root/'results.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in files+[root/'output_manifest.json']:z.write(p,p.relative_to(root))
print(json.dumps({'files':len(files),'bytes':(root/'results.zip').stat().st_size,'sha256':hashlib.sha256((root/'results.zip').read_bytes()).hexdigest()}))
