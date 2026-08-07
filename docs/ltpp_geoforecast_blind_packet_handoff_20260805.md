# LTPP-GeoForecast blind annotation packet handoff

Date: 2026-08-05

## Current decision

`DUAL_ROLES_37_OF_37_LOCKED__PAIRING_REQUIRES_ADJUDICATION`

The qualified `0-50 ft` batch has been frozen as two independently shuffled
packets. It contains 37 unique physical section-date states from six LTPP
sections in each role. Both roles are now fully locked. Pairing has completed,
but no adjudicated ground truth or forecasting result is claimed.

The user subsequently confirmed that the locked nine-map `06-1253` primary
pass was their human annotation. Eight of those maps are byte-identical to the
current climate-complete inventory and were migrated, by source-image SHA-256,
into the human `secondary` role. The excluded 2015 map remains in the old
geometry-only archive because it is outside the current forcing-complete
forecast inventory. The human role subsequently completed the remaining maps.
A final visual review confirmed seven zero-geometry maps as genuinely
reviewed-empty, including one whose source note explicitly reports no distress.
The human `secondary` role is 37/37 locked with 245 geometries. The independent
AI `primary` role is 37/37 locked with 445 geometries. It remained isolated from
the human labels and sealed mapping until its freeze manifest was written.

Human-label migration receipt:

`local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/human_label_migration_receipt.json`

Receipt SHA-256:
`76c068228a529a7babaaf20eebf7c1b0c69bc13072bab8ea090a3ae460bc3e45`

Human locked-role manifest:

`local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/secondary_human_locked_manifest.json`

Manifest SHA-256:
`94f5df136eb06018acaa1a58636c7506e5b1da2ce9fbfedf0b4c8d22867a98ba`

AI locked-role manifest:

`local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/primary_role_freeze_manifest.json`

Manifest SHA-256:
`a78bc99b322881dff80255f2ae54d44ca0da83d87e76b8d94dd5821463ba91ac`

Packet root:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805`

Receipts:

- source multi-section gate SHA-256:
  `22a2a752cb488ec70365ebec098e5b3b5623dffc8fe31b2c3b251240b348bd3b`
- sealed blind-ID/asset mapping SHA-256:
  `a6a6030d881c48fc0c50f7500c86ccceeb29710a2741377fcac8846433f93430`
- input-image hash-manifest SHA-256:
  `72d0e6f0e646c8e79931e9fbb60326b7e833893b00144a9864aee6a3123be742`
- initial-label-template hash-manifest SHA-256:
  `fb8cf95caa271d8c2bd34a26e6f7cc73acde820449d5379b6172bcb05f86d770`

The integrity check passed for all 74 packet images: every copied image hash
matches its qualified source hash, both roles contain the same 37 asset keys,
and neither role contains duplicate keys.

## Independence boundary

The same person or model must not create both passes. A second pass made after
seeing the first is not independent evidence. The annotators must receive only
their assigned role directory and the LTPP distress legend. They must not open:

- the other role directory;
- `sealed_do_not_open_during_annotation/`;
- chronological source maps;
- automatic crack candidates or model outputs.

Run the local workbench for the primary annotator:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "upload code/scripts/ltpp_vector_annotator_server.py" \
  --packet-root \
  local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805 \
  --role primary --port 8765
```

The independent secondary annotator uses the same command with
`--role secondary --port 8766` on a separately controlled session. Each map
must be reviewed and locked.

## Fail-closed pairing

The earlier preflight returned `not_ready` and recorded
`sealed_mapping_read=false` while the AI role was unfinished. After all 74 role
maps were locked, pairing was run with the documented Miniconda interpreter and
recorded `sealed_mapping_read=true`.

After both roles are locked, run:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "upload code/scripts/ltpp_pair_blind_vectorizations.py" \
  --packet-root \
  local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805 \
  --output \
  local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/pairing_result.json
```

Pairing result:

`local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/pairing_result.json`

Result SHA-256:
`42535bdbc7a0a6416e99f58d87c5b44717d64df007f3de6f67fa31381af1a6f3`

- status: `requires_adjudication`
- geometry precision / recall / F1: `0.5913 / 0.8344 / 0.6921`
- matched lines / areas: `96 / 40`
- mean centreline / tip distance: `0.0422 m / 0.0946 m`
- mean area IoU: `0.6385`
- unmatched primary / secondary: `27 / 94` (`121` total)
- matched family disagreements: `1`
- line metrics: pass; area metrics: fail

The default system Python first failed during module import because SciPy was
absent. It did not enter `main`, read the sealed mapping, or create pairing
output; that failure is retained in `pairing_invocation_receipt.json` (SHA-256
`27d80d58770b8786a5bfc93ee6d3d46bb81ec3cb9156d2a5e0dd582b2ec6949a`).

A read-only audit of early locked AI labels identified 17 non-crack semantic
correction candidates: one pumping-arrow backbone and 16 WIM equipment lines.
These features are outside the crack-family pairing metrics and zero locked
labels were modified. The audit is
`primary/semantic_consistency_audit_P001_P020_20260805.md` (SHA-256
`12d53e1eed2a46253d60581d94d3ac8065cea7d657d826d3d2b267f9e7ff696d`).

Pairing alone does not create ground truth. Every unmatched crack geometry and
family disagreement must be adjudicated. Forecast training remains blocked
until the reviewed labels meet the predeclared centreline, tip, and disposition
gate in `ltpp_geoforecast_annotation_forecast_protocol_20260805.md`.

Immutable initial adjudication queue:

`local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudication_queue_initial.json`

Queue SHA-256:
`bb47898b6e85d128b45a2a91a45a974cd059f5e7ed33d6cf4e2a35c885ce3eeb`

The queue contains 139 pending review items: 27 primary-only crack geometries,
94 secondary-only crack geometries, one family disagreement, and 17 non-crack
semantic candidates. It was generated by
`scripts/ltpp_build_adjudication_queue.py`; no disposition is prefilled. Human
progress is stored separately in `adjudication_queue.json`; the generator
refuses to overwrite saved progress unless explicitly forced.

Run the local adjudication workbench:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "upload code/scripts/ltpp_adjudication_server.py" \
  --packet-root \
  local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805 \
  --port 8767
```

Open `http://127.0.0.1:8767/`. The workbench shows three aligned maps for the
same asset-date: an untouched source image, the complete locked AI GeoJSON in
red, and the complete locked human GeoJSON in blue. A gold outer stroke marks
only the current candidate on the relevant annotated panel, so neither role's
geometry can hide the clean visual evidence. Server startup verifies that the
two role images have identical SHA-256 bytes. Reviewers may still decide one
feature at a time, or use reversible map-level actions:

- human reference: accept every human-only crack, reject every AI-only crack,
  and resolve a family conflict to the human label;
- keep both: accept both roles' unmatched cracks while leaving family conflict
  and semantic items pending;
- accept semantics: accept all WIM/pumping corrections on the current map;
- clear asset: remove every saved disposition for the current map.

Each bulk action still writes a separate disposition and timestamp to every
affected queue item. The workbench only writes the working queue; both role
GeoJSON trees remain locked and unchanged. The bulk API was tested against a
temporary queue, including full-map rollback, and the real queue remained
`0/139`.

## Downstream package preparation

The official monthly temperature and precipitation responses needed by all 31
qualified transitions are frozen under:

`local_archive/real_road_acquisition/ltpp_geoforecast_multisection_climate_raw_v1_20260805`

- six sections;
- 178 official `/Data/GetPreviewData` responses;
- raw manifest SHA-256:
  `1df83f1ab6c134a89b48e352c8fe6854263936e7c5ecab28a831dad32cbf3d8b`;
- raw file-list SHA-256:
  `57e4d067e337bbfcdfd2da464bd1d2d9a8e8f740d0f1019063a14ccf5f4667a8`;
- all 44 overlapping `06-1253` responses are byte-identical to the earlier
  independently frozen single-section package.

Leakage-safe source-exclusive, target-inclusive interval features are frozen
under:

`local_archive/real_road_acquisition/ltpp_geoforecast_multisection_interval_climate_v1_20260805`

`interval_climate_features.json` SHA-256:
`5438c99594f0d9c7390912207c7be7cfb4d5200f3b77e9bad24749f007b53e5e`

All 31 intervals have temperature, precipitation, and temperature-change
coverage `1.0`; 25 are development transitions and the final transition of each
section is one of six frozen future-time tests.

The remaining pipeline is already fail-closed:

- `scripts/ltpp_freeze_adjudicated_labels.py` refuses incomplete queues with
  exit `42` and no output;
- `scripts/ltpp_build_adjudicated_transitions.py` refuses a missing adjudicated
  manifest;
- `scripts/ltpp_run_frozen_baselines.py` refuses missing qualified transitions;
- `scripts/ltpp_run_hierarchical_state_space.py` refuses missing baselines.

A temporary test-only automatic-disposition fixture ran through all four code
paths (37 states, 31 transitions) and was then deleted. Its negative model
result is explicitly not scientific evidence and must not be cited; the real
queue remained `0/139` afterward.

## Real adjudication and forecast outcome (2026-08-06)

The historical `0/139` statement above describes the earlier smoke-test
boundary. The human-reviewed queue subsequently reached `139/139` and is the
source of the real frozen artifacts:

- adjudicated labels: `PASS_ADJUDICATED_LABELS_FROZEN`, 37 states, 249 total
  features, 232 crack features, zero per-file hash mismatches; manifest SHA-256
  `6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad`;
- transitions: `PASS_31_ADJUDICATED_LEAKAGE_SAFE_TRANSITIONS`, 25 development
  plus six future-time tests; manifest SHA-256
  `1c38725d23a9cdaea69e3f71b5eaaa6469d02371c85de7a3b2061ba79e92e918`;
- controls: `PASS_FROZEN_BASELINES_COMPLETE`; baseline manifest SHA-256
  `e70564d3e06c81517268c0974845759e7a307769ee3478534cd8f08b8bee2b55`;
- challenger: `RELIABILITY_NEGATIVE`; unseen-section length and new-geometry
  improvements were `-15.63%` and `-6.31%`, joint section wins `0/6`, and
  nominal-90% coverage `0.9355`; decision SHA-256
  `a71e2c87068fc400e12b6e200a6d34c4719545b71819f6f52cdf82650353ecce`.

This is a valid negative benchmark result. It forbids architecture sweeping as
a rescue and leaves persistence as the honest point-forecast control.

## Tool changes made for this packet

The preparer, workbench, and pairer now use dynamic three-digit blind IDs and
the full multi-section asset key rather than the old hard-coded nine-map
`06-1253` inventory. The pairer evaluates crack families while retaining
non-crack and uncertain dispositions in the annotation files.
