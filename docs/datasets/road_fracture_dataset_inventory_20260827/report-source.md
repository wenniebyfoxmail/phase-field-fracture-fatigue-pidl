# Real-road fracture dataset inventory and evidence map

**Snapshot:** 2026-08-27  
**Scope:** data that can support real-world road-crack forecasting, physics-anchor calibration, or observation-operator pretraining.  
**Canonical capability table:** `dataset_inventory.csv`  
**Canonical test/metadata audit:** `route_test_audit.csv`

## Bottom line

No currently possessed dataset closes the full same-asset, same-time gate across repeated registered crack geometry, load/traffic, weather/temperature, moisture, material/structure, mechanical response, and maintenance/censoring.

The defensible design is therefore not to merge every dataset into one fictitious trajectory. It is a three-part evidence system:

1. **Trajectory carrier:** local LTPP sections and PaveTrack provide real-road evolution observations, but with different missing drivers and registration limits.
2. **Mechanics bridge:** MnROAD/WesTrack, if their joins qualify, connect traffic and environment to response; laboratory DIC datasets calibrate observation-to-driving-state mappings but do not prove pavement transfer.
3. **Prospective closure:** a deliberately instrumented road pilot is the only identified route that can close all mandatory variables on the same asset-time key.

This supports the earlier two-tier idea—few expensive physics anchors plus many cheap operational observations—with two important corrections. First, the anchor and carrier datasets must remain separate evidence roles; their variables cannot be silently concatenated as if measured on the same road segment. Second, periodic standardized FWD should be treated as an **active probe** inside the cheap operational tier: it informs an effective structural-state posterior, not crack-tip energy.

## What is obtainable now

| Priority | Dataset or route | What is actually obtainable | Proper role | Main missing link |
|---|---|---|---|---|
| 1 | Local six-section LTPP packet | 37 adjudicated geometry states, 31 transitions and climate-complete prefixes; traffic/FWD/structure are only partial acquisition fields | Present real-road baseline and section-holdout testing | Moisture; complete traffic/FWD joins and censoring; qualified dense registration |
| 2 | PaveTrack PD | Public repeated images and masks across 165 locations; local manifest audit exists | High-cadence morphology and perception learning | Metric registration and physical drivers |
| 3 | MnROAD | Public portal plus a well-defined request route; locally only traffic workbook and sensor layout | Best near-term field physics-anchor candidate | Synchronized numeric sensor series and crack geometry are not possessed |
| 4 | CAMHighways | Public sample and full dataset by request; georeferenced surface, defect and GPR products | Multimodal current-state/registration pretraining | No verified temporal trajectory or load history |
| 5 | Public laboratory DIC | Zenodo 11945905, CrackMNIST, Mendeley fatigue DIC, and staged concrete images | Calibrate DIC/geometry to response or driving-state proxies | Domain transfer; identifiability; full road environment |

The complete availability and claim boundary for every candidate is recorded in the CSV rather than compressed into a single ranking.

## Which routes have actually been tested?

Here, “tested” means a local file, sample, schema or preregistered gate was executed. Confirming that a DOI, paper or facility page exists is recorded separately as public-metadata verification; it is not a data test.

| Evidence level | Count | Routes | Meaning |
|---|---:|---|---|
| `T3_STRICT_LOCAL_*` | 4 | LTPP local six-section packet; PaveTrack PD; CrackMNIST; iDIC Sample 1 | Possessed/selected files were inspected and a scientific or qualification gate was executed |
| `T2_LOCAL_FILE_COVERAGE_AUDIT` | 1 | MnROAD Cell 22 | Local files were inventoried and their join coverage tested, but the required synchronized numeric trajectory is absent |
| `T1_PUBLIC_*` | 12 | WesTrack; CAMHighways; RDD2022; RMDCrack; 3DCrack; ConTrack; AA2024-T3 DIC; Mendeley DIC; multi-temporal concrete; NCCD-PF; NCAT; Virginia Smart Road | Only repository, paper or facility metadata has been verified; no local data-level result exists |
| `T0_DESIGNED_NOT_COLLECTED` | 1 | Cambridge/National Highways prospective pilot | A closure protocol exists, but no observations have been collected |

The test outcomes materially narrow the route map:

- **LTPP:** supports `M0-M1` persistence/observation-only geometry baselines and section/time splits. The frozen `06-1253` 2-D registration gate failed (`2/8` dates qualified), so it does not support current-carrier tip/position forecasting. `M2/M3` remain acquisition candidates, not demonstrated joins.
- **PaveTrack:** supports scene-level temporal morphology and segmentation. Its bounded location-10 registration gate failed, so it cannot support metric tip displacement, initiation or a physical state trajectory.
- **CrackMNIST:** supports an `M4` laboratory observation-operator anchor. A no-fit diagnostic found a crack-tip localization signal in a DIC-gradient energy proxy, but chronology, fatigue history, RUL and road transfer remain blocked.
- **iDIC Sample 1:** is a useful negative control/tooling sample only. It is a synthetic rigid shift with zero strain-energy proxy, not fracture DIC.
- **MnROAD:** supports acquisition design only at present. The possessed workbook/layout files do not contain the synchronized crack-load-temperature-moisture-response trajectory needed for `M3/M5`.

`route_test_audit.csv` gives all 18 rows with the exact tested scope, obtained metadata, result, supported model rung, blocked claim and next gate. This prevents a source-page claim from being promoted into a local empirical result.

## Recommended combination—not a dataset fusion

| Scientific component | Data source | Learned or tested object | Must not be claimed |
|---|---|---|---|
| Road observation model | PaveTrack, CAMHighways, RMDCrack, RDD2022 | image/3D/GPR to crack geometry and uncertainty | causal deterioration or energy |
| Road trajectory baseline | LTPP local sections | future geometry conditional on observed history and available covariates | moisture-complete mechanism |
| Field response bridge | MnROAD or WesTrack after schema qualification | load/environment to response-state likelihood | qualified until same-key joins are demonstrated |
| Laboratory physics bridge | DIC fatigue/concrete datasets | response/geometry to effective driving-state proxy | pavement-specific latent parameters without transfer evidence |
| Prospective validation | new Cambridge/National Highways pilot | calibrated forecast on held-out future times and assets | retrospective fit as prospective success |

The recommended operational input is therefore registered RGB/3D history, weather, traffic proxy, maintenance state, and periodic standardized FWD. The FWD basin updates effective compliance/support/degradation states; it is not a direct measurement of (J) or (G).

The model-level decomposition can be written as

\[
p(c_{t+1}\mid o_{0:t}) = \int p(c_{t+1}\mid z_t,m)\,p(z_t,m\mid o_{0:t})\,dz_t\,dm,
\]

where cheap observations \(o\) estimate a latent effective state \(z\), while the transition law is constrained by qualified physics-anchor data. Missing load or fatigue is therefore **marginalized with uncertainty**, not declared absent. If load/exposure changes outside the training support, the bypass is invalid and the model must abstain or widen uncertainty.

## Can energy be inferred from data?

Only an **effective driving-state posterior** is defensible from sparse observations. Direct unique inversion of \(G\), \(J\), \(G_c\), length scale, fatigue history, and moisture degradation is generally non-identifiable when load, boundary conditions, constitutive response, or full-field displacement are missing.

Useful inference levels are:

1. With synchronized load, geometry and full-field displacement/strain: estimate a J-/energy-release-rate proxy with uncertainty and boundary-sensitivity checks.
2. With load plus sparse response: assimilate an effective damage-driving state, calibrated against the full-field anchor subset.
3. With image/3D history only: infer morphology and conditional hazard; call the latent variable an effective state, not measured energy.

The decisive test is counterfactual: if two different load/moisture histories can generate the same observed crack sequence but imply different futures, the observation set cannot identify the physical state. More training data does not cure that structural ambiguity.

## Minimum prospective pilot

The smallest useful closure study should use a small number of instrumented road segments, but preserve all mandatory joins:

- stable `asset_key` and timestamp for every source;
- registered image/3D crack geometry before and after multiple exposure intervals;
- axle-load/WIM or a qualified load proxy;
- pavement temperature and local weather;
- moisture at a depth tied to the structural model;
- periodic standardized FWD with repeat drops and temperature correction, plus sparse strain/deflection response;
- layer/material metadata and every maintenance/inspection censoring event;
- a frozen asset-level holdout and future-time evaluation.

DIC can be limited to laboratory or short controlled calibration windows. Deployment should consume cheaper observations, but its posterior uncertainty must be inherited from the anchor-to-field transfer.

## Reusable qualification schema

The CSV uses one row per independently accessible dataset/route. `yes`, `no`, `partial`, `unknown`, `request`, and `designed` are evidence states—not scores. The claim columns are mandatory because a downloadable dataset is not automatically suitable for forecasting or mechanism identification.

Promotion to a complete trajectory requires all of:

- stable asset and time keys;
- repeated, future, registered crack geometry;
- load/traffic, temperature/weather and moisture;
- material/structure and mechanical response;
- maintenance/censoring history;
- machine-readable access and leakage-safe asset/time splits.

## Source and evidence ledger

| Claim | Source | Evidence status |
|---|---|---|
| LTPP/InfoPave exposes data download, section timelines, distress, climate, traffic and analysis products | [FHWA InfoPave](https://infopave.fhwa.dot.gov/) | Official portal; local six-section coverage separately audited |
| MnROAD provides performance, weather, traffic and field-monitoring routes including moisture and FWD | [MnROAD data](https://www.dot.state.mn.us/mnroad/data/index.html), [field monitoring](https://www.dot.state.mn.us/mnroad/data/field-monitoring.html) | Official state source; synchronized requested bundle not possessed |
| WesTrack accelerated pavement data are accessible through InfoPave | [FHWA WesTrack](https://infopave.fhwa.dot.gov/Westrack/Overview) | Official overview; exact joins unqualified |
| CAMHighways contains georeferenced textured meshes, point clouds, orthomosaics, defect annotations and GPR products | [Cambridge Digital Roads of the Future](https://drf.eng.cam.ac.uk/research/camhighways-dataset) | Official project page; temporal use not stated |
| NCAT and Virginia Smart Road are instrumented full-scale facilities | [NCAT Test Track](https://eng.auburn.edu/research/centers/ncat/testtrack/index.html), [Virginia Smart Road](https://www.vtti.vt.edu/facilities/highway-section.html) | Official facility pages; joined crack trajectories not verified public |
| PaveTrack PD is publicly deposited | [ScienceDB record](https://doi.org/10.57760/sciencedb.20383) | Public record plus local manifest/registration audits |
| Public fatigue DIC records exist | [AA2024-T3 DIC](https://doi.org/10.5281/zenodo.11945905), [CrackMNIST](https://doi.org/10.5281/zenodo.18454958), [Mendeley DIC fatigue](https://doi.org/10.17632/dywwnjv22h.1) | Repository records; road-domain transfer unqualified |
| A staged multi-temporal concrete crack image record exists | [Zenodo 15187675](https://doi.org/10.5281/zenodo.15187675) | Public record; numeric load/response join still needs file audit |
| Static multimodal perception records exist | [RDD2022](https://doi.org/10.6084/m9.figshare.21431547.v1), [RMDCrack](https://doi.org/10.57760/sciencedb.32469), [3DCrack](https://doi.org/10.21227/2etq-xh36), [NCCD-PF](https://doi.org/10.5281/zenodo.8215100) | Public records; not trajectory evidence |
| ConTrack reports repeated road monitoring | [IEEE article](https://doi.org/10.1109/TITS.2022.3201968) | Paper located; authoritative public dataset download not verified |

## ChatGPT Pro independent review and cross-check

**Completed:** 2026-08-27.  
**Method:** two-stage review in a fresh ChatGPT Pro conversation. Pro first produced an original architecture without seeing this candidate design. Only after that answer was complete was it shown the two-tier strategy and dataset inventory for an adversarial cross-check. No local files or private data were sent. Conversation: [Road-crack research architecture](https://chatgpt.com/c/6a909b9c-7b74-83eb-a828-8d40aef11e6a).

### Independent contribution from Pro

Pro independently proposed a partially observed state-space model and separated measured quantities, latent effective state, physical parameters, and structurally unidentifiable quantities. Its most useful addition was the **FWD active-probe** idea:

\[
y_t = H(x_t,\theta,q_t^{\mathrm{probe}})+\epsilon_t,
\]

where a standardized probe is used to update a posterior over effective compliance, support degradation, fracture susceptibility, moisture memory, and regime state. The target remains future crack morphology/hazard and calibrated uncertainty—not future (J).

### Cross-check verdict

| Candidate judgment | Pro verdict | Final resolution |
|---|---|---|
| Few dense physics anchors plus broad cheap observations | Agreement | Retain; add periodic FWD as the active observation in the cheap tier |
| Learn cheap-observation to driving-state mapping | Partial agreement | Call the output a posterior distribution over effective state; never treat anchor output as ground-truth energy labels |
| Keep trajectory carrier, mechanics bridge and prospective closure separate | Agreement | Retain strict evidence-role separation and prohibit cross-asset pseudo-joins |
| Missing load/fatigue can be marginalized but not causally eliminated | Agreement | Retain; explicit load becomes important under traffic-distribution shift or extreme events |
| No currently possessed dataset closes the entire gate | Not independently verifiable by Pro | Retain as a **local inventory verdict**, supported by the local coverage matrix; do not present it as a universal fact about every possible external dataset |

There was no substantive disagreement on the central identifiability boundary. Both reviews reject image-to-energy claims, direct transfer of metal DIC anchors to pavement, and use of static crack datasets as forecasting evidence.

### Important corrections produced by the review

1. **Split the anchor category.** Laboratory DIC is a fracture-method/observation-operator anchor; MnROAD is a field observability candidate; WesTrack is an accelerated-loading bridge. They are not interchangeable physics truth.
2. **Make latent supervision probabilistic.** The transfer target is (p(z_t\mid o_{0:t})), not a scalar “true driving energy.” Calibration and domain-transfer uncertainty are part of the output.
3. **Make evidence ownership explicit.** Public-source facts, local file audits, and proposed future access are distinct. For example, PaveTrack's scene-level downgrade is a local registration result; MnROAD synchronization remains `Needs schema audit`; the six-section LTPP coverage statement belongs to the local extract.

Pro also identified limitations in its own original answer: it initially described DIC-to-(J) identifiability too absolutely, did not specify how anchor information transfers to cheap observations, and did not assign sufficiently precise roles to individual datasets.

### Dataset-specific reconciliation

| Dataset | Final status after both reviews |
|---|---|
| Local LTPP six-section extract | Qualified local trajectory baseline for its audited fields; moisture/complete censoring remain missing. This is not a claim about all LTPP data. |
| PaveTrack PD | Public repeated scene observations; metric physical registration not demonstrated. Local sample failed the stricter registration gate, so use scene-level morphology only. |
| MnROAD | Highest-priority field bridge request; synchronized crack-map/sensor/FWD joins remain `Needs schema audit`. |
| WesTrack | Accelerated-loading bridge, not local crack-tip mechanics; exact response variables and joins remain `Needs schema audit`. |
| CAMHighways | Multimodal current-state pretraining; usable temporal sequence remains `Unknown`. |
| RDD2022 / 3DCrack / RMDCrack | Perception-only under the present evidence. RMDCrack file/schema still merits direct audit before asserting anything beyond its public static record. |
| Laboratory DIC datasets | Method and observation-operator anchors only; no pavement-transfer claim. Mendeley synchronization and CrackMNIST chronology require file-level audit for temporal use. |
| Multi-temporal concrete | Geometry-evolution anchor; mechanics role remains `Unknown` until numeric image-load-response joins are demonstrated. |
| NCAT / Virginia Smart Road | Collaboration candidates, not possessed evidence. |
| Prospective pilot | Proposed closure route, not existing evidence. |

### Final shared research route

**Hierarchical probe-assisted latent-state assimilation**:

1. laboratory fracture anchors constrain observation operators and broad priors;
2. instrumented-road anchors test field observability and domain transfer;
3. operational roads assimilate RGB/3D, weather, traffic proxy, maintenance and periodic FWD into a calibrated latent-state posterior;
4. the forecast is future geometry, transition hazard and uncertainty under explicit future exposure scenarios.

The minimum falsifiable ladder is:

- `M0`: persistence;
- `M1`: registered geometry only;
- `M2`: geometry + weather + traffic proxy;
- `M3`: `M2` + periodic FWD active probe;
- `M4`: `M3` + anchor-informed latent posterior;
- `M5`: `M4` + explicit WIM/load, only where genuinely available.

The route fails or must be weakened if `M3` does not improve over `M2`, if `M4` does not improve forecast/calibration over `M3`, or if traffic-shift tests show that latent marginalization cannot substitute for explicit exposure. A gain from `M5` mainly under traffic shift would support the narrower conclusion that explicit load improves extrapolation rather than routine in-distribution forecasting.

### Final acquisition priority

1. design the same-asset prospective pilot;
2. request and schema-audit MnROAD;
3. use the audited local LTPP extract as the present operational baseline;
4. schema-audit WesTrack as an accelerated-loading bridge;
5. retain PaveTrack for scene-level temporal morphology;
6. use CAMHighways and static multimodal datasets for perception only;
7. use laboratory DIC datasets for method calibration, never as proof of pavement transfer.

## Local evidence consulted

- `docs/real_road_trajectory_coverage_matrix.md`
- `docs/real_road_trajectory_coverage_matrix.csv`
- `docs/pavetrack_pd_manifest_audit_20260805.md`
- `docs/mnroad_cell22_data_request_20260805.md`
- `docs/reality_assimilation_framework_2026-07-15.md`
- `docs/research/S02/S02-E001/data_trajectory_inventory.csv`
- `local_archive/after_strict_setting_alignment/fem/pf_felino_cycle_jump_and_gate3b_preflight_20260817/public_experimental_dataset_screen.md`
- `local_archive/open_data/crackmnist_20260813/`
