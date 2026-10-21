import json
import datetime as dt
import subprocess
import sys
import tempfile
from pathlib import Path

import owned_subprocess as owned


HERE = Path(__file__).resolve().parent
CONTROLLER = HERE / "owned_subprocess.py"


def fixture(root, role, command, timeout=3):
    lock = root / "lock.json"; lock.write_text('{"frozen":true}\n')
    approval = root / "approval.json"
    approval.write_text(json.dumps({"run_id":"R005-FIXTURE","code_snapshot":"snapshot-fixture",
                                    "data_lock_sha256":owned.sha256(lock)}))
    invocation = root / f"{role}.invocation.json"
    invocation.write_text(json.dumps({
        "schema":1,"run_id":"R005-FIXTURE","role":role,"approval_path":str(approval),
        "lock_path":str(lock),"cwd":str(root),"command":command,"timeout_seconds":timeout,
        "receipt_path":str(root/f"{role}.receipt.json"),"exitcode_path":str(root/f"{role}.exitcode.txt"),
        "stdout_path":str(root/f"{role}.stdout"),"stderr_path":str(root/f"{role}.stderr"),
    }))
    return invocation


def run(invocation):
    return subprocess.run([sys.executable, str(CONTROLLER), str(invocation)], check=False,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        success_root=root/"success"; success_root.mkdir()
        success = fixture(success_root,"success",[sys.executable,"-c","print('ok')"])
        assert run(success).returncode == 0
        assert owned.validate_receipt(success)["status"] == "COMPLETE_ZERO"
        original_receipt = Path(json.loads(success.read_text())["receipt_path"]).read_bytes()
        assert run(success).returncode != 0
        assert Path(json.loads(success.read_text())["receipt_path"]).read_bytes() == original_receipt

        emitter=root/"emit_context.py"
        emitter.write_text("""import datetime as dt, hashlib, json, os, sys
payload = json.dumps(sys.argv, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
mode = sys.argv[2]
pid = os.getpid() if mode == 'same' else os.getpid() + 100000
record = {'status': 'PASS_SCHEDULED_CONTEXT', 'run_id': 'R005-FIXTURE',
          'pid': pid, 'parent_pid': os.getppid(), 'sys_executable': sys.executable,
          'argv_sha256': hashlib.sha256(payload).hexdigest(),
          'context_receipt_path': os.path.abspath(sys.argv[1]),
          'observed_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
open(sys.argv[1], 'w').write(json.dumps(record))
""")

        context_root=root/"context"; context_root.mkdir()
        context_path=context_root/"context.json"
        context_invocation=fixture(context_root,"context",[sys.executable,str(emitter),str(context_path),"same"])
        context_data=json.loads(context_invocation.read_text()); context_data["context_receipt_path"]=str(context_path); context_invocation.write_text(json.dumps(context_data))
        assert run(context_invocation).returncode == 0
        context_receipt=owned.validate_receipt(context_invocation)
        assert context_receipt["context"]["pid"] == context_receipt["pid"]
        assert context_receipt["context_ownership"] == "SAME_PROCESS"

        now=dt.datetime.now(dt.timezone.utc).isoformat()
        direct_invocation={"run_id":"R005-FIXTURE","command":[sys.executable,str(emitter),str(context_path),"same"],
                           "context_receipt_path":str(context_path)}
        direct_context={"status":"PASS_SCHEDULED_CONTEXT","run_id":"R005-FIXTURE","pid":222,"parent_pid":111,
                        "sys_executable":sys.executable,"argv_sha256":owned.canonical_json_sha(direct_invocation["command"][1:]),
                        "context_receipt_path":str(context_path),"observed_utc":now}
        assert owned.validate_context_identity(direct_context,direct_invocation,111,now,now) == "DIRECT_CHILD_OF_OWNED_LAUNCHER"
        unrelated=dict(direct_context,pid=333,parent_pid=222)
        try: owned.validate_context_identity(unrelated,direct_invocation,111,now,now); raise AssertionError("unrelated PID accepted")
        except ValueError: pass
        wrong_exe=dict(direct_context,sys_executable=str(root/"wrong-python"))
        try: owned.validate_context_identity(wrong_exe,direct_invocation,111,now,now); raise AssertionError("wrong executable accepted")
        except ValueError: pass
        wrong_argv=dict(direct_context,argv_sha256="0"*64)
        try: owned.validate_context_identity(wrong_argv,direct_invocation,111,now,now); raise AssertionError("wrong argv accepted")
        except ValueError: pass
        wrong_run=dict(direct_context,run_id="WRONG-RUN")
        try: owned.validate_context_identity(wrong_run,direct_invocation,111,now,now); raise AssertionError("wrong Run accepted")
        except ValueError: pass

        bad_context_root=root/"bad-context"; bad_context_root.mkdir()
        bad_context_path=bad_context_root/"context.json"
        bad_context=fixture(bad_context_root,"bad-context",[sys.executable,str(emitter),str(bad_context_path),"unrelated"])
        bad_data=json.loads(bad_context.read_text()); bad_data["context_receipt_path"]=str(bad_context_path); bad_context.write_text(json.dumps(bad_data))
        assert run(bad_context).returncode == 125
        assert json.loads(Path(bad_data["receipt_path"]).read_text())["status"] == "CONTEXT_EVIDENCE_INVALID"

        replay_root=root/"replay"; replay_root.mkdir()
        replay_path=replay_root/"context.json"; replay_path.write_text("{}")
        replay=fixture(replay_root,"replay",[sys.executable,str(emitter),str(replay_path),"same"])
        replay_data=json.loads(replay.read_text()); replay_data["context_receipt_path"]=str(replay_path); replay.write_text(json.dumps(replay_data))
        assert run(replay).returncode != 0
        assert replay_path.read_text() == "{}"

        nonzero_root=root/"nonzero"; nonzero_root.mkdir()
        nonzero=fixture(nonzero_root,"nonzero",[sys.executable,"-c","import json; print(json.dumps({'ok':True})); raise SystemExit(7)"])
        assert run(nonzero).returncode == 7
        assert owned.validate_receipt(nonzero)["status"] == "COMPLETE_NONZERO"
        nonzero_invocation=json.loads(nonzero.read_text())
        assert json.loads(Path(nonzero_invocation["stdout_path"]).read_text()) == {"ok":True}
        assert int(Path(nonzero_invocation["exitcode_path"]).read_text()) == 7

        timeout_root=root/"timeout"; timeout_root.mkdir()
        timeout=fixture(timeout_root,"timeout",[sys.executable,"-c","import time; time.sleep(3)"],0.15)
        assert run(timeout).returncode == 124
        assert owned.validate_receipt(timeout)["status"] == "TIMEOUT"

        missing_root=root/"missing"; missing_root.mkdir()
        missing=fixture(missing_root,"missing",[sys.executable,"-c","pass"])
        try: owned.validate_receipt(missing); raise AssertionError("missing evidence accepted")
        except FileNotFoundError: pass

        malformed_root=root/"malformed"; malformed_root.mkdir()
        malformed=fixture(malformed_root,"malformed",[sys.executable,"-c","pass"])
        Path(json.loads(malformed.read_text())["receipt_path"]).write_text('{')
        try: owned.validate_receipt(malformed); raise AssertionError("malformed receipt accepted")
        except json.JSONDecodeError: pass

        numeric_root=root/"numeric"; numeric_root.mkdir()
        numeric=fixture(numeric_root,"numeric",[sys.executable,"-c","pass"])
        assert run(numeric).returncode == 0
        Path(json.loads(numeric.read_text())["exitcode_path"]).write_text("not-an-integer\n")
        try: owned.validate_receipt(numeric); raise AssertionError("malformed numeric exit accepted")
        except ValueError: pass

        duplicate_root=root/"duplicate"; duplicate_root.mkdir()
        duplicate=fixture(duplicate_root,"duplicate",[sys.executable,"-c","pass"])
        Path(json.loads(duplicate.read_text())["stdout_path"]).write_text("pre-existing")
        assert run(duplicate).returncode != 0
        assert Path(json.loads(duplicate.read_text())["stdout_path"]).read_text() == "pre-existing"

        unknown_root=root/"unknown"; unknown_root.mkdir()
        unknown=fixture(unknown_root,"scientific_worker",[sys.executable,"-c","pass"])
        unknown_invocation=json.loads(unknown.read_text())
        Path(str(unknown_invocation["receipt_path"])+".claim").write_text("unknown launch claim\n")
        try: owned.assert_clean_launch(unknown_invocation); raise AssertionError("unknown launch claim allowed repeat")
        except FileExistsError: pass

        truncated_root=root/"truncated"; truncated_root.mkdir()
        truncated=fixture(truncated_root,"truncated",[sys.executable,"-c","pass"])
        assert run(truncated).returncode == 0
        receipt=Path(json.loads(truncated.read_text())["receipt_path"]); receipt.write_text(receipt.read_text()[:20])
        try: owned.validate_receipt(truncated); raise AssertionError("truncated receipt accepted")
        except json.JSONDecodeError: pass

    print("PASS_R005_OWNED_SUBPROCESS success same-pid direct-child unrelated-pid wrong-exe wrong-argv wrong-run replay-reject valid-json-nonzero missing malformed malformed-numeric timeout duplicate truncated unknown-launch-no-repeat")


if __name__ == "__main__":
    main()
