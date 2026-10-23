#!/usr/bin/env python3
"""Post-hoc D4 scoring and static figures; targets never enter physics runners.

The CLI is producer/CUDA-only, including saved-network replay. Importable pure
reducers/plotters support tiny artificial tests. See MECHANISM_SCORING.md.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))
import run_mechanism_matrix as runner
from native_q4_diagnostics import native_readout, physical_gap
from score_paired_windows import load_target, target_readout
from window_inputs import bound_file, read_json, sha256

CASES, ARMS, ROOT = runner.CASES, runner.ARMS, runner.ROOT
SNAPSHOT_KEYS = {"completion", "bundle", "fields", "network"}
RECORD_KEYS = {"status", "attempt", "implementation_lock", "phase_inputs", "endpoint", "snapshots", "failure"}
SOURCE_FILES = runner.EXTRA_LOCK_FILES | {
    "source/trial_fatigue_coupling.py", "source/cyclic_acceptance.py", "source/compute_energy.py",
    "source/fatigue_history.py", "source/q4_quadrature.py", "source/network.py", "source/fit.py",
    "source/optim.py", "source/material_properties.py", "source/pff_model.py",
    "SENS_tensile/field_computation.py", "SENS_tensile/run_native_q4_one_step_matrix.py",
    "tools/s04_e036/run_paired_windows.py", "tools/s04_e036/window_inputs.py",
    "tools/s04_e036/stage_a_reuse.py"}
WORK_KEYS = ("rprop_updates", "lbfgs_steps", "lbfgs_closures", "coefficient_refreshes", "history_commits")


def validate_inventory(doc):
    if (set(doc) != {"schema", "physics_manifest", "target_manifest", "cases", "job_wall_seconds"}
            or doc["schema"] != "s04_e036_mechanism_score_inputs_v1" or set(doc["cases"]) != set(CASES)):
        raise ValueError("score inventory must retain exactly all four predeclared states")
    wall = doc["job_wall_seconds"]
    if type(wall) not in (int, float) or not math.isfinite(wall) or wall <= 0:
        raise ValueError("finite per-job scoring anti-hang setting required")
    for case in doc["cases"].values():
        if set(case) != {"matrix", "target_fit", "C0_continuation"} or set(case["matrix"]) != set(ARMS):
            raise ValueError("all predeclared arms and supplementary phases must remain visible")
        for record in [*case["matrix"].values(), case["target_fit"], case["C0_continuation"]]:
            if record is None:
                continue
            if (set(record) != RECORD_KEYS or record["status"] not in ("complete", "failed", "running")
                    or not isinstance(record["snapshots"], list)):
                raise ValueError("invalid phase record")
            if record["status"] == "complete" and (record["endpoint"] is None or record["failure"] is not None):
                raise ValueError("complete phase needs an endpoint and no failure")
            if record["status"] == "failed" and record["failure"] is None:
                raise ValueError("failed phase must preserve its failure receipt")


def verify_attempt(record, root, case, phase, physics_sha, target_sha, matrix_prefix):
    attempt_path = bound_file(record["attempt"], root)
    lock_path = bound_file(record["implementation_lock"], root)
    attempt, lock = read_json(attempt_path), read_json(lock_path)
    authority = attempt["provenance"]["authority"]
    if (attempt.get("schema") != "s04_e036_mechanism_attempt_v1" or attempt.get("phase") != phase
            or attempt.get("manifest_sha256") != physics_sha
            or attempt.get("requested_case") not in (None, case)
            or attempt.get("declared_cases") != list(CASES)
            or attempt.get("execution_cases") != list(runner.execution_cases(attempt.get("requested_case")))
            or attempt.get("history_commit_count") != 0 or authority.get("approved") is not True
            or authority.get("manifest_sha256") != physics_sha or authority.get("mechanism_phase") != phase
            or authority.get("requested_case", "missing") != attempt.get("requested_case")
            or authority["implementation_lock"]["sha256"] != sha256(lock_path)
            or lock.get("schema") != "s04_e036_implementation_lock_v1"
            or not SOURCE_FILES <= set(lock["files"])):
        raise ValueError("attempt/source identity does not bind this declared phase")
    for relative in SOURCE_FILES:
        if sha256(ROOT / relative) != lock["files"][relative]:
            raise ValueError("scientific replay source drift: " + relative)
    if phase == "matrix":
        if record["phase_inputs"] is not None:
            raise ValueError("physics matrix cannot have a target/continuation input")
    else:
        phase_path = bound_file(record["phase_inputs"], root)
        label = "target_manifest" if phase == "target_fit" else "source_endpoints"
        if authority[label]["sha256"] != sha256(phase_path):
            raise ValueError("phase input differs from actual producer authority")
        if phase == "target_fit":
            if sha256(phase_path) != target_sha:
                raise ValueError("witness fitted another target manifest")
        else:
            source = read_json(phase_path)
            if (source.get("schema") != "s04_e036_C0_continuation_v1" or set(source["cases"]) != set(CASES)
                    or source["physics_manifest"]["sha256"] != physics_sha or matrix_prefix is None):
                raise ValueError("continuation has no matching declared C0 prefix")
            for name in ("completion", "bundle"):
                if source["cases"][case][name]["sha256"] != matrix_prefix[name]["sha256"]:
                    raise ValueError("continuation source is not the scored C0 prefix")
    return attempt_path, attempt, lock


def verify_snapshot(spec, root, problem, old, key, arm, phase, provenance, deadline):
    """Bind all separate files, rebuild actual network, compare immutable state."""
    if set(spec) != SNAPSHOT_KEYS:
        raise ValueError("snapshot needs four independently bound saved artifacts")
    paths = {name: bound_file(value, root) for name, value in spec.items()}
    if len({path.parent for path in paths.values()}) != 1:
        raise ValueError("snapshot artifacts must share their published directory")
    receipt = read_json(paths["completion"])
    if (receipt.get("schema") != "s04_e036_mechanism_completion_v1"
            or receipt.get("readback_verified") is not True or receipt.get("fields_reproduced_exactly") is not True
            or receipt.get("history_commit_count") != 0):
        raise ValueError("snapshot lacks exact saved-network readback")
    for name in ("bundle", "fields", "network"):
        if receipt[name + "_sha256"] != sha256(paths[name]):
            raise ValueError("completion does not bind " + name)
    payload = torch.load(paths["bundle"], map_location="cpu", weights_only=True)
    network = torch.load(paths["network"], map_location="cpu", weights_only=True)
    if payload.get("schema") != "s04_e036_mechanism_snapshot_v1":
        raise ValueError("wrong snapshot schema")
    meta = payload["metadata"]
    runner.exact_metadata(meta, receipt["metadata"], "receipt/bundle metadata")
    runner.exact_metadata(meta["state_key"], key, "snapshot physical state")
    mapping, weight = ARMS[arm] if arm in ARMS else ("legacy", 0.)
    if (meta["arm"] != arm or meta["mapping"] != mapping or meta["weight_l2"] != weight
            or meta["changed_function_family"] != (mapping == "nodal_clamp")
            or meta["teacher_initialized"] != (phase == "target_fit")
            or meta["physical_operator_dtype"] != "float64" or meta["physical_field_dtype"] != "float64"
            or meta["old_state_dtype"] != "float64" or meta["network_dtype"] != meta["dtype"]
            or meta["network_state_sha256"] != sha256(paths["network"])
            or meta["predecessor_checkpoint_sha256"] != provenance["predecessor_checkpoint_sha256"]
            or meta["history_commit_count"] != 0
            or meta["complete_endpoint"] != receipt["endpoint_complete"]):
        raise ValueError("snapshot mapping/dtype/commit semantics differ")
    for name, value in provenance.items():
        runner.exact_metadata(payload["provenance"].get(name), value, "snapshot provenance " + name)
    runner.exact_metadata(payload["provenance"]["execution_phase"], phase, "execution phase")
    if phase != "target_fit" and (payload["provenance"].get("seen_target") or "target_admission" in payload["provenance"]):
        raise ValueError("physics endpoint contains seen-target provenance")
    if phase == "target_fit" and payload["provenance"].get("seen_target") is not True:
        raise ValueError("witness must explicitly identify target use")
    runner.exact_metadata(payload["common_problem"], problem.common, "common problem")
    runner.exact_payload(payload["native_old_state"], runner.cpu(old))
    runner.exact_payload(payload["old_state"], payload["native_old_state"])
    runner.exact_payload(payload["network_state"], network)
    work = receipt["actual_work"]
    if type(work.get("snapshot_replays")) is not int or work["snapshot_replays"] < 1:
        raise ValueError("missing successful saved-network replay count")
    for name in WORK_KEYS:
        if type(work[name]) is not int or work[name] < 0 or work[name] != payload["work"][name]:
            raise ValueError("actual saved work differs")
    if (work["history_commits"] != 0 or work["rprop_updates"] != meta["rprop_updates"]
            or work["lbfgs_steps"] != meta["lbfgs_steps"]):
        raise ValueError("metadata work/history count differs")
    result = payload["result"]
    with np.load(paths["fields"], allow_pickle=False) as saved:
        runner.exact_metadata(json.loads(str(saved["metadata_json"].item())), meta, "NPZ metadata")
        arrays = {**{name: result["fields"][name] for name in ("u", "v", "d")}, "raw_damage": result["raw_damage"],
                  **{"old_" + name: value for name, value in payload["native_old_state"].items()}}
        for name, expected in arrays.items():
            actual = np.asarray(saved[name])
            if actual.dtype != expected.numpy().dtype or not np.array_equal(actual, expected.numpy()):
                raise ValueError("NPZ differs from bundle: " + name)
    dtype = {"float32": torch.float32, "float64": torch.float64}[meta["dtype"]]
    engine = runner.EndpointEngine(problem, old, network, key, arm, dtype, deadline, payload["provenance"])
    engine.coefficient = result["f_solve"].to(problem.device)
    fresh = engine.readout()
    for name in ("fields", "raw_damage", "history", "f_solve", "f_commit"):
        runner.exact_payload(result[name], runner.cpu(fresh[name]))
    if (fresh["physical_accepted"] != receipt["physical_accepted"]
            or fresh["physical_accepted"] != result["physical_accepted"]
            or fresh["coefficient_fixed_point"] != result["coefficient_fixed_point"]
            or fresh["C"] != result["C"]):
        raise ValueError("fresh physical replay changed saved endpoint interpretation")
    return dict(payload=payload, receipt=receipt, fresh=fresh, paths=paths)


def endpoint_role(meta, work, phase):
    if not meta["complete_endpoint"]:
        raise ValueError("a diagnostic snapshot cannot replace a phase endpoint")
    if phase == "matrix":
        if (meta["stage"] != "first_2000" or meta["dtype"] != "float32"
                or work["rprop_updates"] != 2000 or work["lbfgs_steps"] != 0 or work["lbfgs_closures"] != 0):
            raise ValueError("2x2 requires the exact float32 first-2000 prefix")
    elif phase == "target_fit":
        if meta["stage"] != "lbfgs_final" or meta["dtype"] != "float64" or work["rprop_updates"] != 0:
            raise ValueError("witness endpoint differs from original-family full64 fit")
    elif meta["stage"] not in ("candidate_rprop_accepted", "lbfgs_final"):
        raise ValueError("continuation endpoint is not a terminal reported state")


def scalar_score(problem, verified, target, reference, mass):
    fresh = verified["fresh"]
    _, approximation = runner.fit_objective(fresh["fields"], target, mass, problem.native_weights,
                                            problem.native_dshape, problem.cells)
    physical = native_readout(problem, fresh["fields"], verified["payload"]["native_old_state"],
                              fresh["f_solve"], fresh["history"], fresh["f_commit"])
    gap = physical_gap(problem, physical, reference)
    if not gap["same_old_state_exact"]:
        raise ValueError("D4 comparison lost exact native F1 predecessor")
    meta = verified["payload"]["metadata"]
    return dict(metadata=meta, work=verified["receipt"]["actual_work"], approximation=approximation,
                C=fresh["C"], physical_accepted=fresh["physical_accepted"], residual=fresh["residual"],
                target_used_in_optimization=meta["teacher_initialized"], physical_gap=gap,
                optimization_diagnostics={name: verified["payload"].get("diagnostics", {}).get(name, {}).get("summary")
                                          for name in ("parameter", "nodal")},
                saved_endpoint_extra=verified["payload"].get("extra"),
                provenance=verified["payload"]["provenance"], source_files={name: dict(path=str(path), sha256=sha256(path))
                    for name, path in verified["paths"].items()}), physical


def factorial_effects(arms):
    """Signed descriptive contrasts; negative reduces an error, not a causal proof."""
    if set(arms) != set(ARMS) or any(value is None for value in arms.values()):
        return dict(status="unavailable", reason="all four completed first-2000 arms required")
    get = {"Q": lambda v: v["approximation"]["Q"], "J": lambda v: v["approximation"]["J"],
           "C": lambda v: v["C"], "active_normalized_rms": lambda v: v["physical_gap"]["native_gp_errors"]["active"]["normalized_rms"],
           "reaction_top_fresh_normalized_rms": lambda v: v["physical_gap"]["reaction_errors"]["fresh_f_commit"]["top_xy"]["normalized_component_rms"]}
    effects = {}
    for name, take in get.items():
        lp, l0, cp, c0 = (float(take(arms[arm])) for arm in ("Lplus", "L0", "Cplus", "C0"))
        effects[name] = dict(clamp_main_effect=.5 * ((cp - lp) + (c0 - l0)),
                             remove_l2_main_effect=.5 * ((l0 - lp) + (c0 - cp)),
                             interaction=(c0 - cp) - (l0 - lp))
    return dict(status="descriptive_equal_work_contrast", effects=effects,
                all_physical_accepted=all(v["physical_accepted"] for v in arms.values()),
                interpretation="negative reduces the named error; clamp changes the function family; interaction is the difference of L2-removal effects; finite rejected states remain diagnostics, not accepted solutions")


def aggregate_effects(states):
    if set(states) != set(CASES) or any(v["factorial"]["status"] != "descriptive_equal_work_contrast" for v in states.values()):
        return dict(status="unavailable", reason="missing/failed predeclared state or arm; no overall aggregate")
    first = next(iter(states.values()))["factorial"]["effects"]
    means = {metric: {effect: float(np.mean([v["factorial"]["effects"][metric][effect] for v in states.values()]))
                      for effect in values} for metric, values in first.items()}
    return dict(status="four_state_descriptive_mean", effects=means,
                interpretation="four fixed states, no sampling uncertainty or cross-trajectory generalization")


def score_record(record, root, name, phase, arm, problem, old, key, provenance, deadline,
                 target, reference, mass, physics_sha, target_sha, matrix_prefix=None):
    if record is None:
        return dict(status="unavailable", endpoint=None, curve=[]), None
    attempt_path, attempt, lock = verify_attempt(record, root, name, phase, physics_sha, target_sha, matrix_prefix)
    arm_root = attempt_path.parent / name / (arm if phase != "target_fit" else "legacy_witness")
    if record["failure"] is not None:
        failure_path = bound_file(record["failure"], root)
        if not failure_path.is_relative_to(attempt_path.parent):
            raise ValueError("failure receipt lies outside its attempt")
        failure = read_json(failure_path)
    else:
        failure = None
    specs = record["snapshots"]
    paths = [bound_file(s["completion"], root) for s in specs]
    discovered = set(arm_root.rglob("completion.json"))
    if len(set(paths)) != len(paths) or set(paths) != discovered:
        raise ValueError("inventory must enumerate every published snapshot exactly once")
    if record["endpoint"] is not None and record["endpoint"] not in specs:
        raise ValueError("phase endpoint must be one of the fully enumerated snapshots")
    result, endpoint, endpoint_fields = [], None, None
    for spec in specs:
        deadline.check()
        verified = verify_snapshot(spec, root, problem, old, key, arm, phase, provenance, deadline)
        score, native = scalar_score(problem, verified, target, reference, mass)
        if phase == "target_fit":
            adm = verified["payload"]["provenance"]["target_admission"]
            if adm["snapshot_sha256"] != target["score_snapshot_sha256"]:
                raise ValueError("witness target differs from the scored F1 snapshot")
        result.append({k: score[k] for k in ("metadata", "work", "approximation", "C", "physical_accepted", "source_files")})
        if spec == record["endpoint"]:
            if record["status"] == "complete":
                endpoint_role(score["metadata"], score["work"], phase)
            endpoint = score
            endpoint_fields = dict(d=runner.cpu(verified["fresh"]["fields"]["d"]).numpy(),
                                   active=runner.cpu(native["gp"]["active"]).numpy())
    if phase == "target_fit" and endpoint is not None:
        endpoint["representation_interpretation"] = dict(observed_original_map_approximation_upper_bound=endpoint["approximation"],
            program_stop_reached=runner.fit_program_stop(endpoint["approximation"]), capacity_sufficient_proven=False,
            interpretation="achieved seen-target error bounds the best error in this original mapped network family from above; failed fitting gives no capacity lower bound; physical admissibility is reported separately")
    return dict(status=record["status"], endpoint=endpoint, curve=result, failure=failure,
                attempt=dict(path=str(attempt_path), sha256=sha256(attempt_path), source=attempt["provenance"]["source"],
                             implementation_lock_sha256=record["implementation_lock"]["sha256"]),
                diagnostic_only=record["status"] != "complete"), endpoint_fields


def _save_figure(fig, directory, stem, text):
    for extension in ("png", "pdf"):
        fig.savefig(directory / (stem + "." + extension), dpi=300, bbox_inches="tight")
    (directory / (stem + ".md")).write_text(text)


def plot_results(directory, report, nodes, cells, shape, fields):
    """All supplied points rendered; native GP active is never element-averaged."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri
    from matplotlib.colors import Normalize
    provenance = "Metrics: scores.json (SHA256 " + sha256(directory / "scores.json") + "). Full artifact/source hashes are embedded per endpoint."
    question = "Compare the four fixed states against admitted F1 at the exact same native predecessor."
    limitations = "Finite rejected/failed fields are diagnostics; no capacity sufficiency, unique-solution, full-cycle or physical-validation claim. Missing panels remain visible. One trajectory and fixed starting networks."
    tri = mtri.Triangulation(nodes[:, 0], nodes[:, 1], np.concatenate((cells[:, [0, 1, 2]], cells[:, [0, 2, 3]])))
    gp = np.einsum("gn,eni->egi", shape, nodes[cells]).reshape(-1, 2)
    titles = ("F1", "Lplus (2000)", "C0 (2000)", "Lplus − F1", "C0 − F1")
    for quantity in ("d", "active"):
        values, errors = [], []
        for case in fields.values():
            for role in ("F1", "Lplus", "C0"):
                if case.get(role) is not None:
                    values.append(case[role][quantity])
            for role in ("Lplus", "C0"):
                if case.get(role) is not None and case.get("F1") is not None:
                    errors.append(case[role][quantity] - case["F1"][quantity])
        lo = min([0.] + [float(v.min()) for v in values])
        hi = max([1. if quantity == "d" else 0.] + [float(v.max()) for v in values])
        hi = hi if hi > lo else lo + 1.
        extent = max([1e-15] + [float(abs(v).max()) for v in errors])
        normal, signed = Normalize(lo, hi), Normalize(-extent, extent)
        fig, axes = plt.subplots(4, 5, figsize=(13, 10), constrained_layout=True)
        for row, name in enumerate(CASES):
            case = fields.get(name, {})
            for col, title in enumerate(titles):
                ax = axes[row, col]
                role = ("F1", "Lplus", "C0", "Lplus", "C0")[col]
                value = None if case.get(role) is None else case[role][quantity]
                if col >= 3:
                    value = None if value is None or case.get("F1") is None else value - case["F1"][quantity]
                if value is None:
                    ax.text(.5, .5, "unavailable", ha="center", va="center", transform=ax.transAxes)
                elif quantity == "d":
                    ax.tripcolor(tri, value, shading="gouraud", cmap="RdBu_r" if col >= 3 else "viridis",
                                 norm=signed if col >= 3 else normal, rasterized=True)
                else:
                    ax.scatter(gp[:, 0], gp[:, 1], c=value.reshape(-1), s=.15, marker="s", linewidths=0,
                               cmap="RdBu_r" if col >= 3 else "magma", norm=signed if col >= 3 else normal, rasterized=True)
                status = ""
                if role != "F1":
                    record = report["states"][name]["matrix"][role]
                    endpoint = record.get("endpoint")
                    if endpoint is not None and (record["status"] != "complete" or not endpoint["physical_accepted"]):
                        status = " · diagnostic"
                ax.set_title(title + status, fontsize=8)
                ax.set_aspect("equal")
                ax.set_xlim(nodes[:, 0].min(), nodes[:, 0].max()); ax.set_ylim(nodes[:, 1].min(), nodes[:, 1].max())
                if col == 0:
                    ax.set_ylabel(name + "\ny / L")
                if row == 3:
                    ax.set_xlabel("x / L")
        fig.colorbar(plt.cm.ScalarMappable(norm=normal, cmap="viridis" if quantity == "d" else "magma"),
                     ax=axes[:, :3], shrink=.7, label=quantity + " (nondimensional)")
        fig.colorbar(plt.cm.ScalarMappable(norm=signed, cmap="RdBu_r"), ax=axes[:, 3:], shrink=.7,
                     label="PIDL − F1 (signed)")
        takeaway = {name: {arm: (record["endpoint"]["approximation"]["J"] if record.get("endpoint") else None)
                          for arm, record in state["matrix"].items()} for name, state in report["states"].items()}
        text = f"# {quantity} comparison\n\n## Figure question\n{question}\n\n## Data provenance\n{provenance}\n\n## Visual grammar\nShared field limits [{lo:.8g}, {hi:.8g}] across all states/methods; signed error limits ±{extent:.8g}. Full domain, no clipping or smoothing. Damage uses visual triangle interpolation of Q4 nodal values; active uses all four native GP samples at their actual coordinates, without element reduction.\n\n## Panel guide\nRows: {', '.join(CASES)}. Columns: {', '.join(titles)}. Both PIDL arms are the equal 2000-RPROP prefix.\n\n## Key numerical takeaway\nNodal J by state/arm: `{json.dumps(takeaway)}`. Interpretation requires scores.json physical acceptance and GP metrics.\n\n## Limitations and claim boundary\n{limitations}\n\n## Related assets\n`score_mechanism_matrix.py`, `scores.json`; PNG and PDF share this sidecar.\n"
        _save_figure(fig, directory, "mechanism_" + quantity, text); plt.close(fig)
    colors = dict(Lplus="#0072B2", L0="#56B4E9", Cplus="#D55E00", C0="#009E73", witness="#CC79A7")
    for metric in ("C", "J"):
        fig, axes = plt.subplots(4, 3, figsize=(13, 11), constrained_layout=True)
        for row, name in enumerate(CASES):
            state = report["states"][name]
            series = [(arm, state["matrix"][arm], 0, "rprop_updates") for arm in ARMS]
            series += [("C0", state["C0_continuation"], 1, "rprop_updates"),
                       ("C0", state["C0_continuation"], 2, "lbfgs_closures"),
                       ("witness", state["target_fit"], 2, "lbfgs_closures")]
            for label, record, col, work in series:
                curve = [v for v in record["curve"] if (col != 1 or v["metadata"]["dtype"] == "float32")
                         and (col != 2 or v["metadata"]["dtype"] == "float64")]
                curve.sort(key=lambda v: (v["work"][work], v["work"]["snapshot_replays"]))
                if curve:
                    axes[row, col].plot([v["work"][work] for v in curve],
                        [v["C"] if metric == "C" else v["approximation"]["J"] for v in curve],
                        marker="o", markersize=2, linewidth=1.3, color=colors[label], label=label,
                        linestyle=":" if record["status"] != "complete" else "-")
            for col, title in enumerate(("2×2 · RPROP updates", "C0 continuation · total RPROP updates", "float64 · LBFGS closure calls")):
                ax = axes[row, col]; ax.set_title(name + " · " + title, fontsize=8)
                values = [float(y) for line in ax.lines for y in line.get_ydata()]
                # A narrow interval containing no power of ten otherwise has
                # no labelled ticks under Matplotlib's default symlog locator.
                broad = values and max(values) > 0 and (min(values) == 0 or max(values) / min(values) >= 10)
                if broad:
                    ax.set_yscale("symlog", linthresh=1e-10)
                ax.grid(alpha=.18)
                ax.set_ylabel(metric); ax.set_xlabel("completed updates" if col < 2 else "actual closure evaluations")
                if ax.lines:
                    ax.legend(fontsize=7)
                else:
                    ax.text(.5, .5, "unavailable", ha="center", transform=ax.transAxes)
        text = f"# {metric} versus actual work\n\n## Figure question\nHow do saved diagnostic {metric} values change with completed optimizer work?\n\n## Data provenance\n{provenance}\n\n## Visual grammar\nRows are the four fixed states; columns separately show first-2000 RPROP, subsequent C0 RPROP (cumulative), and float64 LBFGS closure evaluations. No conversion between these work units. Points are all published saved snapshots; lines only join observations, including ties at equal work and distinct coefficient timing. Dotted lines denote failed/running phase diagnostics. The y axis is linear for positive ranges narrower than one decade, otherwise symmetric-log with a 1e-10 linear region to retain zero.\n\n## Panel guide\nRPROP matrix has Lplus/L0/Cplus/C0; continuation has C0; LBFGS has C0 and original-map target-fit witness. Witness uses F1 targets and fresh-f zero-update physical diagnostics; it is not physics-only optimization.\n\n## Key numerical takeaway\nSee the exact per-point C/J/work/dtype in scores.json. C is the fresh normalized residual score; C alone does not establish full physical acceptance.\n\n## Limitations and claim boundary\n{limitations} Changes of precision and optimizer remain joint interventions, and LBFGS closure counts include rejected line-search trials.\n\n## Related assets\n`score_mechanism_matrix.py`, `scores.json`; PNG and PDF share this sidecar.\n"
        _save_figure(fig, directory, "mechanism_" + metric + "_work", text); plt.close(fig)


def main(args):
    device = torch.device(args.device)
    authority, source = runner.check_authority(args.authority, args.inventory, device)
    doc = read_json(args.inventory); validate_inventory(doc)
    requested_case = getattr(args, "case", None)
    selected_cases = runner.execution_cases(requested_case)
    if authority.get("requested_case") != requested_case:
        raise ValueError("score authority requested_case differs from --case")
    if (authority.get("mechanism_phase") != "score" or authority.get("job_wall_seconds") != doc["job_wall_seconds"]
            or authority.get("cumulative_resource_limit", "missing") is not None):
        raise ValueError("explicit score phase and finite per-job authority required")
    root = args.inventory.resolve().parent
    score_lock = read_json(bound_file(authority["implementation_lock"], args.authority.resolve().parent))
    if not (SOURCE_FILES | {"tools/s04_e036/score_mechanism_matrix.py"}) <= set(score_lock["files"]):
        raise ValueError("scoring implementation dependencies absent from lock")
    deadline = runner.Deadline(doc["job_wall_seconds"], "mechanism score")
    torch.manual_seed(1)
    torch.use_deterministic_algorithms(True)
    physics_path = bound_file(doc["physics_manifest"], root)
    target_path = bound_file(doc["target_manifest"], root)
    physics, physics_root, problem = runner.load_problem(physics_path, device, requested_case=requested_case)
    targets = read_json(target_path)
    if (set(targets) != {"schema", "physics_manifest", "targets"} or targets["schema"] != "s04_e036_mechanism_targets_v1"
            or set(targets["targets"]) != set(CASES)
            or bound_file(targets["physics_manifest"], target_path.parent) != physics_path):
        raise ValueError("same separately bound four-state F1 target manifest required")
    reuse = runner.validate_stage_a_reuse(bound_file(authority["fem_validation"], args.authority.resolve().parent),
        bound_file(authority["stage_a_semantic_binding"], args.authority.resolve().parent), ROOT, problem)
    if args.out.exists():
        raise FileExistsError("fresh score output required")
    args.out.mkdir(parents=True)
    mass = torch.zeros(len(problem.x), dtype=torch.float64, device=device)
    mass.index_add_(0, problem.cells.reshape(-1), torch.einsum("eg,gn->en", problem.native_weights, problem.native_shape).reshape(-1))
    report = dict(schema="s04_e036_mechanism_scores_v1", inventory_sha256=sha256(args.inventory),
                  physics_manifest_sha256=sha256(physics_path), target_manifest_sha256=sha256(target_path),
                  source=source, stage_a_reuse=reuse, score_implementation_lock=authority["implementation_lock"],
                  requested_case=requested_case, execution_cases=list(selected_cases), states={})
    fields = {}
    for name in CASES:
        deadline.check()
        spec, case = physics["cases"][name], doc["cases"][name]
        if name not in selected_cases or targets["targets"][name] is None:
            missing_reason = "case deferred by explicit partition" if name not in selected_cases else "predeclared F1 target unavailable"
            absent = lambda: dict(status="unscored_case_deferred" if name not in selected_cases else "unscored_target_unavailable", endpoint=None, curve=[])
            state = dict(target=None, matrix={arm: absent() for arm in ARMS}, target_fit=absent(),
                         C0_continuation=absent(), supplied_inputs=case,
                         factorial=dict(status="unavailable", reason=missing_reason))
            report["states"][name], fields[name] = state, {}
            runner.new_json(args.out / (name + "_scores.json"), state)
            continue
        old, _, admission = runner.load_predecessor(spec, physics_root, problem)
        provenance = dict(case=name, manifest_sha256=sha256(physics_path), theta0_sha256=runner.NETWORK_SHA[name],
                          predecessor_checkpoint_sha256=admission["source_checkpoint"]["sha256"])
        target, target_receipt = load_target(targets["targets"][name], target_path.parent, spec["state_key"], problem,
            expected_predecessor_sha256=provenance["predecessor_checkpoint_sha256"], expected_old=old)
        if target_receipt["native_solver_policy"] != {"u_tol": 1e-6, "joint_tol": 4e-4}:
            raise ValueError("score comparator must be standard F1")
        target["score_snapshot_sha256"] = target_receipt["snapshot_sha256"]
        reference = target_readout(problem, target)
        state = dict(target=target_receipt, matrix={})
        fields[name] = dict(F1={"d": runner.cpu(target["d"]).numpy(), "active": runner.cpu(reference["gp"]["active"]).numpy()})
        for label, phase, arm, record in [(a, "matrix", a, case["matrix"][a]) for a in ARMS] + [
                ("target_fit", "target_fit", "legacy_witness", case["target_fit"]),
                ("C0_continuation", "candidate_continuation", "C0", case["C0_continuation"])]:
            prefix = None if case["matrix"]["C0"] is None else case["matrix"]["C0"]["endpoint"]
            scored, display = score_record(record, root, name, phase, arm, problem, old, spec["state_key"], provenance,
                deadline, target, reference, mass, sha256(physics_path), sha256(target_path), prefix)
            if phase == "matrix":
                state["matrix"][arm] = scored
                if arm in ("Lplus", "C0"):
                    fields[name][arm] = display
            else:
                state[label] = scored
        state["factorial"] = factorial_effects({a: v["endpoint"] if v["status"] == "complete" else None for a, v in state["matrix"].items()})
        report["states"][name] = state
        runner.new_json(args.out / (name + "_scores.json"), state)
    report["overall"] = aggregate_effects(report["states"])
    report["claim_boundary"] = "Fixed-state conditional approximation/physics diagnostics; fit-stop is not capacity sufficiency, fitting failure not capacity insufficiency; clamp changes the family; no full-cycle reproduction conclusion."
    runner.new_json(args.out / "scores.json", report)
    deadline.check()
    plot_results(args.out, report, problem.native_x.cpu().numpy(), problem.cells.cpu().numpy(),
                 problem.native_shape.cpu().numpy(), fields)
    deadline.check()
    runner.new_json(args.out / "completion.json", dict(schema="s04_e036_mechanism_score_completion_v1", scores_sha256=sha256(args.out / "scores.json"),
        outputs={p.name: sha256(p) for p in args.out.iterdir() if p.is_file()}, history_commits=0, optimizer_updates=0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("inventory", "authority", "out"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--case", choices=tuple(CASES), help="Score one declared case using its real production manifest; retain other cases as deferred.")
    main(parser.parse_args())
