"""Focused fail-closed tests for the S04-E042 producer package."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


WORKTREE = Path(__file__).resolve().parents[1]
LAUNCHER = WORKTREE / "docs" / "research" / "S04" / "S04-E042" / "producer_launch.sh"
BOOTSTRAP = WORKTREE / "docs" / "research" / "S04" / "S04-E042" / "producer_bootstrap.sh"
PACKAGER = WORKTREE / "docs" / "research" / "S04" / "S04-E042" / "prepare_producer_package.py"
REVIEWED_SOURCE = "521c611fb2b24622df50ef5c2f4624b4abfed72d"
RECEIPT_SCHEMA = "S04-E042-producer-package-receipt-v2"
MANIFEST_SCHEMA = "S04-E042-reviewed-runtime-manifest-v2"
MATERIALIZATION_SCHEMA = "S04-E042-materialization-receipt-v1"
DEPENDENCY_SCHEMA = "S04-E042-runtime-dependency-receipt-v1"
RUN_ID = "pf_s04e042_projected_damage_521c611f_20261025T000000Z"
ENTRYPOINT = "docs/research/S04/S04-E042/producer_launch.sh"
LOCK_SOURCE_ROOT = "/home/drtao/.local/lib/python3.10/site-packages/gmshparser"
LOCK_VERSION = "0.2.0"
LOCK_TREE = "8e7134569df830851a9ebfe741c7477e10efbc781bb8e5e76850078e6a64c4ba"
LOCK_FILES = {
    "__init__.py": (377, "2a629709d6c88040451f6974aa761495202770013050ca4b869179e25ff82f93"),
    "abstract_parser.py": (1175, "f7e155409652bbb029174d880cf6080d662d3bb7daf91c86fcc25ed463211ce7"),
    "cli.py": (1320, "44a6dfafbcd93ee4e8c8c78b967d749f019a89534b9dbaa889076dd34ae9dca2"),
    "element.py": (580, "2e7f18430beb0c5d1ced371165c63b806f7763d71da676ffe63c54c98a0f359f"),
    "element_entity.py": (2151, "851ea05778d72e42ba9aff1d1aa350f9dbdd7daae1b7293fdfa47b5f72ce473a"),
    "elements_parser.py": (1570, "64af3d687e7d4078fc1a45e77bd03aa17d9c7aace6a22afa6feb12b5cab33c7e"),
    "helpers.py": (2248, "3150914858ae05cd2055c97be83abfec567ef216921dba291acc72ca4bef7fe9"),
    "main_parser.py": (903, "e4e0820a59ba5051d5cc88c2f23d34023872a8faf70e95171fc8db7eb98a1f22"),
    "mesh.py": (6234, "7f4ac041b0f9209638a7fa0e0e69ebe557387be153a35644873762df9d6c34c3"),
    "mesh_format_parser.py": (437, "987600f30b3c410049ab4320c11e04b4acb3a9fda25facfd782be840e4a5c070"),
    "node.py": (653, "c4e15aef37ae5fdab96db94cc9f327a4d5cb3945df0a8dea943d74a1bdd38083"),
    "node_entity.py": (1800, "e1151da6e52e2fbadb1e59353002643817c75c9c78db87e7db81ada2a06f4af1"),
    "nodes_parser.py": (1511, "a360c95fc0f75ff8edc5539e2117c70bf24d8420cffa3780b720308b4241c60d"),
}
FROZEN_LOCKS = {
    "MODEL_SETTINGS": "015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047",
    "CHECKPOINT": "aad4ebcb60a41caba6e0d2dbfaaba7cb7cb2ece631da8fbbfcaf3d374fc77aae",
    "NETWORK": "09f1fc279007262b1068f0526e36e3aa2005633da271924cb598b7994ba8509a",
    "R001_STEPS": "fd21fced6639591c1966e12c6ed5e7ec086403dc02d889ec49011c0d2524deec",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_tree(files: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for item in sorted(files, key=lambda value: str(value["path"])):
        digest.update(f"gmshparser/{item['path']}\0{item['bytes']}\0{item['sha256']}\n".encode())
    return digest.hexdigest()


def executable(path: Path, source: str) -> None:
    path.write_text(source)
    path.chmod(0o755)


def seal_tree(path: Path) -> None:
    descendants = list(path.rglob("*"))
    for candidate in descendants:
        if candidate.is_file():
            candidate.chmod(candidate.stat().st_mode & ~0o222)
    for candidate in sorted((item for item in descendants if item.is_dir()), key=lambda item: len(item.parts), reverse=True):
        candidate.chmod(candidate.stat().st_mode & ~0o222)
    path.chmod(path.stat().st_mode & ~0o222)


class ProducerDependencySnapshotTest(unittest.TestCase):
    def e042_import_proof(self, module_path: str, module_sha256: str) -> dict[str, str]:
        return {
            "module": "projected_damage",
            "symbol": "ReferenceBaseProjectedDamage",
            "module_path": module_path,
            "runner_path": "scripts/run_s04_e042_projected_damage.py",
            "module_sha256": module_sha256,
        }

    def dependency_source(self, root: Path) -> dict[str, object]:
        site = root / "site-packages"
        source = site / "gmshparser"
        source.mkdir(parents=True)
        files: list[dict[str, object]] = []
        for number, relative in enumerate(sorted(LOCK_FILES)):
            target = source / relative
            target.write_text(f"# synthetic locked source {relative}\nVALUE_{number} = {number}\n")
            files.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
        metadata = site / "gmshparser-0.2.0.dist-info"
        metadata.mkdir()
        (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: gmshparser\nVersion: 0.2.0\n")
        return {"source": source, "files": files, "tree": canonical_tree(files)}

    def patch_script(self, source: Path, runs: Path, archives: Path, dependency: dict[str, object]) -> str:
        text = source.read_text()
        text = text.replace("/mnt/data2/drtao/wennie", str(runs))
        text = text.replace("/mnt/data2/drtao/pidl_archives", str(archives))
        text = text.replace(
            "export PATH=/usr/bin:/bin",
            f"export PATH={shlex.quote(str(runs.parent / 'bin'))}:/usr/bin:/bin",
        )
        text = text.replace(
            f"readonly GMSHPARSER_SOURCE_ROOT={LOCK_SOURCE_ROOT}",
            f"readonly GMSHPARSER_SOURCE_ROOT={dependency['source']}",
        )
        text = text.replace(
            f"readonly GMSHPARSER_TREE_SHA256={LOCK_TREE}",
            f"readonly GMSHPARSER_TREE_SHA256={dependency['tree']}",
        )
        manifest = json.dumps(dependency["files"], separators=(",", ":"))
        text, replaced = re.subn(
            r"readonly GMSHPARSER_FILES_JSON='\[\n.*?\n\]'",
            f"readonly GMSHPARSER_FILES_JSON={shlex.quote(manifest)}",
            text,
            count=1,
            flags=re.DOTALL,
        )
        self.assertEqual(replaced, 1)
        return text

    def add_snapshot(self, task_root: Path, dependency: dict[str, object], package_receipt: Path) -> None:
        snapshot = task_root / "runtime_deps" / "gmshparser"
        snapshot.mkdir(parents=True)
        source = Path(dependency["source"])
        for item in dependency["files"]:
            relative = str(item["path"])
            (snapshot / relative).write_bytes((source / relative).read_bytes())
        receipt = {
            "schema": DEPENDENCY_SCHEMA,
            "package_receipt_sha256": sha256(package_receipt),
            "source_root": str(source),
            "distribution_name": "gmshparser",
            "distribution_version": LOCK_VERSION,
            "snapshot_relative_path": "runtime_deps/gmshparser",
            "canonical_tree_sha256": dependency["tree"],
            "files": dependency["files"],
        }
        (task_root / "runtime_dependency_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )
        for candidate in snapshot.iterdir():
            candidate.chmod(0o400)
        snapshot.chmod(0o500)
        snapshot.parent.chmod(0o500)

    def make_tools(self, root: Path, nvidia: str | None = None) -> tuple[Path, Path]:
        tools = root / "bin"
        tools.mkdir()
        sentinel = root / "nvidia-called"
        executable(
            tools / "sha256sum",
            "#!/usr/bin/env python3\nimport hashlib, pathlib, sys\n"
            "p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest(), p)\n",
        )
        executable(tools / "timeout", "#!/bin/bash\nexit 99\n")
        executable(tools / "flock", "#!/bin/bash\nexit 0\n")
        executable(
            tools / "nvidia-smi",
            nvidia
            or "#!/bin/bash\ntouch \"$S04_E042_NVIDIA_SENTINEL\"\necho unexpected-nvidia >&2\nexit 99\n",
        )
        return tools, sentinel

    def make_timeout_passthrough(self, tools: Path) -> None:
        executable(
            tools / "timeout",
            "#!/bin/bash\n"
            "set -euo pipefail\n"
            "while [[ \"${1:-}\" == --* ]]; do shift; done\n"
            "[[ $# -ge 2 ]] || exit 97\n"
            "shift\n"
            "exec \"$@\"\n",
        )

    def inner_package(self, root: Path, *, frozen_inputs: bool = False) -> dict[str, object]:
        dependency = self.dependency_source(root)
        runs, archives = root / "runs", root / "archives"
        task_root, archive_root = runs / RUN_ID, archives / RUN_ID
        task_root.mkdir(parents=True)
        code = task_root / "code"
        runner = code / "scripts" / "run_s04_e042_projected_damage.py"
        helper = code / "source" / "projected_damage.py"
        runner.parent.mkdir(parents=True)
        helper.parent.mkdir(parents=True)
        runner.write_text(
            "#!/usr/bin/env python3\n"
            "# checkpoint[\"history_driver_mode\"] == \"current_active\"\n"
            "# not checkpoint[\"lagged_stiffness_enabled\"]\n"
            "# if not can_prepare_acceptance:\n"
            "# publish_pointer_last(\n"
            "import json\n"
            "import sys\n"
            "from pathlib import Path\n"
            "output = Path(sys.argv[sys.argv.index(\"--output\") + 1])\n"
            "source_commit = sys.argv[sys.argv.index(\"--source-commit\") + 1]\n"
            "output.mkdir(parents=True)\n"
            "(output / 'manifest.json').write_text(json.dumps({'experiment': 'S04-E042', 'source_commit': source_commit}))\n"
            "(output / 'mesh.npz').write_bytes(b'mesh')\n"
            "arm = output / 'projected_damage'; arm.mkdir()\n"
            "(arm / 'steps.json').write_text(json.dumps([]))\n"
            "(arm / 'accepted_state_pointer.json').write_text(json.dumps({'accepted_commit_id': 'state_015'}))\n"
            "summary = {'outcome': 'completed_all_15_accepted_steps', 'steps_attempted': 15, 'steps_accepted': 15, 'completed_three_cycles': True}\n"
            "(arm / 'summary.json').write_text(json.dumps(summary))\n"
            "(output / 'results.json').write_text(json.dumps([summary]))\n"
            "(output / 'completed.json').write_text(json.dumps({'execution': 'runner_finished', 'outcome': summary['outcome']}))\n"
        )
        helper.write_bytes(b"helper\n")
        replacements: dict[str, str] = {}
        if frozen_inputs:
            for target, value, name in (
                (root / "baseline" / "model_settings.txt", b"settings\n", "MODEL_SETTINGS"),
                (root / "baseline" / "best_models" / "checkpoint_step_0.pt", b"checkpoint\n", "CHECKPOINT"),
                (root / "baseline" / "best_models" / "trained_1NN_0.pt", b"network\n", "NETWORK"),
                (root / "reference" / "original" / "steps.json", b"steps\n", "R001_STEPS"),
            ):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
                replacements[name] = sha256(target)
        launcher = code / ENTRYPOINT
        launcher.parent.mkdir(parents=True)
        launcher_text = self.patch_script(LAUNCHER, runs, archives, dependency)
        for name, digest in replacements.items():
            launcher_text = launcher_text.replace(
                f"readonly EXPECTED_{name}_SHA256={FROZEN_LOCKS[name]}",
                f"readonly EXPECTED_{name}_SHA256={digest}",
            )
        executable(launcher, launcher_text)
        files = [
            {"path": path.relative_to(code).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in (runner, helper)
        ]
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "reviewed_runtime_commit": REVIEWED_SOURCE,
            "files": files,
            "e042_import_proof": self.e042_import_proof("source/projected_damage.py", sha256(helper)),
        }
        manifest_path = task_root / "reviewed_runtime_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        archive = task_root / "s04-e042-code.tar"
        archive.write_bytes(b"checked package tar\n")
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
        self.add_snapshot(task_root, dependency, receipt_path)
        seal_tree(code)
        task_root.chmod(0o700)
        return {
            "task_root": task_root, "archive_root": archive_root, "launcher": launcher,
            "archive": archive, "receipt": receipt_path, "manifest": manifest_path, "runner": runner,
        }

    def inner_environment(self, package: dict[str, object], tools: Path, sentinel: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update({
            "RUN_ID": RUN_ID,
            "TASKROOT": str(package["task_root"]),
            "PIDL_ARCHIVE_DIR": str(package["archive_root"]),
            "PHYSICAL_GPU_INDEX": "0",
            "BASELINE": str(Path(package["task_root"]).parent.parent / "baseline"),
            "REFERENCE_RESULT": str(Path(package["task_root"]).parent.parent / "reference"),
            "PACKAGE_ARCHIVE": str(package["archive"]),
            "PACKAGE_RECEIPT": str(package["receipt"]),
            "PACKAGE_RECEIPT_SHA256": sha256(Path(package["receipt"])),
            "PACKAGE_RUNTIME_MANIFEST": str(package["manifest"]),
            "PATH": f"{tools}:{environment['PATH']}",
            "S04_E042_NVIDIA_SENTINEL": str(sentinel),
        })
        return environment

    def patch_cuda_preflight_for_telemetry_test(self, package: dict[str, object]) -> None:
        """Replace only the real CUDA probe in a sealed synthetic package.

        The package, materialization, and dependency receipts are rebound after
        the test-only replacement so the launcher still exercises its ordinary
        verification and post-preflight admission path.
        """
        task_root = Path(package["task_root"])
        code = task_root / "code"
        launcher = Path(package["launcher"])
        current = launcher.parent
        while True:
            current.chmod(0o700)
            if current == code:
                break
            current = current.parent
        launcher.chmod(0o700)
        opening = "cuda_preflight=\"$(\n    cd \"$TASKROOT/code\"\n    /usr/bin/python3 - <<'PY'\n"
        closing = '\nPY\n)" || fail "CUDA/import preflight failed"'
        before, remainder = launcher.read_text().split(opening, 1)
        _, after = remainder.split(closing, 1)
        launcher.write_text(before + "cuda_preflight='{\"synthetic\": true}'" + after)
        seal_tree(code)

        receipt_path = Path(package["receipt"])
        receipt = json.loads(receipt_path.read_text())
        receipt["entrypoint_sha256"] = sha256(launcher)
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        receipt_digest = sha256(receipt_path)

        materialization_path = task_root / "materialization_receipt.json"
        materialization = json.loads(materialization_path.read_text())
        materialization["package_receipt_sha256"] = receipt_digest
        materialization_path.write_text(json.dumps(materialization, indent=2, sort_keys=True) + "\n")

        dependency_receipt_path = task_root / "runtime_dependency_receipt.json"
        dependency_receipt = json.loads(dependency_receipt_path.read_text())
        dependency_receipt["package_receipt_sha256"] = receipt_digest
        dependency_receipt_path.write_text(json.dumps(dependency_receipt, indent=2, sort_keys=True) + "\n")

    def make_telemetry_nvidia_smi(self, tools: Path) -> None:
        executable(
            tools / "nvidia-smi",
            "#!/bin/bash\n"
            "set -euo pipefail\n"
            "state=\"${S04_E042_NVIDIA_STATE:?}\"\n"
            "case \"$*\" in\n"
            "  *--query-gpu*)\n"
            "    count=0\n"
            "    [[ -f \"$state\" ]] && count=\"$(cat \"$state\")\"\n"
            "    printf '%s' \"$((count + 1))\" > \"$state\"\n"
            "    utilization=0\n"
            "    if (( count >= 1 )) && [[ \"${S04_E042_PERSIST_HIGH_UTILIZATION:-}\" == 1 ]]; then\n"
            "      utilization=8\n"
            "    elif (( count == 1 )); then\n"
            "      utilization=8\n"
            "    fi\n"
            "    printf '0, GPU-test, NVIDIA GeForce RTX 4090, 4, %s, 550.0\\n' \"$utilization\"\n"
            "    ;;\n"
            "  *--query-compute-apps*)\n"
            "    if [[ -n \"${S04_E042_POST_PREFLIGHT_APPS:-}\" && \"$(cat \"$state\")\" -ge 2 ]]; then\n"
            "      printf '%s\\n' \"$S04_E042_POST_PREFLIGHT_APPS\"\n"
            "    fi\n"
            "    ;;\n"
            "  *)\n"
            "    echo \"unexpected nvidia-smi arguments: $*\" >&2\n"
            "    exit 99\n"
            "    ;;\n"
            "esac\n",
        )

    def bootstrap_package(self, root: Path) -> dict[str, object]:
        dependency = self.dependency_source(root)
        package_repo = root / "package-repo"
        package_repo.mkdir()
        for command in (
            ["git", "init", "-q", str(package_repo)],
            ["git", "-C", str(package_repo), "config", "user.email", "test@example.com"],
            ["git", "-C", str(package_repo), "config", "user.name", "Test"],
        ):
            subprocess.run(command, check=True)
        entrypoint = package_repo / ENTRYPOINT
        entrypoint.parent.mkdir(parents=True)
        executable(entrypoint, "#!/bin/bash\nexit 0\n")
        runner = package_repo / "scripts" / "run_s04_e042_projected_damage.py"
        helper = package_repo / "source" / "projected_damage.py"
        runner.parent.mkdir()
        helper.parent.mkdir()
        runner.write_text(
            'checkpoint["history_driver_mode"] == "current_active"\n'
            'not checkpoint["lagged_stiffness_enabled"]\n'
            "if not can_prepare_acceptance:\n"
            "publish_pointer_last(\n"
        )
        helper.write_bytes(b"helper\n")
        subprocess.run(["git", "-C", str(package_repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(package_repo), "commit", "-qm", "package"], check=True)
        commit = subprocess.check_output(["git", "-C", str(package_repo), "rev-parse", "HEAD"], text=True).strip()

        runs, archives = root / "runs", root / "archives"
        task_root, archive_root = runs / RUN_ID, archives / RUN_ID
        task_root.mkdir(parents=True)
        archive = task_root / "s04-e042-code.tar"
        with archive.open("wb") as handle:
            subprocess.run(
                ["git", "-C", str(package_repo), "archive", "--format=tar", "--prefix=code/", "HEAD"],
                stdout=handle, check=True,
            )
        manifest_files = [
            {"path": "scripts/run_s04_e042_projected_damage.py", "bytes": runner.stat().st_size, "sha256": sha256(runner)},
            {"path": "source/projected_damage.py", "bytes": helper.stat().st_size, "sha256": sha256(helper)},
        ]
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "reviewed_runtime_commit": REVIEWED_SOURCE,
            "files": manifest_files,
            "e042_import_proof": self.e042_import_proof("source/projected_damage.py", sha256(helper)),
        }
        manifest_path = task_root / "reviewed_runtime_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        bootstrap = task_root / "producer_bootstrap.sh"
        executable(bootstrap, self.patch_script(BOOTSTRAP, runs, archives, dependency))
        receipt = {
            "schema": RECEIPT_SCHEMA, "package_commit": commit, "reviewed_runtime_commit": REVIEWED_SOURCE,
            "archive_file": archive.name, "archive_sha256": sha256(archive), "archive_bytes": archive.stat().st_size,
            "runtime_manifest_file": manifest_path.name, "runtime_manifest_sha256": sha256(manifest_path),
            "entrypoint": ENTRYPOINT, "entrypoint_sha256": sha256(entrypoint),
            "bootstrap_file": bootstrap.name, "bootstrap_sha256": sha256(bootstrap),
        }
        receipt_path = task_root / "package_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        return {
            "task_root": task_root, "archive_root": archive_root, "archive": archive,
            "manifest": manifest_path, "bootstrap": bootstrap, "receipt": receipt_path,
            "dependency": dependency,
        }

    def bootstrap_tools(self, root: Path) -> tuple[Path, Path]:
        tools = root / "bin"
        tools.mkdir()
        marker = root / "systemd-called"
        executable(
            tools / "sha256sum",
            "#!/usr/bin/env python3\nimport hashlib, pathlib, sys\n"
            "p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest(), p)\n",
        )
        executable(
            tools / "git",
            "#!/bin/bash\n"
            "if [[ \"${1:-}\" == \"get-tar-commit-id\" && -n \"${S04_E042_ARCHIVE_MUTATED_SENTINEL:-}\" ]]; then\n"
            "  printf 'not-a-tar\\n' > \"$PACKAGE_ARCHIVE\"\n"
            "  touch \"$S04_E042_ARCHIVE_MUTATED_SENTINEL\"\n"
            "fi\n"
            "exec /usr/bin/git \"$@\"\n",
        )
        executable(
            tools / "systemd-run",
            "#!/bin/bash\n"
            "if [[ -n \"${S04_E042_SYSTEMD_ARGS:-}\" ]]; then\n"
            "  printf '%s\\n' \"$@\" > \"$S04_E042_SYSTEMD_ARGS\"\n"
            "fi\n"
            "touch \"$S04_E042_SYSTEMD_SENTINEL\"\n"
            "echo 'Running as unit: test.service'\n",
        )
        executable(
            tools / "systemctl",
            "#!/bin/bash\n"
            "if [[ \"$*\" == *show-environment* ]]; then\n"
            "  if [[ -n \"${S04_E042_SYSTEMD_MANAGER_UNAVAILABLE:-}\" ]]; then\n"
            "    echo 'Failed to connect to bus' >&2\n"
            "    exit 1\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "if [[ \"$*\" == *LoadState* ]]; then\n"
            "  echo 'LoadState=not-found'\n"
            "else\n"
            "  printf 'Id=test.service\\nMainPID=42\\nRuntimeMaxUSec=3600000000\\n'\n"
            "fi\n",
        )
        return tools, marker

    def bootstrap_environment(self, package: dict[str, object], tools: Path, marker: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update({
            "RUN_ID": RUN_ID, "TASKROOT": str(package["task_root"]),
            "PIDL_ARCHIVE_DIR": str(package["archive_root"]), "PHYSICAL_GPU_INDEX": "0",
            "BASELINE": str(Path(package["task_root"]).parent.parent / "baseline"),
            "REFERENCE_RESULT": str(Path(package["task_root"]).parent.parent / "reference"),
            "PACKAGE_ARCHIVE": str(package["archive"]), "PACKAGE_RECEIPT": str(package["receipt"]),
            "PACKAGE_RUNTIME_MANIFEST": str(package["manifest"]),
            "PACKAGE_RECEIPT_SHA256": sha256(Path(package["receipt"])),
            "PATH": f"{tools}:{environment['PATH']}", "S04_E042_SYSTEMD_SENTINEL": str(marker),
        })
        return environment

    def test_builder_pins_full_runtime_closure_and_projected_carrier_import(self) -> None:
        spec = importlib.util.spec_from_file_location("s04_e042_packager", PACKAGER)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        packager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(packager)
        self.assertEqual(packager.REVIEWED_RUNTIME_COMMIT, REVIEWED_SOURCE)
        paths = packager.runtime_paths(WORKTREE, REVIEWED_SOURCE)
        reviewed_source_paths = subprocess.check_output(
            ["git", "-C", str(WORKTREE), "ls-tree", "-r", "--name-only", REVIEWED_SOURCE, "--", "source"],
            text=True,
        ).splitlines()
        self.assertEqual([path for path in paths if path.startswith("source/")], reviewed_source_paths)
        self.assertEqual(len(reviewed_source_paths), 23)
        self.assertIn("source/projected_damage.py", paths)
        self.assertIn("scripts/run_s04_e042_projected_damage.py", paths)
        self.assertIn("SENS_tensile/field_computation.py", paths)
        self.assertIn("SENS_tensile/meshed_geom_fem_soft_hist0.msh", paths)
        self.assertNotIn("scripts/analyze_s04_e042_projected_damage.py", paths)
        proof = packager.projected_damage_import_proof(
            packager.blob(WORKTREE, REVIEWED_SOURCE, "scripts/run_s04_e042_projected_damage.py")
        )
        self.assertEqual(proof["module"], "projected_damage")
        self.assertEqual(proof["symbol"], "ReferenceBaseProjectedDamage")
        self.assertEqual(proof["module_path"], "source/projected_damage.py")
        self.assertIn("e042_import_proof", PACKAGER.read_text())

    def test_exact_remote_lock_and_isolated_import_are_declared(self) -> None:
        for script in (BOOTSTRAP, LAUNCHER):
            text = script.read_text()
            self.assertIn(f"readonly GMSHPARSER_SOURCE_ROOT={LOCK_SOURCE_ROOT}", text)
            self.assertIn(f"readonly GMSHPARSER_DISTRIBUTION_VERSION={LOCK_VERSION}", text)
            self.assertIn(f"readonly GMSHPARSER_TREE_SHA256={LOCK_TREE}", text)
            for name, (size, digest) in LOCK_FILES.items():
                self.assertIn(f'"path":"{name}","bytes":{size},"sha256":"{digest}"', text)
        launcher = LAUNCHER.read_text()
        self.assertTrue(BOOTSTRAP.read_text().startswith("#!/bin/bash\n"))
        self.assertTrue(launcher.startswith("#!/bin/bash\n"))
        self.assertIn("export PYTHONNOUSERSITE=1", launcher)
        self.assertIn("export PATH=/usr/bin:/bin", launcher)
        self.assertIn("export PATH=/usr/bin:/bin", BOOTSTRAP.read_text())
        self.assertIn("unset PYTHONPATH PYTHONHOME PYTHONUSERBASE PYTHONSTARTUP TAR_OPTIONS", BOOTSTRAP.read_text())
        self.assertIn("unset BASH_ENV ENV LD_PRELOAD LD_LIBRARY_PATH", launcher)
        self.assertIn("unset BASH_ENV ENV LD_PRELOAD LD_LIBRARY_PATH", BOOTSTRAP.read_text())
        self.assertIn("umask 077", BOOTSTRAP.read_text())
        self.assertIn('export PYTHONPATH="$TASKROOT/runtime_deps:$TASKROOT/code/source:$TASKROOT/code/SENS_tensile"', launcher)
        self.assertIn("gmshparser was not imported from the locked snapshot", launcher)
        self.assertIn("projected_damage was not imported from the checked runtime", launcher)
        self.assertIn("ReferenceBaseProjectedDamage", launcher)
        self.assertIn("/mnt/data2/drtao/wennie/.s04-e040-gpu-locks", launcher)
        self.assertIn("analysis_identity_receipt.json", launcher)
        self.assertIn("S04-E042-analysis-identity-receipt-v1", launcher)
        self.assertNotIn("require_clamp_min_right_derivative", launcher)
        self.assertNotIn("q_ref", launcher)
        self.assertNotIn("q_ref", BOOTSTRAP.read_text())
        self.assertIn('--setenv=PACKAGE_RECEIPT_SHA256="$PACKAGE_RECEIPT_SHA256"', BOOTSTRAP.read_text())
        for variable in ("BASH_ENV", "ENV", "LD_PRELOAD", "LD_LIBRARY_PATH"):
            self.assertIn(f"--setenv={variable}=", BOOTSTRAP.read_text())

    def test_valid_snapshot_reaches_frozen_input_gate_before_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing required file", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_mismatched_approval_receipt_pin_fails_before_snapshot_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            tools, sentinel = self.make_tools(root)
            environment = self.inner_environment(package, tools, sentinel)
            environment["PACKAGE_RECEIPT_SHA256"] = "0" * 64
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 2)
            self.assertIn("package receipt does not match approval-card SHA-256", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_missing_approval_receipt_pin_fails_with_wrapper_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            tools, sentinel = self.make_tools(root)
            environment = self.inner_environment(package, tools, sentinel)
            environment.pop("PACKAGE_RECEIPT_SHA256")
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid approval-card receipt SHA-256", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_tampered_archive_fails_before_input_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            Path(package["archive"]).write_bytes(b"tampered\n")
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("uploaded package archive differs from receipt", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_altered_reviewed_runtime_file_fails_before_input_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            runner = Path(package["runner"])
            runner.chmod(0o600)
            runner.write_bytes(b"x" * runner.stat().st_size)
            runner.chmod(0o400)
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("runtime file hash differs", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_existing_archive_root_fails_before_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            Path(package["archive_root"]).mkdir(parents=True)
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing non-fresh archive root", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_missing_snapshot_fails_before_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            snapshot_root = Path(package["task_root"]) / "runtime_deps"
            snapshot_root.chmod(0o700)
            (snapshot_root / "gmshparser").chmod(0o700)
            for child in snapshot_root.rglob("*"):
                if child.is_file():
                    child.unlink()
            (snapshot_root / "gmshparser").rmdir()
            snapshot_root.rmdir()
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing bootstrap runtime dependency snapshot", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_tampered_snapshot_fails_before_input_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            mesh = Path(package["task_root"]) / "runtime_deps" / "gmshparser" / "mesh.py"
            mesh.chmod(0o600)
            mesh.write_text("tampered\n")
            mesh.chmod(0o400)
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("snapshot dependency file differs from lock", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_writable_code_tree_fails_before_input_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            runner = Path(package["runner"])
            runner.chmod(0o600)
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("materialized code tree contains a writable path", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_writable_snapshot_parent_fails_before_input_or_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            snapshot_parent = Path(package["task_root"]) / "runtime_deps"
            snapshot_parent.chmod(0o700)
            tools, sentinel = self.make_tools(root)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=self.inner_environment(package, tools, sentinel))
            self.assertEqual(result.returncode, 2)
            self.assertIn("runtime dependency parent is writable", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_inner_verifier_clears_inherited_python_path_before_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            tools, sentinel = self.make_tools(root)
            poison = root / "poison-python-path"
            poison.mkdir()
            (poison / "json.py").write_text("raise RuntimeError('poisoned PYTHONPATH')\n")
            environment = self.inner_environment(package, tools, sentinel)
            environment["PYTHONPATH"] = str(poison)
            environment["PYTHONHOME"] = str(poison)
            environment["PYTHONUSERBASE"] = str(poison)
            environment["PYTHONSTARTUP"] = str(poison / "startup.py")
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing required file", result.stderr)
            self.assertNotIn("poisoned PYTHONPATH", result.stderr)
            self.assertFalse(sentinel.exists())

    def test_inner_verifier_clears_inherited_path_before_frozen_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root)
            tools, sentinel = self.make_tools(root)
            poison = root / "poison-path"
            poison.mkdir()
            poison_sentinel = root / "poison-sha256sum-called"
            executable(
                poison / "sha256sum",
                "#!/bin/bash\ntouch \"$S04_E042_POISON_PATH_SENTINEL\"\necho poison\n",
            )
            environment = self.inner_environment(package, tools, sentinel)
            environment["PATH"] = f"{poison}:/usr/bin:/bin"
            environment["S04_E042_POISON_PATH_SENTINEL"] = str(poison_sentinel)
            result = subprocess.run([str(package["launcher"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing required file", result.stderr)
            self.assertFalse(poison_sentinel.exists())
            self.assertFalse(sentinel.exists())

    def test_post_preflight_utilization_tail_must_settle_before_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root, frozen_inputs=True)
            self.patch_cuda_preflight_for_telemetry_test(package)
            tools, sentinel = self.make_tools(root)
            self.make_telemetry_nvidia_smi(tools)
            Path(package["archive_root"]).parent.mkdir(parents=True)
            state = root / "nvidia-query-count"
            environment = self.inner_environment(package, tools, sentinel)
            environment["S04_E042_NVIDIA_STATE"] = str(state)
            result = subprocess.run(
                [str(package["launcher"])], text=True, capture_output=True, env=environment, timeout=15
            )
            self.assertEqual(result.returncode, 99, result.stderr)
            self.assertEqual(state.read_text(), "3")
            preflight = Path(package["archive_root"]) / "producer_preflight.txt"
            self.assertTrue(preflight.is_file())
            self.assertIn("post_cuda_preflight_settle_attempts=1", preflight.read_text())
            identity = Path(package["archive_root"]) / "analysis_identity_receipt.json"
            self.assertTrue(identity.is_file())
            self.assertEqual(identity.stat().st_mode & 0o222, 0)
            receipt = json.loads(identity.read_text())
            self.assertEqual(receipt["schema"], "S04-E042-analysis-identity-receipt-v1")
            self.assertEqual(receipt["history_timing"]["history_driver_mode"], "current_active")
            self.assertIs(receipt["history_timing"]["lagged_stiffness_enabled"], False)
            self.assertEqual(receipt["history_timing"]["transaction_boundary"], "accepted_only")
            self.assertEqual(receipt["runtime"]["reviewed_runtime_commit"], REVIEWED_SOURCE)
            self.assertEqual(receipt["result_linkage"]["state"], "pre_run_identity_only")
            self.assertFalse((Path(package["archive_root"]) / "analysis_result_linkage_receipt.json").exists())

    def test_post_preflight_compute_process_is_not_granted_a_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root, frozen_inputs=True)
            self.patch_cuda_preflight_for_telemetry_test(package)
            tools, sentinel = self.make_tools(root)
            self.make_telemetry_nvidia_smi(tools)
            state = root / "nvidia-query-count"
            environment = self.inner_environment(package, tools, sentinel)
            environment["S04_E042_NVIDIA_STATE"] = str(state)
            environment["S04_E042_POST_PREFLIGHT_APPS"] = "GPU-test, 1234, foreign-worker, 10"
            result = subprocess.run(
                [str(package["launcher"])], text=True, capture_output=True, env=environment, timeout=15
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("already has a compute process at before_runner", result.stderr)
            self.assertEqual(state.read_text(), "2")
            self.assertFalse(Path(package["archive_root"]).exists())

    def test_post_preflight_utilization_still_fails_after_bounded_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root, frozen_inputs=True)
            self.patch_cuda_preflight_for_telemetry_test(package)
            tools, sentinel = self.make_tools(root)
            self.make_telemetry_nvidia_smi(tools)
            state = root / "nvidia-query-count"
            environment = self.inner_environment(package, tools, sentinel)
            environment["S04_E042_NVIDIA_STATE"] = str(state)
            environment["S04_E042_PERSIST_HIGH_UTILIZATION"] = "1"
            result = subprocess.run(
                [str(package["launcher"])], text=True, capture_output=True, env=environment, timeout=15
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("utilization after 3s post-preflight cooldown", result.stderr)
            self.assertEqual(state.read_text(), "5")
            self.assertFalse(Path(package["archive_root"]).exists())

    def test_successful_runner_writes_sealed_result_linkage_after_result_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.inner_package(root, frozen_inputs=True)
            self.patch_cuda_preflight_for_telemetry_test(package)
            tools, _ = self.make_tools(root)
            self.make_timeout_passthrough(tools)
            self.make_telemetry_nvidia_smi(tools)
            Path(package["archive_root"]).parent.mkdir(parents=True)
            state = root / "nvidia-query-count"
            environment = self.inner_environment(package, tools, root / "unused-sentinel")
            environment["S04_E042_NVIDIA_STATE"] = str(state)
            result = subprocess.run(
                [str(package["launcher"])], text=True, capture_output=True, env=environment, timeout=15
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            archive_root = Path(package["archive_root"])
            linkage = archive_root / "analysis_result_linkage_receipt.json"
            self.assertTrue(linkage.is_file())
            self.assertEqual(linkage.stat().st_mode & 0o222, 0)
            receipt = json.loads(linkage.read_text())
            self.assertEqual(receipt["schema"], "S04-E042-analysis-result-linkage-receipt-v2")
            self.assertEqual(receipt["runner_exit_code"], 0)
            self.assertEqual(receipt["result_summary"]["completed_three_cycles"], True)
            self.assertEqual(
                receipt["result_files"]["manifest.json"]["sha256"],
                sha256(archive_root / "results" / "manifest.json"),
            )
            self.assertEqual(
                receipt["result_files"]["projected_damage/steps.json"]["sha256"],
                sha256(archive_root / "results" / "projected_damage" / "steps.json"),
            )
            self.assertEqual(
                receipt["result_files"]["projected_damage/accepted_state_pointer.json"]["sha256"],
                sha256(archive_root / "results" / "projected_damage" / "accepted_state_pointer.json"),
            )
            self.assertEqual(len(receipt["result_files"]), 7)

    def test_bootstrap_snapshots_source_before_systemd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            tools, marker = self.bootstrap_tools(root)
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=self.bootstrap_environment(package, tools, marker))
            self.assertEqual(result.returncode, 0, result.stderr)
            task_root = Path(package["task_root"])
            receipt = json.loads((task_root / "runtime_dependency_receipt.json").read_text())
            self.assertEqual(receipt["package_receipt_sha256"], sha256(Path(package["receipt"])))
            self.assertEqual(receipt["canonical_tree_sha256"], package["dependency"]["tree"])
            self.assertTrue((task_root / "runtime_deps" / "gmshparser" / "mesh.py").is_file())
            for path in (
                task_root / "code",
                task_root / "runtime_deps",
                task_root / "runtime_deps" / "gmshparser",
                task_root / "runtime_deps" / "gmshparser" / "mesh.py",
            ):
                self.assertEqual(path.stat().st_mode & 0o222, 0, str(path))
            self.assertEqual(task_root.stat().st_mode & 0o077, 0)
            self.assertTrue(marker.exists())

    def test_bootstrap_makes_group_writable_staging_root_private_before_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            task_root = Path(package["task_root"])
            task_root.chmod(0o770)
            tools, marker = self.bootstrap_tools(root)
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=self.bootstrap_environment(package, tools, marker))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(task_root.stat().st_mode & 0o077, 0)
            self.assertTrue(marker.exists())

    def test_bootstrap_requires_user_manager_before_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            tools, marker = self.bootstrap_tools(root)
            environment = self.bootstrap_environment(package, tools, marker)
            environment["S04_E042_SYSTEMD_MANAGER_UNAVAILABLE"] = "1"
            task_root = Path(package["task_root"])
            staged_mode = task_root.stat().st_mode & 0o777
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 2)
            self.assertIn("user systemd manager is unreachable", result.stderr)
            self.assertEqual(task_root.stat().st_mode & 0o777, staged_mode)
            self.assertFalse(marker.exists())
            self.assertFalse((task_root / "code").exists())
            self.assertFalse((task_root / "runtime_deps").exists())
            self.assertFalse((task_root / "materialization_receipt.json").exists())
            self.assertFalse((task_root / "launch_once").exists())
            self.assertFalse(list(task_root.glob(".verified-package-*.tar")))

    def test_systemd_submission_clears_preinterpreter_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            tools, marker = self.bootstrap_tools(root)
            systemd_args = root / "systemd-run-args"
            environment = self.bootstrap_environment(package, tools, marker)
            environment["S04_E042_SYSTEMD_ARGS"] = str(systemd_args)
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            arguments = systemd_args.read_text().splitlines()
            for variable in ("BASH_ENV", "ENV", "LD_PRELOAD", "LD_LIBRARY_PATH"):
                self.assertIn(f"--setenv={variable}=", arguments)

    def test_bootstrap_uses_frozen_tar_after_staged_archive_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            tools, marker = self.bootstrap_tools(root)
            mutation_sentinel = root / "staged-archive-mutated"
            environment = self.bootstrap_environment(package, tools, marker)
            environment["S04_E042_ARCHIVE_MUTATED_SENTINEL"] = str(mutation_sentinel)
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(mutation_sentinel.exists())
            self.assertEqual(Path(package["archive"]).read_bytes(), b"not-a-tar\n")
            materialization = json.loads(
                (Path(package["task_root"]) / "materialization_receipt.json").read_text()
            )
            package_receipt = json.loads(Path(package["receipt"]).read_text())
            self.assertEqual(materialization["archive_sha256"], package_receipt["archive_sha256"])
            self.assertTrue((Path(package["task_root"]) / "code" / "scripts" / "run_s04_e042_projected_damage.py").is_file())
            self.assertTrue(marker.exists())
            self.assertFalse(list(Path(package["task_root"]).glob(".verified-package-*.tar")))

    def test_direct_bootstrap_exec_ignores_poisoned_bash_and_tar_options(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            tools, marker = self.bootstrap_tools(root)
            poison = root / "poison-path"
            poison.mkdir()
            poison_sentinel = root / "poison-bash-called"
            executable(
                poison / "bash",
                "#!/bin/bash\ntouch \"$S04_E042_POISON_BASH_SENTINEL\"\nexit 91\n",
            )
            environment = self.bootstrap_environment(package, tools, marker)
            environment["PATH"] = f"{poison}:/usr/bin:/bin"
            environment["TAR_OPTIONS"] = "--definitely-invalid"
            environment["S04_E042_POISON_BASH_SENTINEL"] = str(poison_sentinel)
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(poison_sentinel.exists())
            self.assertTrue(marker.exists())

    def test_bootstrap_verifier_clears_inherited_python_path_before_systemd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            tools, marker = self.bootstrap_tools(root)
            poison = root / "poison-python-path"
            poison.mkdir()
            (poison / "json.py").write_text("raise RuntimeError('poisoned PYTHONPATH')\n")
            environment = self.bootstrap_environment(package, tools, marker)
            environment["PYTHONPATH"] = str(poison)
            environment["PYTHONHOME"] = str(poison)
            environment["PYTHONUSERBASE"] = str(poison)
            environment["PYTHONSTARTUP"] = str(poison / "startup.py")
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("poisoned PYTHONPATH", result.stderr)
            self.assertTrue(marker.exists())

    def test_bootstrap_rejects_mismatched_approval_pin_before_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            tools, marker = self.bootstrap_tools(root)
            environment = self.bootstrap_environment(package, tools, marker)
            environment["PACKAGE_RECEIPT_SHA256"] = "0" * 64
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=environment)
            self.assertEqual(result.returncode, 2)
            self.assertIn("receipt does not match its approval-card SHA-256", result.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse((Path(package["task_root"]) / "code").exists())

    def test_bootstrap_rejects_source_change_before_systemd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.bootstrap_package(root)
            source = Path(package["dependency"]["source"])
            (source / "mesh.py").write_text("tampered source\n")
            tools, marker = self.bootstrap_tools(root)
            result = subprocess.run([str(package["bootstrap"])], text=True, capture_output=True,
                                    env=self.bootstrap_environment(package, tools, marker))
            self.assertEqual(result.returncode, 2)
            self.assertIn("source dependency file differs from lock", result.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse((Path(package["task_root"]) / "code").exists())


if __name__ == "__main__":
    unittest.main()
