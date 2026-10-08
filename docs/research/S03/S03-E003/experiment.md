---
storyline_id: S03
experiment_id: S03-E003
protocol_revision: v2
status: ready
started_at: 2026-10-08
closed_at:
primary_storyline: S03
related_storylines: [S02]
scientific_verdict:
---

# AA2024 value-blinded trajectory qualification audit

## PIDL Experiment Gate

- **Primary claim class:** `observation-validity`.
- **Question:** can Zenodo record `11945905` be mapped, without viewing sealed
  future crack-growth values, into causal acquisition episodes with usable
  cycle-indexed DCPD crack-length targets and synchronized mechanics channels?
- **Claim if pass:** permit design and independent review of a separate
  within-specimen forecast Experiment. No forecast or phase-field claim passes.
- **Claim if fail:** the AA2024 record is blocked for the proposed fixed-cycle
  forecast; do not substitute interpolation, tune a horizon, or start inversion.
- **Cheaper falsification first:** official Zenodo API metadata and remote
  archive manifest, followed by header/schema-only inspection. CARPIUC is not
  required unless a named tooling defect appears.
- **Smallest output asset:** one redacted `data_audit.json`, one human-readable
  `decision.md`, and an immutable dataset receipt.
- **Registry destination:** S03 -> S03-E003. A forecast requires S03-E004 or a
  later new Experiment.
- **Decision:** data-only audit; no training, optimization, FEM solve, PIDL run,
  or material/constitutive parameter fitting.

## Scientific question

Does the released AA2024-T3 MT160 archive expose enough causal chronology,
measurement semantics, and independently measured target support to design one
honest fixed-cycle, within-specimen mechanics-information test?

## Claim contract

- **Primary claim class:** observation-validity.
- **Secondary claim classes:** state-semantics; tooling-only.
- **Estimand and comparison class:** dataset capability, not model performance.
  The unit is a distinct acquisition episode identified by physical cycle and
  acquisition metadata, never an individual DIC file.
- **Claim if primary gate passes:** the dataset is qualified for later protocol
  design under the reported acquisition policy and limitations.
- **Claim if primary gate fails:** the fixed-cycle prediction proposal is
  blocked on this dataset.
- **Blocked regardless of outcome:** forecast accuracy, uncertainty calibration,
  phase-field recovery, parameter identification, material truth, specimen
  generalisation, road transfer, and deployment.

## Five-question intake

1. **Question:** does the archive support causal acquisition episodes and a
   non-interpolated cycle-indexed future crack-length target?
2. **Claim change:** pass allows only a new forecast protocol; fail blocks this
   data source for that role.
3. **Cheaper diagnostic:** API metadata, ZIP manifest, dictionaries, mapping CSV,
   and redacted nodemap-header audit before any field extraction.
4. **Minimal asset:** dataset receipt, redacted audit JSON, and decision.
5. **Placement:** S03-E003 is the observation-validity Experiment feeding a
   possible S03-E004 forecast Experiment.

## Reuse decision

- **Searched:** prior Gate 3B dataset screen, S03-E001/E002 data-audit patterns,
  project registries, external plan review, and official Zenodo metadata.
- **Reused:** Experiment/Run/evidence structure, strict identity locks, causal
  preprocessing rules, and the prior AA2024 candidate screen.
- **New code justification:** no existing audit reconstructs AA2024 acquisition
  episodes while redacting crack-growth outcomes and reporting fixed-cycle
  target support.

## Frozen protocol

### Dataset identity and storage

- Official record: `https://zenodo.org/records/11945905`.
- DOI: `10.5281/zenodo.11945905`.
- Record ID / concept record: `11945905` / `11945904`.
- Publication date: `2024-06-17`.
- Licence: CC BY 4.0.
- Archive: `multiscale_digital_image_correlation.zip`.
- Expected size: `1,248,078,255` bytes.
- Expected checksum: `md5:e671b804e29401e70043bc1e17f66dd1`.
- Local raw path:
  `$PROJECT/local_archive/open_data/aa2024_dic_zenodo_11945905_20261008/raw/`.
- Compact audit path:
  `$PROJECT/local_archive/experiments/S03-E003/runs/S03-E003-R001/`.

The raw archive is immutable. Compact audit artifacts may record identities,
schemas, counts, missingness, cycle spacing, and acquisition grouping. They
must not emit per-episode crack lengths, full displacement/strain values, or
sealed-suffix outcome tables.

### Value-blinded inspection order

1. Lock official API metadata, file size, checksum, licence, and attribution.
2. Inspect archive member names, sizes, and directory structure only.
3. Inspect metadata dictionaries and mapping-table column names.
4. Parse global nodemap headers programmatically; emit field names,
   missingness, episode counts, frames-per-cycle counts, and cycle-gap/target-
   support summaries only.
5. Parse local mapping rows programmatically; emit schema, row counts, mapping
   completeness, and global/local cycle overlap only.
6. Do not extract full-field arrays or print crack-length values.

### Holdout and leakage firewall

- Individual minimum/mean/maximum load images and dense within-cycle images are
  grouped into one acquisition episode by audited physical cycle and metadata.
- No later registration, smoothing, crack-tip tracking, normalization, or
  acquisition interval may enter an earlier episode.
- This audit does not assign train/development/test outcomes. It reports only
  episode/cycle support needed for a later causal split contract.
- The later forecast protocol must keep each origin and its whole target horizon
  within one partition and purge boundary-crossing pairs.

### Strict validity gates

1. Official record identity, archive size, checksum, licence, and attribution
   are verified.
2. Archive member paths are safe and the documented global/local/dictionary
   assets exist.
3. Every included global nodemap maps unambiguously to one physical cycle and
   load/acquisition episode; duplicate timestep labels are explained.
4. Required header fields for cycle, force/load state, actuator displacement,
   DCPD potential/crack length, and both back-face strain channels are present
   or their exact absence is reported.
5. Local microscopic nodemaps map through the released mapping table without
   ambiguous file identity; synchronization gaps are counted.
6. Fixed-cycle future targets are directly observed within a predeclared
   tolerance-window analysis; no crack-length interpolation is used.
7. The audit output contains no sealed per-episode crack-length or full-field
   outcome values.

### Primary gate and stop rule

`QUALIFIED_FOR_FORECAST_PROTOCOL_DESIGN` requires gates 1--7 to pass and at
least one candidate horizon to satisfy the following outcome-blind minimum-
information rule under a physical-cycle-span 60/20/20 structural split:

- at least 12 calibration origins;
- at least 6 development origins;
- at least 8 sealed origins and 8 distinct sealed target episodes;
- one nearest target per origin inside `H +/- max(100 cycles, 0.05 H)`;
- no target reuse in the sealed segment;
- every origin and target remain in the same segment.

Exact-cycle pair counts are reported separately. These thresholds qualify only
later protocol design; they do not make a small dependent suffix population or
calibration evidence. The audit reports all frozen candidate-horizon support
counts without selecting a winning horizon.

- Any identity/checksum/path-safety failure stops immediately.
- Ambiguous cycle/episode identity, absent direct DCPD target support, or
  unresolved synchronization gives `BLOCKED_DATASET_CAPABILITY`.
- Too few distinct eligible origins for a defensible later primary gate gives
  `BLOCKED_EVALUATION_RESOLUTION`; do not relax the horizon after outcome view.
- Weak or inconvenient data complete as a negative/blocked audit; they are not
  repaired by training or parameter inversion.

### Secondary diagnostics

- member counts and uncompressed sizes by directory;
- global frames per acquisition episode and load-state multiplicity;
- physical-cycle gap distribution and candidate fixed-horizon support counts;
- required-field missingness by early/development/sealed structural segment,
  without outcome values;
- global/local cycle overlap and unmapped file counts;
- whether DCPD crack length is independent of DIC field values in acquisition
  provenance, while noting that it is stored in nodemap headers.

### Required evidence

- frozen official API metadata JSON;
- archive receipt with size and MD5;
- redacted `data_audit.json`;
- exact audit command and environment receipt;
- `decision.md` with allowed and blocked conclusions;
- independent read-only code review bound to exact commit, runner, dataset
  lock, and protocol v1;
- independent evidence review before Experiment closure.

## Producer and Run readiness

- **Producer:** Mac-PIDL, data/schema analysis only; no optimizer loop.
- **Commit / dirty status:** to be frozen after audit runner and tests are added.
- **Runner:** `scripts/aa2024_value_blind_audit.py`.
- **Output:** local archive path above; compact receipt and evidence only.
- **Safety:** raw archive is read-only; no extraction of unsafe paths; no
  training, inversion, or remote compute.

## Amendments

### 2026-10-08 — protocol v2 before any Run

The first Code Ready review of commit `930b6ab` returned `REVISE_CODE`. It found
that v1 did not implement episode/timestep identity, file-level local mapping,
direct-target validity, evaluation resolution, strict parsing, manifest-first
stopping, output redaction verification, or input/output collision protection.
It also found a required-header counter bug. No real archive audit had run.

Protocol v2 freezes the minimum-information rule above and requires exact
timestep/connection identity, monotone integer cycles, complete local-file
joins, consistent DCPD targets, bounded member reads, allowlisted output schema,
atomic writes, and decision-level synthetic tests. These changes strengthen the
original claim boundary; they do not add a forecast claim.

A later prediction horizon, comparator, CRPS threshold, or mechanics package
still belongs to a new reviewed forecast Experiment.

## Code review

- **Reviewer task:** first review returned `REVISE_CODE`; corrective re-review pending.
- **Bound commit / runner / config / data lock / protocol revision:** first
  review bound to `930b6ab` and v1; corrected commit and v2 pending.
- **Verdict:** pending; do not execute the audit runner before PASS.
- **Blocking findings:** v1 findings are recorded in the amendment above; all
  must be closed by code, decision-level tests, and re-review.

## Runs

| Run ID | Purpose | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S03-E003-R001 | value-blinded archive qualification | prepared | pending | pending |

## Evidence review

- **Reviewer task:** pending.
- **Bound Run IDs:** S03-E003-R001.
- **Bound analysis package:** pending.
- **Verdict:** pending.
- **Blocking findings:** pending.

## Scientific verdict

Pending.

## Claim impact

No claim changes before the audit closes.

## Next action

Acquire and verify the immutable archive only after this contract is frozen;
then finalize, test, and independently review the value-blinded audit runner
before executing it.
