# S02-E003 pre-run code review

Date: 2026-10-08

Review type: independent, read-only

Verdict: `PASS`

## Reviewed identities

- Protocol v1 scientific contract SHA-256:
  `cdce6e7a31824bc7a259c8d1220c9844664fd4c9b8b88e29abd2a05f58b4cffc`
- Runner SHA-256:
  `399d40447860a62f42a4e5346eb7177ffbd60c7aafaf0425dc17c52d36f92cd2`
- Selective-extraction receipt SHA-256:
  `ca7d10beeb963c5629f9537f82bb6bbd487bb1d53806dafe831a5c55177b90fc`

The protocol identity above precedes only the administrative transition from
`draft` to `ready` and insertion of this review receipt. No scientific field,
gate, metric, threshold, exclusion, or outcome map changed afterward.

## Round 1 — BLOCK

The reviewer found four blockers: an incorrect expected value in the constant
analytic fixture; no runtime enforcement of the extraction receipt; duplicate
specimen paths could affect the equal-specimen mean; and the experiment was
marked ready before review. It also identified internal-blank-row handling,
missing secondary bias/quantile outputs, and division by zero in an explanatory
ratio.

## Round 2 — PASS

The corrected runner was found to:

- pass the constant, linear, and accelerating analytic fixtures;
- enforce twelve unique receipt targets, exact input-root membership,
  uncompressed sizes, and CRC-32 values before workbook reading;
- fail closed on duplicate identities and internal blank rows while allowing
  only trailing blank spreadsheet rows;
- emit the declared bias and absolute-error quantiles;
- handle a zero persistence MAE without changing the primary inequality;
- preserve correct origin indexing, allowed inputs, equal-specimen aggregation,
  and read-only workbook access.

The reviewer did not run the evaluator on the real workbooks and did not edit
the protocol or runner.
