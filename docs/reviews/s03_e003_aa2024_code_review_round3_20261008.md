# S03-E003 external Code Ready review — round 3

- Date: 2026-10-08
- Bound commit: `00dee5d13c9b625720e51b7fbf2106a70f64a0a0`
- Bound protocol: v3
- Verdict: `REVISE_CODE`
- Reviewer surface: external ChatGPT web conversation
- Conversation: `https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb`

## Blocking findings

1. `ZipInfo.filename` is truncated at an embedded NUL. A patched central entry
   `root/safe\x00/../../escape.txt` therefore appeared safe and could falsely
   qualify. Validation and counts must use the untruncated
   `ZipInfo.orig_filename`, explicitly rejecting NUL before normalization.
2. A central filename marked UTF-8 but containing an invalid byte raises
   `UnicodeDecodeError` outside the fixed failure interface. It must produce a
   complete redacted block with `ZIP_CENTRAL_DIRECTORY_INVALID`.
3. Ordinary `json.loads()` silently accepts contradictory duplicate identity
   keys by retaining the last declaration. Duplicate keys must invalidate the
   official metadata before ZIP construction.
4. Metadata/archive identity failures prevented manifest inspection but still
   emitted `locked_archive_does_not_meet_declared_manifest_contract`. Those
   branches establish only `qualification_not_established`.

## Bounded non-blocking notes

- The review confirmed the normal read boundary uses `infolist()` without
  opening or extracting members, and the production CLI has no override for
  the frozen identity/counts.
- The output validator was only a partial recursive schema validator, although
  no separate production-reachable source-string leak was found.
- Required-basename case sensitivity was ambiguous between protocol wording and
  the implementation's case-folding and should be made explicit.
- The reviewer could not run the supplied pytest suite because pytest was not
  installed in its isolated environment; it made no suite-PASS claim.

## Attachment identity reported by reviewer

| Attached file | SHA-256 |
|---|---|
| `aa2024_value_blind_audit.py` | `2502fdc07c583aeb0ff9ae9e858fd2d771d2e0f194e46f1b9dc2727b98c3b64e` |
| `test_aa2024_value_blind_audit.py` | `d25d3541333997384e0314a0da878198e74f0d50d3a90e8186c92cc6b070b54b` |
| `experiment.md` | `bf04da743c6f31b672e2ac2ac55c09612f64edadd984cf9680c0f50184a61877` |

## Disposition

No real archive audit had run. v4 addresses all four blockers and the bounded
basename-policy note. Any corrected code requires a new exact-commit Code Ready
review; round 3 does not authorize S03-E003-R001.
