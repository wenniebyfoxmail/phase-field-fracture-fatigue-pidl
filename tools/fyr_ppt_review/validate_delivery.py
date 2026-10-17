from pathlib import Path
from zipfile import ZipFile
import json,xml.etree.ElementTree as E
from pypdf import PdfReader
from PIL import Image,ImageChops
W=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_process_revision_20261017');ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
p=W/'output/Wennie_Wan_First_Year_Assessment_Revised_v2.pptx';texts={};notes={};native={}
with ZipFile(p) as z:
 assert z.testzip() is None
 for i in range(1,26):
  s=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'));texts[i]=' '.join(t.text or '' for t in s.findall('.//a:t',ns));native[i]=len(s.findall('.//a:tbl',ns))
  n=E.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml'));notes[i]=' '.join(t.text or '' for t in n.findall('.//a:t',ns));assert 'English narration' in notes[i] and '中文对照' in notes[i]
 assert 'Wennie Wan' in texts[1] and 'Brian Sheil' in texts[1]
 assert 'trial fatigue' in texts[6] and 'fixed old fatigue factor' in texts[7]
 assert '(x, y)' in texts[7] and 'boundary constraints' in texts[7]
 assert all(native[i]==1 for i in [8,9,11,17,19])
 assert '3 physical cycles' in texts[11] and '3 raw loading' not in texts[11]
 assert all(k in texts[11] for k in ['84','85','89','87','88','92'])
 assert '29.87%' in texts[13] and '16.90%' in texts[13]
 assert '0.02712' in texts[14] and '0.03617' in texts[14]
 assert not any(x in texts[i] for i in range(1,23) for x in ['state alignment open','Historical eight-step','3 raw loading substeps','Xiaofang Wen'])
 same=[]
 for i in range(1,26):
  a=Image.open(W/f'review/final_slides/{i:02d}.png').convert('RGB');b=Image.open(W/f'review/roundtrip/{i:02d}.png').convert('RGB');assert a.size==b.size and not ImageChops.difference(a,b).getbbox();same.append(i)
reader=PdfReader(W/'output/Wennie_Wan_Bilingual_Learning_Notes_Revised.pdf');assert len(reader.pages)==25
assert all('English narration' in (pg.extract_text() or '') for pg in reader.pages)
res={'slides':25,'main_slides':22,'backup_slides':3,'native_process_slides':[6,7],'cycle_levels_slide':8,'native_table_slides':[8,9,11,17,19],'bilingual_PPT_notes':25,'bilingual_PDF_pages':25,'roundtrip_pixel_identical_slides':same,'source_deck_preserved':True,'report_or_Overleaf_changed':False,'new_experiments':False,'visual_QA':'All source and final slides inspected individually; notes PDF checked as contact sheet with full-size process/cycle pages.','native_PowerPoint_application_test':False}
(W/'review/content_validation.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
