"""Pure budget files, no subprocess/GPU/NN execution."""
import importlib.util,json
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/s04_e036/gpu_watchdog.py'
s=importlib.util.spec_from_file_location('e036_gpu_watchdog',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_unknown_attempt_blocks_dispatch(tmp_path):
    m.new_json(tmp_path/'paired_main_attempt.json',{'reservation_gpu_seconds':86400})
    with pytest.raises(RuntimeError,match='unfinished'):m.available_seconds(tmp_path,172800)

def test_accounting_and_no_overwrite(tmp_path):
    p=tmp_path/'paired_main_attempt.json';m.new_json(p,{'reservation_gpu_seconds':86400})
    m.new_json(tmp_path/'paired_main_finished.json',dict(attempt_sha256=m.digest(p),charged_gpu_seconds=27.5))
    assert m.available_seconds(tmp_path,100)==72.5
    with pytest.raises(FileExistsError):m.new_json(p,{})

def test_accounting_tamper_rejected(tmp_path):
    p=tmp_path/'paired_main_attempt.json';m.new_json(p,{})
    m.new_json(tmp_path/'paired_main_finished.json',dict(attempt_sha256='bad',charged_gpu_seconds=0))
    with pytest.raises(ValueError):m.available_seconds(tmp_path,100)


def test_group_survivors_checked_without_leader(monkeypatch,tmp_path):
    calls=[];remaining=[[432],[]]
    monkeypatch.setattr(m,'owned_group_members',lambda *a:remaining.pop(0))
    monkeypatch.setattr(m.os,'killpg',lambda group,sig:calls.append((group,sig)))
    m.settle_owned_group(123,tmp_path)
    assert calls==[(123,m.signal.SIGTERM)]


def test_process_group_outside_task_not_claimed(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();p=proc/'432';p.mkdir()
    # state, ppid, pgrp, session are the only fields inspected.
    (p/'stat').write_text('432 (worker) S 1 123 123 0 0')
    other=tmp_path/'other';other.mkdir();(p/'cwd').symlink_to(other,target_is_directory=True)
    with pytest.raises(RuntimeError,match='ownership'):m.owned_group_members(123,tmp_path/'task',proc)


def test_live_group_member_with_deleted_cwd_is_unknown(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();p=proc/'432';p.mkdir()
    (p/'stat').write_text('432 (worker) S 1 123 123 0 0')
    (p/'cwd').symlink_to(tmp_path/'deleted',target_is_directory=True)
    with pytest.raises(RuntimeError,match='ownership'):m.owned_group_members(123,tmp_path,proc)


def test_removed_ceiling_keeps_accounting_and_unknown_stop(tmp_path):
    p=tmp_path/'paired_main_attempt.json';m.new_json(p,{'anti_hang_seconds':86400})
    with pytest.raises(RuntimeError,match='unfinished'):m.available_seconds(tmp_path,None)
    m.new_json(tmp_path/'paired_main_finished.json',dict(attempt_sha256=m.digest(p),charged_gpu_seconds=200000.))
    assert m.available_seconds(tmp_path,None) is None
    assert m.available_seconds(tmp_path,172800)==0.


def _owned_process(tmp_path, monkeypatch, command, start=1000):
    proc=tmp_path/'proc';proc.mkdir();p=proc/'432';p.mkdir()
    task=tmp_path/'task';task.mkdir();entry=str(task/'runner.py')
    fields=['S','1','123','123']+['0']*15+[str(start)]
    (p/'stat').write_text('432 (worker) '+' '.join(fields))
    (p/'cwd').symlink_to(task,target_is_directory=True)
    (p/'cmdline').write_bytes(b'\0'.join(x.encode() for x in command(entry))+b'\0')
    (proc/'uptime').write_text('20.00 10.00')
    monkeypatch.setattr(m.os,'sysconf',lambda name:100)
    return proc,task,entry


def test_owned_command_elapsed_and_cwd_all_recorded(tmp_path,monkeypatch):
    proc,task,entry=_owned_process(tmp_path,monkeypatch,lambda entry:['/usr/bin/python3',entry])
    observed=[]
    assert m.owned_group_members(123,task,proc,expected_entry=entry,
        not_before_ticks=999,observations=observed)==[432]
    assert observed[0]['elapsed_seconds']==10.
    assert observed[0]['cwd']==str(task)
    assert observed[0]['cmdline']==['/usr/bin/python3',entry]


@pytest.mark.parametrize('wrong_command,not_before',[(True,999),(False,1001)])
def test_same_group_and_cwd_do_not_override_command_or_birth(tmp_path,monkeypatch,wrong_command,not_before):
    proc,task,entry=_owned_process(tmp_path,monkeypatch,
        lambda entry:['/usr/bin/python3','/elsewhere/worker.py' if wrong_command else entry])
    with pytest.raises(RuntimeError,match='ownership mismatch'):
        m.owned_group_members(123,task,proc,expected_entry=entry,not_before_ticks=not_before)
