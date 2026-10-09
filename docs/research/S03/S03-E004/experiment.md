---
storyline_id: S03
experiment_id: S03-E004
protocol_revision: v1
status: code_revised_re_review_pending
started_at: 2026-10-09
primary_storyline: S03
related_storylines: [S02]
scientific_verdict: pending
---

# AA2024 empirical global-DIC sequence qualification

## Road-Fracture Experiment Gate

- **Claim class / domain:** bounded `C1 evidence-validity`; controlled experiment.
- **Question:** ignoring the official advertised member count and basename, does
  the immutable archive actually in hand contain an internally self-consistent
  global 3D-DIC sequence that can support design of a later observation-only
  transition experiment?
- **Evaluation unit:** every global nodemap stage actually present in the locked
  archive; no file or stage is sampled out.
- **Allowed inputs:** ZIP central directory and bounded header prefix of every
  matched global nodemap. Connection bodies and nodemap numerical bodies are
  not read. The released dictionaries and local mapping are not pass criteria.
- **Estimand:** whether all discovered global stages form one auditable,
  one-to-one nodemap/connection sequence with complete finite mechanics and
  chronology headers and one stable spatial-field schema.
- **Primary criterion:** all validity clauses below pass simultaneously.
- **Stop rule:** stop at the first archive-identity, unsafe-path, pairing,
  bounded-header, required-field, stage-identity, chronology, or schema failure.
- **Decision:** implement and independently review before the real archive run.

## Why this is a new Experiment

S03-E003 correctly remains closed under its frozen official-manifest contract.
The owner has now chosen a different scientific question: use the contents of
the immutable archive actually obtained, rather than test consistency with the
record's advertised count or filename. Because that changes the evidence
semantics and primary gate after results were viewed, it is registered here as
a new Experiment rather than rewriting S03-E003.

## Immutable input

- Archive: `multiscale_digital_image_correlation.zip`
- Size: `1,248,078,255` bytes
- MD5: `e671b804e29401e70043bc1e17f66dd1`
- Raw root:
  `$PROJECT/local_archive/open_data/aa2024_dic_zenodo_11945905_20261008/raw/`
- Run root:
  `$PROJECT/local_archive/experiments/S03-E004/runs/S03-E004-R001/`

The count of discovered stages is an observed result, not an expected value.
No check compares it with `797`, and no official mapping basename is required.

## Frozen empirical contract v1

### Discovery and pairing

1. Validate the archive size and MD5 before opening it.
2. Validate safe, unique POSIX member paths and ordinary supported ZIP members.
3. Discover global nodemap and connection **file entries** only by these
   released structural forms, case-insensitively for directories and exactly
   for numeric stage ID. ZIP directory entries, including Unix directory-mode
   entries without a trailing slash, cannot satisfy either role:
   `global_3d_dic/Nodemaps/global_3d_dic_results_1_<stage>.txt` and
   `global_3d_dic/Connections/global_3d_dic_results_1_<stage>_connections.txt`.
4. Require at least two discovered stages, unique numeric IDs, and exact equality
   of the nodemap and connection stage-ID sets.

### Bounded header audit

For every discovered global nodemap, comments may supply required scalar
metadata, but only the first non-comment line is the column-header line.
Schema-like comments do not satisfy or override it. Read only through that
line, with a hard per-member parser-consumption cap of 131,072 uncompressed
bytes. A numerical-row prefix before the column header is a parser failure and
must stop before the complete row is consumed. Do not read any connection body.

Require exactly one parseable finite value for:

- `current_stage_index`, `current_stage_relative_date`,
  `reference_stage_index`;
- `force`, `displacement`, `cycles`, `time`, and `cracklength`.

Required numbers are parsed as finite decimal values without preliminary
binary-float rounding. The `current_stage_index` must equal the numeric ID in
the member basename exactly. Across ascending stage IDs,
`current_stage_relative_date`, `cycles`, and `time` must be nondecreasing under
exact decimal comparison. There must be at least two distinct cycle values and
two distinct crack-length values. All stages must expose the same normalized
nodemap column schema, which must include node ID, undeformed coordinates,
displacements, and strain components. Per-stage identity, schema, and
chronology checks occur before the next member is opened; only variation checks
wait for the complete sequence.

No monotonic-crack-growth assumption is imposed: DCPD crack length may be noisy.
No fixed forecast horizon, split, model, threshold, or inverse parameter is
chosen in this Experiment.

## Outcome map

- `QUALIFIED_EMPIRICAL_GLOBAL_SEQUENCE`: the actual locked global-DIC sequence
  is structurally and semantically auditable enough to design a separate,
  independently reviewed observation-only transition experiment.
- `BLOCKED_EMPIRICAL_SEQUENCE`: the actual archive cannot support that bounded
  sequence claim under v1.
- Parser/identity failure permits only `qualification_not_established`.
  Whole-sequence positive flags remain false whenever header coverage is
  incomplete.

## Independent Code Ready review history

- Exact commit `10b1bf6607991e78fbec8fa58fdf325c5bc0a79d` received
  `REVISE_CODE`. Attachment hashes matched, but synthetic counterexamples found
  six blocking classes: directories satisfying file pairing; commented-schema
  substitution; byte/body/first-failure read-boundary violations; lossy float
  comparison; escaping parse/decode/decompression failures; and overstrong
  failure conclusions/partial-coverage flags.
- The subsequent local revision preserves the v1 scientific question while
  closing those implementation gaps. It must receive a new independent
  `PASS_CODE_READY` on its exact committed bytes before any real archive run.

## Required evidence

- independently reviewed exact runner/tests/commit with `PASS_CODE_READY`;
- `data_audit.json`, `execution_receipt.json`, and `decision.md`;
- compact decision table, independent evidence review, and dated Storyline
  claim-impact entry before closure.

## Blocked conclusions

Even a pass does not establish a causal forecast, independent-specimen
generalisation, phase-field recovery, material-property identification,
fatigue-law truth, road transfer, or deployment. The released DIC fields and
DCPD crack length are observations; they are not phase-field labels.
