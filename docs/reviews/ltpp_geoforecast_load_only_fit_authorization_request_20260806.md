# Request: authorize frozen load-only posterior fit

The authorized outcome-free input preflight for the LTPP load-only track has
completed and passed.

Please authorize exactly the following, or reject with the minimum required
changes:

`APPROVE_LOAD_ONLY_POSTERIOR_FIT`

## Sealed input state

- 29 transitions across six sections;
- only excluded transition: `06-1253-T07`;
- 24 development + 5 future-time rows;
- G = source crack length, source crack area, forecast horizon;
- G+L = G plus `TRF_TREND.ANNUAL_ESAL_TREND` from the latest complete
  pre-source calendar year under source-active construction;
- no climate, moisture, structure, FWD, AADTT, alternate traffic fields,
  interactions, splines, PCA, or feature selection;
- primary validation: LOSO; future-time split secondary;
- endpoint: `max(0, target_crack_length - source_crack_length)`;
- nominal 90% coverage gate: exactly 25--27 of 29 rows;
- no outcome field was present or read during preflight.

## Receipts

- input manifest:
  `local_archive/real_road_acquisition/ltpp_geoforecast_load_only_input_preflight_v1_20260806/load_only_input_manifest.json`;
- feature table SHA-256:
  `c332037d208baaa23c22288008dc629736f4822549bde6089f25fa6c175bd02e`;
- T1 join receipt SHA-256:
  `eca8c035572524ee9a7aa797d8e2a0171c9e17897a7f4f28d529d9e62f7d4a44`;
- split receipt SHA-256:
  `0303868dbd998e8650d72d22bfe95be6f5a0f62416363210ffc186e8823ed452`;
- preflight runner SHA-256:
  `4067ef7d0a7abb554441e14cbb1c9dde86d5a543b4aa0bacb0504abf1efa50fa`.

This request authorizes no architecture search, no feature changes, no row
changes, no threshold changes, and no exploratory rescue.
