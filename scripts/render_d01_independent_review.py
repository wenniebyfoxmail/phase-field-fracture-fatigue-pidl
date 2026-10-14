#!/usr/bin/env python3
"""Compare a frozen independent implementation with existing E015 outputs."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = {4: "#0072B2", 5: "#D55E00", 6: "#009E73"}


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def key(row):
    return int(row["beam"]), int(row["stage_index"]), int(row["transect_id"])


def valid(row):
    return row["valid"].lower() in ("true", "1")


def write(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save(fig, output, stem, question, reading, takeaway, sources, limitations):
    for fmt in ("png", "pdf"):
        fig.savefig(output / f"{stem}.{fmt}", dpi=180, bbox_inches="tight")
    plt.close(fig)
    (output / f"{stem}.md").write_text(f"""# How to read {stem}

## Figure question
{question}

## Data provenance
{sources}
Plotting/comparison script: `scripts/render_d01_independent_review.py`.
Three controlled-experiment DEVELOPMENT beams; independent computation run S03-E018-D01-R002. Same native-pixel units within each beam; no physical mm conversion.

## Visual grammar and panel guide
{reading}

## Key numerical takeaway
{takeaway}

## Limitations and claim boundary
{limitations}
Same-model independent implementation is not a human or physical reference. No new forecast scoring, fitting or threshold tuning. No new held-out specimens.

## Related assets
Exact tables and summary are in this directory; `README_analysis.md` explains the figure set. Same-stem PNG/PDF share this sidecar.
""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--independent", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    original = [r for r in read(a.original / "profile_measurements.csv") if r["role"] == "crack"]
    independent = read(a.independent / "independent_measurements.csv")
    old = {key(r): r for r in original}
    new = {key(r): r for r in independent}
    assert len(old) == len(original) == 168 and len(new) == len(independent) == 168
    assert old.keys() == new.keys()
    comparisons = []
    for k in sorted(old):
        r, s = old[k], new[k]
        assert float(r["load_kN"]) == float(s["load_kN"])
        both = valid(r) and valid(s)
        x = float(r["fwhm_native_px"]) if valid(r) else np.nan
        y = float(s["width_px"]) if valid(s) else np.nan
        comparisons.append(dict(beam=k[0], stage_index=k[1], load_kN=float(r["load_kN"]), transect_id=k[2],
                                original_valid=valid(r), independent_valid=valid(s),
                                original_width_px=x, independent_width_px=y,
                                abs_width_difference_px=abs(y-x) if both else np.nan,
                                validity_match=valid(r) == valid(s)))
    write(a.output / "computation_comparison.csv", comparisons)
    diffs = np.array([r["abs_width_difference_px"] for r in comparisons])
    paired = np.array([r["original_valid"] and r["independent_valid"] for r in comparisons])
    maxdiff = float(np.max(diffs[paired])) if paired.any() else None
    validity_matches = sum(r["validity_match"] for r in comparisons)
    primary = validity_matches == 168 and paired.any() and np.isfinite(diffs[paired]).all() and maxdiff <= 1e-8
    per_beam_computation = []
    for beam in (4, 5, 6):
        group = [r for r in comparisons if r["beam"] == beam]
        delta = np.array([r["abs_width_difference_px"] for r in group if r["original_valid"] and r["independent_valid"]])
        per_beam_computation.append(dict(beam=beam, profiles=len(group), paired_valid=len(delta),
                                        max_width_difference_px=float(np.max(delta)) if len(delta) else None,
                                        median_width_difference_px=float(np.median(delta)) if len(delta) else None))
    fig, ax = plt.subplots(figsize=(7, 5))
    finite_widths = [r["original_width_px"] for r in comparisons if np.isfinite(r["original_width_px"])]
    largest = max(finite_widths) * 1.05 if finite_widths else 1.
    ax.plot([0, largest], [0, largest], "--", color="#777777", lw=1.2, label="Identical computation")
    for beam in (4, 5, 6):
        rows = [r for r in comparisons if r["beam"] == beam and r["original_valid"] and r["independent_valid"]]
        total = sum(r["beam"] == beam for r in comparisons)
        ax.scatter([r["original_width_px"] for r in rows], [r["independent_width_px"] for r in rows],
                   color=COLORS[beam], s=20, alpha=.65, label=f"Beam {beam} | paired {len(rows)}/{total}")
    ax.set(xlim=(0, largest), ylim=(0, largest), xlabel="Original stored-profile half-depth width (native px)",
           ylabel="Independent stored-profile implementation (native px)",
           title="Same-profile computation: all 168 cases")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="upper left", fontsize=9)
    maxtext = f"{maxdiff:.3g}" if maxdiff is not None else "undefined"
    fig.text(.12, .01, f"Max difference {maxtext} px; validity agreement {validity_matches}/168.\n"
             "Software tolerance 1e-8 px; reproduction only, NOT physical accuracy.", fontsize=9)
    fig.subplots_adjust(bottom=.2)
    save(fig, a.output, "computation_agreement", "Does the independent implementation recover the old same-profile widths?",
         "One panel. All 168 cases, coloured by beam, with a 1:1 dashed line and identical axes. No examples selected by outcome.",
         f"Maximum absolute width difference {maxtext} px; paired-valid {int(paired.sum())}/168; validity matches {validity_matches}/168; computation criterion {'met' if primary else 'not met or undefined'} (1e-8 px software tolerance).",
         f"- `{a.original / 'profile_measurements.csv'}` (crack rows only)\n- `{a.independent / 'independent_measurements.csv'}`\n- `computation_comparison.csv` is the exact join.",
         "Agreement on the SAME stored input does not validate sampling, registration, true crack boundaries or future prediction. Scatter overlap is expected; no zero physical uncertainty is inferred.")

    variants = read(a.independent / "location_variants.csv")
    groups = {}
    for row in variants:
        assert row["variant"] not in groups.setdefault(key(row), {})
        groups[key(row)][row["variant"]] = row
    expected = {"baseline", "normal_minus2", "normal_plus2", "tangent_minus2", "tangent_plus2"}
    assert groups.keys() == old.keys() and all(set(g) == expected for g in groups.values())
    sensitive = []
    variant_differences = []
    for k, group in sorted(groups.items()):
        base = group["baseline"]
        shifted = [r for name, r in group.items() if name != "baseline"]
        for name, row in sorted(group.items()):
            available = valid(base) and valid(row)
            variant_differences.append(dict(beam=k[0], stage_index=k[1], load_kN=float(base["load_kN"]), transect_id=k[2],
                                           variant=name, valid=valid(row), paired_baseline_valid=available,
                                           abs_difference_from_baseline_px=abs(float(row["width_px"])-float(base["width_px"])) if available else np.nan))
        complete = valid(base) and all(valid(r) for r in shifted)
        delta = max(abs(float(r["width_px"])-float(base["width_px"])) for r in shifted) if complete else np.nan
        sensitive.append(dict(beam=k[0], stage_index=k[1], load_kN=float(base["load_kN"]), transect_id=k[2],
                              complete_five_variant_support=complete, max_location_difference_px=delta))
    write(a.output / "location_sensitivity.csv", sensitive)
    write(a.output / "location_variant_differences.csv", variant_differences)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True, sharey=True)
    per_beam = []
    for beam, axis in zip((4, 5, 6), axes):
        location = np.array([r["max_location_difference_px"] for r in sensitive if r["beam"] == beam])
        valid_location = location[np.isfinite(location)]
        stages = sorted({k[1] for k in old if k[0] == beam})
        widths = np.array([[float(old[(beam, j, t)]["fwhm_native_px"]) if valid(old[(beam, j, t)]) else np.nan for t in range(1, 13)] for j in stages])
        raw_changes = np.abs(np.diff(widths, axis=0)).ravel()
        changes = raw_changes[np.isfinite(raw_changes)]
        for values, color, style, label in ((valid_location, COLORS[beam], "-", "Max change across +/-2 px locations"),
                                             (changes, "#777777", "--", "Absolute adjacent-stage change")):
            values = np.sort(values[np.isfinite(values)])
            if len(values):
                axis.step(np.r_[0, values], np.r_[0, np.arange(1, len(values)+1)/len(values)], where="post", color=color, ls=style, lw=1.5, label=label)
        axis.set(title=f"Beam {beam}", xlabel="Half-depth width difference (native px)")
        axis.grid(alpha=.18)
        per_beam.append(dict(beam=beam, complete_location_profiles=len(valid_location), total_profiles=len(location),
                             median_max_location_difference_px=float(np.median(valid_location)) if len(valid_location) else None,
                             median_absolute_adjacent_stage_change_px=float(np.median(changes)) if len(changes) else None,
                             available_adjacent_stage_transects=len(changes), total_adjacent_stage_transects=len(raw_changes),
                             variant_coverage={name: dict(valid=sum(valid(r) for r in variants if int(r["beam"]) == beam and r["variant"] == name), total=len(location)) for name in sorted(expected)}))
    axes[0].set_ylabel("Fraction of available cases at or below x")
    axes[-1].legend(loc="lower right", fontsize=8)
    fig.suptitle("Location perturbation versus observed stage change | all cases", fontsize=13)
    fig.text(.03, .01, "Three DEVELOPMENT beams. Position sensitivity, not measurement noise or a confidence interval.\n"
             "All four shifted variants retained; incomplete groups excluded from max statistic and counted separately.", fontsize=9)
    fig.subplots_adjust(bottom=.23, top=.84, wspace=.12)
    save(fig, a.output, "location_sensitivity", "How does a +/-2-native-pixel change in location compare with typical observed stage changes?",
         "Three beam panels, same x/y scales. Solid ECDF: per-profile max absolute difference across ALL four location shifts; dashed ECDF: absolute adjacent-stage changes across all frozen transects. Farther right means larger differences. No independent sample or confidence claim.",
         json.dumps(per_beam, indent=2),
         f"- `{a.independent / 'location_variants.csv'}`\n- `{a.original / 'profile_measurements.csv'}`\n- `location_sensitivity.csv`",
         "Uses manual-quantised source sampling and the fixed first-frame lock; perturbed locations are not repeated physical measurements. Coordinate/registration and illumination uncertainties remain. Different distribution sample counts are shown through the summary rather than interpreted as independent trials.")

    replay = read(a.independent / "source_replay.csv")
    assert len(replay) == 168 and {key(r) for r in replay} == old.keys()
    replay_comparisons = []
    for r in replay:
        s = new[key(r)]
        row = {name: r[name] for name in ("beam", "stage_index", "load_kN", "transect_id")}
        for mode in ("quantised", "continuous"):
            paired_mode = valid(s) and r[f"{mode}_valid"].lower() in ("true", "1")
            row[f"{mode}_paired_valid"] = paired_mode
            row[f"{mode}_width_difference_px"] = abs(float(r[f"{mode}_width_px"])-float(s["width_px"])) if paired_mode else np.nan
            row[f"{mode}_profile_max_abs_diff_gray"] = float(r[f"{mode}_profile_max_abs_diff"])
        replay_comparisons.append(row)
    write(a.output / "source_replay_comparison.csv", replay_comparisons)
    replay_summary = []
    for beam in (4, 5, 6):
        group = [r for r in replay_comparisons if int(r["beam"]) == beam]
        modes = {}
        for mode in ("quantised", "continuous"):
            delta = np.array([r[f"{mode}_width_difference_px"] for r in group if r[f"{mode}_paired_valid"]])
            modes[mode] = dict(paired_valid=len(delta), total=len(group),
                               max_width_difference_px=float(np.max(delta)) if len(delta) else None,
                               median_width_difference_px=float(np.median(delta)) if len(delta) else None,
                               max_profile_difference_gray=max(r[f"{mode}_profile_max_abs_diff_gray"] for r in group))
        replay_summary.append(dict(beam=beam, modes=modes))

    metadata = json.loads((a.independent / "examples.json").read_text())
    assert len(metadata) == 6 and all(int(r["transect_id"]) == 6 for r in metadata)
    with np.load(a.independent / "examples.npz", allow_pickle=False) as z:
        fig, axes = plt.subplots(4, 3, figsize=(12, 9), gridspec_kw={"height_ratios": [1, 1.4, 1, 1.4]})
        for column, beam in enumerate((4, 5, 6)):
            examples = sorted([r for r in metadata if int(r["beam"]) == beam], key=lambda r: int(r["stage_index"]))
            assert len(examples) == 2
            for endpoint, item in enumerate(examples):
                prefix = item["prefix"]
                strip = z[prefix + "_strip"]
                s = z[prefix + "_normal_offsets"]
                stored_deficit = z[prefix + "_stored_deficit"]
                deficit = z[prefix + "_quantised_deficit"]
                left, right, width = z[prefix + "_quantised_crossings_width"]
                image_ax, profile_ax = axes[2*endpoint, column], axes[2*endpoint+1, column]
                image_ax.imshow(strip, cmap="gray", vmin=0, vmax=255, extent=[-60.5,60.5,24.5,-24.5], aspect="auto")
                image_ax.axhspan(-2.5, 2.5, color="#56B4E9", alpha=.18)
                image_ax.plot([-2,2,0,0],[0,0,-2,2], "+", color="#D55E00", markersize=6)
                image_ax.set(title=f"Beam {beam} | {float(item['load_kN']):g} kN | T6", yticks=[-24,0,24], xticks=[])
                image_ax.set_ylabel("Tangent px" if column == 0 else "")
                profile_ax.plot(s, stored_deficit, color="#777777", lw=1.5, label="Stored-input deficit")
                profile_ax.plot(s, deficit, color="#0072B2", lw=1., ls="--", label="Independent source replay")
                half = .5 * float(np.max(deficit[np.abs(s) <= 15]))
                if np.isfinite([left,right,width]).all():
                    profile_ax.hlines(half, left, right, color="#D55E00", linewidth=2)
                    profile_ax.plot([left,right],[half,half], "o", color="#D55E00", markersize=3)
                    profile_ax.text(.97,.95,f"width={width:.2f} px",transform=profile_ax.transAxes,ha="right",va="top",fontsize=9)
                else:
                    profile_ax.text(.97,.95,"Unscorable",transform=profile_ax.transAxes,ha="right",va="top",fontsize=9)
                profile_ax.axhline(0,color="#aaaaaa",lw=.7)
                profile_ax.set(xlim=(-60,60), ylim=(-25,220), xlabel="Normal offset (native px)")
                profile_ax.set_ylabel("Darkness deficit\n(gray levels)" if column == 0 else "")
        axes[1,0].legend(loc="upper left", fontsize=7)
        fig.suptitle("What half-depth width measures | fixed T6 first/last examples", fontsize=14)
        fig.text(.02,.01,"Strips: original fixed-camera gray data in the locked local coordinate frame (no smoothing). Blue band: five sampling lines.\n"
                 "Orange +: four +/-2 px centre variants; orange profile segment: half-depth crossing interval, NOT physical/visible edge truth.",fontsize=9)
        fig.tight_layout(rect=[0,.07,1,.96])
        save(fig,a.output,"half_depth_source_examples","Where is the sampling location and what defines half-depth width?",
             "Three beam columns; first two rows first fixed stage, last two rows last fixed stage. Raw local image strip followed by stored-input and independent-source darkness deficit. Strip normal/tangent axes are native pixels; profile y uses a shared -25..220-gray-level range, not physical energy. Orange profile segment joins half-depth crossings. The image blue band covers the five tangent sampling lines; orange crosses mark all four shifted centres. Examples fixed at T6 before outcomes.",
             "Six prescribed source examples; original stored-input and independently replayed profiles are shown together. Full numeric replay statistics are in summary.json/source_replay_comparison.csv; no outcome-based crop selection.",
             f"- `{a.independent / 'examples.npz'}`\n- `{a.independent / 'examples.json'}` identify all raw photographs and coordinates.\n- The old frozen first-frame geometry is reused; these are source-image resamplings, not synthetic AI images.",
             "The five-line median boundary is not the central-row visible crack boundary; crossings are shown on the profile only. Local strips are image-coordinate crops aligned using shared stored H, not independent physical registration. Sampling step 0.25 px is not claimed physical subpixel accuracy.")

    # Explain old predictions without constructing or scoring a new forecast.
    stored_metrics = read(a.original / "forecast_metrics.csv")
    pairs = sorted({(int(r["beam"]), float(r["origin_kN"]), float(r["target_kN"])) for r in stored_metrics})
    fig, axis = plt.subplots(figsize=(8, 5))
    for i, pair in enumerate(pairs):
        metrics = {r["arm"]: float(r["MAE_native_px"]) for r in stored_metrics
                   if (int(r["beam"]), float(r["origin_kN"]), float(r["target_kN"])) == pair}
        axis.plot([i, i], [metrics["persistence"], metrics["secant"]], color="#bbbbbb", lw=1)
        axis.scatter(i, metrics["persistence"], color="#777777", marker="s", s=40, label="Persistence (no change)" if i == 0 else None)
        axis.scatter(i, metrics["secant"], color="#0072B2", marker="o", s=40, label="Secant (last two stages)" if i == 0 else None)
    axis.set_xticks(range(len(pairs)), [f"B{b}\n{o:g}->{t:g}" for b, o, t in pairs])
    axis.set(ylabel="Stored next-stage MAE (native px), lower is better", xlabel="Beam | origin -> target nominal load (kN)",
             ylim=(0, None), title="Earlier E015 diagnostic: every forecast pair")
    axis.legend(fontsize=9)
    axis.grid(axis="y", alpha=.2)
    fig.text(.1, .01, "Original E015-D01-R001 metrics only; 12 transects per pair, eight pairs / three beams.\n"
             "Observation-updated, retrospective conditional-load DEVELOPMENT task; not new forecast validation.", fontsize=9)
    fig.subplots_adjust(bottom=.24)
    old_summary = json.loads((a.original / "summary.json").read_text())
    secant_better = sum(next(float(r["MAE_native_px"]) for r in stored_metrics if (int(r["beam"]),float(r["origin_kN"]),float(r["target_kN"])) == p and r["arm"] == "secant") < next(float(r["MAE_native_px"]) for r in stored_metrics if (int(r["beam"]),float(r["origin_kN"]),float(r["target_kN"])) == p and r["arm"] == "persistence") for p in pairs)
    save(fig, a.output, "earlier_forecast_explanation", "What does the previously reported secant advantage mean?",
         "One panel includes all eight original origin-target pairs. Gray squares are persistence, blue circles secant; lower y is better. Connecting lines pair methods on the same 12 transects. No newly computed prediction/error is used.",
         f"Original equal-beam MAE: persistence {old_summary['equal_beam_MAE_native_px']['persistence']:.6f}, secant {old_summary['equal_beam_MAE_native_px']['secant']:.6f} native px; improvement {-100*old_summary['relative_change_vs_persistence']['secant']:.3f}%. {secant_better}/{len(pairs)} original pairs favour secant.",
         f"- `{a.original / 'forecast_metrics.csv'}`\n- `{a.original / 'summary.json'}`",
         "Target is the algorithm's half-depth observable, not independently measured physical opening. These beams and outcomes were already viewed. Availability of the next nominal load at prediction origin is not independently established; interpret as conditional continuation, not deployed future-load forecasting.")
    summary = dict(experiment_id="S03-E018-D01", primary_same_profile_computation_met=bool(primary),
                   profiles=168, validity_matches=validity_matches, max_width_difference_px=maxdiff,
                   paired_valid_profiles=int(paired.sum()), per_beam_computation=per_beam_computation,
                   complete_location_profiles=sum(r["complete_five_variant_support"] for r in sensitive),
                   per_beam=per_beam, source_replay=replay_summary,
                   coordinates=json.loads((a.independent / "coordinate_summary.json").read_text()),
                   new_forecast_scores=False, physical_accuracy_validated=False)
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
