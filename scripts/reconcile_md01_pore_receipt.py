"""Read-only artifact reconciliation after E039's final exclusive-save collision.

Writes a new reconciliation file; never overwrites the original receipt or
reruns segmentation/filtering. Invoke before modifying protected source files.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

import md01_frame_geometry as v1
from md01_geometry_stability import receipt
from md01_early_relative import save, now


def run(a):
    m = json.loads(a.manifest.read_text())
    start = json.loads((a.run / "run_receipt.json").read_text())
    assert start["execution"] == "running" and start["dirty"] == []
    assert v1.sha(a.manifest) == start["manifest_sha256"]
    assert all(v1.sha(p) == h for p, h in m["protected_files"].items())
    rows = json.loads((a.run / "all_metrics.json").read_text())
    summary = json.loads((a.run / "summary.json").read_text())
    assert len(rows) == 45 and len(summary) == 5
    cases = []
    for row in rows:
        rel = Path(f"step{row['stage']}") / row["arm"]
        with np.load(Path(m["input_root"]) / rel / "geometry_arrays.npz") as f:
            old = f["mask"]
        with np.load(a.run / rel / "geometry_arrays.npz") as f:
            mask, removed, points = f["mask"], f["removed"], f["protected_points"]
        assert np.array_equal(mask, old & ~removed) and not np.any(removed & ~old)
        assert int(removed.sum()) == row["removed_px"]
        assert np.array_equal(distance_transform_edt(mask)[points], distance_transform_edt(old)[points])
        assert json.loads((a.run / rel / "metrics.json").read_text()) == row
        json.loads((a.run / rel / "branches.json").read_text())
        json.loads((a.run / rel / "paths.json").read_text())
        cases.append(str(rel))
    hashes = {str(p.relative_to(a.run)):v1.sha(p) for p in sorted(a.run.rglob("*")) if p.is_file()}
    artifact_finished = datetime.fromtimestamp((a.run / "summary.json").stat().st_mtime, timezone.utc)
    artifact_interval = (artifact_finished-datetime.fromisoformat(start["started_at_utc"])).total_seconds()
    rec = receipt("E039_receipt_reconciliation_no_producer_rerun")
    rec.update(protocol=m["protocol"], original_run=str(a.run), original_commit=start["commit"],
               original_process_execution="failed_at_final_receipt_exclusive_save",
               original_receipt_preserved=True, retrieval="complete_artifacts_verified",
               cases_verified=cases, protected_inputs_verified=len(m["protected_files"]), output_hashes=hashes,
               summary_file_completed_at_utc=artifact_finished.isoformat(),
               start_to_summary_file_s=artifact_interval,
               original_final_wall_cpu_not_recovered=True, no_producer_rerun=True,
               explanation="save() opens mode x. Initial running receipt exists; final save raises FileExistsError. "
                           "All45 output artifacts and summary exist and were independently reviewed. "
                           "Original running record is historical, not current execution status. "
                           "File timestamps are provenance diagnostics, not exact final wall/CPU timing.",
               execution="reconciliation_succeeded", ended_at_utc=now())
    save(a.run / "completion_reconciliation.json", rec)
    print(json.dumps({k:rec[k] for k in ("original_process_execution", "retrieval", "protected_inputs_verified", "start_to_summary_file_s")}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    run(p.parse_args())
