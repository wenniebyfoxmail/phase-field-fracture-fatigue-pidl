# LTPP enriched-input forecast preflight

Date: 2026-08-06  
Status: `CHATGPT_PRO_APPROVED_FOR_INPUT_FREEZE__NO_FIT`

Update: the six requested technical revisions are now specified in
`ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`. The revised
primary task uses only source-available information; realized interval exposure
is a non-confirmatory oracle diagnostic. This preflight still does not authorize
fitting. After the requested rationales and prior-predictive gate were applied,
ChatGPT Pro returned `APPROVE_FOR_INPUT_FREEZE` for the exact preregistration
artifact with SHA-256 `3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992`.
The immutable 31-row feature package, hash preflight, and prior-predictive
receipt remain outstanding, so outcome fitting is still forbidden.

## PIDL Experiment Gate

- **Mechanism question:** can observed traffic demand, pavement structure, and
  the latest source-available FWD state explain held-out-section crack growth
  heterogeneity that geometry plus climate could not explain?
- **Claim changed if success:** the negative six-section result was primarily
  an omitted-state failure, and a small observation-conditioned model is worth
  a frozen ablation test.
- **Claim changed if failure:** these section-level additions remain
  insufficient; exact crack geometry needs more local state or new prospective
  assets, not a larger architecture.
- **Cheaper diagnostic first:** official InfoPave table/row coverage and
  source-time leakage audit, completed below.
- **Minimal output asset:** one immutable interval-feature table, one ablation
  table, and one decision note. No model archive dump.
- **Code/producer alignment:** acquisition and deterministic statistical
  evaluation are lightweight Mac tasks; no PIDL/FEM training and no CSD3 use.
- **Success criteria:** drafted and locked for external review in preregistration
  v2; they may not be changed after the feature-table hash is recorded.
- **Failure criteria:** missing coverage, source-after-target leakage, stale FWD
  treated as synchronous, or no frozen improvement over persistence.
- **Registry destination:** `docs/research_frontier.md` and this bounded record.
- **Decision:** `input freeze only`; ChatGPT Pro approved acquisition and
  hashing of the 31-row source-cutoff feature table. The formal claim-changing
  ablation remains blocked until every immutable pre-fit gate passes.

## Official live availability audit

The public InfoPave SDR 39 Table Export dictionary and preview endpoints were
queried with the official structured section filter for the six frozen section
IDs. This is a live read-only audit, not yet a frozen raw-data package.

| section | TRF_TREND rows | layer rows | FWD tests | backcal rows | construction events | SMP moisture rows |
|---|---:|---:|---:|---:|---:|---:|
| 06-1253 | 42 | 4 | 7 | 68 | 0 | 0 |
| 06-2041 | 53 | 16 | 7 | 52 | 2 | 0 |
| 06-2647 | 34 | 5 | 4 | 36 | 0 | 0 |
| 06-8149 | 58 | 35 | 10 | 60 | 5 | 0 |
| 06-8150 | 46 | 37 | 9 | 56 | 8 | 0 |
| 06-8201 | 37 | 5 | 5 | 40 | 0 | 0 |

The moisture count is zero in each of
`SMP_TDR_AUTO_MOISTURE_TLE`, `SMP_TDR_MANUAL_MOISTURE`,
`SMP_GRAV_MOIST`, and `SMP_WATERTAB_DEPTH_MAN` for every section.

## Leakage and time-coverage diagnostic

- 30/31 transition intervals have complete calendar-year ESAL trend coverage;
  the final `06-1253` interval has `0.8333` coverage because its target is in
  2012 while the traffic trend ends in 2011.
- Every transition has at least one FWD test on or before its source survey.
- Median latest-prior FWD age is `0.0 years` in five sections and `0.998 years`
  in `06-8150`.
- Worst latest-prior FWD ages range from `2.84` to `6.55 years`; therefore FWD
  must include measurement age and missing/staleness treatment rather than be
  interpreted as a synchronous latent state.
- Each selected transition construction number is represented in
  `SECTION_LAYER_STRUCTURE`; structure can be joined without crossing a
  construction/reset boundary.

## Superseded candidate order (not authorized to fit)

1. persistence;
2. geometry + climate control already frozen;
3. add interval truck volume / ESAL with source flags;
4. add construction-matched layer thickness/material summaries;
5. add latest-prior FWD/backcal state plus age and missingness;
6. evaluate only under the existing leave-one-section-out and future-time
   receipts.

The first target should be new crack length or initiation probability, not
exact 2D crack placement. Section-level loading and structure may explain rate
heterogeneity but do not localize a future crack path.

This candidate list is superseded by preregistration v2, which removes spatial
metrics from this scalar experiment, fixes a source-available primary forecast,
and specifies the exact algorithm, feature fields, validation axes, success
rules, and pre-fit evidence gate.
