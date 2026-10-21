import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
BOOT = HERE / "scheduled_context_bootstrap.py"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    dep = root / "dep"
    shadow = root / "shadow"
    for base, marker in ((dep, "frozen"), (shadow, "shadow")):
        (base / "skimage" / "morphology").mkdir(parents=True)
        (base / "skimage" / "__init__.py").write_text(f"__version__='{marker}'\n")
        (base / "skimage" / "morphology" / "__init__.py").write_text(f"MARKER='{marker}'\n")
    target = root / "target.py"
    result = root / "result.json"
    (root / "d5_runner.py").write_text("MARKER='reviewed'\n")
    (root / "centerline_core.py").write_text("MARKER='reviewed'\n")
    target.write_text("import centerline_core,json,skimage,skimage.morphology,sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps({'version':skimage.__version__,'morphology':skimage.morphology.MARKER,'task':centerline_core.MARKER,'path':sys.path}))\n")
    receipt = root / "context.json"
    command = [sys.executable, str(BOOT), "--context-receipt", str(receipt), "--dependency-root", str(dep),
               "--expected-skimage-sha256", digest(dep/"skimage/__init__.py"),
               "--expected-morphology-sha256", digest(dep/"skimage/morphology/__init__.py"),
               "--target", str(target), "--", str(result)]
    env = dict(os.environ, PYTHONPATH=str(shadow))
    completed = subprocess.run(command, env=env, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    context = json.loads(receipt.read_text())
    outcome = json.loads(result.read_text())
    assert context["status"] == "PASS_SCHEDULED_CONTEXT"
    assert outcome["version"] == outcome["morphology"] == "frozen"
    assert outcome["task"] == "reviewed"
    assert Path(outcome["path"][0]).resolve() == root.resolve()
    assert Path(outcome["path"][1]).resolve() == dep.resolve()

    for task_name in ("d5_runner.py", "centerline_core.py"):
        shadow_task = dep / task_name
        shadow_task.write_text("MARKER='dependency-shadow'\n")
        shadow_receipt = root / f"shadow-{task_name}.json"
        shadow_command = command.copy()
        shadow_command[shadow_command.index(str(receipt))] = str(shadow_receipt)
        shadowed = subprocess.run(shadow_command, env=env, text=True, capture_output=True)
        assert shadowed.returncode != 0
        shadow_record = json.loads(shadow_receipt.read_text())
        assert shadow_record["status"] == "FAIL_SCHEDULED_CONTEXT" and "task module shadow" in shadow_record["error"]
        shadow_task.unlink()

    failed_receipt = root / "failed.json"
    failed = subprocess.run(command[:2] + ["--context-receipt", str(failed_receipt), "--dependency-root", str(dep),
                            "--expected-skimage-sha256", "0"*64,
                            "--expected-morphology-sha256", digest(dep/"skimage/morphology/__init__.py"),
                            "--target", str(target), "--", str(result)], env=env, text=True, capture_output=True)
    assert failed.returncode != 0
    assert json.loads(failed_receipt.read_text())["status"] == "FAIL_SCHEDULED_CONTEXT"

print("PASS_R004_SCHEDULED_CONTEXT frozen-priority success failure-receipt")
