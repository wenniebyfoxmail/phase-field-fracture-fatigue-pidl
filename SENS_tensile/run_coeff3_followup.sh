#!/usr/bin/env bash
# Apr 26 follow-up: α-0 + trajectory G1-cols on coeff=3 archives.
#
# Naming discipline:
#   α-0 outputs:        alpha0_results_Umax<U>_coeff3.0.csv
#                       figures/audit/alpha0_fem_vs_pidl_projection_Umax<U>_coeff3.0.png
#   trajectory outputs: trajectory_coeff3_<archive_tail>.npz
#                       (already disambiguated from coeff1 by the
#                        `_coeff{1|3}_` prefix in analyze_e2_trajectory.py)
#
# This is read-only / forward-pass-only on existing trained models. Will
# share Mac CPU with MIT-8 K=5 training (PID 87042) — expect K=5 to slow
# ~30-50% during the ~45 min this takes; net delay <1h.
set -e
cd "$(dirname "$0")"

START_TS=$(date '+%Y-%m-%d %H:%M:%S')
echo "=== Apr 26 coeff=3 follow-up — start $START_TS ==="

# --- α-0 mesh-projection on coeff=3 -----------------------------------------
echo
echo "==> [1/7] α-0 Umax=0.12 coeff=3.0"
python -u alpha0_fem_to_pidl_projection.py 0.12 --coeff 3.0 2>&1 | tail -30

echo
echo "==> [2/7] α-0 Umax=0.08 coeff=3.0"
python -u alpha0_fem_to_pidl_projection.py 0.08 --coeff 3.0 2>&1 | tail -30

# --- trajectory analysis on 5 coeff=3 archives (G1 cols) ---------------------
COEFF3_ARCHIVES=(
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12"
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.11"
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.1"
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N500_R0.0_Umax0.09"
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N600_R0.0_Umax0.08"
)

for i in "${!COEFF3_ARCHIVES[@]}"; do
  echo
  echo "==> [$((i+3))/7] trajectory G1 — ${COEFF3_ARCHIVES[$i]}"
  MIT4_ARCHIVE="${COEFF3_ARCHIVES[$i]}" python -u analyze_e2_trajectory.py 2>&1 | tail -15
done

echo
echo "=== Done. Listing new outputs ==="
ls -la alpha0_results_*coeff3*.csv trajectory_coeff3_*.npz 2>/dev/null | tail -10
echo "=== End $(date '+%Y-%m-%d %H:%M:%S') ==="
