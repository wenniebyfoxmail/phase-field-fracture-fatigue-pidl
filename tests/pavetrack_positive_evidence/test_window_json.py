import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts/pavetrack_positive_evidence'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load('window_base','scoped_json.py');window=load('window_fix','window_json.py');Fast=window.cursor_type(base.Cursor)

def parse(cls,path):
    checks=[];c=cls(path,lambda:checks.append(1))
    try:spans=dict(c.fields());result=list(c.selected_rows(spans['rows'],{'24'}))
    finally:c.close()
    return result,len(checks)

@pytest.mark.parametrize('size',[10,100,1000])
def test_same_selected_rows_with_bounded_real_refills(tmp_path,size):
    rows=[dict(reid='24' if i%2 else 'sealed',image_id=str(i),split='train',payload={'shape':[1,2,3],'s':'x'*100}) for i in range(size)]
    path=tmp_path/'rows.json';path.write_text(json.dumps({'rows':rows}));slow,old=parse(base.Cursor,path);fast,new=parse(Fast,path)
    assert fast==slow==[r for r in rows if r['reid']=='24']
    assert new<old/4 and new<=12*(path.stat().st_size//65536+1)

def test_cross_window_large_value_and_preserved_following_fields(tmp_path):
    rows=[dict(reid='sealed',image_id='s',payload='x'*70000),dict(reid='24',image_id='a',payload='y'*140000),dict(reid='24',image_id='b',payload={'tail':True})]
    path=tmp_path/'large.json';path.write_text(json.dumps({'rows':rows,'after':[3]}));assert parse(Fast,path)[0]==parse(base.Cursor,path)[0]==rows[1:]

def test_excluded_payload_never_deserialized(tmp_path,monkeypatch):
    path=tmp_path/'scope.json';path.write_text(json.dumps({'rows':[dict(reid='sealed',image_id='x',payload='DO_NOT_DECODE'),dict(reid='24',image_id='y',payload='ok')]}));original=json.loads
    def checked(raw,*a,**kw):
        if 'DO_NOT_DECODE' in (raw.decode() if isinstance(raw,bytes) else raw):pytest.fail('excluded payload decoded')
        return original(raw,*a,**kw)
    monkeypatch.setattr(window.json,'loads',checked);assert parse(Fast,path)[0][0]['image_id']=='y'

def test_real_refill_callback_still_stops_resource_excess(tmp_path):
    path=tmp_path/'stop.json';path.write_text('{"rows":[]}')
    def stop():raise RuntimeError('RSS_CAP')
    c=Fast(path,stop)
    try:
        with pytest.raises(RuntimeError,match='RSS_CAP'):list(c.fields())
    finally:c.close()

def test_cap_and_truncation_and_seek_outside_window(tmp_path):
    path=tmp_path/'cap.json';path.write_text('"abc"');c=Fast(path)
    try:
        c.peek()
        with pytest.raises(ValueError,match='size cap'):c.decode((0,5),cap=3)
        with pytest.raises(ValueError,match='truncated'):c.decode((0,8))
        c.seek(100);assert c.peek() is None
        c.seek(0);assert c.decode((0,5))=='abc' and c.take()==34
    finally:c.close()
