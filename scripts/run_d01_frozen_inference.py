import subprocess,sys,os,json,hashlib,socket,time,zipfile
from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parents[1];env=dict(os.environ,CUDA_VISIBLE_DEVICES="0");began=time.time();receipt={"host":socket.gethostname(),"pid":os.getpid(),"started_utc":datetime.now(timezone.utc).isoformat(),"training":False,"new_cases":8,"gpu":0,"status":"running"}
(r/"extension_execution.json").write_text(json.dumps(receipt,indent=2))
try:
 for file,expected in [("sam_vit_h_4b8939.pth","a7bf3b02f3ebf1267aba913ff637d9a2d5c33d3173bb679e46d9f338c26f262e"),("CrackSAM_adapter_d32.pth","acd3260b01515db5b24734e358aded9363003ed7e76f440cda61d857f1da6268")]:
  h=hashlib.sha256();f=(r/"model"/file).open("rb")
  for chunk in iter(lambda:f.read(8388608),b""):h.update(chunk)
  assert h.hexdigest()==expected,file
 for script in ["d01_cracksam_preview.py","d01_cracksam_cleanup.py"]:
  subprocess.run([sys.executable,str(r/"code"/script),"--root",str(r)],env=env,check=True,timeout=450)
 receipt.update(status="succeeded",seconds=time.time()-began,completed_utc=datetime.now(timezone.utc).isoformat())
except Exception as e:
 receipt.update(status="failed",error=repr(e),seconds=time.time()-began)
(r/"extension_execution.json").write_text(json.dumps(receipt,indent=2))
files=list((r/"outputs").glob("*"))+list((r/"refined").glob("*_cleanup.json"))+[r/"extension_execution.json"]
if (r/"refined/summary.json").exists():files.append(r/"refined/summary.json")
hashes={str(p.relative_to(r)).replace(chr(92),"/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(r/"retrieval_hashes.json").write_text(json.dumps(hashes,indent=2));files.append(r/"retrieval_hashes.json")
with zipfile.ZipFile(r/"extension_results.zip","w",compression=zipfile.ZIP_STORED) as z:
 for p in files:z.write(p,str(p.relative_to(r)))
print(json.dumps(receipt),flush=True)
