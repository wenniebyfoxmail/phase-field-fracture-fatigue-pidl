# exp/sidecar-sampling — experiment snapshot (DO NOT MERGE to main as-is)

This branch is a **reproducibility snapshot** of the sidecar-sampling experiment
as it ran on the Taobo `tip-local-net-18runs-f2d648` checkout (the most recent
active sidecar runs). It is base `origin/main` + an overlay of that checkout's
co-evolved `source/` library and the sidecar runners.

It intentionally preserves co-evolved base-file hooks (model_train.py,
network.py, construct_model.py, fit.py, config.py, ... carry sidecar AND
tip-local / fem-anchor / delta1 hooks that grew together in one checkout).
Purity was deliberately NOT pursued — reproducibility first.

Canonical pieces:
- `source/sidecar_sampling.py` = aeb6a17f (902L, has `cumulative_refine_step`)
- `SENS_tensile/run_sidecar_S2_umax.py` = 4d565fed (same checkout as the lib)
- `SENS_tensile/run_sidecar_S1_tip_oversample_umax.py` (single version, ×12 identical)
- `SENS_tensile/config.py` = the 18runs run config (per-experiment, not for main)

Do NOT merge directly. Future clean integration: cherry-pick
`source/sidecar_sampling.py` + minimal sidecar hooks, re-ported onto current main.
Raw provenance of all uncommitted Taobo code: branch rescue/taobo-raw-20260528-f7ba430.
