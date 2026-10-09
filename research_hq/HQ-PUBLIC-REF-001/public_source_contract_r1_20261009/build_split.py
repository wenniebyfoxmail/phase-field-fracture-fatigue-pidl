"""Deterministic group assignment; not an independence certificate or launcher."""
from pathlib import Path
import csv,hashlib,json
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'metu_full_group_audit_20261009/conservative_group_manifest_r0.csv'
def build():
 rows=list(csv.DictReader(SOURCE.open()));groups=sorted({r['candidate_group'] for r in rows})
 assert len(rows)==458 and len({r['stem'] for r in rows})==458 and len(groups)==392
 assert all(r['split']=='UNASSIGNED' and r['site_id']=='UNKNOWN' for r in rows)
 seed='20261009'
 ordered=sorted(groups,key=lambda g:(hashlib.sha256((seed+':'+g).encode()).hexdigest(),g))
 assignment={g:('train' if i<274 else 'validation' if i<333 else 'internal_test') for i,g in enumerate(ordered)}
 result=[dict(r,split=assignment[r['candidate_group']]) for r in rows]
 target=ROOT/'metu_group_split_r1.csv'
 with target.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=result[0].keys());w.writeheader();w.writerows(result)
 summary={s:{'groups':sum(v==s for v in assignment.values()),'images':sum(r['split']==s for r in result)} for s in ['train','validation','internal_test']}
 receipt={'seed':seed,'algorithm':'lexicographic SHA256(seed:group), ties group name; 274/59/59 groups via largest remainder','source_manifest_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'split_manifest_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'counts':summary,'site_independence':'UNKNOWN','status':'DESIGN_ASSIGNMENT_NOT_TRAINING_AUTHORIZATION'}
 (ROOT/'split_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
if __name__=='__main__':build()
