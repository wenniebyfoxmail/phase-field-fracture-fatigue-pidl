"""Pure-I/O bindings for the prospective release; no torch/solver imports."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re

BASE_COMMIT = "68291a0ae9d8723c8747ba87ab8c6a077ac0f9a7"
PHYSICS_SHA = "600009c049758468833f756ce13c2582b38e2676178db1eb333a475e52528e38"
CASE = "c1s2"
METHOD = "nodal_damage_raw_preimage_release_v1"
SOURCE_JOB = "d4_c1s2_continue_01"
SCIENTIFIC_STOPS = {"fixed_f_numerical_stagnation_not_stationarity_proof",
                    "line_search_limit_restored_previous_state"}
PREP_DIR = "tools/s04_e036/constraint_release_preparation/"
OVERLAY_FILES = {PREP_DIR + name for name in
                 ("release.py", "contract.py", "bind_source.py", "run_release.py", "release_config.json")}
SOURCE_REFS = {"physics_manifest", "worker_attempt", "worker_finished", "worker_outcome",
               "execution_authority", "source_endpoints", "implementation_lock", "source_snapshot",
               "supervisor_authority", "supervisor_attempt", "supervisor_started", "supervisor_finished"}
SNAPSHOT_REFS = {"completion", "bundle", "fields", "network"}
CONFIG = dict(schema="s04_e036_constraint_release_config_v1", method=METHOD, case=CASE,
    source_job=SOURCE_JOB, base_source_commit=BASE_COMMIT, physics_manifest_sha256=PHYSICS_SHA,
    source_must_be="completed_failed_C0_continuation_float64_terminal",
    source_scientific_stops=sorted(SCIENTIFIC_STOPS), future_target_used=False,
    teacher_initialized=False, history_commit_count=0,
    release_plan=dict(damage_trust_radius=.02, node_armijo=1e-4, node_backtracks=25,
        energy_fraction=.1, blocked_work_fraction=.1, lbfgs_history=100,
        closures_per_step=25, stagnant_steps=20, proxy_relative_change=1e-10),
    physical_continuation_once=True,
    physical_solver=dict(lbfgs_history_size=100, lbfgs_closures_per_step=25,
        lbfgs_fixed_f_steps=200, lbfgs_stagnation_steps=20, physics_relative_energy_change=1e-10),
    continuation_failure_retained_state="verified_release_candidate",
    release_failure_retained_state="verified_source_terminal", no_automatic_retry=True,
    job_wall_seconds=86400, cumulative_resource_limit=None)


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    def reject(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(Path(path).read_text(), parse_constant=reject)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path):
    path = Path(path).resolve(strict=True)
    return dict(path=str(path), sha256=sha(path))


def bound(spec, root):
    require(isinstance(spec, dict) and set(spec) == {"path", "sha256"}, "invalid bound reference")
    require(isinstance(spec["path"], str) and bool(spec["path"]), "missing actual path")
    require(isinstance(spec["sha256"], str) and re.fullmatch("[0-9a-f]{64}", spec["sha256"]), "missing actual SHA")
    candidate = Path(spec["path"])
    candidate = candidate if candidate.is_absolute() else Path(root) / candidate
    require(not candidate.is_symlink(), "symlink input is not an immutable binding")
    path = candidate.resolve(strict=True)
    require(path.is_file() and sha(path) == spec["sha256"], "input byte binding differs: " + str(path))
    return path


def same(a, b, label):
    require(json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False), label)


def argv_values(argv):
    require(isinstance(argv, list) and len(argv) >= 4 and len(argv) % 2 == 0
            and all(isinstance(v, str) and v for v in argv), "expected explicit flag/value argv")
    flags = argv[2::2]
    require(len(set(flags)) == len(flags) and all(x.startswith("--") for x in flags), "duplicate/nonflag argv")
    return dict(zip(flags, argv[3::2]))


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "UTC clock needs timezone")
    return parsed.timestamp()


def verify_source(binding, root):
    """Verify a clean completed source attempt, all byte identities and clocks.

    It only reads JSON/bytes. Tensor semantics/replay happen on the producer.
    """
    require(set(binding) == {"schema", "case", "source_job_root", "refs", "endpoint"}
            and binding["schema"] == "s04_e036_constraint_release_source_v1"
            and binding["case"] == CASE, "wrong closed source-binding schema")
    require(set(binding["refs"]) == SOURCE_REFS and set(binding["endpoint"]) == SNAPSHOT_REFS,
            "incomplete source chain or unexpected target input")
    require(Path(binding["source_job_root"]).is_absolute()
            and all(Path(v["path"]).is_absolute() for v in
                    (*binding["refs"].values(), *binding["endpoint"].values())),
            "late binder must preserve actual absolute producer paths")
    paths = {k: bound(v, root) for k, v in binding["refs"].items()}
    endpoint = {k: bound(v, root) for k, v in binding["endpoint"].items()}
    docs = {k: read(p) for k, p in paths.items()}
    job = Path(binding["source_job_root"]).resolve(strict=True)
    require(job.name == SOURCE_JOB and str(job).startswith("/mnt/data2/drtao/wennie/pf_s04e036_"), "wrong source job")
    sa, attempt, started, ended = (docs[k] for k in ("supervisor_authority", "supervisor_attempt",
                                                   "supervisor_started", "supervisor_finished"))
    require(sa["schema"] == "s04_e036_gpu_supervisor_v2" and sa["approved"] is True
            and sa["hostname"] == "GPUServer8" and sa["gpu"] == 5
            and Path(sa["root"]).resolve() == job and sa["label"] == "optimization_probe",
            "wrong source producer/supervisor")
    values = argv_values(sa["argv"])
    require(set(values) == {"--manifest", "--authority", "--out", "--device", "--case", "--phase", "--source-endpoints"}
            and values["--phase"] == "candidate_continuation" and values["--case"] == CASE
            and values["--device"] == "cuda:0", "source is not the prescribed target-free continuation")
    output = Path(values["--out"]).resolve()
    code = Path(sa["cwd"]).resolve()
    require(output == job / "output" and code == job / "code"
            and Path(sa["argv"][1]).resolve() == code / "tools/s04_e036/run_mechanism_matrix.py"
            and sa["entry_sha256"] == sha(sa["argv"][1]), "source executable/output identity changed")
    for flag, name in (("--manifest", "physics_manifest"), ("--authority", "execution_authority"),
                       ("--source-endpoints", "source_endpoints")):
        require(Path(values[flag]).resolve() == paths[name], "source argument differs: " + flag)
    for name, relative in (("worker_attempt", "attempt.json"), ("worker_finished", "finished.json")):
        require(paths[name] == output / relative, "worker receipt outside original output")
    for name, suffix in (("supervisor_attempt", "attempt"), ("supervisor_started", "started"), ("supervisor_finished", "finished")):
        require(paths[name] == job / "supervisor" / ("optimization_probe_" + suffix + ".json"), "wrong source supervisor receipt")
    require(not (output / "job_failure.json").exists()
            and not (job / "supervisor" / "optimization_probe_unknown.json").exists(), "source technical failure/unknown outcome")
    require(attempt["schema"] == "s04_e036_gpu_attempt_v2" and attempt["host"] == "GPUServer8"
            and attempt["gpu"] == 5 and attempt["gpu_count"] == 1
            and attempt["authority_sha256"] == sha(paths["supervisor_authority"])
            and attempt["argv"] == sa["argv"] and attempt["cwd"] == sa["cwd"], "source supervisor attempt differs")
    require(started["attempt_sha256"] == ended["attempt_sha256"] == sha(paths["supervisor_attempt"])
            and ended["exit_code"] == 0 and ended["reason"] == "completed"
            and ended["within_anti_hang_interval"] is True
            and attempt["anti_hang_seconds"] == ended["anti_hang_seconds"] == sa["wall_seconds"],
            "source did not complete cleanly under its actual watchdog")
    require(started["pid"] == started["pgid"] and started["command"][-len(sa["argv"]):] == sa["argv"], "source worker identity differs")
    start, finish = timestamp(attempt["started_utc"]), timestamp(ended["ended_utc"])
    charge = ended["charged_gpu_seconds"]
    require(type(charge) in (int, float) and math.isfinite(charge) and charge >= 0 and finish >= start,
            "invalid source elapsed clock")
    require(start <= timestamp(started["started_utc"]) <= finish, "source start receipt clock differs")
    wa, wf, wo, ea = (docs[k] for k in ("worker_attempt", "worker_finished", "worker_outcome", "execution_authority"))
    require(wa["schema"] == "s04_e036_mechanism_attempt_v1" and wa["phase"] == "candidate_continuation"
            and wa["requested_case"] == CASE and wa["execution_cases"] == [CASE]
            and wa["history_commit_count"] == 0 and start <= wa["started_unix"] <= finish,
            "source worker/clock identity differs")
    same(wa["command"], sa["argv"][1:], "worker argv differs from supervised command")
    same(wa["provenance"]["authority"], ea, "worker did not use this execution authority")
    require(ea["approved"] is True and ea["mechanism_phase"] == "candidate_continuation"
            and ea["requested_case"] == CASE and ea["manifest_sha256"] == PHYSICS_SHA == sha(paths["physics_manifest"])
            and wa["manifest_sha256"] == PHYSICS_SHA
            and ea["implementation_lock"]["sha256"] == sha(paths["implementation_lock"])
            and ea["source_endpoints"]["sha256"] == sha(paths["source_endpoints"]), "source input/code authority differs")
    require(wf["status"] == "program_completed" and wf["phase"] == "candidate_continuation"
            and wf["requested_case"] == CASE and wf["execution_cases"] == [CASE]
            and wf["history_commit_count"] == 0 and len(wf["outcomes"]) == 1,
            "source worker is incomplete")
    same(wf["outcomes"][0], wo, "source outcome differs from finished record")
    require(paths["worker_outcome"].parent == output and wo["case"] == CASE
            and wo["status"] in SCIENTIFIC_STOPS and wo["physical_accepted"] is False,
            "source must have a real terminal scientific failure, not success or technical abort")
    lock, snap = docs["implementation_lock"], docs["source_snapshot"]
    require(lock["schema"] == "s04_e036_implementation_lock_v1"
            and snap["schema"] == "s04_e036_source_snapshot_v1" and snap["source_commit"] == BASE_COMMIT
            and paths["source_snapshot"] == code / "source_snapshot.json", "wrong frozen base source")
    require(wa["provenance"]["source"]["source_kind"] == "standalone_snapshot"
            and wa["provenance"]["source"]["source_commit"] == BASE_COMMIT
            and wa["provenance"]["source"]["source_snapshot_sha256"] == sha(paths["source_snapshot"]),
            "worker did not use the independently bound frozen snapshot")
    same(lock["files"], snap["files"], "source snapshot and independent lock differ")
    for rel, digest in snap["files"].items():
        file = (code / rel).resolve()
        require(not Path(rel).is_absolute() and file.is_relative_to(code) and sha(file) == digest,
                "frozen source bytes changed: " + rel)
    receipt = read(endpoint["completion"])
    require(len({p.parent for p in endpoint.values()}) == 1 and endpoint["completion"].parent.is_relative_to(output / CASE / "C0"),
            "terminal snapshot lies outside source C0 output")
    require(receipt["schema"] == "s04_e036_mechanism_completion_v1" and receipt["endpoint_complete"] is True
            and receipt["readback_verified"] is True and receipt["fields_reproduced_exactly"] is True
            and receipt["physical_accepted"] is False and receipt["history_commit_count"] == 0,
            "source endpoint is not a verified failed terminal state")
    meta = receipt["metadata"]
    require(meta["arm"] == "C0" and meta["stage"] == "lbfgs_final" and meta["dtype"] == "float64"
            and meta["mapping"] == "nodal_clamp" and meta["weight_l2"] == 0
            and meta["teacher_initialized"] is False and meta["complete_endpoint"] is True,
            "wrong terminal stage/map/dtype")
    same(meta["state_key"], docs["physics_manifest"]["cases"][CASE]["state_key"], "source state differs")
    for name in ("bundle", "fields", "network"):
        require(receipt[name + "_sha256"] == sha(endpoint[name]), "endpoint bytes differ: " + name)
    same(wo["work"], receipt["actual_work"], "terminal work differs from worker outcome")
    return dict(paths=paths, endpoint=endpoint, docs=docs, receipt=receipt,
                source_clock=dict(started_utc=attempt["started_utc"], ended_utc=ended["ended_utc"],
                                  charged_gpu_seconds=charge, worker_started_unix=wa["started_unix"]))
