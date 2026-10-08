# S03-E003 external Code Ready review — round 4

- Date: 2026-10-09
- Bound commit: `53eb40e593cb1fff5979c8ebb035b53e862aba8e`
- Bound protocol: v4
- Verdict: `REVISE_CODE`
- Reviewer surface: external ChatGPT web conversation
- Conversation: `https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb`

## Blocking findings

1. `_validated_output_path` accepted an output path equal to the allowed audit
   root. If that root already existed as a directory, atomic writing failed and
   could leave a temporary file outside the root; if absent, the JSON could be
   written as the root pathname. The output must be a strict descendant, and a
   directory target must be rejected before audit execution.
2. The path control-character check rejected code points below U+0020 but
   omitted ASCII DEL U+007F and C1 controls such as U+0085. These names could
   qualify unless the complete defined control set is rejected.
3. Standard-library JSON parsing can reject a 5,000-digit integer with
   `ValueError` and deeply nested arrays with `RecursionError`. Both escaped the
   fixed metadata-failure interface and must map to `OFFICIAL_METADATA_INVALID`
   before ZIP construction.

## Confirmed closures and bounded notes

- All four round-3 blockers were closed in v4: untruncated central names,
  malformed-UTF-8 handling, duplicate-key rejection, and conclusion semantics.
- Required-basename case sensitivity was consistent between protocol and code.
- The normal production path still used `infolist()` without reading or
  extracting member contents, and the CLI exposed no frozen-lock override.
- The output validator remained a partial recursive validator, but the reviewer
  found no production-reachable source-string leak; this was not blocking.
- The reviewer could not independently run pytest because it was unavailable in
  its isolated environment. It made no test-suite PASS, real-audit, scientific,
  or field-validity claim.

## Attachment identity reported by reviewer

| Attached file | SHA-256 |
|---|---|
| `aa2024_value_blind_audit(1).py` | `9a409376aa914ef46bebb25888d400a8e6c20c3ab4d665179ef456e677169a7c` |
| `test_aa2024_value_blind_audit(1).py` | `1e6c5dfc2f948d364980dfd5263a83b21fb22b2c1dbf99d6b27972ebfc00755e` |
| `experiment(1).md` | `023b56fade31eb18617a5ba60d48a3a0490a80ad18bb14307a6f7f43486edf29` |

## Disposition

No real archive audit had run. v5 addresses all three blockers with synthetic
regressions. Because the runner, tests, and protocol changed, round 4 does not
authorize S03-E003-R001; the exact v5 commit requires a new independent Code
Ready review.
