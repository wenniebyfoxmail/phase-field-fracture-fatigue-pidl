"""Single authorised D5 producer run: centreline target plus frozen D1/D2 comparators."""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import importlib.util
import json
import math
import os
import platform
import random
import socket
import sys
import time
from pathlib import Path

import numpy as np
import PIL
from PIL import Image, ImageDraw
import psutil
import scipy
import skimage
import torch
import torchvision
from scipy.ndimage import distance_transform_edt

from centerline_core import (aggregate, centreline, centreline_metrics, field_dice,
                             paired_bootstrap, resize_bool_short_side,
                             resize_probability_short_side, soft_centreline_field)

HERE = Path(__file__).resolve().parent
OWNER = HERE.parent
PROTOCOL = json.loads((HERE / "d5_protocol.json").read_text())
SEED = int(PROTOCOL["seed"])

_spec = importlib.util.spec_from_file_location("d5_base", OWNER / "runner.py")
base = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(base)
sys.path.insert(0, str(OWNER / "d2_public_b_repair_20261019"))
from repair_model import ResNet18UNet
_spec = importlib.util.spec_from_file_location("d5_d2", OWNER / "d2_public_b_repair_20261019" / "d2_runner.py")
d2 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(d2)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot():
    files = [HERE / "d5_runner.py", HERE / "centerline_core.py", HERE / "d5_preflight.py",
             HERE / "d5_admission.ps1",
             HERE / "invoke_d5_admission_once.ps1",
             HERE / "owned_subprocess.py",
             HERE / "environment.invocation.json", HERE / "preflight.invocation.json",
             HERE / "admission_child.invocation.json", HERE / "scientific_worker.invocation.json",
             HERE / "d5_protocol.json", HERE / "d5_data_lock.json", OWNER / "runner.py",
             OWNER / "frozen_protocol.json", OWNER / "d2_public_b_repair_20261019" / "repair_model.py",
             OWNER / "d2_public_b_repair_20261019" / "d2_runner.py",
             OWNER / "d2_public_b_repair_20261019" / "d2_protocol.json",
             OWNER / "runs" / "HQ-ROAD-CENTERLINE-001-R003" / "launch_gpu_server.cmd",
             OWNER / "runs" / "HQ-ROAD-CENTERLINE-001-R003" / "register_and_start.ps1"]
    payload = {path.relative_to(OWNER).as_posix(): sha256(path) for path in files}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def environment():
    return {"python": platform.python_version(), "torch": torch.__version__, "torchvision": torchvision.__version__,
            "numpy": np.__version__, "pillow": PIL.__version__, "scipy": scipy.__version__,
            "skimage": skimage.__version__, "skimage_file": str(Path(skimage.__file__).resolve()),
            "matplotlib": __import__("matplotlib").__version__,
            "psutil": psutil.__version__, "cuda": torch.version.cuda}


def output_bytes(path):
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def canonical(path):
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def extract_verified(archive, destination):
    archive = Path(archive); destination = Path(destination); expected = sha256(archive)
    marker = destination / ".complete"
    if marker.exists():
        observed = marker.read_text().strip()
        if observed != expected:
            raise RuntimeError(f"cache marker mismatch for {destination}: {observed}")
        return
    base.extract_once(archive, destination)
    if not marker.exists() or marker.read_text().strip() != expected:
        raise RuntimeError(f"cache marker missing or invalid for {destination}")


def enforce_resources(output):
    rss = psutil.Process().memory_info().rss
    cuda = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
    if rss > PROTOCOL["max_rss_gib"] * 1024 ** 3:
        raise MemoryError(f"RSS cap exceeded: {rss}")
    if cuda > PROTOCOL["max_cuda_allocated_gib"] * 1024 ** 3:
        raise MemoryError(f"CUDA allocation cap exceeded: {cuda}")
    size = output_bytes(output)
    if size > PROTOCOL["max_output_gib"] * 1024 ** 3:
        raise RuntimeError(f"Output cap exceeded: {size}")
    return rss, cuda, size


class CentrelineTrainSet(torch.utils.data.Dataset):
    def __init__(self, rows):
        self.rows = rows
        self.targets = {}
        for row in rows:
            _, mask = base.load_crack(row)
            self.targets[row["id"]] = np.rint(soft_centreline_field(mask) * 255).astype(np.uint8)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]; image, _ = base.load_crack(row); target = self.targets[row["id"]].astype(np.float32) / 255
        size = int(PROTOCOL["train_crop"][0])
        image = base.reflect_to(image, max(size, image.shape[0]), max(size, image.shape[1]))
        target = base.reflect_to(target, image.shape[0], image.shape[1])
        top = random.randint(0, image.shape[0] - size); left = random.randint(0, image.shape[1] - size)
        image = image[top:top + size, left:left + size]; target = target[top:top + size, left:left + size]
        if random.random() < .5: image, target = image[:, ::-1], target[:, ::-1]
        if random.random() < .5: image, target = image[::-1], target[::-1]
        return (torch.from_numpy(image.copy().transpose(2, 0, 1)).float() / 255,
                torch.from_numpy(target.copy()[None]).float())


@torch.no_grad()
def evaluate_field(model, rows, loader, target_cache, device, deadline):
    values = []
    for row in rows:
        if time.monotonic() >= deadline: raise TimeoutError("D5 train deadline reached")
        image, mask = loader(row); probability, _ = base.predict(model, image, device, deadline)
        target = target_cache.get(row["id"])
        if target is None: target = soft_centreline_field(mask)
        values.append({"id": row["id"], "group": row["group"], "field_dice": field_dice(probability, target)})
    return values


@torch.no_grad()
def evaluate_centreline(model, rows, loader, device, source, deadline):
    output = []
    for row in rows:
        if time.monotonic() >= deadline: raise TimeoutError("D5 hard deadline reached")
        image, mask = loader(row); probability, _ = base.predict(model, image, device, deadline)
        raw = raw_matrix_metrics(probability, mask)
        metrics = centreline_metrics(probability, mask)
        output.append({"id": row["id"], "group": row["group"], "source": source,
                       **{f"raw_mask_{key}": value for key, value in raw.items()}, **metrics})
    return output


def tolerance_overlap(prediction, reference, radius):
    if not prediction.any() and not reference.any(): return 1.0, 1.0, 1.0
    if not prediction.any() or not reference.any(): return 0.0, 0.0, 0.0
    precision = float((distance_transform_edt(~reference)[prediction] <= radius).mean())
    recall = float((distance_transform_edt(~prediction)[reference] <= radius).mean())
    f1 = 0.0 if precision + recall == 0 else 2.0 * precision * recall / (precision + recall)
    return precision, recall, f1


def raw_matrix_metrics(probability, target):
    metrics = base.metric(probability, target); prediction = probability >= 0.5
    metrics.update({"target_empty": bool(not target.any()), "target_fg_fraction": float(target.mean()),
                    "pred_fg_fraction": float(prediction.mean())})
    for radius in (2, 4):
        precision, recall, f1 = tolerance_overlap(prediction, target, radius)
        metrics.update({f"tol{radius}_precision": precision, f"tol{radius}_recall": recall, f"tol{radius}_f1": f1})
    return metrics


def verify_d3_replay(recomputed, frozen_csv, tolerance=1e-5):
    with open(frozen_csv, newline="") as stream:
        frozen = {row["id"]: row for row in csv.DictReader(stream)}
    observed = {row["id"]: row for row in recomputed}
    if set(observed) != set(frozen):
        raise RuntimeError(f"D3 replay identity mismatch for {frozen_csv}")
    numeric = ("dice", "error", "U_LC", "U_H", "target_fg_fraction", "pred_fg_fraction",
               "tol2_precision", "tol2_recall", "tol2_f1", "tol4_precision", "tol4_recall", "tol4_f1")
    boolean = ("pred_empty", "pred_full", "target_empty")
    maximum = 0.0
    for identity, row in observed.items():
        prior = frozen[identity]
        maximum = max(maximum, *(abs(float(row[f"raw_mask_{key}"]) - float(prior[key])) for key in numeric))
        for key in boolean:
            expected = prior[key].strip().lower() == "true"
            if bool(row[f"raw_mask_{key}"]) != expected:
                raise RuntimeError(f"D3 replay boolean mismatch {identity}/{key}")
    result = {"frozen_csv_sha256": sha256(frozen_csv), "matched_ids": len(observed),
              "max_abs_metric_difference": maximum, "tolerance": tolerance, "comparable": maximum <= tolerance}
    if not result["comparable"]:
        raise RuntimeError(f"D3 replay exceeded tolerance for {frozen_csv}: {maximum}")
    return result


def write_csv(path, rows):
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def source_decision(candidate_rows, old_rows, validation_f1_4):
    candidate = aggregate(candidate_rows); old = aggregate(old_rows)
    paired = paired_bootstrap(candidate_rows, old_rows, key="cl2_f1",
                              replicates=PROTOCOL["decision_rule"]["paired_bootstrap_replicates"], seed=SEED)
    absolute_floor = max(.50, .60 * validation_f1_4)
    checks = {
        "mean_cl4_f1_at_least_validation_scaled_floor": candidate["mean_cl4_f1"] >= absolute_floor,
        "component_omission_rate_at_most_0_25": candidate["component_omission_rate"] <= .25,
        "paired_cl2_improvement_at_least_0_10": paired["candidate_minus_baseline_mean"] >= .10,
        "paired_cl2_bootstrap_lower_positive": paired["bootstrap_95_ci"][0] > 0,
    }
    return {"candidate": candidate, "primary_baseline_D1": old, "paired_candidate_vs_D1": paired,
            "validation_ceiling_cl4_f1": validation_f1_4, "absolute_cl4_f1_floor": absolute_floor,
            "checks": checks, "source_pass": all(checks.values())}


def select_visual_ids(candidate, old):
    c = {r["id"]: r for r in candidate if not r["target_empty"]}; o = {r["id"]: r for r in old if not r["target_empty"]}
    ranked = sorted(c, key=lambda identity: (c[identity]["cl2_f1"] - o[identity]["cl2_f1"], identity))
    chosen = ranked[:2] + ranked[-2:]
    omitted = sorted(c, key=lambda identity: (-c[identity]["reference_components_omitted"], identity))[:2]
    return list(dict.fromkeys(chosen + omitted))


def overlay(image, line, color):
    shown = image.copy(); shown[line] = (.45 * shown[line] + .55 * np.asarray(color)).astype(np.uint8)
    return Image.fromarray(shown)


@torch.no_grad()
def make_panel(path, identities, rows, loader, models, device, deadline):
    lookup = {row["id"]: row for row in rows}; cell_w, cell_h = 300, 230
    canvas = Image.new("RGB", (cell_w * 5, cell_h * len(identities)), "white"); draw = ImageDraw.Draw(canvas)
    for index, identity in enumerate(identities):
        image, mask = loader(lookup[identity]); nh, nw = resize_bool_short_side(mask).shape
        image_n = np.asarray(Image.fromarray(image).resize((nw, nh), Image.Resampling.BILINEAR))
        reference = centreline(resize_bool_short_side(mask))
        cells = [Image.fromarray(image_n), overlay(image_n, reference, (255, 40, 40))]
        for name in ("D1", "D2", "D5"):
            probability, _ = base.predict(models[name], image, device, deadline)
            band = resize_probability_short_side(probability) >= .5
            cells.append(overlay(image_n, centreline(band), {"D1": (20, 220, 255), "D2": (255, 220, 20), "D5": (30, 240, 70)}[name]))
        for column, cell in enumerate(cells):
            cell.thumbnail((cell_w, 200)); canvas.paste(cell, (column * cell_w, index * cell_h))
        draw.text((4, index * cell_h + 204), f"{identity}: image | reference | D1 | D2 | D5", fill="black")
    canvas.save(path)


def plot_summary(path, summaries):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    sources = ["CFD", "GAPS384"]; models = ["D1", "D2", "D5"]
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    x = np.arange(len(sources)); width = .25
    for offset, model in enumerate(models):
        axes[0].bar(x + (offset - 1) * width, [summaries[source][model]["mean_cl2_f1"] for source in sources], width, label=model)
        axes[1].bar(x + (offset - 1) * width, [summaries[source][model]["component_omission_rate"] for source in sources], width, label=model)
    axes[0].set_title("Centreline F1 at 2 normalised px"); axes[1].set_title("Reference-component omission rate at 4 px")
    for axis in axes:
        axis.set_xticks(x, sources); axis.grid(axis="y", alpha=.25); axis.legend()
    figure.tight_layout(); figure.savefig(path, dpi=180); plt.close(figure)


def approval_gate(approval, lock_path, args):
    lock = json.loads(Path(lock_path).read_text())
    if platform.system() != "Windows" or not torch.cuda.is_available(): raise RuntimeError("Windows CUDA producer required")
    if approval.get("execute") is not True or approval.get("hostname") != socket.gethostname(): raise RuntimeError("authority/host mismatch")
    if approval.get("experiment_id") != PROTOCOL["experiment_id"] or approval.get("run_id") != PROTOCOL["run_id"]: raise RuntimeError("run identity mismatch")
    if str(approval.get("gpu")) != "0" or os.environ.get("CUDA_VISIBLE_DEVICES") != "0": raise RuntimeError("GPU identity mismatch")
    for key in ("canonical_output", "canonical_cache", "launch_identity", "task_dependency_path", "thread_environment",
                "package_clock_start_utc", "package_deadline_utc", "minimum_launch_remaining_seconds",
                "expected_gpu_uuid"):
        if approval.get(key) != PROTOCOL[key]: raise RuntimeError(f"approval drift from protocol: {key}")
    if approval.get("scientific_protocol_fingerprint_sha256") != PROTOCOL["scientific_protocol_fingerprint_sha256"]:
        raise RuntimeError("scientific protocol fingerprint mismatch")
    resource_fields = {"max_wall_clock_hours":"wall_clock_budget_hours", "max_gpu_hours":"gpu_budget_hours",
                       "max_cpu_threads":"max_cpu_threads", "max_rss_gib":"max_rss_gib",
                       "max_cuda_allocated_gib":"max_cuda_allocated_gib", "max_output_gib":"max_output_gib"}
    for approval_key, protocol_key in resource_fields.items():
        if approval.get(approval_key) != PROTOCOL[protocol_key]: raise RuntimeError(f"approval resource drift: {approval_key}")
    remote = lock["remote_identity"]
    if approval.get("producer_alias") != remote["producer_alias"] or approval.get("hostname") != remote["hostname"] or str(approval.get("gpu")) != str(remote["gpu"]):
        raise RuntimeError("approval producer drift from data lock")
    if approval.get("code_snapshot") != snapshot() or approval.get("data_lock_sha256") != sha256(lock_path): raise RuntimeError("unreviewed code or data lock")
    if approval.get("environment") != environment(): raise RuntimeError("environment drift")
    if canonical(args.output) != canonical(approval.get("canonical_output", "")): raise RuntimeError("noncanonical output path")
    if canonical(args.cache) != canonical(approval.get("canonical_cache", "")): raise RuntimeError("noncanonical cache path")
    if os.environ.get("HQ_RUN_LAUNCH_ID") != approval.get("launch_identity"): raise RuntimeError("launch identity mismatch")
    python_paths = [canonical(item) for item in os.environ.get("PYTHONPATH", "").split(os.pathsep) if item]
    dependency_path = canonical(approval.get("task_dependency_path", ""))
    if python_paths != [dependency_path]: raise RuntimeError("task dependency path must be sole PYTHONPATH entry")
    if not canonical(skimage.__file__).startswith(dependency_path + os.sep): raise RuntimeError("skimage not loaded from task dependency path")
    for key, value in approval.get("thread_environment", {}).items():
        if os.environ.get(key) != value: raise RuntimeError(f"thread environment mismatch: {key}")
    if any("road420" in str(value).lower() for value in vars(args).values()): raise RuntimeError("Road420 argument prohibited")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--approval", required=True); parser.add_argument("--lock", required=True)
    parser.add_argument("--trainzip", required=True); parser.add_argument("--valzip", required=True)
    parser.add_argument("--cfd", required=True); parser.add_argument("--gapszip", required=True); parser.add_argument("--weights", required=True)
    parser.add_argument("--d1-checkpoint", required=True); parser.add_argument("--d2-checkpoint", required=True)
    parser.add_argument("--d3-old-cfd-csv", required=True); parser.add_argument("--d3-old-gaps-csv", required=True)
    parser.add_argument("--d3-repair-cfd-csv", required=True); parser.add_argument("--d3-repair-gaps-csv", required=True)
    parser.add_argument("--cache", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); approval = json.loads(Path(args.approval).read_text()); lock = json.loads(Path(args.lock).read_text())
    approval_gate(approval, args.lock, args)
    for key in ("trainzip", "valzip", "gapszip", "weights", "d1_checkpoint", "d2_checkpoint",
                "d3_old_cfd_csv", "d3_old_gaps_csv", "d3_repair_cfd_csv", "d3_repair_gaps_csv"):
        path = Path(getattr(args, key)); observed = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        if observed != {k: lock[key][k] for k in ("bytes", "sha256")}: raise RuntimeError(f"identity mismatch {key}: {observed}")
    if base.cfd_lock(Path(args.cfd)) != lock["cfd_lock"]: raise RuntimeError("CFD identity mismatch")
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False); cache = Path(args.cache)
    torch.set_num_threads(PROTOCOL["max_cpu_threads"]); torch.set_num_interop_threads(1)
    run_start = time.monotonic()
    deadline_epoch = datetime.datetime.fromisoformat(PROTOCOL["package_deadline_utc"].replace("Z", "+00:00")).timestamp()
    package_remaining_s = deadline_epoch - time.time()
    if package_remaining_s < PROTOCOL["minimum_launch_remaining_seconds"]:
        raise TimeoutError(f"original package clock cannot fit the complete run: {package_remaining_s:.3f}s remaining")
    hard_deadline = run_start + min(PROTOCOL["wall_clock_budget_hours"] * 3600, package_remaining_s)
    train_budget_s = min(PROTOCOL["train_deadline_hours"] * 3600,
                         package_remaining_s - PROTOCOL["post_train_reserve_seconds"])
    train_deadline = run_start + train_budget_s
    receipt = {"status": "running", "experiment_id": PROTOCOL["experiment_id"], "run_id": approval["run_id"],
               "hostname": socket.gethostname(), "pid": os.getpid(), "gpu": os.environ.get("CUDA_VISIBLE_DEVICES"),
               "code_snapshot": snapshot(), "data_lock_sha256": sha256(args.lock), "environment": environment(),
               "launch_identity": os.environ.get("HQ_RUN_LAUNCH_ID"),
               "task_dependency_path": approval["task_dependency_path"],
               "thread_environment": {key: os.environ.get(key) for key in approval["thread_environment"]},
               "command": sys.argv, "started_unix": time.time(), "road420_access": False, "scientific_attempt": 1,
               "package_clock_start_utc": PROTOCOL["package_clock_start_utc"],
               "package_deadline_utc": PROTOCOL["package_deadline_utc"],
               "package_remaining_seconds_at_runner_start": package_remaining_s}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2))
    try:
        extract_verified(args.trainzip, cache / "train"); extract_verified(args.valzip, cache / "val")
        train = base.crack_pairs(cache / "train", "traincrop", set(base.PROTOCOL["crack500_excluded_train_parents"]))
        val = base.crack_pairs(cache / "val", "valcrop", set(base.PROTOCOL["crack500_excluded_val_parents"]))
        cfd = base.cfd_pairs(Path(args.cfd)); gaps = d2.gaps_pairs(args.gapszip)
        nonempty = [bool(d2.load_gaps(row)[1].any()) for row in gaps]; expected = PROTOCOL["expected"]
        counts = (len(train), len({r['group'] for r in train}), len(val), len({r['group'] for r in val}), len(cfd), len(gaps), sum(nonempty), len(gaps)-sum(nonempty))
        wanted = tuple(expected[k] for k in ("train_pairs","train_groups","val_pairs","val_groups","cfd_labeled","gaps_labeled","gaps_nonempty","gaps_empty"))
        if counts != wanted: raise RuntimeError(f"inventory mismatch {counts}")
        random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
        torch.use_deterministic_algorithms(True); torch.backends.cudnn.benchmark = False; torch.cuda.reset_peak_memory_stats()
        device = torch.device("cuda:0"); candidate = ResNet18UNet(args.weights).to(device)
        optimizer = torch.optim.Adam(candidate.parameters(), lr=1e-3)
        train_set = CentrelineTrainSet(train); val_targets = {}
        for row in val:
            _, mask = base.load_crack(row); val_targets[row["id"]] = soft_centreline_field(mask)
        generator = torch.Generator().manual_seed(SEED)
        loader = torch.utils.data.DataLoader(train_set, batch_size=8, shuffle=True, num_workers=0, generator=generator)
        history = []; best = -1.; best_epoch = None
        for epoch in range(1, 41):
            if time.monotonic() >= train_deadline: break
            candidate.train(); losses = []
            for image, target in loader:
                if time.monotonic() >= train_deadline: break
                image = image.to(device); target = target.to(device); optimizer.zero_grad(set_to_none=True)
                loss = base.loss_fn(candidate(image), target)
                if not torch.isfinite(loss): raise RuntimeError("nonfinite loss")
                loss.backward(); optimizer.step(); losses.append(float(loss.detach().cpu()))
            if time.monotonic() >= train_deadline: break
            validation = evaluate_field(candidate, val, base.load_crack, val_targets, device, train_deadline)
            score = float(np.mean([row["field_dice"] for row in validation])); selected = score > best
            if selected:
                best = score; best_epoch = epoch
                torch.save({"model": candidate.state_dict(), "epoch": epoch, "val_mean_field_dice": score}, output / "best.pt")
            rss, cuda, size = enforce_resources(output)
            history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "val_mean_field_dice": score,
                            "selected": selected, "elapsed_s": time.monotonic()-run_start, "rss_bytes": rss,
                            "cuda_max_allocated_bytes": cuda, "output_bytes": size})
            (output / "selection.json").write_text(json.dumps(history, indent=2))
            (output / "fit_status.json").write_text(json.dumps({"status":"running","completed_epoch":epoch,"best_epoch":best_epoch,
                "budget_s":PROTOCOL["wall_clock_budget_hours"]*3600}, indent=2))
        if len(history) != 40: raise TimeoutError(f"full 40-epoch schedule not completed: {len(history)}")
        state = torch.load(output / "best.pt", map_location=device, weights_only=True); candidate.load_state_dict(state["model"])
        d1_model = base.UNet().to(device); d1_state = torch.load(args.d1_checkpoint, map_location=device, weights_only=True); d1_model.load_state_dict(d1_state["model"])
        d2_model = ResNet18UNet().to(device); d2_state = torch.load(args.d2_checkpoint, map_location=device, weights_only=True); d2_model.load_state_dict(d2_state["model"])
        models = {"D1": d1_model, "D2": d2_model, "D5": candidate}
        val_rows = evaluate_centreline(candidate, val, base.load_crack, device, "CRACK500_val", hard_deadline)
        write_csv(output / "d5_crack500_validation_metrics.csv", val_rows)
        validation_summary = aggregate(val_rows); validation_ceiling = validation_summary["mean_cl4_f1"]
        results = {}; source_rows = {"CFD": (cfd, base.load_cfd), "GAPS384": (gaps, d2.load_gaps)}
        for source, (rows, row_loader) in source_rows.items():
            for model_name, model in models.items():
                evaluated = evaluate_centreline(model, rows, row_loader, device, source, hard_deadline)
                results[(source, model_name)] = evaluated; write_csv(output / f"{source.lower()}_{model_name.lower()}_metrics.csv", evaluated)
        replay = {
            "D1_CFD": verify_d3_replay(results[("CFD","D1")], args.d3_old_cfd_csv),
            "D1_GAPS384": verify_d3_replay(results[("GAPS384","D1")], args.d3_old_gaps_csv),
            "D2_CFD": verify_d3_replay(results[("CFD","D2")], args.d3_repair_cfd_csv),
            "D2_GAPS384": verify_d3_replay(results[("GAPS384","D2")], args.d3_repair_gaps_csv),
        }
        decisions = {source: source_decision(results[(source,"D5")], results[(source,"D1")], validation_ceiling)
                     for source in source_rows}
        summaries = {source: {name: aggregate(results[(source,name)]) for name in models} for source in source_rows}
        for source in decisions:
            decisions[source]["secondary_baseline_D2"] = summaries[source]["D2"]
        final = {"run_id": approval["run_id"], "best_epoch": state["epoch"], "validation": validation_summary,
                 "baseline_replay_against_D3": replay, "sources": decisions, "all_sources_pass": all(item["source_pass"] for item in decisions.values()),
                 "verdict": "D5_ADVANCE_TO_SELECTIVE_ACCEPTANCE_DESIGN" if all(item["source_pass"] for item in decisions.values()) else "D5_STOP_PUBLIC_MASK_ARCHITECTURE_UQ_EXPANSION",
                 "scope": "named public published-label centreline localisation only; not physical truth, width, independent-site, safety or human-review utility"}
        (output / "result.json").write_text(json.dumps(final, indent=2))
        selection = {}
        for source, (rows, row_loader) in source_rows.items():
            identities = select_visual_ids(results[(source,"D5")], results[(source,"D1")]); selection[source] = identities
            make_panel(output / f"centreline_panel_{source}.png", identities, rows, row_loader, models, device, hard_deadline)
        (output / "visual_selection.json").write_text(json.dumps(selection, indent=2))
        plot_summary(output / "centreline_comparison.png", summaries)
        rss, cuda, size = enforce_resources(output)
        (output / "fit_status.json").write_text(json.dumps({"status":"completed","completed_epoch":40,"best_epoch":best_epoch,
            "budget_s":PROTOCOL["wall_clock_budget_hours"]*3600,"budget_stop":False}, indent=2))
        receipt.update({"status":"succeeded","ended_unix":time.time(),"duration_seconds":time.monotonic()-run_start,
                        "checkpoint_sha256":sha256(output/"best.pt"),"result_sha256":sha256(output/"result.json"),
                        "rss_bytes":rss,"cuda_max_allocated_bytes":cuda,"output_bytes":size,"verdict":final["verdict"]})
    except BaseException as error:
        receipt.update({"status":"failed","ended_unix":time.time(),"duration_seconds":time.monotonic()-run_start,"error":repr(error)})
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
