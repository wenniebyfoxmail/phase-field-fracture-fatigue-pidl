#!/usr/bin/env bash
# Run MIT-4 trajectory analysis across 10 archives:
#   5 coeff=1.0 baseline × 5 Umax {0.08, 0.09, 0.10, 0.11, 0.12}
#   5 coeff=3.0          × 5 Umax {0.08, 0.09, 0.10, 0.11, 0.12}
#
# Output: 10 distinct trajectory_*.npz files for the 2D (init_coeff x Umax)
# dose-response analysis. Used to test whether "active driver g·ψ⁺_raw
# method-invariant ~0.4" is truly invariant or just Umax=0.12 artifact.

set -e
cd "$(dirname "$0")"

ARCHIVES=()
LABELS=()

# coeff=1.0 baseline at all 5 Umax (already on Mac, long-standing)
for tag in \
  "_N700_R0.0_Umax0.08" \
  "_N400_R0.0_Umax0.09" \
  "_N350_R0.0_Umax0.1" \
  "_N250_R0.0_Umax0.11" \
  "_N300_R0.0_Umax0.12"; do
  ARCHIVES+=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5${tag}")
  LABELS+=("coeff1_${tag##*_}")
done

# coeff=3.0 at all 5 Umax (extracted from OneDrive Apr 25)
for tag in \
  "_N600_R0.0_Umax0.08" \
  "_N500_R0.0_Umax0.09" \
  "_N400_R0.0_Umax0.1" \
  "_N300_R0.0_Umax0.11" \
  "_N300_R0.0_Umax0.12"; do
  ARCHIVES+=("hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5${tag}")
  LABELS+=("coeff3_${tag##*_}")
done

n=${#ARCHIVES[@]}
echo "=================================================================="
echo "Running MIT-4 trajectory analysis on $n archives"
echo "=================================================================="

for i in "${!ARCHIVES[@]}"; do
  echo "==> [$((i+1))/$n] ${LABELS[$i]}: ${ARCHIVES[$i]:0:80}..."
  if [ ! -d "${ARCHIVES[$i]}" ]; then
    echo "    SKIP: archive directory not found"
    continue
  fi
  if [ ! -f "${ARCHIVES[$i]}/best_models/trained_1NN_0.pt" ] && \
     [ ! -f "${ARCHIVES[$i]}/best_models/checkpoint_step_0.pt" ]; then
    echo "    SKIP: no checkpoints in best_models/"
    continue
  fi
  MIT4_ARCHIVE="${ARCHIVES[$i]}" python -u analyze_e2_trajectory.py 2>&1 \
    | tail -20
  echo
done

echo "=================================================================="
echo "Done. Listing trajectory files:"
ls -la trajectory_*.npz 2>/dev/null
echo "=================================================================="
