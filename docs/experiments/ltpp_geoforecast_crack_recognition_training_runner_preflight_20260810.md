# LTPP non-destructive recognition training-runner preflight

Status: `PASS_RUNNER_PREFLIGHT_NO_FIT__TRAINING_AUTHORIZATION_REQUIRED`  
Date: 2026-08-10  
Optimizer steps: `0`

## Result

The exact Taobo runner is now frozen at SHA-256
`4022096e8ab47d17770e2c58498e3c13a3f6007711f8101ab7620a25aecc5c33`.

The Mac-safe preflight reverified all frozen source/data/no-fit hashes, all 37
maps, the six section folds, the seven zero-crack IDs, and the 27,473-parameter
two-channel architecture without a real-image model forward pass or saved
weights.

The runner rejects both a missing authorization and the pending authorization
template with exit code 1 before creating an output directory. Its training
path additionally requires:

- Linux with `LTPP_PRODUCER_ID=taobo`;
- the Taobo `/mnt/data2/drtao/wennie` identity root;
- exactly one numeric `CUDA_VISIBLE_DEVICES` value and one visible CUDA device;
- an output below `/mnt/data2/drtao/pidl_archives` that does not yet exist;
- an approval JSON whose complete frozen specification and runner hash match;
- an absent one-use authorization claim.

Immediately before training, the runner atomically creates the claim with
`O_EXCL`. A crash or partial attempt leaves the claim in place and therefore
prohibits restart, fold rerun, rescue fit, or reuse of the same authorization.

## Assets

- runner: `scripts/ltpp_run_nondestructive_crack_recognition_taobo.py`
- pending authorization schema:
  `docs/reviews/ltpp_geoforecast_crack_recognition_training_authorization_template_20260810.json`
- receipt:
  `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_training_runner_preflight_20260810/runner_preflight_receipt.json`

## Authorization boundary

This is a tooling/preflight pass only. Training remains prohibited until the
external reviewer explicitly approves this exact runner SHA-256.
