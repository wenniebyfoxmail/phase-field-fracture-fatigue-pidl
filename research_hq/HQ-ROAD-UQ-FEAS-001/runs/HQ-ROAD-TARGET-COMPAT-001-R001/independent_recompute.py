"""Independent stdlib recomputation of the frozen D4 CSV decision."""
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
RADII = [0, 1, 2, 3, 4, 6, 8, 12, 16]
SOURCES = ["CRACK500", "CFD", "GAPS384"]


def group_mean(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row["group"]].append(float(row[key]))
    return statistics.mean(statistics.mean(values) for values in groups.values())


with (ART / "per_mask_metrics.csv").open() as f:
    rows = list(csv.DictReader(f))
summary = json.loads((ART / "source_summary.json").read_text())
assert len(rows) == 2903
assert Counter(r["source"] for r in rows) == Counter({"CRACK500": 2401, "CFD": 118, "GAPS384": 384})
assert sum(r["source"] == "GAPS384" and r["empty"] == "True" for r in rows) == 2
assert all(math.isfinite(float(r["oracle_dice"])) for r in rows)

fit_scores = {}
source_radius = {}
for source in SOURCES:
    fit = [r for r in rows if r["source"] == source and r["split"] == "fit" and r["empty"] == "False"]
    fit_scores[source] = {radius: group_mean(fit, f"dice_r{radius}") for radius in RADII}
    source_radius[source] = max(RADII, key=lambda radius: (fit_scores[source][radius], -radius))
global_scores = {radius: statistics.mean(fit_scores[source][radius] for source in SOURCES) for radius in RADII}
global_radius = max(RADII, key=lambda radius: (global_scores[radius], -radius))
assert global_radius == summary["global_radius_px"] == 1

recomputed = {"rows": len(rows), "global_radius_px": global_radius, "sources": {}}
all_source_ok = True; all_global_ok = True
for source in SOURCES:
    eval_rows = [r for r in rows if r["source"] == source and r["split"] == "eval" and r["empty"] == "False"]
    radius = source_radius[source]
    oracle = group_mean(eval_rows, "oracle_dice")
    src = group_mean(eval_rows, f"dice_r{radius}")
    glob = group_mean(eval_rows, f"dice_r{global_radius}")
    src_ret, glob_ret = src / oracle, glob / src
    src_ok = oracle >= .75 and src_ret >= .9
    glob_ok = glob_ret >= .95
    all_source_ok &= src_ok; all_global_ok &= glob_ok
    expected = summary["sources"][source]
    assert radius == expected["source_radius_px"]
    for observed, key in [(oracle, "oracle_eval_mean_dice"), (src, "source_eval_mean_dice"),
                          (glob, "global_eval_mean_dice"), (src_ret, "source_oracle_retention"),
                          (glob_ret, "global_source_retention")]:
        assert abs(observed - expected[key]) < 1e-12, (source, key, observed, expected[key])
    recomputed["sources"][source] = {"source_radius_px": radius, "oracle_eval_mean_dice": oracle,
                                      "source_eval_mean_dice": src, "global_eval_mean_dice": glob,
                                      "source_oracle_retention": src_ret, "global_source_retention": glob_ret,
                                      "source_renderer_adequate": src_ok, "global_renderer_adequate": glob_ok}
decision = ("ROUTE_A_COMMON_RENDERER_NUMERICALLY_SUPPORTED" if all_source_ok and all_global_ok
            else "ROUTE_B_SOURCE_SPECIFIC_RENDERERS_NUMERICALLY_SUPPORTED" if all_source_ok
            else "STOP_CENTRELINE_WIDTH_RENDERER_NOT_ADEQUATE")
assert decision == summary["geometry_decision"]
recomputed["decision"] = decision
(ART / "independent_recompute.json").write_text(json.dumps(recomputed, indent=2))
print(json.dumps(recomputed, indent=2))
