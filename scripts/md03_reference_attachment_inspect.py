"""Read author scripts, table headers and MAT structure, never execute author code."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

OUT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/reference_attachment_check_20261020/R001')
BUNDLED='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'


def workbook_schema(path):
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            for s in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns):
                strings.append(''.join(t.text or '' for t in s.findall('.//m:t',ns)))
        sheets=ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns)
        rel={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result=[]
        for s in sheets:
            rid=s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target=rel[rid];target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            tree=ET.fromstring(z.read(target)); cells=[]
            for row in tree.findall('m:sheetData/m:row',ns):
                if int(row.attrib['r'])>12:break
                for c in row.findall('m:c',ns):
                    v=c.find('m:v',ns); text=c.find('m:is',ns)
                    value=strings[int(v.text)] if c.attrib.get('t')=='s' and v is not None else (
                        ''.join(t.text or '' for t in text.findall('.//m:t',ns)) if text is not None else (v.text if v is not None else None))
                    if value is not None:cells.append(dict(cell=c.attrib['r'],value=value,formula=c.findtext('m:f',default=None,namespaces=ns)))
            dim=tree.find('m:dimension',ns)
            result.append(dict(sheet=s.attrib['name'],dimension=dim.attrib if dim is not None else None,first12rows=cells))
        return dict(sheets=result,all_shared_strings=strings,embedded_media=[n for n in z.namelist() if n.startswith('xl/media/')])


def main():
    from scipy.io import loadmat
    import numpy as np
    assert not (OUT/'schema_and_text.json').exists()
    report=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                author_code_executed=False,forecast_or_image_processing=False,archives=[])
    for file in ['Compression test data.zip','Four point bending test data.zip']:
        with zipfile.ZipFile(OUT/file) as z:
            members=[n for n in z.namelist() if not n.startswith('__MACOSX/') and not n.endswith('/') and Path(n).name!='.DS_Store']
            items=[]
            for n in members:
                assert not Path(n).is_absolute() and '..' not in Path(n).parts
                assert Path(n).suffix in ('.m','.txt','.csv','.mat','.xlsx')
                payload=z.read(n);dest=OUT/'unpacked'/n
                dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(payload)
                item=dict(member=n,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),local=str(dest))
                if n.endswith('.m'):item['source_text']=payload.decode('utf-8-sig')
                elif n.endswith(('.txt','.csv')):
                    lines=payload.decode('utf-8-sig',errors='replace').splitlines()
                    item['first_line']=lines[0] if lines else ''
                    item['first_line_is_header']=bool(lines and re.search('[A-Za-z]',lines[0]))
                    item['line_count']=len(lines)
                elif n.endswith('.xlsx'):
                    item['schema']=json.loads(subprocess.check_output([BUNDLED,__file__,'--xlsx-schema',str(dest)],text=True))
                elif n.endswith('.mat'):
                    data=loadmat(io.BytesIO(payload),simplify_cells=True)['beamData']; beams={}
                    for name,b in data.items():
                        shapes={}
                        def walk(value,path):
                            if isinstance(value,dict):
                                for k,v in value.items():walk(v,path+'.'+k)
                            elif isinstance(value,np.ndarray):shapes[path]=dict(shape=list(value.shape),dtype=str(value.dtype))
                            else:shapes[path]=dict(type=type(value).__name__)
                        walk(b,name)
                        td=b['testData']
                        maps={k:np.atleast_1d(td[k]).astype(int).tolist() for k in ['missing','present','time','n']}
                        first=int(td['firstPhoto']);present=np.asarray(maps['present']);times=np.asarray(maps['time'])
                        beams[name]=dict(fields=list(b),shapes=shapes,colheaders=b['colheaders'].tolist(),
                            extensometer_heading=str(b['textdata'][0,0]),firstPhoto=first,folderPath=td['folderPath'],
                            mapping_metadata=maps,dic_time=np.atleast_1d(b['time']).astype(int).tolist(),
                            candidate_time_rule='5*(present-firstPhoto+1)',
                            candidate_time_rule_exact=bool(np.array_equal(times,5*(present-first+1))))
                    item['mat_structure']=beams
                items.append(item)
            report['archives'].append(dict(archive=file,substantive_member_count=len(members),items=items))
    (OUT/'schema_and_text.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--xlsx-schema':print(json.dumps(workbook_schema(Path(sys.argv[2]))))
    else:main()
