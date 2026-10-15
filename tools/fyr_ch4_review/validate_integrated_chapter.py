"""Local content/link/layout checks for the integrated chapter; no scientific rerun."""
from pathlib import Path
import json,re,subprocess,xml.etree.ElementTree as ET
R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');O=R/'local_archive/report_ch4_rewrite_integrated_20261015';V=O/'review'
md=(O/'draft/Chapter4_Integrated_Rewrite.md').read_text()
text=subprocess.check_output(['pdftotext','-layout',str(O/'draft/Chapter4_Integrated_Rewrite.pdf'),'-'],text=True)
(V/'pdf_text.txt').write_text(text)
pages=[p for p in text.split('\f') if p.strip()]
assert len(pages)>=10 and all(len(p.strip())>60 for p in pages)
assert re.findall(r'^## (4\.\d+)',md,flags=re.M)==['4.'+str(i) for i in range(1,8)]
figs=re.findall(r'^\*Figure 4\.(\d+)\.',md,flags=re.M);tabs=re.findall(r'^\*Table 4\.(\d+)\.',md,flags=re.M)
assert figs==[str(i) for i in range(1,13)] and tabs==[str(i) for i in range(1,10)]
for i in range(1,13):assert re.search(r'Figure\s+4\.'+str(i)+r':',text)
for i in range(1,10):assert re.search(r'Table\s+4\.'+str(i)+r':',text)
assert all(Path(p).exists() for p in re.findall(r'!\[[^]]*\]\(([^)]+)\)',md))
assert not re.search(r'\b(PASS|FAIL|TODO|TBD|EVIDENCE NEEDED)\b',md)
log=(V/'chapter4_preview.log').read_text();assert not re.search(r'Overfull|Undefined control sequence|LaTeX Error|undefined references',log)
subprocess.run(['pdftotext','-bbox',str(O/'draft/Chapter4_Integrated_Rewrite.pdf'),str(V/'pdf_bbox.html')],check=True)
x=ET.fromstring(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',(V/'pdf_bbox.html').read_text()));ns={'x':'http://www.w3.org/1999/xhtml'}
info=subprocess.check_output(['pdfinfo','-f','1','-l',str(len(pages)),str(O/'draft/Chapter4_Integrated_Rewrite.pdf')],text=True)
rotations={int(n):int(r) for n,r in re.findall(r'Page\s+(\d+) rot:\s+(\d+)',info)}
for page_id,p in enumerate(x.findall('.//x:page',ns),1):
 width,height=float(p.attrib['width']),float(p.attrib['height'])
 if rotations.get(page_id,0) in [90,270]:width,height=height,width
 for w in p.findall('x:word',ns):
  assert 0<=float(w.attrib['xMin'])<=float(w.attrib['xMax'])<=width+.2,(w.text,w.attrib,width)
  assert 0<=float(w.attrib['yMin'])<=float(w.attrib['yMax'])<=height+.2,(w.text,w.attrib,height)
v={'chapter_sections':7,'figures':12,'tables':9,'PDF_pages':len(pages),'all_captions_in_PDF':True,'all_image_paths_exist':True,'no_LaTeX_errors_or_overfull_boxes':True,'all_text_within_page_bounds':True,'word_count_including_captions_tables':len(md.split()),'new_numerical_experiment':False,'overleaf_changed':False,'original_drafts_preserved':True,'review_scope':'designated local chapter, fatigue-field review and linked existing analysis outputs; no new literature or whole-thesis compilation'}
(V/'validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2))
