# LTPP cross-state acquisition track

Status: `PARTIAL_TWO_NEW_CANDIDATES__FULL_GATE_FAILED__NO_FIT`

## Mechanism question

Can official LTPP InfoPave records yield a larger, climate-diverse asset-time
panel with repeated fixed-panel distress maps and auditable construction/reset
boundaries, before any forecasting model is proposed?

## Five-question gate

1. Success changes only the data-availability claim; failure means LTPP cannot
   supply the required expansion under the frozen criteria.
2. The cheaper diagnostic is the official Viewer metadata inventory. It must
   run before image download, rectification, climate/table joins, or fitting.
3. The minimum primary asset is one cross-state candidate table plus raw JSON
   and SHA-256 receipts in `local_archive/real_road_acquisition/`.
4. The next bounded asset is one nominal `0-50 ft` map per survey for selected
   candidates, followed by the unchanged regular-grid gate.
5. This document is the canonical registry endpoint; update
   `docs/research_frontier.md` only if a new panel actually passes the full
   acquisition gate.

Decision: `LAUNCH_ACQUISITION_ONLY__NO_MODEL_FIT`.

## Frozen first-stage criteria

- Official InfoPave SDR 39 Viewer endpoints.
- State inventory: Minnesota (27), Texas (48), Florida (12), New York (36),
  Colorado (08).
- Asphalt construction description.
- At least five non-empty surveys inside one construction number.
- Identical ordered nominal panel labels within that construction.
- No relaxation after results.

The inventory pass does not prove printed station identity, registration,
distress semantics, climate/traffic/structure/FWD coverage, or absence of
unrecorded maintenance.

## Bounded second-stage candidates

Selected before downloading images, using survey count, cross-state diversity,
and explicit inclusion of both original and post-maintenance constructions:

| State | Section | Inventory surveys | Rationale |
|---|---|---:|---|
| Colorado | `08-1053` | 14 in construction 1; 8 in construction 2 | long trajectory plus explicit maintenance/rehabilitation boundary |
| Minnesota | `27-1028` | 9 | cold-climate original asphalt construction |
| Minnesota | `27-6251` | 9 in construction 1; 6 in construction 3 | explicit crack-sealing boundary |
| Florida | `12-1030` | 12 | warm/wet post-shoulder-maintenance construction |
| Florida | `12-0901` | 8 | warm/wet post-mill-and-overlay construction |
| Texas | `48-1122` | 14 | long original asphalt construction |
| Texas | `48-1060` | 11 | independent original asphalt construction |
| Texas | `48-A502` | 13 | explicit overlay/shoulder-restoration construction |

Second-stage pass requires every retained date in a single declared
construction to pass the unchanged regular-grid detector and then pass manual
printed-station review. Climate, traffic, structure/FWD, and timeline/reset
joins occur only after that geometry gate.

## Claim boundary

This is acquisition evidence only. It authorizes no STID, APT, GNN, PIDL, FEM,
or other forecast training. Viewer labels and automatic rectification are not
crack truth and do not reopen the closed LTPP 2-D registration claim.

## Batch 2 amendment (frozen before download)

Batch 1 produced only two all-date automatic geometry passes, below the fixed
target of five. A second and final bounded batch is selected from the already
frozen inventories without changing any threshold:

- Florida: `12-0903`, `12-0902`, `12-0959`;
- Texas: `48-1077`, `48-3739`, `48-9005`;
- Minnesota: `27-0508`, `27-0509`.

Selection uses remaining rank by survey count while retaining multiple states.
No Batch 1 failure is deleted or reclassified. Stop after Batch 2 if the total
all-date geometry+climate count remains below five.

## Terminal result (2026-08-12)

- Official Viewer inventory audited 476 sections across five states with zero
  endpoint failures: Minnesota 82, Texas 217, Florida 83, New York 26, and
  Colorado 68.
- Sixty-six constructions passed the metadata-only repeated-map inventory:
  Minnesota 5, Texas 47, Florida 13, New York 0, and Colorado 1.
- Two frozen image batches covered 16 selected sections, 18 construction
  trajectories, and 162 nominal `0-50 ft` survey images.
- The unchanged regular-grid detector passed every date for only two
  trajectories: `27-6251 c3` (`6/6`) and `08-1053 c2` (`8/8`). All other
  trajectories remain recorded as failures or partial diagnostics; no dates
  were removed to manufacture a pass.
- Contact-sheet review confirmed printed `0--50 ft` station coordinates on all
  retained dates for the two automatic passes.
- Both candidates have continuous official temperature/precipitation coverage,
  daily-traffic availability, layer records, and FWD master/location records.
  Sixty-two monthly climate request/response pairs were frozen with complete
  12-month coverage.
- `27-6251` has a complete seven-table raw package, including 67,744
  `MON_DEFL_DROP_DATA` rows. For `08-1053`, InfoPave returned the same
  `Invalid SQL statement` internal error on two attempts to page
  `MON_DEFL_DROP_DATA`; traffic, structure, FWD master, and FWD location tables
  remain available, but numeric FWD drop-series completeness is blocked.
- `27-6251` exposes no humidity. `08-1053` exposes ambient humidity, which is
  not pavement moisture. Neither route passes the full mechanics/moisture
  trajectory gate.

### Decision

`PARTIAL_PASS_TWO_NEW_SOURCE_AVAILABLE_CANDIDATES__FAIL_TARGET_OF_FIVE`

The result expands the acquisition inventory with two climate-diverse,
post-maintenance candidate trajectories. It does not authorize annotation,
forecast fitting, STID/APT, 2-D crack motion, or a deployable prediction claim.
The bounded independent-control preflight produced an immutable blind packet
and external approval for optional two-person Tier B collection. For the
current stage, the owner instead selected a separate single-owner line
annotation route: 17 lines × two clicks plus eight classification-only local
spot checks per map, followed by mechanical derivation of 66 points. This is not a
registration pass: no independent consensus exists and no transform may be
fit. The initial cropped line interface was rejected unused when it hid the
2001 Colorado left boundary; the approved replacement displays the complete
source and uses the owner's four outer lines as the no-fallback frame. If
owner-level source observability is inadequate, switch acquisition
effort to MnROAD / a prospective pilot. No further LTPP state sweep is
authorized by this track. See
`ltpp_cross_state_single_owner_line_annotation_result_20260812.md` and
`ltpp_cross_state_spatial_registration_tier_b_packet_result_20260812.md`.

### Primary receipts

- Cross-state geometry/climate gate:
  `local_archive/real_road_acquisition/ltpp_cross_state_geometry_climate_gate_20260812/multisection_gate.json`,
  SHA-256 `935fd944fdb86521a5b958d2f98bc4a053806deca2715c49b28c01c14a672262`.
- Monthly climate manifest:
  `local_archive/real_road_acquisition/ltpp_cross_state_climate_raw_20260812/climate_raw_manifest.json`,
  SHA-256 `a9ffce36364f385b93070b74337838efaa7b0ae848960abf79417bfa1c38540c`.
- Complete Minnesota FWD drop table:
  `local_archive/real_road_acquisition/ltpp_cross_state_enriched_raw_20260812/27-6251/MON_DEFL_DROP_DATA.csv`,
  SHA-256 `557aae2c95c78e3eae92355fdafdc4a93a97762adade44180770a58fd67aa837`.
