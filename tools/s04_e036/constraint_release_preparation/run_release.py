#!/usr/bin/env python3
"""Producer-only prospective C0 release; requires a real separately bound job.

Preparation does not grant execution. No FEM-target CLI, loader call, queue edit,
history commit, retry or alternate checkpoint selection exists in this entry.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))

from contract import (BASE_COMMIT, CASE, CONFIG, METHOD, OVERLAY_FILES, bound, read,
                      ref, require, same, sha, timestamp, verify_source)

AUTHORITY_KEYS = {"schema", "approved", "approval_reference", "manifest_sha256", "hostname",
    "cuda_visible_devices", "gpu_uuid", "implementation_lock", "fem_validation", "stage_a_semantic_binding",
    "requested_case", "mechanism_phase", "method", "source_binding", "release_config", "owner_scope",
    "base_source_commit", "release_source_commit", "job_wall_seconds", "cumulative_resource_limit", "no_automatic_retry"}


def validate_authority(args, runner, torch):
    authority, source = runner.check_authority(args.authority, args.manifest, torch.device(args.device))
    require(set(authority) == AUTHORITY_KEYS, "release authority must have exact target-free fields")
    require(authority["hostname"] == "GPUServer8" and authority["cuda_visible_devices"] == "5"
            and authority["requested_case"] == CASE and authority["mechanism_phase"] == "constraint_release"
            and authority["method"] == METHOD and authority["base_source_commit"] == BASE_COMMIT
            and authority["no_automatic_retry"] is True and authority["cumulative_resource_limit"] is None
            and authority["job_wall_seconds"] == CONFIG["job_wall_seconds"], "release authority changed the fixed scope")
    root = args.authority.resolve().parent
    for name, path in (("source_binding", args.source_binding), ("release_config", args.config)):
        require(bound(authority[name], root) == path.resolve(), "authority does not bind " + name)
    bound(authority["owner_scope"], root)
    same(read(args.config), CONFIG, "release numerical config differs")
    require(isinstance(authority["release_source_commit"], str)
            and re.fullmatch("[0-9a-f]{40}", authority["release_source_commit"]), "actual release commit required")
    require(source["source_kind"] == "standalone_snapshot"
            and source["source_commit"] == authority["release_source_commit"], "wrong release source snapshot")
    source_binding = read(args.source_binding)
    original = verify_source(source_binding, args.source_binding.resolve().parent)
    require(original["paths"]["physics_manifest"] == args.manifest.resolve(), "reuse the actual original physics manifest")
    current_lock = read(bound(authority["implementation_lock"], root))["files"]
    base_lock = original["docs"]["implementation_lock"]["files"]
    require(set(current_lock) == set(base_lock) | OVERLAY_FILES, "only the named release overlay may join frozen base")
    for name, digest in base_lock.items():
        require(current_lock[name] == digest, "frozen production dependency changed: " + name)
    for name in OVERLAY_FILES:
        require(current_lock[name] == sha(ROOT / name), "release overlay byte drift")
    require(sha(args.config) == sha(ROOT / "tools/s04_e036/constraint_release_preparation/release_config.json"),
            "runtime configuration differs from locked source configuration")
    import gpu_watchdog
    supervisor = read(args.supervisor_authority)
    job, cwd, argv, wall = gpu_watchdog.validate(supervisor, args.supervisor_authority)
    require(cwd == ROOT and supervisor["label"] == "optimization_probe" and supervisor["gpu"] == 5
            and wall == CONFIG["job_wall_seconds"] and args.out.resolve() == job / "output",
            "release must have its own fresh supervised job/output")
    require(Path(argv[0]).resolve() == Path(sys.executable).resolve()
            and argv[1:] == sys.argv, "worker argv is not the exact supervised argv")
    require(job != Path(source_binding["source_job_root"]).resolve(), "cannot reuse the source job directory")
    supervised = read(job / "supervisor/optimization_probe_attempt.json")
    require(supervised["authority_sha256"] == sha(args.supervisor_authority)
            and supervised["argv"] == argv and supervised["cwd"] == str(ROOT)
            and supervised["gpu"] == 5 and supervised["gpu_count"] == 1,
            "missing real current supervisor attempt; direct worker launch is forbidden")
    uuid = subprocess.check_output(["nvidia-smi", "-i", "5", "--query-gpu=uuid", "--format=csv,noheader"], text=True).strip()
    require(authority["gpu_uuid"] == uuid and uuid.startswith("GPU-"), "GPU identity differs from bound authority")
    require(os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8", "preserve the original deterministic CUDA workspace setting")
    clock_start = timestamp(supervised["started_utc"])
    remaining = wall - (time.time() - clock_start) - 30
    require(0 < remaining <= wall, "invalid/exhausted actual job clock")
    return dict(authority=authority, source=source, binding=source_binding, original=original,
                job=job, source_clock=original["source_clock"], current_supervisor=supervised,
                deadline=runner.Deadline(remaining, "constraint-release supervised job"))


def restore_source(context, doc, problem, runner, torch):
    """Use the existing target-free snapshot verifier; restore exact terminal state."""
    # This module defines scoring helpers too, but no scoring/target loader is
    # called. verify_snapshot only consumes four saved NN artifacts and old state.
    from score_mechanism_matrix import verify_snapshot, endpoint_role
    original, binding = context["original"], context["binding"]
    manifest = original["paths"]["physics_manifest"]
    spec = doc["cases"][CASE]
    old, _, admission = runner.load_predecessor(spec, manifest.parent, problem)
    source_endpoints = original["docs"]["source_endpoints"]
    require(set(source_endpoints) == {"schema", "physics_manifest", "cases"}
            and source_endpoints["schema"] == "s04_e036_C0_continuation_v1"
            and set(source_endpoints["cases"]) == set(runner.CASES), "source continuation input schema changed")
    require(bound(source_endpoints["physics_manifest"], original["paths"]["source_endpoints"].parent) == manifest,
            "source continuation binds another physics manifest")
    prefix = source_endpoints["cases"][CASE]
    require(set(prefix) == {"completion", "bundle"}, "source must name its actual initial C0 matrix endpoint")
    for item in prefix.values():
        bound(item, original["paths"]["source_endpoints"].parent)
    provenance = dict(case=CASE, manifest_sha256=sha(manifest), theta0_sha256=runner.NETWORK_SHA[CASE],
        predecessor_checkpoint_sha256=admission["source_checkpoint"]["sha256"],
        predecessor=spec["predecessor"], predecessor_admission=spec["admission"],
        execution_phase="candidate_continuation", source_endpoint=prefix,
        continuation="precision_plus_solver; not isolated dtype effect")
    verified = verify_snapshot(binding["endpoint"], Path("/"), problem, old, spec["state_key"], "C0",
        "candidate_continuation", provenance, context["deadline"])
    payload, receipt = verified["payload"], verified["receipt"]
    same(payload["provenance"], provenance, "source contains unrecognized/target provenance")
    endpoint_role(payload["metadata"], receipt["actual_work"], "candidate_continuation")
    same(payload["extra"]["stop_reason"], original["docs"]["worker_outcome"]["status"], "terminal stop reason differs")
    same(payload["extra"]["objective_report"], original["docs"]["worker_outcome"]["objective_report"], "terminal objective differs")
    require(payload["metadata"]["dtype"] == "float64" and verified["fresh"]["physical_accepted"] is False,
            "release only a real failed float64 terminal state")
    require(receipt["actual_work"]["snapshot_replays"] == payload["work"]["snapshot_replays"] + 1,
            "terminal snapshot replay accounting differs")
    method_provenance = dict(provenance, source_execution_phase="candidate_continuation",
        execution_phase="constraint_release", method=METHOD, future_target_used=False,
        teacher_initialized=False, source_terminal=binding["endpoint"],
        source_binding_sha256=sha(context["source_binding_path"]), source_clock=context["source_clock"],
        base_source_commit=BASE_COMMIT, release_source_commit=context["authority"]["release_source_commit"])
    engine = runner.EndpointEngine(problem, old, payload["network_state"], spec["state_key"], "C0",
        torch.float64, context["deadline"], method_provenance)
    engine.coefficient = payload["result"]["f_solve"].to(problem.device).clone()
    engine.work.update(receipt["actual_work"])
    runner.exact_payload(runner.cpu(engine.field.net.state_dict()), payload["network_state"])
    runner.exact_payload(runner.cpu(engine.coefficient), payload["result"]["f_solve"])
    engine.verify_old()
    return engine, verified


def main(args):
    # Imports define helpers only; authority precedes geometry/model construction.
    import torch
    import run_mechanism_matrix as runner
    from release import PLAN, _energy, attempt_release
    from stage_a_reuse import validate_stage_a_reuse
    context = validate_authority(args, runner, torch)
    context["source_binding_path"] = args.source_binding.resolve()
    same(asdict(PLAN), CONFIG["release_plan"], "release implementation/config differs")
    same({k: runner.SOLVER[k] for k in CONFIG["physical_solver"]}, CONFIG["physical_solver"], "physical continuation changed")
    require(not args.out.exists(), "fresh output only; no resume/retry")
    args.out.mkdir(parents=False)
    runner.new_json(args.out / "attempt.json", dict(schema="s04_e036_constraint_release_attempt_v1",
        method=METHOD, phase="constraint_release", requested_case=CASE, command=sys.argv,
        pid=os.getpid(), started_unix=time.time(), authority=ref(args.authority),
        config=ref(args.config), source_binding=ref(args.source_binding), source=context["source"],
        original_source_clock=context["source_clock"], current_supervisor=context["current_supervisor"],
        job_wall_seconds=CONFIG["job_wall_seconds"], cumulative_resource_limit=None,
        future_target_used=False, teacher_initialized=False, history_commit_count=0))
    torch.manual_seed(1)
    torch.use_deterministic_algorithms(True)
    doc, _, problem = runner.load_problem(args.manifest, torch.device(args.device), requested_case=CASE)
    aroot, authority = args.authority.resolve().parent, context["authority"]
    reuse = validate_stage_a_reuse(bound(authority["fem_validation"], aroot),
        bound(authority["stage_a_semantic_binding"], aroot), ROOT, problem)
    engine, verified = restore_source(context, doc, problem, runner, torch)
    baseline_work = engine.work.copy()
    initial = verified["fresh"]
    energy, force = _energy(engine, initial["fields"], engine.coefficient, damage_force=True)
    lower, raw = engine.old["damage"], initial["raw_damage"]
    free = lower < 1
    free[problem.common["fixed_damage_nodes_zero_based"]] = False
    blocked = free & (((raw < lower) & (force < 0)) | ((raw > 1) & (force > 0)))
    eligibility = dict(source_failed=True, saved_f_blocked_nodes=int(blocked.sum()),
        saved_f_blocked_force_l2=float(torch.linalg.vector_norm(force[blocked])),
        saved_f_energy=energy, source_fresh_C=initial["C"],
        source_coefficient_fixed_point=initial["coefficient_fixed_point"],
        stage_a_reuse=reuse, source_work=baseline_work, future_target_used=False,
        adapter_verification_work=dict(source_saved_network_replays=1, saved_f_nodal_admission_reads=1))
    runner.new_json(args.out / "eligibility.json", eligibility)
    if not bool(blocked.any()):
        runner.new_json(args.out / "finished.json", dict(status="program_completed", method=METHOD,
            outcome="ineligible_no_saved_f_blocked_direction", release_attempted=False,
            physical_continuation_attempted=False, history_commit_count=0, retry_permitted=False,
            physical_accepted=False, C=initial["C"], future_target_used=False,
            retained_state="verified_source_terminal", ended_unix=time.time()))
        return

    def emit(event, payload):
        if event == "node_proposal":
            path = runner.atomic_file(args.out, "node_proposal.pt", lambda stream: torch.save(payload, stream))
            runner.exact_payload(payload, torch.load(path, map_location="cpu", weights_only=True))
            payload = dict(saved_arrays=ref(path), readback_verified=True)
        runner.append_event(args.out / "release_events.jsonl", dict(event=event, payload=payload))

    def publish(current, fresh, extra):
        return runner.publish_snapshot(args.out / "release_candidate", current, fresh,
            "constraint_release_candidate", endpoint=True, extra=extra)

    release = attempt_release(engine, emit=emit, publish=publish)
    continuation = None
    retained = "verified_source_terminal"
    if release["status"] == "release_accepted":
        retained = "verified_release_candidate"
        if not release["physical_accepted"]:
            accepted_weights = runner.cpu(engine.field.net.state_dict())
            accepted_f = engine.coefficient.detach().clone()
            keep_continuation = False
            try:
                # New persistent optimizer inside this call: proxy curvature is discarded.
                continuation = runner.lbfgs_phase(engine, args.out / "physical_continuation", target=None)
                keep_continuation = continuation["physical_accepted"] is True
                if keep_continuation:
                    retained = "qualified_release_plus_physical_continuation"
            finally:
                if not keep_continuation:
                    engine.field.net.load_state_dict(accepted_weights, strict=True)
                    engine.coefficient = accepted_f
                    runner.exact_payload(runner.cpu(engine.field.net.state_dict()), accepted_weights)
                    engine.verify_old()
                    for parameter in engine.field.net.parameters():
                        parameter.grad = None
    else:
        runner.exact_payload(runner.cpu(engine.field.net.state_dict()), verified["payload"]["network_state"])
        runner.exact_payload(runner.cpu(engine.coefficient), verified["payload"]["result"]["f_solve"])
    final = engine.readout()
    completion = runner.publish_snapshot(args.out / "retained_final", engine, final,
        "constraint_release_retained_final", endpoint=True,
        extra=dict(method=METHOD, release=release, physical_continuation=continuation,
                   retained_state=retained, source_work=baseline_work,
                   proxy_work=release["proxy_work"], future_target_used=False, teacher_initialized=False))
    runner.new_json(args.out / "finished.json", dict(status="program_completed", method=METHOD,
        phase="constraint_release", requested_case=CASE, release=release, physical_continuation=continuation,
        retained_state=retained, physical_accepted=final["physical_accepted"], C=final["C"],
        retained_completion=completion, source_work=baseline_work, actual_physical_work=engine.work,
        adapter_verification_work=eligibility["adapter_verification_work"],
        proxy_work=release["proxy_work"], history_commit_count=0, future_target_used=False,
        teacher_initialized=False, retry_permitted=False, ended_unix=time.time()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-binding", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--supervisor-authority", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda:0",), required=True)
    arguments = parser.parse_args()
    try:
        main(arguments)
    except BaseException as error:
        if (arguments.out / "attempt.json").is_file() and not (arguments.out / "job_failure.json").exists():
            import run_mechanism_matrix as runner
            runner.new_json(arguments.out / "job_failure.json", dict(error_type=type(error).__name__,
                message=str(error), method=METHOD, history_commit_count=0,
                retry_permitted=False, ended_unix=time.time()))
        raise
