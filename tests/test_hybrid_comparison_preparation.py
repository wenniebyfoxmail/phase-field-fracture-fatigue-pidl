"""Preparation-only metadata/command tests; no SSH, fit or FEM execution."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import hybrid_runtime_inventory as inventory
import request_hybrid_runtime_inventory as request


def test_metadata_collection_restores_paths_and_never_imports_science(tmp_path,monkeypatch):
    import sys
    previous=list(sys.path)
    calls=[]
    def fake_dist(name):
        calls.append(name)
        return SimpleNamespace(version='1.2.3',locate_file=lambda _:tmp_path)
    monkeypatch.setattr(inventory.metadata,'distribution',fake_dist)
    # The full existing test suite has already imported science; isolate the
    # inventory's guard without unloading modules from the test interpreter.
    monkeypatch.setattr(inventory,'sys',SimpleNamespace(path=sys.path,modules={},executable='/usr/bin/python3'))
    result=inventory.collect(tmp_path)
    assert calls==list(inventory.PACKAGES) and sys.path==previous
    assert result['scientific_states_opened'] is False and result['gpu_seconds']==0


def test_missing_metadata_remains_missing_not_zero_or_substitution(tmp_path,monkeypatch):
    import sys
    def absent(name):raise inventory.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(inventory.metadata,'distribution',absent)
    monkeypatch.setattr(inventory,'sys',SimpleNamespace(path=list(sys.path),modules={},executable='test'))
    result=inventory.collect(tmp_path)
    assert all(v is None for v in result['runtime_metadata'].values())
    assert len(result['metadata_errors'])==7


def test_single_inventory_attempt_and_existing_receipt_prevents_ssh(tmp_path,monkeypatch):
    code=tmp_path/'code';(code/'tools').mkdir(parents=True)
    payload=code/'tools/hybrid_runtime_inventory.py';payload.write_text('print("metadata")\n')
    req=request.request_for(payload,'/exact/retained/deps')
    calls=[]
    def failure(*a,**kw):
        calls.append(a)
        return SimpleNamespace(returncode=255,stdout=b'',stderr=b'connection timeout')
    monkeypatch.setattr(request.subprocess,'run',failure)
    out=tmp_path/'receipt.json'
    result=request.execute(req,code,out)
    assert result['status']=='failed' and len(calls)==1
    with pytest.raises(FileExistsError):request.execute(req,code,out)
    assert len(calls)==1 and json.loads(out.read_text())['numerical_seconds']==0


def test_changed_destination_or_payload_rejected_before_any_ssh(tmp_path,monkeypatch):
    code=tmp_path/'code';(code/'tools').mkdir(parents=True)
    payload=code/'tools/hybrid_runtime_inventory.py';payload.write_text('pass\n')
    req=request.request_for(payload,'/exact/retained/deps')
    monkeypatch.setattr(request.subprocess,'run',lambda *a,**k:pytest.fail('SSH forbidden'))
    bad=copy.deepcopy(req);bad['ssh_argv'][-2]='someone@else'
    with pytest.raises(RuntimeError,match='destination'):request.execute(bad,code,tmp_path/'a')
    payload.write_text('changed\n')
    with pytest.raises(RuntimeError,match='payload'):request.execute(req,code,tmp_path/'b')


def test_timeout_is_recorded_and_not_retried(tmp_path,monkeypatch):
    code=tmp_path/'code';(code/'tools').mkdir(parents=True)
    payload=code/'tools/hybrid_runtime_inventory.py';payload.write_text('pass\n')
    req=request.request_for(payload,'/exact/retained/deps');calls=[]
    def timeout(*a,**kw):
        calls.append(kw['timeout']);raise request.subprocess.TimeoutExpired(a[0],45)
    monkeypatch.setattr(request.subprocess,'run',timeout)
    result=request.execute(req,code,tmp_path/'receipt.json')
    assert calls==[45] and 'TimeoutExpired' in result['error']
