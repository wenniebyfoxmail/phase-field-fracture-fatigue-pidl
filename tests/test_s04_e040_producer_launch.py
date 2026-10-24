"""Fail-closed checks for the S04-E040 producer materialization chain."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


WORKTREE = Path(__file__).resolve().parents[1]
LAUNCHER = WORKTREE / "docs" / "research" / "S04" / "S04-E040" / "producer_launch.sh"
BOOTSTRAP = WORKTREE / "docs" / "research" / "S04" / "S04-E040" / "producer_bootstrap.sh"
REVIEWED_SOURCE = "5aaa317ed55175e80acb581d922eb6a1a4cb6d49"
RECEIPT_SCHEMA = "S04-E040-producer-package-receipt-v2"
MANIFEST_SCHEMA = "S04-E040-reviewed-runtime-manifest-v1"
MATERIALIZATION_SCHEMA = "S04-E040-materialization-receipt-v1"
RUN_ID = "pf_s04e040_feasible_damage_5aaa317e_20261024T004435Z"
ENTRYPOINT = "docs/research/S04/S04-E040/producer_launch.sh"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o755)


class ProducerLaunchTest(unittest.TestCase):
    def patch_paths(self, source: Path, runs: Path, archives: Path, lock_dir: Path) -> str:
        text = source.read_text()
        text = text.replace("/mnt/data2/drtao/wennie", str(runs))
        text = text.replace("/mnt/data2/drtao/pidl_archives", str(archives))
        text = text.replace(
            "lock_dir=/mnt/data2/drtao/wennie/.s04-e040-gpu-locks",
            f"lock_dir={lock_dir}",
        )
        return text

    def make_tools(self, root: Path, nvidia: str | None = None) -> tuple[Path, Path]:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        sentinel = root / "nvidia-called"
        write_executable(
            bin_dir / "sha256sum",
            "#!/usr/bin/env python3\n"
            "import hashlib, pathlib, sys\n"
            "p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest(), p)\n",
        )
        write_executable(bin_dir / "timeout", "#!/bin/bash\nexit 99\n")
        write_executable(bin_dir / "flock", "#!/bin/bash\nexit 0\n")
        write_executable(
            bin_dir / "nvidia-smi",
            nvidia
            or "#!/bin/bash\ntouch \"$S04_E040_NVIDIA_SENTINEL\"\necho unexpected-nvidia >&2\nexit 99\n",
        )
        return bin_dir, sentinel

    def install_inner_package(self, temporary: Path, *, frozen_inputs: bool = False) -> dict[str, object]:
        runs = temporary / "runs"
        archives = temporary / "archives"
        task_root = runs / RUN_ID
        archive_root = archives / RUN_ID
        task_root.mkdir(parents=True)
        code = task_root / "code"
        runner = code / "scripts" / "run_s04_e040_feasible_damage.py"
        helper = code / "source" / "feasible_damage.py"
        runner.parent.mkdir(parents=True)
        helper.parent.mkdir(parents=True)
        runner.write_bytes(b"reviewed runner bytes\n")
        helper.write_bytes(b"reviewed helper bytes\n")

        baseline = temporary / "baseline"
        reference = temporary / "reference"
        expected: dict[str, str] = {}
        if frozen_inputs:
            checkpoint = baseline / "best_models" / "checkpoint_step_0.pt"
            network = baseline / "best_models" / "trained_1NN_0.pt"
            settings = baseline / "model_settings.txt"
            steps = reference / "original" / "steps.json"
            for path, data, name in (
                (settings, b"settings\n", "MODEL_SETTINGS"),
                (checkpoint, b"checkpoint\n", "CHECKPOINT"),
                (network, b"network\n", "NETWORK"),
                (steps, b"steps\n", "R001_STEPS"),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                expected[name] = sha256(path)

        launcher = code / ENTRYPOINT
        launcher.parent.mkdir(parents=True)
        text = self.patch_paths(LAUNCHER, runs, archives, temporary / "locks")
        for name, value in expected.items():
            text = text.replace(
                f"readonly EXPECTED_{name}_SHA256="
                + {
                    "MODEL_SETTINGS": "015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047",
                    "CHECKPOINT": "aad4ebcb60a41caba6e0d2dbfaaba7cb7cb2ece631da8fbbfcaf3d374fc77aae",
                    "NETWORK": "09f1fc279007262b1068f0526e36e3aa2005633da271924cb598b7994ba8509a",
                    "R001_STEPS": "fd21fced6639591c1966e12c6ed5e7ec086403dc02d889ec49011c0d2524deec",
                }[name],
                f"readonly EXPECTED_{name}_SHA256={value}",
            )
        write_executable(launcher, text)

        files = []
        for path in (runner, helper):
            relative = path.relative_to(code).as_posix()
            files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "reviewed_runtime_commit": REVIEWED_SOURCE,
            "files": files,
        }
        manifest_path = task_root / "reviewed_runtime_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        archive = task_root / "s04-e040-code.tar"
        archive.write_bytes(b"checked package tar bytes\n")
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "package_commit": "a" * 40,
            "reviewed_runtime_commit": REVIEWED_SOURCE,
            "archive_file": archive.name,
            "archive_sha256": sha256(archive),
            "archive_bytes": archive.stat().st_size,
            "runtime_manifest_file": manifest_path.name,
            "runtime_manifest_sha256": sha256(manifest_path),
            "entrypoint": ENTRYPOINT,
            "entrypoint_sha256": sha256(launcher),
            "bootstrap_file": "producer_bootstrap.sh",
            "bootstrap_sha256": "b" * 64,
        }
        receipt_path = task_root / "package_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        materialization = {
            "schema": MATERIALIZATION_SCHEMA,
            "package_receipt_sha256": sha256(receipt_path),
            "archive_sha256": receipt["archive_sha256"],
            "runtime_manifest_sha256": receipt["runtime_manifest_sha256"],
            "package_commit": receipt["package_commit"],
        }
        (task_root / "materialization_receipt.json").write_text(
            json.dumps(materialization, indent=2, sort_keys=True) + "\n"
        )
        return {
            "runs": runs,
            "archives": archives,
            "task_root": task_root,
            "archive_root": archive_root,
            "code": code,
            "runner": runner,
            "archive": archive,
            "receipt": receipt_path,
            "manifest": manifest_path,
            "launcher": launcher,
            "baseline": baseline,
            "reference": reference,
        }

    def inner_environment(self, package: dict[str, object], bin_dir: Path, sentinel: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "RUN_ID": RUN_ID,
                "TASKROOT": str(package["task_root"]),
                "PIDL_ARCHIVE_DIR": str(package["archive_root"]),
                "PHYSICAL_GPU_INDEX": "0",
                "BASELINE": str(package["baseline"]),
                "REFERENCE_RESULT": str(package["reference"]),
                "PACKAGE_ARCHIVE": str(package["archive"]),
                "PACKAGE_RECEIPT": str(package["receipt"]),
                "PACKAGE_RUNTIME_MANIFEST": str(package["manifest"]),
                "PATH": f"{bin_dir}:{environment['PATH']}",
                "S04_E040_NVIDIA_SENTINEL": str(sentinel),
            }
        )
        return environment

    def run_inner(self, package: dict[str, object], environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(package["launcher"])], text=True, capture_output=True, env=environment
        )

    def test_valid_materialized_tree_reaches_input_lock_before_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.install_inner_package(root)
            bin_dir, sentinel = self.make_tools(root)
            result = self.run_inner(package, self.inner_environment(package, bin_dir, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing required file", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_tampered_archive_fails_before_input_lock_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.install_inner_package(root)
            Path(package["archive"]).write_bytes(b"tampered\n")
            bin_dir, sentinel = self.make_tools(root)
            result = self.run_inner(package, self.inner_environment(package, bin_dir, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("uploaded package archive differs", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_altered_runtime_file_fails_before_input_lock_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.install_inner_package(root)
            runner = Path(package["runner"])
            original = runner.read_bytes()
            runner.write_bytes(b"X" + original[1:])
            bin_dir, sentinel = self.make_tools(root)
            result = self.run_inner(package, self.inner_environment(package, bin_dir, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("runtime file hash differs", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_existing_archive_root_fails_before_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.install_inner_package(root)
            Path(package["archive_root"]).mkdir(parents=True)
            bin_dir, sentinel = self.make_tools(root)
            result = self.run_inner(package, self.inner_environment(package, bin_dir, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing non-fresh archive root", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_failed_compute_process_query_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.install_inner_package(root, frozen_inputs=True)
            nvidia = (
                "#!/bin/bash\n"
                "touch \"$S04_E040_NVIDIA_SENTINEL\"\n"
                "if [[ \"$*\" == *--query-gpu=* ]]; then\n"
                "  echo '0, GPU-test, NVIDIA GeForce RTX 4090, 0, 0, 999.0'\n"
                "  exit 0\n"
                "fi\n"
                "echo query-failed >&2\n"
                "exit 7\n"
            )
            bin_dir, sentinel = self.make_tools(root, nvidia)
            result = self.run_inner(package, self.inner_environment(package, bin_dir, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("could not query compute processes", result.stderr)
            self.assertTrue(sentinel.exists())
            self.assertNotIn("CUDA/import preflight", result.stderr)

    def test_bootstrap_extracts_checked_tar_before_fake_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_repo = root / "package-repo"
            package_repo.mkdir()
            subprocess.run(["git", "init", "-q", str(package_repo)], check=True)
            subprocess.run(["git", "-C", str(package_repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(package_repo), "config", "user.name", "Test"], check=True)
            dummy_entrypoint = package_repo / ENTRYPOINT
            dummy_entrypoint.parent.mkdir(parents=True)
            dummy_entrypoint.write_text("#!/bin/bash\nexit 0\n")
            dummy_entrypoint.chmod(0o755)
            dummy_runner = package_repo / "scripts" / "run_s04_e040_feasible_damage.py"
            dummy_helper = package_repo / "source" / "feasible_damage.py"
            dummy_runner.parent.mkdir()
            dummy_helper.parent.mkdir()
            dummy_runner.write_bytes(b"runner\n")
            dummy_helper.write_bytes(b"helper\n")
            subprocess.run(["git", "-C", str(package_repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(package_repo), "commit", "-qm", "package"], check=True)
            commit = subprocess.check_output(["git", "-C", str(package_repo), "rev-parse", "HEAD"], text=True).strip()

            runs = root / "runs"
            archives = root / "archives"
            task_root = runs / RUN_ID
            task_root.mkdir(parents=True)
            archive_root = archives / RUN_ID
            archive = task_root / "s04-e040-code.tar"
            with archive.open("wb") as handle:
                subprocess.run(
                    ["git", "-C", str(package_repo), "archive", "--format=tar", "--prefix=code/", "HEAD"],
                    stdout=handle,
                    check=True,
                )
            manifest = {
                "schema": MANIFEST_SCHEMA,
                "reviewed_runtime_commit": REVIEWED_SOURCE,
                "files": [
                    {"path": "scripts/run_s04_e040_feasible_damage.py", "bytes": len(dummy_runner.read_bytes()), "sha256": sha256(dummy_runner)},
                    {"path": "source/feasible_damage.py", "bytes": len(dummy_helper.read_bytes()), "sha256": sha256(dummy_helper)},
                ],
            }
            manifest_path = task_root / "reviewed_runtime_manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            bootstrap = task_root / "producer_bootstrap.sh"
            write_executable(bootstrap, self.patch_paths(BOOTSTRAP, runs, archives, root / "locks"))
            receipt = {
                "schema": RECEIPT_SCHEMA,
                "package_commit": commit,
                "reviewed_runtime_commit": REVIEWED_SOURCE,
                "archive_file": archive.name,
                "archive_sha256": sha256(archive),
                "archive_bytes": archive.stat().st_size,
                "runtime_manifest_file": manifest_path.name,
                "runtime_manifest_sha256": sha256(manifest_path),
                "entrypoint": ENTRYPOINT,
                "entrypoint_sha256": sha256(dummy_entrypoint),
                "bootstrap_file": bootstrap.name,
                "bootstrap_sha256": sha256(bootstrap),
            }
            receipt_path = task_root / "package_receipt.json"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "systemd-run-called"
            write_executable(
                bin_dir / "systemd-run",
                "#!/bin/bash\ntouch \"$S04_E040_SYSTEMD_SENTINEL\"\necho 'Running as unit: test.service'\n",
            )
            write_executable(
                bin_dir / "systemctl",
                "#!/bin/bash\n"
                "if [[ \"$*\" == *LoadState* ]]; then echo 'LoadState=not-found'; else printf 'Id=test.service\\nMainPID=42\\nRuntimeMaxUSec=3600000000\\n'; fi\n",
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "RUN_ID": RUN_ID,
                    "TASKROOT": str(task_root),
                    "PIDL_ARCHIVE_DIR": str(archive_root),
                    "PHYSICAL_GPU_INDEX": "0",
                    "BASELINE": str(root / "baseline"),
                    "REFERENCE_RESULT": str(root / "reference"),
                    "PACKAGE_ARCHIVE": str(archive),
                    "PACKAGE_RECEIPT": str(receipt_path),
                    "PACKAGE_RUNTIME_MANIFEST": str(manifest_path),
                    "PACKAGE_RECEIPT_SHA256": sha256(receipt_path),
                    "PATH": f"{bin_dir}:{environment['PATH']}",
                    "S04_E040_SYSTEMD_SENTINEL": str(marker),
                }
            )
            result = subprocess.run([str(bootstrap)], text=True, capture_output=True, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((task_root / "code" / ENTRYPOINT).is_file())
            self.assertTrue((task_root / "materialization_receipt.json").is_file())
            self.assertTrue((task_root / "submission_receipt.txt").is_file())
            self.assertTrue(marker.exists())


if __name__ == "__main__":
    unittest.main()
