"""Create/verify portable read-only file identity lock; never train."""
import csv,json,hashlib,sys,zipfile,zlib,io
from pathlib import Path
from PIL import Image,ImageOps
from core import sha
HERE=Path(__file__).resolve().parent
CONTRACT=HERE.parent/'public_source_contract_r1_20261009'
DEFAULT_ROOTS={'METU':'/Users/wenxiaofang/Downloads/METU_recovered_20261009','BuildCrack':'/Users/wenxiaofang/Downloads/BuildCrack_official_20261009'}
PINNED={'metu_group_split_r1.csv':'82b0b89fb91aaecbd58990293445a4570ea7895af30885c723f4928d79f6e67c','buildcrack_external_role_r1.csv':'13bea360b7df5e5ba270f8610f4463d100503d10197305eb4e1464743a8c04bd','CODE_CONTRACT_R1.md':'4d5faa893c55337a3e126861cae34a2799d51da25be047f76759f23563229c44'}
PROVENANCE={'buildcrack_official_md5':'bca16a248aa884661f69367cbcc80dae','metu_archive_receipt_sha256':'720d0b82efc02802396f2b871e5fae5017a61a99affb1c99e493ed656f2ec842','metu_crc_checked':916}
def canonical():
 for name,h in PINNED.items():
  if sha(CONTRACT/name)!=h:raise ValueError('Canonical contract/roles changed')
 out={}
 for r in csv.DictReader(io.StringIO((CONTRACT/'metu_group_split_r1.csv').read_text())):out[('METU',r['stem'])]=(r['split'],r['candidate_group'])
 for r in csv.DictReader(io.StringIO((CONTRACT/'buildcrack_external_role_r1.csv').read_text())):out[('BuildCrack',Path(r['filename']).stem)]=(r['role'],r['candidate_family_NOT_verified'])
 return out

def provenance(roots):
 archive=Path('/Users/wenxiaofang/Downloads/BuildCrack_official_20261009.zip')
 if hashlib.md5(archive.read_bytes()).hexdigest()!='bca16a248aa884661f69367cbcc80dae':raise ValueError('BuildCrack official archive mismatch')
 with zipfile.ZipFile(archive) as z:
  for name in z.namelist():
   if name.endswith('.png') and not name.startswith('__MACOSX/'):
    rel=Path(*Path(name).parts[1:]);data=(Path(roots['BuildCrack'])/rel).read_bytes()
    if len(data)!=z.getinfo(name).file_size or zlib.crc32(data)!=z.getinfo(name).CRC:raise ValueError('BuildCrack extracted file changed')
 receipt=HERE.parent/'METU_RECOVERED_RAR_CHECK_2026-10-09.json'
 if sha(receipt)!=PROVENANCE['metu_archive_receipt_sha256']:raise ValueError('Recovery evidence changed')
 records=json.loads(receipt.read_text())['records'];checked=0
 for r in records:
  if r.get('name','').lower().endswith(('.jpg','.jpeg')):
   data=(Path(roots['METU'])/r['name']).read_bytes()
   if len(data)!=r['unpacked_size'] or zlib.crc32(data)!=r['expected_data_crc32']:raise ValueError('METU recovery content changed')
   checked+=1
 if checked!=916:raise ValueError('Incomplete recovery provenance')
 return {'buildcrack_official_md5':'bca16a248aa884661f69367cbcc80dae','metu_archive_receipt_sha256':sha(receipt),'metu_crc_checked':checked}

def create(roots,destination):
 origin=provenance(roots)
 m=list(csv.DictReader(io.StringIO((CONTRACT/'metu_group_split_r1.csv').read_text())));b=list(csv.DictReader(io.StringIO((CONTRACT/'buildcrack_external_role_r1.csv').read_text())))
 assert sha(CONTRACT/'metu_group_split_r1.csv')=='82b0b89fb91aaecbd58990293445a4570ea7895af30885c723f4928d79f6e67c'
 rows=[]
 for source,raw in [('METU',m),('BuildCrack',b)]:
  root=Path(roots[source])
  for r in raw:
   if source=='METU':
    stem=r['stem'];a=list((root/'rgb').glob(stem+'.*'));y=list((root/'BW').glob(stem+'.*'));role=r['split'];group=r['candidate_group']
   else:
    stem=Path(r['filename']).stem;a=[root/'images'/r['filename']];y=[root/'labels'/r['filename']];role=r['role'];group=r['candidate_family_NOT_verified']
   if len(a)!=1 or len(y)!=1:raise ValueError('Ambiguous input')
   with Image.open(a[0]) as im:im=ImageOps.exif_transpose(im);shape=[im.height,im.width]
   with Image.open(y[0]) as im:
    if [im.height,im.width]!=shape or im.getexif().get(274,1)!=1:raise ValueError('Reference geometry changed')
   rows.append({'id':stem,'source':source,'role':role,'group':group,'image':str(a[0].relative_to(root)),'mask':str(y[0].relative_to(root)),'image_sha256':sha(a[0]),'mask_sha256':sha(y[0]),'shape':shape})
 lock={'schema':'hq-r1','provenance':origin,'rows':rows,'contract_sha256':sha(CONTRACT/'CODE_CONTRACT_R1.md'),'roles_sha256':{n:sha(CONTRACT/n) for n in ['metu_group_split_r1.csv','buildcrack_external_role_r1.csv']}}
 validate(lock,roots,check_files=False)
 with Path(destination).open('x') as f:json.dump(lock,f,indent=2)
 print(json.dumps({'rows':len(rows),'lock_sha256':sha(destination)}))
def validate(lock,roots,check_files=True):
 expected=canonical()
 if lock.get("provenance")!=PROVENANCE:raise ValueError("Unverified provenance record")
 if lock.get('contract_sha256')!=PINNED['CODE_CONTRACT_R1.md'] or lock.get('roles_sha256')!={n:PINNED[n] for n in ['metu_group_split_r1.csv','buildcrack_external_role_r1.csv']}:raise ValueError('Unpinned lock contract')
 rows=lock['rows'];seen=set();paths=set();content={};groups={};counts={} 
 for r in rows:
  key=(r['source'],r['id'])
  if key in seen:raise ValueError('Duplicate ID')
  if expected.get(key)!=(r['role'],r['group']):raise ValueError('Unknown or reassigned canonical ID')
  seen.add(key);counts[(r['source'],r['role'])]=counts.get((r['source'],r['role']),0)+1
  if r['source']=='BuildCrack' and r['role']!='external_diagnostic':raise ValueError('External leakage')
  g=(r['source'],r['group']);groups.setdefault(g,set()).add(r['role'])
  for kind in ['image','mask']:
   p=Path(r[kind])
   if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe path')
   expected_dir=('rgb' if kind=='image' else 'BW') if r['source']=='METU' else ('images' if kind=='image' else 'labels')
   if p.parent.as_posix()!=expected_dir or p.stem!=r['id']:raise ValueError('Noncanonical file path')
   pathkey=(r['source'],str(p))
   if pathkey in paths:raise ValueError('Repeated file path')
   paths.add(pathkey)
   if kind=='image':
    digest=r.get('image_sha256')
    if not digest:raise ValueError('Missing content identity')
    if digest in content and content[digest]!=r['role']:raise ValueError('Image content crosses roles')
    content[digest]=r['role']
   if check_files and sha(Path(roots[r['source']])/p)!=r[kind+'_sha256']:raise ValueError('Input content changed')
 if any(len(v)!=1 for v in groups.values()):raise ValueError('Group leakage')
 if counts!={('METU','train'):316,('METU','validation'):62,('METU','internal_test'):80,('BuildCrack','external_diagnostic'):358}:raise ValueError('Inventory/role changed')
 return rows
if __name__=='__main__':create(DEFAULT_ROOTS,sys.argv[1])
