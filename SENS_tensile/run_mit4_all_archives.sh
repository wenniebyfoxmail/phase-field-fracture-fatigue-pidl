#!/usr/bin/env bash
# Run MIT-4 trajectory analysis on all 4 archives sequentially.
# Output: 4 distinct trajectory_*.npz files + a single (overwritten) figure.
set -e
cd "$(dirname "$0")"

ARCHIVES=(
  # baseline (no hack, no enrichment)
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12"
  # Enriched v1
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_enriched_ansatz_modeI_v1_cycle94_Nf84_real_fracture"
  # Enriched v2 STRONGER
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_enriched_ansatz_modeI_v2_cinit0.1_rcut0.05"
  # E2 hack
  "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_psiHack_m1000_r0.02_cycle91_Nf81_real_fracture"
)

LABELS=("baseline" "enriched_v1" "enriched_v2" "e2_hack")

for i in "${!ARCHIVES[@]}"; do
  echo "=================================================================="
  echo "[$((i+1))/4] ${LABELS[$i]}: ${ARCHIVES[$i]}"
  echo "=================================================================="
  MIT4_ARCHIVE="${ARCHIVES[$i]}" python -u analyze_e2_trajectory.py 2>&1 \
    | tail -25
  echo
done

echo "=================================================================="
echo "All 4 archives done. Distinct trajectory_*.npz files generated."
ls -la trajectory_*.npz 2>/dev/null
echo "=================================================================="
