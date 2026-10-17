"""Validate preservation, notes, visibility and rendering of the shortened deck."""
from pathlib import Path
from zipfile import ZipFile
import json,xml.etree.ElementTree as E
from PIL import Image,ImageChops
from pypdf import PdfReader

R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');W=R/'local_archive/fyr_ppt_15slide_revision_20261017';O=R/'local_archive/fyr_ppt_evidence_revision_20261017'
S=json.loads((W/'build/content_final.json').read_text());assert len(S)==61
z=ZipFile(W/'output/Wennie_Wan_First_Year_Assessment_15_Main_v3.pptx');old=ZipFile(O/'output/Wennie_Wan_First_Year_Assessment_Evidence_v6.pptx')
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
visible=[];table_pages=[]
def note(arc,n):
 root=E.fromstring(arc.read(f'ppt/notesSlides/notesSlide{n}.xml'))
 return ' '.join(t.text or '' for t in root.findall('.//a:t',ns))
for i,d in enumerate(S,1):
 root=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
 if root.get('show','1')!='0':visible.append(i)
 if root.findall('.//a:tbl',ns):table_pages.append(i)
 text=note(z,i);assert d['en'] in text and d['zh'] in text and 'Sources' in text,i
 a=Image.open(W/f'review/final_slides/{i:02d}.png').convert('RGB')
 b=Image.open(W/f'review/roundtrip/{i:02d}.png').convert('RGB')
 assert not ImageChops.difference(a,b).getbbox(),('roundtrip',i)
 if i>15:
  j=d['backup_original_slide'];b=Image.open(O/f'review/final_slides/{j:02d}.png').convert('RGB')
  assert not ImageChops.difference(a.crop((0,0,1280,660)),b.crop((0,0,1280,660))).getbbox(),('preservation',i,j)
  assert text==note(old,j),('backup notes',i,j)
assert visible==list(range(1,16))
assert sorted(d['backup_original_slide'] for d in S[15:])==list(range(1,47))
states=json.loads((W/'review/roundtrip_visibility.json').read_text())
assert [r['number'] for r in states if not r['hidden']]==visible
pages=PdfReader(W/'output/Wennie_Wan_15_Main_Bilingual_Notes.pdf').pages;assert len(pages)==15
assert all('English narration' in p.extract_text() and 'Related detailed slides:' in p.extract_text() for p in pages)
receipt=json.loads((W/'review/finalization_v3.json').read_text())
assert receipt['packageIntegrity']['status']=='pass' and receipt['presentationLayout']['exitCode']==0
result=dict(visible_main_slides=visible,hidden_backup_count=46,total_slides=61,all_46_original_pages_preserved=True,backup_notes_unchanged=True,backup_body_pixels_unchanged=True,roundtrip_all_61_pages_identical=True,all_61_pages_bilingual=True,main_PDF_pages=15,native_table_pages=table_pages,english_main_words=sum(len(d['en'].split()) for d in S[:15]),native_PowerPoint_opened=False,new_training_inference_or_solver=False,report_and_Overleaf_changed=False)
(W/'review/delivery_validation_v3.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
