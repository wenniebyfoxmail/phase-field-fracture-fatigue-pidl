"""No-training evaluator for the paired old/new checkpoint x CFD/GAPS matrix."""
import argparse, csv, hashlib, importlib.util, json, math, os, platform, socket, sys, time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import torch
from scipy.ndimage import distance_transform_edt

HERE = Path(__file__).resolve().parent
OWNER = HERE.parent
spec = importlib.util.spec_from_file_location("matrix_base", OWNER / "runner.py")
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
sys.path.insert(0, str(OWNER / "d2_public_b_repair_20261019"))
spec = importlib.util.spec_from_file_location("matrix_d2", OWNER / "d2_public_b_repair_20261019" / "d2_runner.py")
d2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(d2)
from repair_model import ResNet18UNet

PROTOCOL = json.loads((HERE / "matrix_protocol.json").read_text())


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def snapshot():
    payload = {p.name: sha256(p) for p in [HERE / "paired_matrix_evaluator.py", HERE / "matrix_protocol.json"]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def environment():
    import PIL, scipy, matplotlib, torchvision
    return {"python": platform.python_version(), "torch": torch.__version__, "torchvision": torchvision.__version__,
            "numpy": np.__version__, "pillow": PIL.__version__, "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__, "cuda": torch.version.cuda}


def tolerance_overlap(pred, target, radius):
    if not pred.any() and not target.any(): return 1.0, 1.0, 1.0
    if not pred.any() or not target.any(): return 0.0, 0.0, 0.0
    precision = float((distance_transform_edt(~target)[pred] <= radius).mean())
    recall = float((distance_transform_edt(~pred)[target] <= radius).mean())
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


@torch.no_grad()
def evaluate(model, rows, loader, device, source, mean, variance, deadline):
    output = []
    for row in rows:
        if time.monotonic() >= deadline: raise TimeoutError("paired matrix two GPU-hour budget reached")
        rgb, target = loader(row); probability, feature = base.predict(model, rgb, device, deadline)
        metrics = base.metric(probability, target); pred = probability >= 0.5
        metrics.update({"id": row["id"], "group": row["group"], "source": source,
                        "target_empty": bool(not target.any()), "target_fg_fraction": float(target.mean()),
                        "pred_fg_fraction": float(pred.mean()),
                        "U_Z": float(np.mean((feature - mean) ** 2 / variance))})
        for radius in [2, 4]:
            precision, recall, f1 = tolerance_overlap(pred, target, radius)
            metrics.update({f"tol{radius}_precision": precision, f"tol{radius}_recall": recall, f"tol{radius}_f1": f1})
        output.append(metrics)
    return output


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def risk(rows, key):
    ordered = sorted(rows, key=lambda r: (r[key], r["id"])); errors = np.asarray([r["error"] for r in ordered])
    values = np.cumsum(errors) / np.arange(1, len(errors) + 1)
    return [{"k": i + 1, "coverage": (i + 1) / len(rows), "risk": float(value), "id": ordered[i]["id"]}
            for i, value in enumerate(values)]


def summarize(rows):
    primary = [r for r in rows if not r["target_empty"]]; n = len(primary); accepted = math.floor(0.25 * n)
    full = float(np.mean([r["error"] for r in primary])); curves = {key: risk(primary, key) for key in ["U_LC", "U_H", "U_Z"]}
    return {"n_all": len(rows), "n_nonempty": n, "n_empty": len(rows) - n, "full_risk": full,
            "mean_dice": float(np.mean([r["dice"] for r in primary])),
            "degenerate": sum(r["pred_empty"] or r["pred_full"] for r in primary),
            "mean_tol2_f1": float(np.mean([r["tol2_f1"] for r in primary])),
            "mean_tol4_f1": float(np.mean([r["tol4_f1"] for r in primary])),
            "accepted_n": accepted,
            "scores": {key: {"risk_at_25": curve[accepted - 1]["risk"],
                              "risk_reduction": full - curve[accepted - 1]["risk"],
                              "aurc": float(np.mean([point["risk"] for point in curve]))}
                       for key, curve in curves.items()}, "curves": curves}


def bootstrap_delta(old_rows, new_rows):
    old = {r["id"]: r for r in old_rows if not r["target_empty"]}; new = {r["id"]: r for r in new_rows if not r["target_empty"]}
    ids = sorted(old.keys() & new.keys()); delta = np.asarray([new[i]["error"] - old[i]["error"] for i in ids])
    rng = np.random.default_rng(PROTOCOL["bootstrap_seed"]); samples = []
    for _ in range(PROTOCOL["paired_bootstrap_replicates"]): samples.append(float(delta[rng.integers(0, len(delta), len(delta))].mean()))
    return {"n": len(ids), "new_minus_old_mean_error": float(delta.mean()),
            "bootstrap_95_interval": [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]}


def read_csv(path):
    with open(path, newline="") as f: return list(csv.DictReader(f))


def verify_diagonal(recomputed, frozen_csv):
    frozen = {row["id"]: row for row in read_csv(frozen_csv)}; differences = []
    for row in recomputed:
        if row["id"] not in frozen: continue
        prior = frozen[row["id"]]
        differences.append(max(abs(float(row[key]) - float(prior[key])) for key in ["dice", "U_LC", "U_H", "U_Z"]))
    return {"matched_ids": len(differences), "max_abs_metric_difference": max(differences) if differences else None,
            "comparable": bool(differences) and max(differences) <= 1e-5}


def overlay(rgb, mask, color):
    image = rgb.copy(); image[mask] = (0.45 * image[mask] + 0.55 * np.asarray(color)).astype(np.uint8)
    return Image.fromarray(image).resize((320, 200), Image.Resampling.BILINEAR)


def selected_ids(old_rows, new_rows):
    old = {r["id"]: r for r in old_rows}; new = {r["id"]: r for r in new_rows}; common = sorted(old.keys() & new.keys())
    ranked = sorted(common, key=lambda i: (new[i]["error"] - old[i]["error"], i))
    chosen = ranked[:3] + ranked[-3:]
    chosen += [i for i in common if (old[i]["pred_empty"] or old[i]["pred_full"]) and (new[i]["pred_empty"] or new[i]["pred_full"])][:2]
    return list(dict.fromkeys(chosen))


@torch.no_grad()
def make_panel(path, ids, rows, loader, old_model, new_model, device, deadline):
    lookup = {r["id"]: r for r in rows}; canvas = Image.new("RGB", (1280, 230 * len(ids)), "white"); draw = ImageDraw.Draw(canvas)
    for index, identity in enumerate(ids):
        rgb, target = loader(lookup[identity]); old, _ = base.predict(old_model, rgb, device, deadline); new, _ = base.predict(new_model, rgb, device, deadline)
        cells = [Image.fromarray(rgb).resize((320, 200), Image.Resampling.BILINEAR), overlay(rgb, target, (255, 40, 40)),
                 overlay(rgb, old >= 0.5, (20, 220, 255)), overlay(rgb, new >= 0.5, (255, 220, 20))]
        for col, cell in enumerate(cells): canvas.paste(cell, (320 * col, 230 * index))
        draw.text((4, 230 * index + 204), f"{identity}: image | target | old | repair", fill="black")
    canvas.save(path)


def approval_gate(approval, lock_path):
    if platform.system() != "Windows" or not torch.cuda.is_available(): raise RuntimeError("Windows CUDA evaluator required")
    if approval.get("execute_matrix") is not True or approval.get("hostname") != socket.gethostname(): raise RuntimeError("authorization/host mismatch")
    if approval.get("run_id") != "HQ-ROAD-UQ-MATRIX-001-R001": raise RuntimeError("matrix run identity mismatch")
    if approval.get("code_snapshot") != snapshot() or approval.get("data_lock_sha256") != sha256(lock_path): raise RuntimeError("unreviewed evaluator or lock")
    if approval.get("environment") != environment(): raise RuntimeError("environment drift")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--approval", required=True); parser.add_argument("--lock", required=True)
    parser.add_argument("--old-checkpoint", required=True); parser.add_argument("--new-checkpoint", required=True)
    parser.add_argument("--valzip", required=True); parser.add_argument("--cfd", required=True); parser.add_argument("--gapszip", required=True)
    parser.add_argument("--old-cfd-csv", required=True); parser.add_argument("--new-gaps-csv", required=True)
    parser.add_argument("--cache", required=True); parser.add_argument("--output", required=True); args = parser.parse_args()
    approval = json.loads(Path(args.approval).read_text()); lock = json.loads(Path(args.lock).read_text()); approval_gate(approval, args.lock)
    paths = {key: Path(getattr(args, key.replace("-", "_"))) for key in ["old_checkpoint", "new_checkpoint", "valzip", "gapszip", "old_cfd_csv", "new_gaps_csv"]}
    for key, path in paths.items():
        if sha256(path) != lock[key]["sha256"]: raise RuntimeError(f"hash mismatch {key}")
    if base.cfd_lock(Path(args.cfd)) != lock["cfd_lock"]: raise RuntimeError("CFD content drift")
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False); deadline = time.monotonic() + 2 * 3600
    cache = Path(args.cache); base.extract_once(args.valzip, cache / "val")
    val = base.crack_pairs(cache / "val", "valcrop", set(base.PROTOCOL["crack500_excluded_val_parents"]))
    cfd = base.cfd_pairs(Path(args.cfd)); gaps = d2.gaps_pairs(args.gapszip); device = torch.device("cuda:0")
    old_model = base.UNet().to(device); old_state = torch.load(args.old_checkpoint, map_location=device, weights_only=True); old_model.load_state_dict(old_state["model"])
    new_model = ResNet18UNet().to(device); new_state = torch.load(args.new_checkpoint, map_location=device, weights_only=True); new_model.load_state_dict(new_state["model"])
    results = {}; models = {"old": old_model, "repair": new_model}
    for name, model in models.items():
        av = base.evaluate(model, val, base.load_crack, device, f"A_val_{name}", deadline); features = np.asarray([r["feature"] for r in av])
        mean, variance = features.mean(0), np.maximum(features.var(0), 1e-6)
        results[(name, "CFD")] = evaluate(model, cfd, base.load_cfd, device, "CFD", mean, variance, deadline)
        results[(name, "GAPS384")] = evaluate(model, gaps, d2.load_gaps, device, "GAPS384", mean, variance, deadline)
    for (model, source), rows in results.items(): write_csv(output / f"{model}_{source.lower()}_metrics.csv", rows)
    summary = {f"{model}_{source}": {k: v for k, v in summarize(rows).items() if k != "curves"} for (model, source), rows in results.items()}
    summary["paired_delta"] = {source: bootstrap_delta(results[("old", source)], results[("repair", source)]) for source in ["CFD", "GAPS384"]}
    summary["diagonal_verification"] = {"old_CFD": verify_diagonal(results[("old", "CFD")], args.old_cfd_csv),
                                        "repair_GAPS384": verify_diagonal(results[("repair", "GAPS384")], args.new_gaps_csv)}
    curves = {f"{m}_{s}": summarize(rows)["curves"] for (m, s), rows in results.items()}
    (output / "matrix_summary.json").write_text(json.dumps(summary, indent=2)); (output / "risk_curves.json").write_text(json.dumps(curves, indent=2))
    for source, rows, loader in [("CFD", cfd, base.load_cfd), ("GAPS384", gaps, d2.load_gaps)]:
        ids = selected_ids(results[("old", source)], results[("repair", source)])
        make_panel(output / f"paired_failures_{source}.png", ids, rows, loader, old_model, new_model, device, deadline)
        (output / f"paired_failures_{source}_selection.json").write_text(json.dumps({"rule": "three largest repair improvements, three largest degradations, then up to two both-degenerate", "ids": ids}, indent=2))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    for axis, ((model, source), rows) in zip(axes.flat, results.items()):
        cell = summarize(rows)
        for key, curve in cell["curves"].items(): axis.plot([p["coverage"] for p in curve], [p["risk"] for p in curve], label=key)
        axis.axhline(cell["full_risk"], color="black", ls="--", lw=1); axis.set_title(f"{model} / {source}"); axis.legend()
    fig.supxlabel("Accepted fraction"); fig.supylabel("Mean 1-Dice vs published label"); fig.tight_layout(); fig.savefig(output / "paired_matrix_risk_curves.png", dpi=180); plt.close(fig)
    receipt = {"status": "succeeded", "run_id": approval["run_id"], "code_snapshot": snapshot(),
               "data_lock_sha256": sha256(args.lock), "training_steps": 0, "road420_access": False,
               "summary_sha256": sha256(output / "matrix_summary.json")}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2))


if __name__ == "__main__": main()
