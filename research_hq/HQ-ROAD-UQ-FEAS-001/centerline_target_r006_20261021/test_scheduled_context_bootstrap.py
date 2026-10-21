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

def command(dep, receipt, target, result, *, version="0.25.2", skeleton_hash=None, skimage_hash=None):
    skeleton = dep / "skimage/morphology/_skeletonize.py"
    return [sys.executable, str(BOOT), "--context-receipt", str(receipt),
        "--dependency-root", str(dep),
        "--expected-skimage-sha256", skimage_hash or digest(dep / "skimage/__init__.py"),
        "--expected-morphology-sha256", digest(dep / "skimage/morphology/__init__.py"),
        "--expected-skimage-version", version,
        "--expected-skeletonize-sha256", skeleton_hash or digest(skeleton),
        "--target", str(target), "--", str(result)]

def expect_failure(cmd, env, phrase):
    completed = subprocess.run(cmd, env=env, text=True, capture_output=True)
    assert completed.returncode != 0, completed.stdout
    receipt = Path(cmd[cmd.index("--context-receipt") + 1])
    record = json.loads(receipt.read_text())
    assert record["status"] == "FAIL_SCHEDULED_CONTEXT"
    assert phrase in record["error"], record["error"]

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    dep = root / "dep"
    shadow = root / "shadow"
    for base, version, marker in ((dep, "0.25.2", "frozen"), (shadow, "shadow", "shadow")):
        (base / "skimage/morphology").mkdir(parents=True)
        (base / "skimage/__init__.py").write_text(f"__version__={version!r}\n")
        (base / "skimage/morphology/__init__.py").write_text(
            f"MARKER={marker!r}\nfrom ._skeletonize import skeletonize\n")
        (base / "skimage/morphology/_skeletonize.py").write_text(
            "def skeletonize(value):\n    return value\n")
    (shadow / "sitecustomize.py").write_text(
        "import importlib.machinery,sys,types\n"
        "m=types.ModuleType('skimage')\n"
        "m.__path__=[r'" + str(shadow / "skimage") + "']\n"
        "m.__spec__=importlib.machinery.ModuleSpec('skimage',None,is_package=True)\n"
        "m.__spec__.submodule_search_locations=m.__path__\n"
        "sys.modules['skimage']=m\n")
    target = root / "target.py"
    result = root / "result.json"
    (root / "d5_runner.py").write_text("MARKER='reviewed'\n")
    (root / "centerline_core.py").write_text("MARKER='reviewed'\n")
    target.write_text(
        "import centerline_core,json,os,skimage,skimage.morphology,sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[1]).write_text(json.dumps({'version':skimage.__version__,"
        "'morphology':skimage.morphology.MARKER,'task':centerline_core.MARKER,"
        "'path':sys.path,'pid':os.getpid()}))\n")
    receipt = root / "context.json"
    env = dict(os.environ, PYTHONPATH=str(shadow))
    completed = subprocess.run(command(dep, receipt, target, result), env=env, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    context = json.loads(receipt.read_text())
    outcome = json.loads(result.read_text())
    assert context["status"] == "PASS_SCHEDULED_CONTEXT"
    assert outcome["version"] == "0.25.2" and outcome["morphology"] == "frozen"
    assert outcome["task"] == "reviewed"
    assert outcome["pid"] == context["pid"] == context["explicit_binding"]["pid"]
    assert "skimage" in context["explicit_binding"]["removed_preexisting_modules"]
    for package in ("skimage", "morphology"):
        assert context["explicit_binding"][package]["loader_type"] == "SourceFileLoader"
        assert len(context["explicit_binding"][package]["path"]) == 1
    assert context["explicit_binding"]["skeletonize_source_sha256"] == digest(dep / "skimage/morphology/_skeletonize.py")
    assert Path(outcome["path"][0]).resolve() == root.resolve()
    assert Path(outcome["path"][1]).resolve() == dep.resolve()

    for task_name in ("d5_runner.py", "centerline_core.py"):
        shadow_task = dep / task_name
        shadow_task.write_text("MARKER='dependency-shadow'\n")
        expect_failure(command(dep, root / f"shadow-{task_name}.json", target, result), env, "task module shadow")
        shadow_task.unlink()

    expect_failure(command(dep, root / "wrong-init-hash.json", target, result, skimage_hash="0" * 64), env, "initializer hash mismatch")
    expect_failure(command(dep, root / "wrong-version.json", target, result, version="9.9.9"), env, "version mismatch")
    expect_failure(command(dep, root / "wrong-skeleton-hash.json", target, result, skeleton_hash="0" * 64), env, "skeletonize implementation hash mismatch")

    skinit = dep / "skimage/__init__.py"
    original = skinit.read_text()
    skinit.write_text(original + "__spec__.origin='drifted-origin.py'\n")
    expect_failure(command(dep, root / "spec-drift.json", target, result), env, "spec origin mismatch")
    skinit.write_text(original + "__path__.append('drifted-path')\n")
    expect_failure(command(dep, root / "path-drift.json", target, result), env, "package path mismatch")
    skinit.write_text(original)

    missing_init = dep / "skimage/morphology/__init__.py"
    saved = missing_init.read_text()
    missing_init.unlink()
    missing_cmd = [sys.executable, str(BOOT), "--context-receipt", str(root / "missing.json"),
        "--dependency-root", str(dep), "--expected-skimage-sha256", digest(skinit),
        "--expected-morphology-sha256", "0" * 64, "--expected-skimage-version", "0.25.2",
        "--expected-skeletonize-sha256", digest(dep / "skimage/morphology/_skeletonize.py"),
        "--target", str(target), "--", str(result)]
    expect_failure(missing_cmd, env, "initializer missing")
    missing_init.write_text(saved)

    bad_dep = root / "bad-dep"
    (bad_dep / "skimage/morphology").mkdir(parents=True)
    (bad_dep / "skimage/__init__.py").write_text("__version__='0.25.2'\n")
    (bad_dep / "skimage/morphology/__init__.py").write_text("raise RuntimeError('initializer exploded')\n")
    (bad_dep / "skimage/morphology/_skeletonize.py").write_text("def skeletonize(x): return x\n")
    expect_failure(command(bad_dep, root / "bad-init.json", target, result), env, "initializer exploded")

print("PASS_R006_EXPLICIT_PACKAGE_ENTRY normal polluted-namespace exact-version spec-origin singleton-path exact-skeleton-hash wrong-hash missing-file initializer-error task-shadow same-pid-target")
