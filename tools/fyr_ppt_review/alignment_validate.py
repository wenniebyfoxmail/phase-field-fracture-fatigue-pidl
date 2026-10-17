"""Check scope, preservation, notes and roundtrip of the targeted revision."""
from pathlib import Path
from zipfile import ZipFile
import json,posixpath,xml.etree.ElementTree as E
from PIL import Image,ImageChops
from pypdf import PdfReader

R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive')
W=R/'fyr_ppt_alignment_update_20261017';OLD=R/'fyr_ppt_15slide_revision_20261017'
S=json.loads((W/'build/content_final.json').read_text());assert len(S)==70
z=ZipFile(W/'output/Wennie_Wan_First_Year_Assessment_15_Main_v5.pptx')
old=ZipFile(OLD/'output/Wennie_Wan_First_Year_Assessment_15_Main_v3.pptx')
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
def text(arc,i):
    return [t.text or '' for t in E.fromstring(arc.read(f'ppt/slides/slide{i}.xml')).findall('.//a:t',ns)]
def note(arc,i):
    return ' '.join(t.text or '' for t in E.fromstring(arc.read(f'ppt/notesSlides/notesSlide{i}.xml')).findall('.//a:t',ns))
visible=[];tables=[]
for i,d in enumerate(S,1):
    xml=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
    if xml.get('show','1')!='0':visible.append(i)
    if xml.findall('.//a:tbl',ns):tables.append(i)
    n=note(z,i);assert d['en'] in n and d['zh'] in n and 'Sources' in n,i
    if i<=6 or 16<=i<=61:
        assert text(z,i)==text(old,i),('unrelated text changed',i)
        assert note(z,i)==note(old,i),('unrelated notes changed',i)
        a=Image.open(W/f'review/slides/{i:02d}.png').convert('RGB')
        b=Image.open(OLD/f'review/final_slides/{i:02d}.png').convert('RGB')
        assert ImageChops.difference(a,b).getbbox() is None,('unrelated render changed',i)
    if i>=62:
        j=d['backup_original_main']
        assert note(z,i)==note(old,j),('old main notes changed',i,j)
        # Only the page marker is intentionally replaced by B47–B55.
        a=text(z,i);b=text(old,j)
        a=[t for t in a if t!=d['backup_label']];b=[t for t in b if t!=f'{j:02d}']
        assert a==b,('old main body text changed',i,j)
        ai=Image.open(W/f'review/slides/{i:02d}.png').convert('RGB').crop((0,0,1280,660))
        bi=Image.open(OLD/f'review/final_slides/{j:02d}.png').convert('RGB').crop((0,0,1280,660))
        assert ImageChops.difference(ai,bi).getbbox() is None,('old main body render changed',i,j)
assert visible==list(range(1,16))
assert all(i in tables for i in [7,11,13,14])
for i in [7,8,9,10]:
    # Scientific images are the same embedded bytes, even when placement changes.
    def images(arc,n):
        rr=E.fromstring(arc.read(f'ppt/slides/_rels/slide{n}.xml.rels'))
        paths=[r.get('Target') for r in rr if r.get('Type','').endswith('/image')]
        return sorted(arc.read(t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join('ppt/slides',t))) for t in paths)
    assert images(z,i)==images(old,i),('scientific image changed',i)
pages=PdfReader(W/'output/Wennie_Wan_15_Main_Bilingual_Notes_v5.pdf').pages
assert len(pages)==15,len(pages)
assert all('English narration' in p.extract_text() and 'Related backups:' in p.extract_text() for p in pages)
receipt=json.loads((W/'review/finalization_v5.json').read_text())
assert receipt['packageIntegrity']['status']=='pass'
assert receipt['presentationLayout']['exitCode']==0
states=json.loads((W/'review/roundtrip_visibility.json').read_text())
assert [d['number'] for d in states if not d['hidden']]==visible
for i in range(1,71):
    a=Image.open(W/f'review/slides/{i:02d}.png').convert('RGB')
    b=Image.open(W/f'review/roundtrip/{i:02d}.png').convert('RGB')
    assert ImageChops.difference(a,b).getbbox() is None,('roundtrip',i)
result={'main_slides':15,'hidden_backups':55,'total_slides':70,'changed_main_slides':list(range(7,16)),
 'old_46_backups_unchanged':True,'old_main7_to15_preserved_as':'B47–B55',
 'first6_slides_and_notes_unchanged':True,'all70_slides_bilingual':True,'numerical_images_unchanged':True,
 'native_tables_preserved':True,'roundtrip70_slides_identical':True,'main_notes_pdf_pages':15,
 'english_main_words':sum(len(d['en'].split()) for d in S[:15]),'native_PowerPoint_opened':False,
 'experiments_started':False,'Overleaf_changed':False}
(W/'review/delivery_validation_v5.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
