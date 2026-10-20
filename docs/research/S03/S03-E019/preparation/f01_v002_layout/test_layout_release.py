"""Artificial XML and memory-only IO checks. Never opens real SVGs or arrays."""
import time
START = time.monotonic()
import argparse
import copy
import hashlib
import io
import os
from pathlib import Path
import sys
import types
import unittest
import warnings
import xml.etree.ElementTree as ET
import pyexpat

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--code-sha',required=True)
parser.add_argument('--test-sha',required=True)
args = parser.parse_args()
HERE = Path(__file__).absolute().parent
code_path, test_path = HERE/'layout_release.py', Path(__file__).absolute()
code_bytes, test_bytes = code_path.read_bytes(), test_path.read_bytes()
if hashlib.sha256(code_bytes).hexdigest() != args.code_sha or hashlib.sha256(test_bytes).hexdigest() != args.test_sha:
    raise RuntimeError('STOP_ARTIFICIAL_SOURCE_IDENTITY_NO_RETRY')
if os.environ.get('CUDA_VISIBLE_DEVICES') != '' or any(os.environ.get(k) != '1' for k in (
    'OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS')):
    raise RuntimeError('STOP_ARTIFICIAL_SINGLE_CPU')
module = types.ModuleType('f01_layout_release_units'); module.__file__ = str(code_path)
exec(compile(code_bytes,str(code_path),'exec'),module.__dict__)
M, N = module, module.NS
warnings.simplefilter('error')
def audit(event, values):
    if event == 'open':
        p, mode, flags = values
        if not isinstance(p,(str,bytes,os.PathLike)) or os.fsdecode(p) not in {str(code_path),str(test_path)} or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise RuntimeError('STOP_ARTIFICIAL_FILE_IO_OUTSIDE_TWO_CODE_FILES')
    if event.startswith(('subprocess.','socket.')) or event in ('os.system','os.mkdir','os.remove','os.rename','os.rmdir','os.link','os.symlink'):
        raise RuntimeError('STOP_ARTIFICIAL_SIDE_EFFECT')
sys.addaudithook(audit)

def canvas(width,height):
    r = ET.Element(N+'svg',{'viewBox':f'0 0 {width} {height}','width':str(width),'height':str(height)})
    ET.SubElement(r,N+'rect',{'x':'0','y':'0','width':str(width),'height':str(height),'fill':'white'})
    ET.SubElement(r,N+'metadata').text = '{"fixture":"artificial, not DIC"}'
    return r

def residual_fixture():
    r = canvas(1460,730)
    for row in range(2):
        for col in range(4):
            ET.SubElement(r,N+'rect',{'x':str(90+300*col),'y':'415' if row else '170','width':'260','height':'110','stroke':'#555555'})
            labels = [('377' if row else '132','title'),('567' if row else '322','tick1'),
                      ('567' if row else '322','tick2'),('590' if row else '345','x-axis'),
                      ('419' if row else '174','y1'),('530' if row else '285','y2'),
                      ('613' if row else '368','y direction')]
            for y,value in labels:
                ET.SubElement(r,N+'text',{'x':str(100+300*col),'y':y}).text = value
            for point in range(2):
                ET.SubElement(r,N+'circle',{'cx':'101','cy':'430' if row else '185','r':'2.1','fill':'#123456',
                    'data-panel':f'{row}:{col}','data-point':str(point),'data-mm':'artificial-value',
                    'data-x-mm':'artificial-x','data-y-mm':'artificial-y'})
    ET.SubElement(r,N+'rect',{'x':'1330','y':'155','width':'22','height':'3.3','fill':'#abcdef','id':'artificial-colourbar'})
    ET.SubElement(r,N+'text',{'x':'1360','y':'162'}).text = 'artificial colourbar value'
    ET.SubElement(r,N+'text',{'x':'40','y':'695'}).text = 'artificial footer'
    return r

def ledger_fixture():
    r = canvas(1020,660)
    for arm in ('old','proxy','intact'):
        ET.SubElement(r,N+'rect',{'x':'220','y':'479.97','width':'80','height':'0.029214469610109317',
                    'fill':'#0072B2','data-arm':arm,'data-quantity':'J_Q_mm2','data-value':'1.25e-10'})
        ET.SubElement(r,N+'rect',{'x':'220','y':'200','width':'80','height':'279.97',
                    'fill':'#E69F00','data-arm':arm,'data-quantity':'gap2_mm2','data-value':'fixture-gap'})
        ET.SubElement(r,N+'circle',{'cx':'260','cy':'200','r':'5','fill':'black',
                    'data-arm':arm,'data-quantity':'J_k_mm2','data-value':'fixture-total'})
    ET.SubElement(r,N+'text',{'x':'40','y':'620'}).text = 'artificial ledger footer'
    return r

def signature(e):
    return (e.tag,tuple(sorted(e.attrib.items())),e.text,e.tail,tuple(signature(c) for c in e))

def fake_sources():
    note = b'# artificial\n\n'+M.GUIDE+b'fixture guide\n\n## Key numerical takeaway\n\nSAVED-TEXT-UNCHANGED\n\n'+M.RELATED+b'\n'
    return {'residuals.svg':ET.tostring(residual_fixture(),encoding='utf-8'),'square_ledger.svg':ET.tostring(ledger_fixture(),encoding='utf-8'),
            'residuals.sidecar_s01.md':note,'square_ledger.sidecar_s01.md':note}

class MemoryFS:
    def __init__(self): self.data, self.writes = {}, []
    def exists(self,path): return str(path) in self.data
    def read(self,path): return self.data[str(path)]
    def open(self,path,mode):
        if mode != 'xb' or self.exists(path): raise FileExistsError('artificial collision')
        owner, key = self,str(path)
        class Sink(io.BytesIO):
            def close(self):
                if not self.closed:
                    owner.data[key] = self.getvalue(); owner.writes.append(key)
                super().close()
        return Sink()

class Units(unittest.TestCase):
    def test_residual_canvas(self):
        out = M.residual_layout(residual_fixture(),2)
        self.assertEqual((out.get('viewBox'),out[0].get('height')),('0 0 1460 820','820'))
    def test_v_group_translation(self):
        out = M.residual_layout(residual_fixture(),2)
        g = out.find(N+'g'); self.assertEqual(g.get('transform'),'translate(0 70)')
        self.assertEqual(len(list(g.iter(N+'circle'))),8)
    def test_point_attributes_unchanged(self):
        src = residual_fixture(); out = M.residual_layout(src,2)
        self.assertEqual([e.attrib for e in src.iter(N+'circle')],[e.attrib for e in out.iter(N+'circle')])
    def test_source_not_mutated(self):
        src = residual_fixture(); before = signature(src); M.residual_layout(src,2)
        self.assertEqual(signature(src),before)
    def test_colourbar_unchanged(self):
        src = residual_fixture(); out = M.residual_layout(src,2)
        select = lambda r:[signature(e) for e in r if e.get('x') in ('1330','1360')]
        self.assertEqual(select(src),select(out))
    def test_footer_relocation(self):
        out = M.residual_layout(residual_fixture(),2)
        self.assertEqual([e.get('y') for e in out if e.text == 'artificial footer'],['785'])
    def test_wrong_point_scope_stops(self):
        with self.assertRaises(M.Stop): M.residual_layout(residual_fixture(),3)
    def test_wrong_canvas_stops(self):
        src = residual_fixture(); src.set('height','999')
        with self.assertRaises(M.Stop): M.residual_layout(src,2)
    def test_ledger_no_height_inflation(self):
        src = ledger_fixture(); out = M.ledger_layout(src)
        marks = lambda r:[signature(e) for e in r if e.tag in (N+'rect',N+'circle') and e.get('data-arm')]
        self.assertEqual(marks(src),marks(out))
    def test_literal_jq_labels(self):
        out = M.ledger_layout(ledger_fixture())
        labels = [e for e in out if e.get('data-layout-only') == 'saved-JQ-label']
        self.assertEqual([e.get('y') for e in labels],['585','607','629'])
        self.assertTrue(all('1.25e-10 mm^2' in e.text for e in labels))
    def test_ledger_canvas_footer(self):
        out = M.ledger_layout(ledger_fixture())
        self.assertEqual(out.get('height'),'720')
        self.assertEqual([e.get('y') for e in out if e.text == 'artificial ledger footer'],['690'])
    def test_missing_jq_stops(self):
        r = ledger_fixture(); r.remove(next(e for e in r if e.get('data-quantity') == 'J_Q_mm2'))
        with self.assertRaises(M.Stop): M.ledger_layout(r)
    def test_source_provenance_retained(self):
        src = fake_sources(); out = M.payloads(src,2)
        tree = ET.fromstring(out['residuals.svg'])
        self.assertEqual(tree.find(N+'metadata').text,'{"fixture":"artificial, not DIC"}')
        self.assertEqual(len(tree.findall(N+'metadata')),2)
    def test_companion_scientific_text_retained(self):
        out = M.payloads(fake_sources(),2)
        for stem in ('residuals','square_ledger'):
            self.assertIn(b'SAVED-TEXT-UNCHANGED',out[stem+'.md'])
            self.assertIn(str(M.OLD/'derived_receipt.json').encode(),out[stem+'.md'])
            self.assertNotIn(M.RELATED,out[stem+'.md'])
    def test_companion_missing_section_stops(self):
        with self.assertRaises(M.Stop): M.companion(b'wrong section','residuals')
    def test_xml_declaration_stops(self):
        with self.assertRaises(M.Stop): M.parse_svg(b'<!DOCTYPE svg><svg/>')
    def test_mapping_is_exact(self):
        src = fake_sources(); out = M.payloads(src,2); hashes = {n:M.sha(v) for n,v in src.items()}
        mapped = M.mapping(hashes,out)
        self.assertEqual(len(mapped),2)
        self.assertEqual(mapped[0]['figure_sha256'],M.sha(out['residuals.svg']))
        self.assertEqual(mapped[0]['source_companion_sha256'],hashes['residuals.sidecar_s01.md'])
    def test_exclusive_memory_write(self):
        fs = MemoryFS(); b = M.Budget(start=0,clock=lambda:1)
        M.exclusive_write('artificial',b'payload',b,fs.exists,fs.open,fs.read)
        self.assertEqual(fs.data,{'artificial':b'payload'})
    def test_existing_target_refused(self):
        fs = MemoryFS(); fs.data['artificial'] = b'old'
        with self.assertRaises(M.Stop):
            M.exclusive_write('artificial',b'new',M.Budget(0,lambda:1),fs.exists,fs.open,fs.read)
        self.assertEqual(fs.data['artificial'],b'old'); self.assertEqual(fs.writes,[])
    def test_open_race_no_retry(self):
        calls = []
        def fail(*a): calls.append(a); raise FileExistsError('artificial race')
        with self.assertRaises(FileExistsError):
            M.exclusive_write('artificial',b'new',M.Budget(0,lambda:1),lambda p:False,fail,lambda p:b'new')
        self.assertEqual(len(calls),1)
    def test_bad_readback_stops(self):
        fs = MemoryFS()
        with self.assertRaises(M.Stop):
            M.exclusive_write('artificial',b'new',M.Budget(0,lambda:1),fs.exists,fs.open,lambda p:b'bad')
    def test_exact_budget_stops(self):
        with self.assertRaises(M.Stop): M.Budget(0,lambda:60).check()
    def test_wrong_authority_stops(self):
        with self.assertRaises(M.Stop): M.authorize(M.OLD,Path('/artificial/wrong'))
    def test_completion_binding_and_json_duplicates(self):
        payload = M.json_bytes({'status':'artificial'})
        complete = M.strict_json(M.json_bytes({'receipt_sha256':M.sha(payload)}))
        self.assertEqual(complete['receipt_sha256'],M.sha(payload))
        with self.assertRaises(M.Stop): M.strict_json('{"same":1,"same":2}')

result = unittest.TextTestRunner(verbosity=2,failfast=True).run(unittest.defaultTestLoader.loadTestsFromTestCase(Units))
if not result.wasSuccessful() or result.skipped or result.testsRun != 24:
    raise SystemExit(1)
if time.monotonic()-START >= 60: raise RuntimeError('STOP_ARTIFICIAL_SOFT60S')
print('{"status":"ARTIFICIAL_XML_MEMORY_ONLY_24_PASS_NOT_VISUAL_QA","actual_svd":0,"actual_qr":0}',flush=True)
if time.monotonic()-START >= 60: raise RuntimeError('STOP_ARTIFICIAL_FINAL_SOFT60S')
