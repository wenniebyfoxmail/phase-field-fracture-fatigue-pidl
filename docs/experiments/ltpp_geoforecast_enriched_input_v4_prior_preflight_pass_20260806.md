# LTPP enriched-input v4 prior-predictive preflight result

Date: 2026-08-06

Decision: `PASS_PRIOR_PREDICTIVE_PREFLIGHT__FIT_AUTHORIZATION_REQUIRED__NO_FIT`

## Authorization and immutable inputs

ChatGPT Pro returned `APPROVE_V4_PRIOR_PREFLIGHT_ONLY` for the exact prior
amendment SHA-256
`d8fa9840581b1aa0ad9a19a11bd892fdf3ac6d5325ecacb1454f2c9a7f955565`.
The approval receipt SHA-256 is
`2e7013b3dd3bf10bf795c8586939d21f36d293f7fe52ea128579ad5548b70bac`.

The run used:

- frozen 30x11 feature manifest SHA-256:
  `e17313471628e28573c62f27c84f1fdca197bb20e6d477d28afb60358989aaf3`;
- fixed split receipt SHA-256:
  `1cb574e0d9e7cb2976f043ad5c83b718c017bff9dff508f1798b603aac4e4a2b`;
- amended priors `alpha ~ Normal(0,1)`, `beta ~ Normal(0,0.1)`,
  `sigma ~ HalfNormal(0.5)`, and `sigma_s ~ HalfNormal(0.5)`;
- unchanged 500 draws, deterministic seeds, `100.189733 m` cap, and
  at-most-1% row-level exceedance gate;
- runner SHA-256:
  `b917bb710010328fc50d3d1c706d75411d348a7f7475ce7ca6dd864f7657f933`.

Both amendment and approval hashes were checked by the runner before output
creation. This was the only execution of the approved v4 prior amendment.

## Result

All 28 preregistered model/design checks passed.

| model | fold exceedance range | fold p95 range (m) | largest individual draw (m) |
|---|---:|---:|---:|
| M0 | 0.0000--0.00233 | 6.47--8.56 | 7,695.00 |
| M1 | 0.00120--0.00314 | 7.00--9.99 | 178,684.35 |
| M2 | 0.00050--0.00400 | 6.65--9.73 | 19,693.21 |
| M3 | 0.00100--0.00350 | 6.90--11.16 | 179,894.66 |

- failed model/folds: none;
- prior-predictive report SHA-256:
  `8689fec9d6644bc3f62a77cdcae3e1409139b5aad095498cb578b8cabde1d644`;
- outcome fields read: none;
- posterior fit performed: false;
- held-out enriched prediction performed: false;
- ablation scoring performed: false.

The local immutable receipt is:

`local_archive/real_road_acquisition/ltpp_geoforecast_enriched_input_v4_prior_preflight_20260806/prior_predictive/prior_predictive_report.json`

## Interpretation boundary

This result proves only that the amended prior distribution passes the
predeclared aggregate physical-scale sanity gate. It does not show predictive
accuracy or incremental information value.

The table discloses rare very large draws. They do not fail the frozen gate
because each model/fold remains below 1% above the cap. The maximum or gate must
not be changed after inspection. These tails must remain visible in reporting
and can be considered by the independent fit-authorization reviewer.

## Next action

Request separate explicit authorization for the frozen posterior-fitting and
ablation protocol. Do not fit outcomes until that authorization is recorded.
