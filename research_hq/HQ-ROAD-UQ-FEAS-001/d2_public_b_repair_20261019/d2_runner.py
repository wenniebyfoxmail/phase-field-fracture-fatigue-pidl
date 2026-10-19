"""Prepared D2 producer runner. This file does not itself authorize execution."""
import argparse
import csv
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
import zipfile
from pathlib import Path

import numpy as np
import PIL
from PIL import Image
import torch

from repair_model import ResNet18UNet

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
PROTOCOL = json.loads((HERE / "d2_protocol.json").read_text())
SEED = int(PROTOCOL["seed"])
_spec = importlib.util.spec_from_file_location("hq_d1_base", PARENT / "runner.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot():
    names = ["d2_runner.py", "repair_model.py", "d2_protocol.json", "d2_data_lock.json"]
    payload = {name: sha256(HERE / name) for name in names}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def environment():
    import matplotlib
    return {"python": platform.python_version(), "torch": torch.__version__, "torchvision": __import__("torchvision").__version__,
            "numpy": np.__version__, "pillow": PIL.__version__, "matplotlib": matplotlib.__version__, "cuda": torch.version.cuda}


def gaps_pairs(archive):
    archive = Path(archive)
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    images = {Path(name).stem: name for name in names if name.startswith("img/") and name.lower().endswith((".jpg", ".png"))}
    masks = {Path(name).stem.removesuffix("_mask"): name for name in names if name.startswith("gt/") and name.endswith("_mask.png")}
    return [{"id": stem, "group": stem, "archive": archive, "image_member": images[stem], "mask_member": masks[stem]}
            for stem in sorted(images.keys() & masks.keys())]


def load_gaps(row):
    with zipfile.ZipFile(row["archive"]) as zf:
        with zf.open(row["image_member"]) as source, Image.open(source) as image:
            rgb = np.asarray(image.convert("RGB"))
        with zf.open(row["mask_member"]) as source, Image.open(source) as mask:
            raw = np.asarray(mask.convert("L"))
    values = set(np.unique(raw).tolist())
    if not values.issubset({0, 255}):
        raise ValueError(f"Nonbinary GAPS384 mask {row['id']}: {values}")
    target = raw > 0
    if rgb.shape[:2] != target.shape:
        raise ValueError(f"GAPS384 shape mismatch {row['id']}")
    return rgb, target


def risk(rows, key):
    ordered = sorted(rows, key=lambda row: (row[key], row["id"]))
    values = np.asarray([row["error"] for row in ordered])
    cumulative = np.cumsum(values) / np.arange(1, len(values) + 1)
    return [{"k": i + 1, "coverage": (i + 1) / len(values), "risk": float(value), "id": ordered[i]["id"]}
            for i, value in enumerate(cumulative)]


def summarize(nonempty_rows):
    n = len(nonempty_rows)
    if n != 382:
        raise ValueError(f"Primary GAPS384 cohort must have 382 nonempty masks, got {n}")
    dice_positive_min = math.ceil(0.75 * n)
    degenerate_max_exclusive = math.ceil(0.50 * n)
    accepted_n = math.floor(0.25 * n)
    full = float(np.mean([row["error"] for row in nonempty_rows]))
    curves = {key: risk(nonempty_rows, key) for key in ["U_LC", "U_H", "U_Z"]}
    scores = {}
    for key, curve in curves.items():
        at_25 = curve[accepted_n - 1]["risk"]
        scores[key] = {"risk_at_25": at_25, "aurc": float(np.mean([point["risk"] for point in curve])),
                       "F2": at_25 <= full - 0.05}
    positive = sum(row["dice"] > 0 for row in nonempty_rows)
    degenerate = sum(row["pred_empty"] or row["pred_full"] for row in nonempty_rows)
    f1 = positive >= dice_positive_min and degenerate < degenerate_max_exclusive
    f2 = any(item["F2"] for item in scores.values())
    f3 = scores["U_Z"]["risk_at_25"] < scores["U_LC"]["risk_at_25"]
    return {"n": n, "full_risk": full,
            "thresholds": {"nonempty_n": n, "dice_positive_min": dice_positive_min,
                           "degenerate_max_exclusive": degenerate_max_exclusive, "accepted_n": accepted_n},
            "scores": scores, "F1": f1, "F2": f2, "F3_U_Z_directional": f3,
            "dice_positive_count": positive, "degenerate_prediction_count": degenerate,
            "catastrophic_error_ge_0_9": sum(row["error"] >= 0.9 for row in nonempty_rows),
            "verdict": "FEASIBILITY_GO" if f1 and f2 else "FEASIBILITY_NO_GO"}


def write_csv(path, rows):
    clean = [{key: value for key, value in row.items() if key != "feature"} for row in rows]
    with open(path, "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(clean[0]))
        writer.writeheader()
        writer.writerows(clean)


def approval_gate(approval, lock_path, args):
    if platform.system() != "Windows" or not torch.cuda.is_available():
        raise RuntimeError("Windows CUDA producer required")
    if approval.get("execute") is not True or approval.get("hostname") != socket.gethostname():
        raise RuntimeError("Authorization/host mismatch")
    if approval.get("experiment_id") != PROTOCOL["experiment_id"] or approval.get("run_id") != "HQ-ROAD-UQ-FEAS-002-R001":
        raise RuntimeError("Run identity mismatch")
    if approval.get("code_snapshot") != snapshot() or approval.get("data_lock_sha256") != sha256(lock_path):
        raise RuntimeError("Unreviewed snapshot or data lock")
    if approval.get("environment") != environment():
        raise RuntimeError("Environment drift")
    if any("road420" in key.lower() or "road420" in str(value).lower() for key, value in vars(args).items()):
        raise RuntimeError("Road420 path/config prohibited")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True); parser.add_argument("--lock", required=True)
    parser.add_argument("--trainzip", required=True); parser.add_argument("--valzip", required=True); parser.add_argument("--testzip", required=True)
    parser.add_argument("--gapszip", required=True); parser.add_argument("--weights", required=True)
    parser.add_argument("--cache", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    approval = json.loads(Path(args.approval).read_text()); lock = json.loads(Path(args.lock).read_text())
    approval_gate(approval, args.lock, args)
    for key, path in [("trainzip", args.trainzip), ("valzip", args.valzip), ("testzip", args.testzip),
                      ("gapszip", args.gapszip), ("weights", args.weights)]:
        if sha256(path) != lock[key]["sha256"]:
            raise RuntimeError(f"Hash mismatch {key}")
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False); cache = Path(args.cache)
    receipt = {"status": "running", "experiment_id": PROTOCOL["experiment_id"], "run_id": approval["run_id"],
               "hostname": socket.gethostname(), "pid": os.getpid(), "gpu": os.environ.get("CUDA_VISIBLE_DEVICES"),
               "code_snapshot": snapshot(), "data_lock_sha256": sha256(args.lock), "command": sys.argv,
               "started_unix": time.time(), "scope": "finite public published-label backbone-transfer feasibility only",
               "road420_access": False}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2))
    try:
        base.extract_once(args.trainzip, cache / "train"); base.extract_once(args.valzip, cache / "val"); base.extract_once(args.testzip, cache / "test")
        old_protocol = base.PROTOCOL
        train = base.crack_pairs(cache / "train", "traincrop", set(old_protocol["crack500_excluded_train_parents"]))
        val = base.crack_pairs(cache / "val", "valcrop", set(old_protocol["crack500_excluded_val_parents"]))
        test = base.crack_pairs(cache / "test", "testdata")
        gaps = gaps_pairs(args.gapszip)
        mask_nonempty = []
        for row in gaps:
            _, target = load_gaps(row); mask_nonempty.append(bool(target.any()))
        expected = PROTOCOL["expected"]
        counts = (len(train), len(set(row["group"] for row in train)), len(val), len(set(row["group"] for row in val)),
                  len(test), len(gaps), sum(mask_nonempty), len(gaps) - sum(mask_nonempty))
        wanted = tuple(expected[key] for key in ["train_pairs", "train_groups", "val_pairs", "val_groups", "test_pairs", "gaps_labeled", "gaps_nonempty", "gaps_empty"])
        if counts != wanted:
            raise RuntimeError(f"Inventory mismatch {counts}")
        random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
        torch.use_deterministic_algorithms(True); torch.backends.cudnn.benchmark = False
        device = torch.device("cuda:0"); model = ResNet18UNet(args.weights).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        generator = torch.Generator().manual_seed(SEED)
        loader = torch.utils.data.DataLoader(base.TrainSet(train), batch_size=8, shuffle=True, num_workers=0, generator=generator)
        run_start = time.monotonic(); train_deadline = run_start + 5.5 * 3600; hard_deadline = run_start + 6 * 3600
        history = []; best = -1.0; best_epoch = None
        for epoch in range(1, 41):
            if time.monotonic() > train_deadline: break
            model.train(); losses = []
            for x, y in loader:
                if time.monotonic() > train_deadline: break
                x = x.to(device); y = y.to(device); optimizer.zero_grad(set_to_none=True)
                loss = base.loss_fn(model(x), y)
                if not torch.isfinite(loss): raise RuntimeError("Nonfinite loss")
                loss.backward(); optimizer.step(); losses.append(float(loss.detach().cpu()))
            if time.monotonic() > train_deadline: break
            metrics = base.evaluate(model, val, base.load_crack, device, "CRACK500_val", train_deadline)
            score = float(np.mean([row["dice"] for row in metrics])); selected = score > best
            if selected:
                best = score; best_epoch = epoch
                torch.save({"model": model.state_dict(), "epoch": epoch, "val_mean_dice": score}, output / "best.pt")
            history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "val_mean_dice": score,
                            "selected": selected, "elapsed_s": time.monotonic() - run_start})
            (output / "selection.json").write_text(json.dumps(history, indent=2))
            (output / "fit_status.json").write_text(json.dumps({"status": "running", "completed_epoch": epoch,
                "best_epoch": best_epoch, "budget_s": 21600}, indent=2))
        if not (output / "best.pt").exists(): raise RuntimeError("No validated checkpoint within budget")
        state = torch.load(output / "best.pt", map_location=device, weights_only=True); model.load_state_dict(state["model"])
        a_val = base.evaluate(model, val, base.load_crack, device, "CRACK500_val", hard_deadline)
        features = np.asarray([row["feature"] for row in a_val]); mean = features.mean(0); variance = np.maximum(features.var(0), 1e-6)
        a_test = base.evaluate(model, test, base.load_crack, device, "CRACK500_test", hard_deadline)
        b_all = base.evaluate(model, gaps, load_gaps, device, "GAPS384", hard_deadline)
        for rows in [a_val, a_test, b_all]:
            for row in rows: row["U_Z"] = float(np.mean((np.asarray(row["feature"]) - mean) ** 2 / variance))
        b_primary = [row for row, nonempty in zip(b_all, mask_nonempty) if nonempty]
        b_empty = [row for row, nonempty in zip(b_all, mask_nonempty) if not nonempty]
        write_csv(output / "a_validation_metrics.csv", a_val); write_csv(output / "a_test_metrics.csv", a_test)
        write_csv(output / "gaps384_nonempty_metrics.csv", b_primary); write_csv(output / "gaps384_empty_reference_metrics.csv", b_empty)
        result = summarize(b_primary); result.update({"best_epoch": state["epoch"], "a_val_mean_dice": state["val_mean_dice"],
            "empty_reference_n": len(b_empty), "empty_reference_false_positive_n": sum(not row["pred_empty"] for row in b_empty),
            "scope": "finite public published-label backbone-transfer feasibility only; not physical truth, crack width, prevalence, independent-site generalization, field safety, or human-review utility"})
        curves = {key: risk(b_primary, key) for key in ["U_LC", "U_H", "U_Z"]}
        (output / "gaps384_risk_curves.json").write_text(json.dumps(curves, indent=2)); (output / "result.json").write_text(json.dumps(result, indent=2))
        (output / "all_failures.json").write_text(json.dumps(sorted([row for row in b_primary if row["error"] >= 0.9], key=lambda row: -row["error"]), indent=2))
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        figure, axis = plt.subplots(figsize=(7, 5))
        for key, curve in curves.items(): axis.plot([p["coverage"] for p in curve], [p["risk"] for p in curve], label=key)
        axis.axhline(result["full_risk"], color="black", ls="--", lw=1, label="full nonempty cohort")
        axis.set(xlabel="Accepted fraction", ylabel="Mean 1-Dice vs GAPS384 published labels", title="HQ-ROAD-UQ-FEAS-002-R001")
        axis.legend(); figure.tight_layout(); figure.savefig(output / "gaps384_risk_curves.png", dpi=180); plt.close(figure)
        (output / "README_analysis.md").write_text("Read result.json, both GAPS384 CSV files and gaps384_risk_curves.png. The 382 nonempty published masks define the primary gate; two empty-reference cases are separate. This diagnostic does not establish physical crack truth, crack width, natural prevalence, independent-site generalization, field safety or human-review utility.\n")
        (output / "fit_status.json").write_text(json.dumps({"status": "completed", "completed_epoch": history[-1]["epoch"],
            "best_epoch": best_epoch, "budget_s": 21600, "budget_stop": history[-1]["epoch"] < 40}, indent=2))
        receipt["status"] = "succeeded"; receipt["checkpoint_sha256"] = sha256(output / "best.pt"); receipt["result_sha256"] = sha256(output / "result.json")
    except BaseException as error:
        receipt["status"] = "failed"; receipt["error"] = repr(error); raise
    finally:
        receipt["ended_unix"] = time.time(); (output / "receipt.json").write_text(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
