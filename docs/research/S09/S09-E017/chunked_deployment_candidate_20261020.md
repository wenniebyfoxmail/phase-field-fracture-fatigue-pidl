---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
status: LOCAL_DEPLOYMENT_CANDIDATE__NO_REMOTE_ACTION__NO_AUTHORITY
date: 2026-10-20
---

# Content-addressed deployment candidate

## Purpose and frozen boundary

This candidate repairs delivery of the already frozen 14,359,316-byte code
archive. It does not change the scientific package, reviewed control commit
`2002538d9a30c8d4006ccaff5959cd214958fc82`, reviewed adapter commit
`662005f1fde22cb9a6e8069f4e430b7190f21860`, candidate configuration SHA256
`4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1`,
three arms, 16 exposed cycles, 64 updates per arm, `beta=0.25`, packet,
checkpoint, GPU5 or holdout boundary. It creates no execution authority and
contains no admission, model or training call.

The exact archive is divided into 28 content-addressed chunks of 524,288 bytes,
except the 203,540-byte final chunk. The canonical manifest SHA256 is
`a88a23859c2edd2ac2ddc09d9140029d128fbcbb21b689c46274918d6f1318ae`.
Assembly rereads every chunk, verifies the final archive size and SHA256, and
publishes `control/code.tar.gz` using a same-directory no-replace hard link.

## Old partial and bounded reuse

`audit-legacy` verifies every complete manifest range independently.
`import-legacy` rehashes a verified range again before atomically creating a
final chunk. A filename, byte count or progress percentage never establishes
reuse.

Locally truncating the exact archive to the previously recorded remote size of
12,572,127 bytes reproduced the recorded SHA256
`b3d53aad9797a4c19ee30f18c1f0ca6b721dabae3a82fd9b58463579132bd9e0`.
If a future authorised audit shows that the remote partial is unchanged, 23
complete chunks (12,058,624 bytes) are reusable and 2,300,692 chunk bytes
remain. This is a local cost scenario, not current remote evidence.

## Enforced finite envelope

The outer Python guard accepts only canonical candidate, plan and authority
files with exact SHA256 values. Its authority schema permits deployment only;
`execution_authorized` must be false. It launches the exact plan in a new
process group, stops that group at 1,800 seconds, writes a terminal receipt and
never retries. Before `Popen`, it atomically creates the authority-bound fixed
consumption path; replaying the same attempt with another receipt stops locally
before any connection.

The shell plan enforces:

- one SSH master connection attempt;
- one metadata `rsync` site and at most one missing-chunk `rsync` site;
- no whole-archive transfer and no per-chunk retry;
- at most 14,500,000 transmitted source bytes;
- one outer deadline checked through final verification;
- `ProxyCommand=/usr/bin/false` on every multiplexed SSH/rsync command, so a
  missing control master cannot open another connection;
- exact remote hostname, clean control commit and absence of execution,
  authority, admission, output and final archive paths before mutation;
- exact remote helper hashes, chunk hashes, archive size/SHA256 and
  `git get-tar-commit-id` before success.

The helper records an attempt journal before assembly and a prepared journal
before archive publication. A post-link durability failure reports that the
archive is already visible. A terminal receipt failure leaves the attempt,
prepared and fallback failure records. Report-path conflicts are rejected
before legacy chunks are imported. Stopped assembly exits non-zero.
The final archive check fully consumes the gzip stream before asking Git for
the embedded commit, avoiding the valid early-reader `SIGPIPE` case.

## Disabled authority template

`chunked_deployment_authority_template_20261020.json` is intentionally invalid
for execution: `approval_status=NOT_GRANTED`, `deployment_authorized=false`,
`allowed_actions=[]`, and no attempt identity or grant exists. A later grant
would have to be a new canonical file that binds the final candidate SHA256,
exact plan SHA256 and a unique deployment attempt. Preparing this candidate
does not create that grant.

## Parked exact invocation

This command is documentation only and must remain disabled unless a new exact
deployment authority exists. The candidate binds implementation commit `6a83eb3fd2f167c5ace2a846a123a214982184f4`
and the exact candidate and plan hashes below are ready for independent rereview.

```bash
cd /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012

PYTHONPATH=source /Users/wenxiaofang/miniconda3/bin/python3 \
  scripts/s09_e017_finite_deployment_guard.py \
  --candidate docs/research/S09/S09-E017/chunked_deployment_candidate_20261020.json \
  --candidate-sha256 90d0caab8752d662a1db8d475b2f9769f2185f3ea88b06ead5e1a675d8e3be25 \
  --authority <NEW_CANONICAL_DEPLOYMENT_AUTHORITY.json> \
  --plan scripts/s09_e017_chunked_deployment_plan.sh \
  --plan-sha256 0f5179cbbcc0e52f1923b4132d1e05694a3eccea2e8ffbfb9df1ac1562c0093a \
  --receipt <NEW_WRITE_ONCE_GUARD_RECEIPT.json> \
  --execute-authorised-deployment
```

The plan may publish only the verified frozen archive. It cannot mint or revive
an execution authority. Resolver, admission and scientific execution remain a
separate later gate.

## Local validation and review state

Twenty-seven focused tests pass. They cover manifest canonicalisation, missing
and corrupt chunks, legacy-range revalidation, output/report conflicts, wall
expiry, non-zero stops, post-publication I/O failure, terminal receipt failure,
guard rejection, non-zero plan exit, process-group timeout, exact invocation
counts and helper-hash binding. Ruff, `py_compile`, `bash -n` and a full
14,359,316-byte reassembly pass; the result has the original
`4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22`
SHA256.

Independent review round 1 returned `E017_CHUNKED_DEPLOYMENT_REVISE` for commit
`6a7f5bed...` and identified four control gaps. Those gaps are locally repaired;
the repair has no valid review verdict until the final exact commit is bound and
rereviewed.

This candidate records zero remote actions and no connection recovery, remote
audit, verified remote chunk, authority, admission or scientific result.
