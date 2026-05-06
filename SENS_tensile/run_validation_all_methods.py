#!/usr/bin/env python3
"""
run_validation_all_methods.py — sweep validate_pidl_archive.py across all
canonical PIDL method archives + consolidate to a Ch2 supplementary table.

Methods covered (Umax=0.12 unless noted):
  - baseline (no interventions)
  - Williams v4 (input enrichment)
  - Fourier v1 (random spectral)
  - Enriched Ansatz v1 (output XFEM-like, c_init=0.01)
  - spAlphaT b0.8 r0.03 (narrow spatial α_T)
  - Golahmar+narrow (Dir 6.2)
  - Oracle 0.12 (zone=0.02)
  - Cross-Umax: baseline 0.11, Oracle 0.10/0.11

Outputs:
  validation_table_all_methods.csv  — one row per archive × test
  validation_table_all_methods.txt  — human-readable summary
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
VALIDATE_PY = HERE / "validate_pidl_archive.py"

# Canonical archive list (curated; method × Umax matrix)
ARCHIVES = [
    # method label, archive directory name
    ("baseline 0.12",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12"),
    ("Williams v4 0.12",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_williams_std_v4_cycle87_Nf77_real_fracture"),
    ("Fourier v1 0.12",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_fourier_nf16_sig1.0_v1_cycle94_Nf84_real_fracture"),
    ("Enriched v1 0.12",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_enriched_ansatz_modeI_v1_cycle94_Nf84_real_fracture"),
    ("spAlphaT b0.8 r0.03",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.8_r0.03_cycle90_Nf80_real_fracture"),
    ("Golahmar+narrow 0.12",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_golahmar_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.8_r0.03_cycle164_Nf154_real_fracture"),
    ("Oracle 0.12 (zone=0.02)",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_oracle_zone0.02"),
    ("Oracle 0.11 (zone=0.02)",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.11_oracle_zone0.02"),
    ("baseline 0.11",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11"),
    ("baseline 0.08",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.08"),
]


def run_one(archive_path: Path) -> dict | None:
    """Run validate_pidl_archive on one archive, return parsed JSON results."""
    if not archive_path.is_dir():
        return None
    proc = subprocess.run(
        [sys.executable, str(VALIDATE_PY), str(archive_path)],
        capture_output=True, text=True, timeout=300,
    )
    json_out = archive_path / "best_models" / "validation_report.json"
    if not json_out.is_file():
        return None
    return json.loads(json_out.read_text())


def main():
    print("=" * 110)
    print(f"{'method':<28} | {'V1':<5} {'V2':<5} {'V3':<5} {'V4':<5} {'V5':<5} {'V6':<5} {'V7':<5} {'V8':<5}")
    print("-" * 110)

    rows = []
    for label, name in ARCHIVES:
        archive = HERE / name
        results = run_one(archive)
        if results is None:
            print(f"{label:<28} | (archive missing or run failed: {name[:50]}…)")
            continue

        # Build per-test status badge
        badges = {}
        details = {}
        for t in results:
            tname = t.get('test', '?')
            # Map test name to slot (V1..V8)
            slot = None
            for vk in ('V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8'):
                if tname.startswith(vk + '_'):
                    slot = vk
                    break
            if slot is None:
                continue
            status = t.get('status', '?')
            if status == 'PASS':
                badges[slot] = '✓'
            elif status == 'PASS-by-construction':
                badges[slot] = '✓¹'
            elif status == 'WARN':
                badges[slot] = '~'
            elif status == 'FAIL':
                badges[slot] = '✗'
            elif status == 'SKIP':
                badges[slot] = '–'
            else:
                badges[slot] = '?'
            details[slot] = t

        line = f"{label:<28} | "
        for vk in ('V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8'):
            line += f"{badges.get(vk, '?'):<5} "
        print(line)

        rows.append({"label": label, "name": name, "results": results, "badges": badges, "details": details})

    # Write consolidated CSV
    out_csv = HERE / "validation_table_all_methods.csv"
    out_txt = HERE / "validation_table_all_methods.txt"

    with open(out_csv, 'w') as f:
        f.write(
            "method,archive,"
            "V1,V2,V3,V4,V5,V6,V7,V8,"
            "V4_alpha_even,V4_ux_corr_even,V4_vy_corr_odd,V4_dalpha_dy,"
            "V4_rms_alpha,V4_rms_ux_corr,V4_rms_vy_corr,V4_rms_dalpha_dy,"
            "V1_detail,V3_K_med,V5_alpha_max,V6_f_min,V7_rel_sxx,V8_log_ratio\n"
        )
        for r in rows:
            badges = r['badges']
            details = r.get('details', {})
            v1d = details.get('V1', {})
            v3d = details.get('V3', {})
            v4d = details.get('V4', {})
            v5d = details.get('V5', {})
            v6d = details.get('V6', {})
            v7d = details.get('V7', {})
            v8d = details.get('V8', {})
            f.write(
                f"{r['label']},{r['name'][:60]},"
                f"{badges.get('V1','?')},{badges.get('V2','?')},"
                f"{badges.get('V3','?')},{badges.get('V4','?')},"
                f"{badges.get('V5','?')},{badges.get('V6','?')},"
                f"{badges.get('V7','?')},{badges.get('V8','?')},"
                f"{v4d.get('status_alpha_even', '')},"
                f"{v4d.get('status_ux_corr_even', '')},"
                f"{v4d.get('status_vy_corr_odd', '')},"
                f"{v4d.get('status_dalpha_dy_centerline', '')},"
                f"{v4d.get('rms_alpha_skew', '')},"
                f"{v4d.get('rms_ux_corr_even', '')},"
                f"{v4d.get('rms_vy_corr_odd', '')},"
                f"{v4d.get('rms_dalpha_dy_centerline', '')},"
                f"{v1d.get('max_rel_increase_E_el', '')},"
                f"{v3d.get('K_r1_med', '')},"
                f"{v5d.get('alpha_max_at_Nf', '')},"
                f"{v6d.get('f_min_at_Nf_global', '')},"
                f"{v7d.get('rel_residual_sxx', '')},"
                f"{v8d.get('delta_log10', '')}\n"
            )

    print()
    print(f"Saved: {out_csv}")
    print(f"  Legend: ✓=PASS  ✓¹=PASS-by-construction  ~=WARN  ✗=FAIL  –=SKIP/no-data")


if __name__ == "__main__":
    main()
