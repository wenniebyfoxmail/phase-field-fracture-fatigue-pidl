---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
status: LOCAL_DEPLOYMENT_CANDIDATE__NO_REMOTE_ACTION__NO_AUTHORITY
date: 2026-10-20
---

# Content-addressed deployment candidate

## Purpose and separation

This candidate repairs only delivery of the already frozen 14,359,316-byte
code archive. It does not change the scientific package, reviewed control
commit, three arms, exposed cycles, `beta=0.25`, update budget, packet,
checkpoint, GPU, producer or holdout boundary. The helper has no SSH, authority,
admission, model or training API. Network commands remain parked in this card
until a new exact user authority exists.

The frozen archive is divided into 28 fixed 524,288-byte content-addressed
chunks; the last chunk is 203,540 bytes. Every final chunk name contains its
SHA-256. The canonical archive manifest SHA256 is
`a88a23859c2edd2ac2ddc09d9140029d128fbcbb21b689c46274918d6f1318ae`.
Assembly rereads every chunk, checks its size and SHA-256, checks the final
14,359,316-byte archive against
`4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22`,
and publishes `control/code.tar.gz` with a same-directory no-replace hard-link.
An incomplete, corrupt, late or conflicting assembly never exposes that path.

## Old partial is not trusted

The helper's `audit-legacy` command reads every complete manifest range and
classifies it as verified, mismatched, incomplete or absent. `import-legacy`
rereads and rehashes a verified range before atomically creating its chunk. It
does not trust a progress percentage, filename, size or prefix assumption.

Locally truncating the exact archive to the previously recorded remote size
(12,572,127 bytes) produced the same recorded SHA256
`b3d53aad9797a4c19ee30f18c1f0ca6b721dabae3a82fd9b58463579132bd9e0`.
Under the explicit condition that the remote file still has that exact size
and hash, 23 complete chunks (12,058,624 bytes) are content-identical and the
remaining chunk transfer is 2,300,692 bytes. This is a local identity/cost
scenario, not a claim that the remote file still exists or is reusable. A new
authority must begin with a fresh read-only remote audit.

## Finite deployment envelope

The future deployment is bounded to one SSH master connection attempt, one
metadata transfer, one missing-chunk `rsync` invocation, no per-chunk retry, no
reconnect, no whole-archive transfer, at most 14,500,000 transmitted source
bytes and 1,800 seconds from the first connection attempt through final
publication. A broken master or expired wall clock stops before admission.

The prior whole-file attempt reached about 93% logical progress in 1,800
seconds, so a fresh full 14.36 MB transfer is not demonstrated reliable inside
the existing cap. If the old partial validates, the estimated remaining source
bytes fall to 2.30 MB and fit comfortably by the prior observed effective rate.
That estimate does not establish future connection stability. If the audit
cannot reuse enough verified chunks, extending the 1,800-second cap is a new
pending decision; this candidate does not enlarge it automatically.

## Exact local build and verification

```bash
cd /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012

PYTHONPATH=source /Users/wenxiaofang/miniconda3/bin/python3 \
  scripts/s09_e017_chunked_archive.py build \
  --archive /tmp/S09-E017-code-2002538d-repair-20261020.tar.gz \
  --chunk-dir /tmp/S09-E017-code-4ece34be-chunks-v1 \
  --manifest docs/research/S09/S09-E017/chunked_archive_manifest_20261020.json \
  --chunk-size-bytes 524288 \
  --expected-archive-bytes 14359316 \
  --expected-archive-sha256 4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22 \
  --reviewed-control-commit 2002538d9a30c8d4006ccaff5959cd214958fc82
```

The tracked manifest already exists, so reproduction must target a fresh
manifest path and compare its bytes rather than overwrite it.

## Parked future deployment sequence

The following is reviewable command text, not current authority. A later grant
must bind a unique `DEPLOYMENT_ATTEMPT_ID`, the exact helper commit and hashes,
the same archive manifest and the limits above.

1. Start the outer 1,800-second clock before exactly one SSH master connection
   attempt. Recheck hostname, clean `2002538d...` checkout, GPU5 identity, no
   runner/session/token/authority/output, expected archive absence, old partial
   identity and task-owned paths. Any discrepancy stops.
2. Transfer the three small tracked helper/manifest files once with `rsync -aR`
   over that master into `control/chunked_deployment_v1/`; verify their exact
   candidate hashes remotely. This does not change `code/`.
3. Run `audit-legacy` with a write-once attempt report. If the recorded partial
   is present, `import-legacy` re-verifies and atomically materialises only exact
   complete chunks into
   `control/archive_chunks/4ece34be786fc85bb/`. If absent, no reuse is claimed.
4. Run `inspect-store`, retrieve its canonical report, require zero corrupt
   chunks, and derive a local `missing-files.txt` only from manifest-listed
   `missing_names`. Reject duplicate, absolute or parent-traversal names. Sum
   selected chunk sizes plus metadata and stop if above 14,500,000 bytes.
5. With the remaining outer time, run exactly one command of the form below.
   `--ignore-existing` prevents a race from replacing a final chunk; the post
   inspection still rehashes every final name. No `--partial`, `--append` or
   per-chunk loop is allowed.

```bash
rsync -a --ignore-existing \
  --files-from=/private/tmp/S09-E017-<DEPLOYMENT_ATTEMPT_ID>-missing-files.txt \
  -e 'ssh -S /tmp/S09-E017-<DEPLOYMENT_ATTEMPT_ID>.sock -o ControlMaster=no' \
  /tmp/S09-E017-code-4ece34be-chunks-v1/ \
  gpu-taobo:/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/archive_chunks/4ece34be786fc85bb/
```

6. Run a new write-once `inspect-store` report and require all 28 chunks valid,
   none missing/corrupt. Pass only the remaining outer seconds to `assemble`:

```bash
PYTHONPATH=/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/chunked_deployment_v1/source \
python3 /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/chunked_deployment_v1/scripts/s09_e017_chunked_archive.py \
  assemble \
  --manifest /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/chunked_deployment_v1/docs/research/S09/S09-E017/chunked_archive_manifest_20261020.json \
  --manifest-sha256 a88a23859c2edd2ac2ddc09d9140029d128fbcbb21b689c46274918d6f1318ae \
  --chunk-dir /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/archive_chunks/4ece34be786fc85bb \
  --output /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/code.tar.gz \
  --receipt /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/<DEPLOYMENT_ATTEMPT_ID>-assembly-receipt.json \
  --max-wall-seconds <REMAINING_OUTER_SECONDS>
```

7. Independently reread size, archive SHA256 and `git get-tar-commit-id`. Only
   `14359316`, `4ece34be...dd22` and `2002538d...` may close deployment. The
   later exact resolver/admission may begin only if the same still-live grant
   authorises it and time remains; otherwise park the verified archive without
   minting or reviving an authority.

## Local fault evidence

Twelve tests cover manifest canonicalisation, missing and corrupt chunks,
unexpected store entries, wrong complete legacy ranges, incomplete legacy
ranges, reverified import, existing-output conflict, wall expiry before any
publish, write-once receipts and successful original-byte atomic publication.
The full real archive was split, inspected and reassembled locally; its output
was 14,359,316 bytes with the original `4ece34be...dd22` SHA256. Ruff,
`py_compile` and `git diff --check` are required again at the exact review
commit.

This candidate remains local and disabled. It records no connection recovery,
remote audit, verified remote chunk, authority, admission or scientific result.
