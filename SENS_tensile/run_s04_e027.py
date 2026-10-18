#!/usr/bin/env python3
"""Prepare by default. Execution requires a future complete lock + HQ grant.

There is intentionally no fallback checkpoint, remote fetch, resume or retry.
No code in this module executes at import time.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
import numpy as np
import torch
import s04_e027 as method

LOCK = ROOT / "docs/research/S04/S04-E027/data_lock.json"


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def execution_admission(lock, grant):
    # All barriers precede scientific data/model reads and optimizer construction.
    if platform.system() == "Darwin":
        raise PermissionError("Mac training prohibited")
    if not lock["initializer"]["sha256"] or not lock["initializer"]["bytes"]:
        raise PermissionError("initializer identity unresolved; HQ must resolve/review lock")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if dirty or grant.get("approved_commit") != head or grant.get("protocol") != method.PROTOCOL:
        raise PermissionError("source/protocol approval mismatch")
    if grant.get("execution_authorized") is not True or not grant.get("review_reference") or not grant.get("human_approval_reference"):
        raise PermissionError("missing explicit HQ authorization/review references")
    if grant.get("initializer_sha256") != lock["initializer"]["sha256"]:
        raise PermissionError("initializer approval mismatch")
    if grant.get("gpu_hours_cap") != 2 or grant.get("ram_gib_cap") != 32 or grant.get("output_gib_cap") != 2:
        raise PermissionError("budget mismatch")
    if not os.environ.get("CUDA_VISIBLE_DEVICES") or "," in os.environ["CUDA_VISIBLE_DEVICES"]:
        raise PermissionError("explicit single CUDA_VISIBLE_DEVICES required")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise PermissionError("one CUDA producer required")
    return head


def render(problem, arrays, predictions, records, output):
    """Render only actual scored outputs; called only in an authorized Run."""
    os.environ["MPLCONFIGDIR"] = str(output/"mplcache")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    cpu = method.Problem(arrays)
    all_predictions = dict(reference=arrays["ref"], **predictions)
    display = {}
    with torch.no_grad():
        for arm, values in all_predictions.items():
            a = torch.as_tensor(values, dtype=torch.float64)
            parts = cpu.parts(*a.unbind(1))
            gp = [method.q4_interpolate(a[:, j], cpu.conn, cpu.N) for j in range(3)]+list(parts[3:5])
            display[arm] = np.stack([((x*cpu.w).sum(1)/cpu.w.sum(1)).numpy() for x in gp])
    fig, axes = plt.subplots(5, 7, figsize=(28, 20))
    polygons = arrays["xy"][arrays["conn"]]
    for j, name in enumerate(("u", "v", "d", "raw", "active")):
        lo = min(display[k][j].min() for k in display)
        hi = max(display[k][j].max() for k in display)
        errors = [display[k][j]-display["reference"][j] for k in ("P", "S", "C")]
        lim = max(float(abs(x).max()) for x in errors) or 1e-30
        for col, (label, val) in enumerate([(k, display[k][j]) for k in display]+list(zip(("P-ref", "S-ref", "C-ref"), errors))):
            ax = axes[j, col]
            artist = PolyCollection(polygons, array=val, edgecolors="none", cmap="viridis" if col < 4 else "RdBu_r")
            artist.set_clim((lo, hi) if col < 4 else (-lim, lim))
            ax.add_collection(artist); ax.autoscale(); ax.set_aspect("equal")
            ax.set_title(f"{name}: {label}"); ax.set_xlabel("x"); ax.set_ylabel("y")
            fig.colorbar(artist, ax=ax, shrink=.75)
    fig.suptitle("S04-E027 | exposed synthetic c20s4, horizon0 | native element weighted means")
    fig.tight_layout(); fig.savefig(output/"fields.png", dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for target, ax in zip((.25, .40), axes):
        x = arrays["xy"][:, 0]
        selected_x = x[np.argmin(abs(x-target))]
        idx = np.flatnonzero((abs(x-selected_x) < 1e-12) & (abs(arrays["xy"][:, 1]) <= .03))
        idx = idx[np.argsort(arrays["xy"][idx, 1])]
        for arm, pred in all_predictions.items():
            ax.plot(arrays["xy"][idx, 1], pred[idx, 2], label=arm)
        ax.set_title(f"damage profile, x={selected_x:.8g}"); ax.set_xlabel("y"); ax.set_ylabel("raw d"); ax.legend()
    fig.tight_layout(); fig.savefig(output/"profiles.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    for arm in ("P", "S", "C"):
        rows = [r for r in records if r["arm"] == arm]
        ax.plot([r["step"] for r in rows], [r["sampled_training_loss"] for r in rows], label=arm)
    ax.set_xlabel("optimizer update (C starts at 1001)"); ax.set_ylabel("own objective; different scales")
    ax.set_title("S04-E027: optimization trace, not physical evolution"); ax.legend()
    fig.tight_layout(); fig.savefig(output/"loss.png", dpi=150); plt.close(fig)


def optimize(problem, model, opt, rng, arm, first, last, normalizer, guard, records, progress, output):
    """Future producer-only loop. Never called in local preparation/tests."""
    for step in range(first, last+1):
        guard()
        opt.zero_grad(set_to_none=True)
        q = method.fields(model, problem.xy)
        if arm == "P":
            loss = method.physical_loss(problem, q, model)
        else:
            loss = problem.supervised(q, problem.sample(rng))
            if arm == "C":
                loss = loss+.1*method.mechanical_loss(problem, q, normalizer)
        method.finite(loss, "loss").backward()
        for p in model.parameters():
            if p.grad is None:
                raise ValueError("missing gradient")
            method.finite(p.grad, "gradient")
        progress["optimizer_attempt"] = "in_progress_or_unknown"
        progress["optimizer_step_calls"] += 1
        opt.step()
        for p in model.parameters():
            method.finite(p, "updated parameter")
        progress["optimizer_steps"] += 1
        progress["optimizer_attempt"] = "completed_finite"
        row = dict(arm=arm, step=step, sampled_training_loss=float(loss.detach()))
        records.append(row)
        with (output/"loss_trace.jsonl").open("a") as f:
            f.write(json.dumps(row, allow_nan=False)+"\n")
        if step == 1000:
            dump(output/f"{arm}_1000.json", problem.score(method.fields(model, problem.xy)))
        guard()


def run(root, lock, grant, output, initializer):
    head = execution_admission(lock, grant)
    if output.exists():
        raise FileExistsError("fresh output only")
    if grant.get("output") != str(output.resolve()) or grant.get("hostname") != platform.node():
        raise PermissionError("producer/output approval mismatch")
    if torch.cuda.mem_get_info()[0] < 24*1024**3:
        raise MemoryError("less than 24 GiB GPU free before preflight")
    start = time.monotonic()
    output.mkdir(parents=True)
    receipt = dict(protocol=method.PROTOCOL, commit=head, execution="preflight",
                   optimizer_steps=0, history_commits=0, host=platform.node(), pid=os.getpid(),
                   cuda_visible_devices=os.environ["CUDA_VISIBLE_DEVICES"], command=sys.argv,
                   gpu=torch.cuda.get_device_name(0), source_dirty=False)
    progress = dict(optimizer_steps=0, optimizer_step_calls=0, optimizer_attempt="not_started")
    def guard():
        torch.cuda.synchronize()
        if time.monotonic()-start > 7200:
            raise TimeoutError("2 hour joint cap")
        # Linux ru_maxrss is KiB; Darwin is rejected before reaching this path.
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > 32*1024**3:
            raise MemoryError("32 GiB process RSS cap")
        if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > 2*1024**3:
            raise OSError("2 GiB output cap")
    try:
        root = Path(grant["data_root"])  # explicitly approved producer staging, never a fallback
        check = method.prepare(root, lock)
        payload = dict(relative=initializer.name, bytes=lock["initializer"]["bytes"], sha256=lock["initializer"]["sha256"])
        method.verify_payload(initializer.parent, payload)
        state = torch.load(initializer, map_location="cpu", weights_only=True)
        arrays = method.load_reference(root, lock)
        problem = method.Problem(arrays, "cuda:0")
        torch.manual_seed(1)
        common = method.make_model(state, "cuda:0")
        q = method.fields(common, problem.xy)
        normalizer = float(torch.linalg.vector_norm(problem.force(q)[problem.free]).detach())
        if normalizer <= 1e-12 or not np.isfinite(normalizer):
            raise ValueError("mechanical normalization unavailable")
        # Benchmark three actual computation graphs without optimizer updates.
        benchmark = {}
        torch.cuda.reset_peak_memory_stats()
        for arm in ("P", "S", "C"):
            model = copy.deepcopy(common)
            rng = torch.Generator().manual_seed(1)
            # Account for Adam's two moments without updating real parameters.
            moments = [(torch.zeros_like(p), torch.zeros_like(p)) for p in model.parameters()]
            torch.cuda.synchronize(); t0 = time.monotonic()
            for _ in range(100):
                guard(); model.zero_grad(set_to_none=True)
                q = method.fields(model, problem.xy)
                loss = method.physical_loss(problem, q, model) if arm == "P" else problem.supervised(q, problem.sample(rng))
                if arm == "C": loss = loss+.1*method.mechanical_loss(problem, q, normalizer)
                method.finite(loss, "benchmark loss").backward()
            torch.cuda.synchronize()
            benchmark[arm] = (time.monotonic()-t0)/100
            del moments, model, q, loss
        # Explicit conservative optimizer/controller allowance, not measured cost.
        estimate = 1.25*(1500*benchmark["P"]+1500*benchmark["S"]+500*benchmark["C"])
        estimate += time.monotonic()-start+600  # predeclared final evaluation/save reserve
        if estimate > 7200:
            raise TimeoutError("preflight estimated joint budget exceeds cap")
        dump(output/"preflight.json", dict(reference=check, benchmark_seconds=benchmark,
             allowance_factor=1.25, evaluation_save_reserve_seconds=600,
             total_estimate_seconds=estimate, peak_cuda_bytes=torch.cuda.max_memory_allocated()))
        # Independent empty optimizers; both initial models contain identical state.
        pmodel, smodel = copy.deepcopy(common), copy.deepcopy(common)
        adam = lambda model: torch.optim.Adam(model.parameters(), lr=1e-4, betas=(.9, .999), eps=1e-8, weight_decay=0)
        popt, sopt = adam(pmodel), adam(smodel)
        prng, srng = torch.Generator().manual_seed(1), torch.Generator().manual_seed(1)
        initial = problem.score(method.fields(common, problem.xy))
        dump(output/"initial.json", initial)
        records = []
        optimize(problem, pmodel, popt, prng, "P", 1, 1500, normalizer, guard, records, progress, output)
        optimize(problem, smodel, sopt, srng, "S", 1, 1000, normalizer, guard, records, progress, output)
        cmodel, copt, crng = method.clone_branch(smodel, sopt, srng)
        torch.save(dict(model=smodel.state_dict(), optimizer=sopt.state_dict(), rng=srng.get_state()), output/"prefix1000.pt")
        dump(output/"prefix1000.json", problem.score(method.fields(smodel, problem.xy)))
        optimize(problem, smodel, sopt, srng, "S", 1001, 1500, normalizer, guard, records, progress, output)
        optimize(problem, cmodel, copt, crng, "C", 1001, 1500, normalizer, guard, records, progress, output)
        scores, predictions = {}, {}
        for arm, model in (("P", pmodel), ("S", smodel), ("C", cmodel)):
            guard()
            pred = method.fields(model, problem.xy)
            scores[arm] = problem.score(pred)
            predictions[arm] = pred.detach().cpu().numpy()
            torch.save(model.state_dict(), output/f"{arm}_1500.pt")
        np.savez_compressed(output/"predictions.npz", reference=arrays["ref"], **predictions)
        dump(output/"scores.json", dict(scores=scores, decision=method.decision(scores)))
        dump(output/"loss_trace.json", records)
        render(problem, arrays, predictions, records, output)
        receipt.update(execution="completed_retrieval_and_evidence_review_pending")
        (output/"README_analysis.md").write_text("# S04-E027\nSingle exposed synthetic c20s4; horizon0.\n"
            "scores.json is the fixed endpoint table; predictions.npz contains exact scored nodal fields.\n"
            "fields.png displays native-GP-weighted element means; scores retain original nodal/GP supports.\n"
            "rows u/v/d/raw/active; reference/P/S/C share row limits and all signed errors share row limits.\n"
            "profiles.png uses geometry-only nearest columns to x=.25/.40, actual x labelled.\n"
            "loss.png is sampled optimization loss, not physical evolution; losses differ between arms.\n"
            "Visual inspection and independent evidence review pending; not Evidence Ready.\n")
        guard()
    except BaseException as ex:
        receipt.update(execution="failed_or_partial", error_type=type(ex).__name__, error=str(ex))
        raise
    finally:
        receipt.update(progress)
        receipt["elapsed_seconds"] = time.monotonic()-start
        dump(output/"receipt.json", receipt)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--grant", type=Path)
    ap.add_argument("--initializer", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.prepare == a.execute:
        ap.error("choose exactly one mode")
    lock = json.loads(LOCK.read_text())
    torch.set_num_threads(1)
    if a.execute:
        if a.grant is None or a.initializer is None:
            ap.error("future execution requires grant and pinned initializer")
        run(Path(lock["root"]), lock, json.loads(a.grant.read_text()), a.out, a.initializer)
    else:
        if a.out.exists():
            raise FileExistsError("fresh preparation receipt only")
        result = method.prepare(Path(lock["root"]), lock)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        dump(a.out, result)


if __name__ == "__main__":
    main()
