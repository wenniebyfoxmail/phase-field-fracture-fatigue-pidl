"""Small synthetic subprocess tests; no FEM archives, SSH or training."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_fixed_weight_legacy_native_remote.py"
loader = importlib.util.spec_from_file_location("legacy_controller", SCRIPT)
controller = importlib.util.module_from_spec(loader)
loader.loader.exec_module(controller)

STDOUT = b'{"synthetic":true}\r\n\xff\x00'
STDERR = b'synthetic stderr\r\n\xff'


def fixture(root, exit_code=0):
    root = root.resolve()
    bundle = root / "bundle"
    source, scripts, deps = bundle / "source", bundle / "scripts", root / "deps"
    for directory in (source, scripts, deps):
        directory.mkdir(parents=True)
    runner = scripts / "validate_fixed_weight_legacy_native_archives.py"
    runner.write_text(
        "import os,sys\nfrom pathlib import Path\n"
        "assert len(sys.argv)==4\n"
        "assert not Path('execution.json').exists()\n"
        "assert os.environ['OMP_NUM_THREADS']==os.environ['MKL_NUM_THREADS']==os.environ['OPENBLAS_NUM_THREADS']=='2'\n"
        "assert os.environ['CUDA_VISIBLE_DEVICES']==''\n"
        "assert os.environ['PYTHONDONTWRITEBYTECODE']=='1'\n"
        "assert os.environ['PYTHONNOUSERSITE']=='1'\n"
        "assert sys.flags.dont_write_bytecode and sys.flags.no_user_site and sys.flags.safe_path\n"
        "assert len(os.environ['PYTHONPATH'].split(os.pathsep))==2\n"
        f"sys.stdout.buffer.write({STDOUT!r})\n"
        f"sys.stderr.buffer.write({STDERR!r})\n"
        f"raise SystemExit({exit_code})\n", encoding="utf-8")
    return {"py_launcher": sys.executable, "run_root": root / "run",
            "runner": runner, "source_dir": source, "deps_dir": deps,
            "archive_roots": [root / f"synthetic_archive_{i}" for i in range(3)],
            "verifier_source_commit": "2e5061b0be5deae5098b36461dcdfadd981c60ad"}


class ControllerTests(unittest.TestCase):
    def test_binary_transport_and_child_exit_status(self):
        real_popen = subprocess.Popen
        for child_exit in (0, 7):
            with self.subTest(child_exit=child_exit), tempfile.TemporaryDirectory() as directory:
                args = fixture(Path(directory), child_exit)
                calls = []

                def synthetic_py_launcher(command, **kwargs):
                    # Emulate only py's -3 selection; run the tiny fixture with
                    # the actual test interpreter and the actual binary handles.
                    self.assertEqual(command[0], str(Path(args["py_launcher"]).resolve()))
                    self.assertEqual(command[1:6], ["-3", "-B", "-s", "-P", "-u"])
                    self.assertEqual(command[6], str(args["runner"]))
                    self.assertEqual(command[7:], [str(p) for p in args["archive_roots"]])
                    self.assertIn("b", kwargs["stdout"].mode)
                    self.assertIn("b", kwargs["stderr"].mode)
                    self.assertFalse(kwargs["shell"])
                    self.assertNotIn("text", kwargs)
                    calls.append(command)
                    return real_popen([command[0], *command[2:]], **kwargs)

                with mock.patch.object(controller.subprocess, "Popen", side_effect=synthetic_py_launcher):
                    result = controller.run_controller(**args)
                self.assertEqual(result, child_exit)
                self.assertEqual(len(calls), 1)
                root = args["run_root"]
                self.assertEqual((root / "receipt.jsonl").read_bytes(), STDOUT)
                self.assertEqual((root / "stderr.txt").read_bytes(), STDERR)
                execution = json.loads((root / "execution.json").read_bytes())
                self.assertEqual(execution["schema"], controller.SCHEMA)
                self.assertEqual(execution["exit_code"], child_exit)
                self.assertEqual(execution["verifier_source_commit"], args["verifier_source_commit"])
                self.assertEqual(execution["receipt_sha256"], hashlib.sha256(STDOUT).hexdigest())
                self.assertEqual(execution["stderr_sha256"], hashlib.sha256(STDERR).hexdigest())
                self.assertEqual(execution["controller_sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
                self.assertTrue(execution["runner_started"])
                self.assertIsNone(execution["launcher_error"])
                self.assertGreater(execution["runner_pid"], 0)
                self.assertEqual({p.name for p in root.iterdir()}, set(controller.OUTPUT_NAMES))
                self.assertTrue(all(not p.exists() for p in args["archive_roots"]))

    def test_existing_output_or_active_claim_refuses_before_launch(self):
        for existing in (*controller.OUTPUT_NAMES, controller.LOCK_NAME):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as directory:
                args = fixture(Path(directory))
                root = args["run_root"]
                root.mkdir()
                (root / existing).write_bytes(b"do not overwrite")
                with mock.patch.object(controller.subprocess, "Popen") as popen:
                    with self.assertRaises(FileExistsError):
                        controller.run_controller(**args)
                    popen.assert_not_called()
                self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()},
                                 {existing: b"do not overwrite"})

    def test_launcher_failure_has_terminal_failure_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            args = fixture(Path(directory))
            with mock.patch.object(controller.subprocess, "Popen", side_effect=FileNotFoundError("synthetic missing launcher")):
                self.assertEqual(controller.run_controller(**args), 127)
            execution = json.loads((args["run_root"] / "execution.json").read_bytes())
            self.assertEqual(execution["exit_code"], 127)
            self.assertFalse(execution["runner_started"])
            self.assertEqual(execution["launcher_error"]["type"], "FileNotFoundError")
            self.assertIsNone(execution["runner_pid"])
            self.assertEqual(execution["receipt_sha256"], hashlib.sha256(b"").hexdigest())

    def test_atomic_publish_refuses_existing_execution_and_cleans_its_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "execution.json"
            output.write_bytes(b"previous receipt")
            with self.assertRaises(FileExistsError):
                controller.publish_execution(output, {"exit_code": 0})
            self.assertEqual(output.read_bytes(), b"previous receipt")
            self.assertEqual([p.name for p in root.iterdir()], ["execution.json"])

    def test_invalid_paths_or_commit_do_not_start_or_create_output(self):
        for mutation in ("commit", "relative", "overlap", "duplicates", "layout",
                         "named_launcher", "relative_launcher", "missing_launcher", "directory_launcher"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                args = fixture(Path(directory))
                if mutation == "commit":
                    args["verifier_source_commit"] = "HEAD"
                elif mutation == "relative":
                    args["runner"] = Path("runner.py")
                elif mutation == "overlap":
                    args["archive_roots"][0] = args["run_root"] / "archive"
                elif mutation == "duplicates":
                    args["archive_roots"][1] = args["archive_roots"][0]
                elif mutation == "named_launcher":
                    args["py_launcher"] = "py"
                elif mutation == "relative_launcher":
                    args["py_launcher"] = "bin/py.exe"
                elif mutation == "missing_launcher":
                    args["py_launcher"] = str(Path(directory) / "missing-py.exe")
                elif mutation == "directory_launcher":
                    args["py_launcher"] = str(args["source_dir"])
                else:
                    args["source_dir"] = args["deps_dir"]
                with mock.patch.object(controller.subprocess, "Popen") as popen:
                    with self.assertRaises(ValueError):
                        controller.run_controller(**args)
                    popen.assert_not_called()
                self.assertFalse(args["run_root"].exists())

    def test_controller_refuses_each_missing_runtime_flag_before_output(self):
        required = {"dont_write_bytecode": "-B", "no_user_site": "-s", "safe_path": "-P"}
        for missing, flag in required.items():
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                args = fixture(Path(directory))
                flags = SimpleNamespace(**{name: name != missing for name in required})
                with mock.patch.object(controller.sys, "flags", flags), \
                        mock.patch.object(controller.subprocess, "Popen") as popen:
                    with self.assertRaisesRegex(ValueError, "missing " + flag):
                        controller.run_controller(**args)
                    popen.assert_not_called()
                self.assertFalse(args["run_root"].exists())

    def test_controller_refuses_unsupported_python_before_output(self):
        for attribute, value in (("implementation", SimpleNamespace(name="pypy")),
                                 ("version_info", (3, 10, 99))):
            with self.subTest(attribute=attribute), tempfile.TemporaryDirectory() as directory:
                args = fixture(Path(directory))
                with mock.patch.object(controller.sys, attribute, value), \
                        mock.patch.object(controller.subprocess, "Popen") as popen:
                    with self.assertRaisesRegex(ValueError, "CPython >= 3.11"):
                        controller.run_controller(**args)
                    popen.assert_not_called()
                self.assertFalse(args["run_root"].exists())

    @unittest.skipIf(os.name == "nt", "Mac/Unix production launch guard")
    def test_cli_rejects_non_windows_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            args = fixture(Path(directory))
            argv = ["--py-launcher", args["py_launcher"], "--run-root", str(args["run_root"]),
                    "--runner", str(args["runner"]), "--source-dir", str(args["source_dir"]),
                    "--deps-dir", str(args["deps_dir"]), "--archive-roots",
                    *(str(p) for p in args["archive_roots"]),
                    "--verifier-source-commit", args["verifier_source_commit"]]
            with mock.patch.object(controller, "run_controller") as run:
                with mock.patch("sys.stderr"), self.assertRaises(SystemExit) as error:
                    controller.main(argv)
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
