"""Launcher-only artificial checks: never invokes a scientific model or solver."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import pytest

spec=importlib.util.spec_from_file_location('d013_launch',Path(__file__).with_name('launch_d013.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def authorization():
    return dict(user_approved_final_execution=True,scope=m.SCOPE,package_id=m.PACK,package_manifest_sha256='fixture',
        execution_commit=m.SCIENCE,run_output=str(m.OUTPUT),control_root=str(m.CONTROL),user_approval_quote='ARTIFICIAL TEST ONLY',
        training_authorized=False,remote_actions_authorized=False)

@pytest.mark.parametrize('case',['unapproved','package','source','path','quote','training','remote'])
def test_approval_is_version_source_path_and_scope_bound(case):
    a=authorization()
    if case=='unapproved':a['user_approved_final_execution']=False
    if case=='package':a['package_manifest_sha256']='different'
    if case=='source':a['execution_commit']='different'
    if case=='path':a['run_output']='/tmp/wrong'
    if case=='quote':a['user_approval_quote']=''
    if case=='training':a['training_authorized']=True
    if case=='remote':a['remote_actions_authorized']=True
    with pytest.raises(m.PackageError):m.validate_authorization(a,'fixture')

def test_default_cli_never_spawns_or_extracts(monkeypatch):
    monkeypatch.setattr(sys,'argv',['launch_d013.py'])
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:pytest.fail('spawn forbidden'))
    monkeypatch.setattr(m,'safe_extract',lambda *a,**k:pytest.fail('extraction forbidden'))
    with pytest.raises(SystemExit):m.main()

def test_unapproved_template_stops_before_preflight_or_writes(tmp_path,monkeypatch):
    path=tmp_path/'auth.json';m.write(path,dict(user_approved_final_execution=False))
    monkeypatch.setattr(sys,'argv',['launch_d013.py','--authorization',str(path)])
    monkeypatch.setattr(m,'sha',lambda *a:'fixture')
    monkeypatch.setattr(m,'validate_package',lambda *a:pytest.fail('no preflight before approval'))
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:pytest.fail('spawn forbidden'))
    with pytest.raises(m.PackageError,match='approval'):m.main()

@pytest.mark.parametrize('kind',['absolute','parent','symlink','valid'])
def test_source_tar_paths_and_links(tmp_path,kind):
    archive=tmp_path/'fixture.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        info=tarfile.TarInfo({'absolute':'/source/a','parent':'source/../a','symlink':'source/a','valid':'source/a'}[kind])
        if kind=='symlink':info.type=tarfile.SYMTYPE;info.linkname='/tmp/a';tf.addfile(info)
        else:info.size=3;tf.addfile(info,io.BytesIO(b'abc'))
    if kind=='valid':m.safe_extract(archive,tmp_path/'out');assert (tmp_path/'out/source/a').read_bytes()==b'abc'
    else:
        with pytest.raises(m.PackageError):m.safe_extract(archive,tmp_path/'out')

def test_manifest_hashes_and_file_set_are_closed(tmp_path):
    f=tmp_path/'a';f.write_bytes(b'abc')
    manifest=dict(package_id=m.PACK,science_commit=m.SCIENCE,science_tree_sha256=m.TREE,
        files={'a':dict(bytes=3,sha256=m.sha(f))})
    m.write(tmp_path/'package_manifest.json',manifest)
    m.validate_package(tmp_path)
    f.write_bytes(b'bad')
    with pytest.raises(m.PackageError,match='hash'):m.validate_package(tmp_path)
    f.write_bytes(b'abc');(tmp_path/'extra').write_bytes(b'x')
    with pytest.raises(m.PackageError,match='file set'):m.validate_package(tmp_path)

def test_input_hash_and_archive_boundary(tmp_path):
    f=tmp_path/'local_archive/experiments/a';f.parent.mkdir(parents=True);f.write_bytes(b'abc')
    row=dict(path=str(f.relative_to(tmp_path)),bytes=3,sha256=m.sha(f))
    assert m.input_admission(tmp_path,dict(files=[row]))['files']==1
    f.write_bytes(b'bad')
    with pytest.raises(m.PackageError,match='changed'):m.input_admission(tmp_path,dict(files=[row]))
    row['path']='../outside'
    with pytest.raises(m.PackageError,match='outside'):m.input_admission(tmp_path,dict(files=[row]))

def test_numeric_JSON_and_environment_fail_closed(tmp_path):
    f=tmp_path/'bad.json';f.write_text('{"budget": NaN}')
    with pytest.raises(m.PackageError):m.read(f)
    with pytest.raises(m.PackageError):m.environment_admission(dict(versions={},python='wrong'))

def test_combined_archive_cap_stops_owned_group(tmp_path):
    import subprocess,time,os
    a=tmp_path/'control';b=tmp_path/'output';a.mkdir();b.mkdir()
    (a/'a').write_bytes(b'x'*60);(b/'b').write_bytes(b'x'*60)
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)'],start_new_session=True)
    with pytest.raises(m.PackageError,match='combined'):
        m.supervise_child(child,(a,b),time.monotonic()+5,cap=100,poll=.01)
    assert child.poll() is not None and child.d013_supervision['observed_combined_archive_bytes']==120

def test_owned_group_global_deadline_and_success_are_distinct(tmp_path):
    import subprocess,time
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)'],start_new_session=True)
    with pytest.raises(m.PackageError,match='deadline'):
        m.supervise_child(child,(tmp_path,),time.monotonic()+.05,poll=.01)
    assert child.poll() is not None
    child=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True)
    record=m.supervise_child(child,(tmp_path,),time.monotonic()+5,poll=.01)
    assert record['exit_code']==0 and record['stop'] is None
