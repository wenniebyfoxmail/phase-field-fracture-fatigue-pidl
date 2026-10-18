# Request 28 Terminal Dependency Audit

**Date**: 2026-08-18

**Source worktree**:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/kan-rbf-u012-micro`

**Source branch/head**: `codex/kan-rbf-u012-micro@94d9c2b`

**Mode**: isolated read-only review. No merge, cherry-pick, commit, push,
experiment launch or result rewrite was performed.

## Terminal ownership and preservation

The source worktree is clean. A live `git ls-remote` query found the remote
Request 28 branches `agent/fem-request-28@368a7e8` and
`codex/request28-replay-authorization@fe61cc2`, but no remote ref for
`codex/kan-rbf-u012-micro`. Neither `f3bbc14` nor `94d9c2b` is contained by a
locally known remote-tracking branch.

Therefore the terminal evidence is currently local-only. This is a preservation
risk, not authorization to push it.

## File dependency matrix

| Source commit/path group | Direct project dependencies | Patch check against current `e71ece3` index | Decision |
|---|---|---|---|
| `f3bbc14`: `SENS_tensile/audit_request28_first_detect_export.py` | Python `numpy`, `h5py`; external Request 28 package | clean | include in acceptance unit |
| `f3bbc14`: Request 28 handover and inbox append | existing initial Request 28 text | clean at index level; working inbox also contains an unrelated dirty Request 27 append | include only in isolated integration; preserve Request 27 explicitly |
| `94d9c2b`: `SENS_tensile/analyze_request28_xdem_observability.py` | Python `numpy`, `h5py`, `scipy`; accepted Request 28 package | clean | include in terminal-analysis unit |
| `94d9c2b`: gate, GPT review and canonical track documents | analyzer, local archive decision package and attempt ledger | clean | include in terminal-analysis unit |
| `94d9c2b`: `docs/pidl_experiment_inventory.md` | earlier KAN rows in the source branch | does not apply | do not transplant hunk; add one current-context row manually in Bundle X |
| `94d9c2b`: `docs/research_frontier.md` | earlier KAN closure wording in the source branch | does not apply | do not transplant hunk; reconcile current frontier manually in Bundle X |
| current `docs/research_storylines.md` | created outside the terminal branch | not part of `94d9c2b`; S3 still describes Request 28 as pending | reconcile S3 manually in Bundle X |

The two source scripts are standalone offline analysis entrypoints; neither
imports a KAN runner or any of the twelve intervening KAN/RBF commits. The
terminal evidence can therefore be integrated without merging the mixed
fourteen-commit branch.

## Independent evidence checks

Using the project Mac Python
`/Users/wenxiaofang/miniconda3/bin/python3` with `h5py 3.16.0`, `numpy 2.2.6`
and `scipy 1.14.1`:

- the Request 28 audit was rerun read-only and returned
  `independent_audit_pass=true`;
- all package checksums, the producer result and all producer checks passed;
- all three cases passed state semantics, finite-array, native-peak equality,
  damage irreversibility and history irreversibility checks;
- the four terminal observability outputs match the SHA256 values in the local
  manifest;
- the analyzer source hash `fb1b3aee...` and GPT review hash `749b77c1...`
  match the closed attempt-ledger entry;
- a fresh in-memory affine Q4 field check reproduced the analytic strain norm;
- all three analyzed cases have the same mesh hash and no equal-distance
  nearest-neighbour tie under the frozen mirrored-centre pairing.

The frozen pairing is nearest-neighbour rather than bijective: 181 accepted
positive cells reuse a negative-side nearest neighbour in each case. This is
permitted by the frozen reviewed definition and is identical across all three
cases, but it remains part of the narrow claim boundary. It must not be silently
reinterpreted as a one-to-one crack-face correspondence.

Raw MAT/CSV/JSON payloads and the attempt ledger remain local archive assets;
they should not be copied into Git. The compact script, gate, review, track,
registry row and provenance pointers are the Git-sized evidence.

## PIDL Experiment Gate

- **Mechanism question**: does one frozen crack-oriented antisymmetric-opening
  representation encode the immediately preceding two process-zone
  coordinates better than plain gradients and Umax?
- **Claim changed if success**: authorize only a sparse, preregistered earlier-
  origin observability diagnostic; not early warning or training.
- **Claim changed if failure**: close this enriched retrospective route and its
  pairing/ROI/Williams/KAN rescues.
- **Cheaper diagnostic first**: completed deterministic offline analysis of the
  already accepted Request 28 package; no replay or training.
- **Minimal output asset**: audit script and decision, frozen analyzer, three
  compact experiment documents, four hashed decision payloads and closed
  attempt ledger.
- **Code/producer alignment**: Mac offline analysis only; no producer execution.
- **Success criteria**: all six enriched calibrations monotone and defined,
  enriched beats both plain and Umax on all six fold-target comparisons.
- **Failure criteria**: any structural failure or any missed frozen comparison.
- **Registry destination**: one negative row in
  `docs/pidl_experiment_inventory.md`, one concise current-status update in
  `docs/research_frontier.md`, and S3 reconciliation in
  `docs/research_storylines.md`.
- **Decision**: `reject/close enriched route`; evidence is qualified as a
  negative independently reviewed retrospective diagnostic.

## Minimum selective-integration plan

### Unit A — accept the Request 28 state package

Apply `f3bbc14` as one provenance-preserving commit in an isolated integration
worktree based on the current LTPP-preserving history. Its complete patch passes
an index-only apply check against `e71ece3`.

Because the uncommitted Request 27 inbox append is not part of that clean base,
preserve it in a separately reviewed adjacent unit after Unit A. Place it
without replacing the whole inbox, then verify that both the Request 28
acceptance update and Request 27 remain present in the assembled tree.

### Unit B — retain the terminal observability evidence

Import only these four additions from `94d9c2b`:

- `SENS_tensile/analyze_request28_xdem_observability.py`;
- `docs/experiments/request28_xdem_observability_gate_20260818.md`;
- `docs/experiments/request28_xdem_observability_gpt_pro_review_20260818.md`;
- `docs/experiments/request28_xdem_observability_track.md`.

Each addition passes an index-only apply check against `e71ece3`. Record
`94d9c2b` as source provenance. Do not import its inventory/frontier hunks and
do not merge its preceding KAN/RBF commits.

### Unit X — reconcile shared status documents

After the current owners of the dirty shared files are identified, manually:

1. append exactly one Request 28 negative row to
   `docs/pidl_experiment_inventory.md` without losing the four newer cross-Umax
   rows already present in the working copy;
2. replace only the Request 28 clause in `docs/research_frontier.md`, preserving
   the concurrent LTPP recognition/registration edits;
3. update S3 in `docs/research_storylines.md` from “Request 28 pending” to the
   terminal negative enriched result and its separate reopening condition.

Unit X must be a separate management/registry reconciliation commit. This keeps
scientific source evidence reviewable and prevents one branch's stale index
context from overwriting another storyline.

## Current stop

The dependency audit is complete.

## Isolated integration receipt — 2026-08-18

After explicit user approval, the approved units were assembled in:

```text
worktree: /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/request28-terminal-integration
branch: codex/request28-terminal-integration
base: e71ece3
```

Three unpublished commits were created:

| Commit | Unit | Content |
|---|---|---|
| `a2218cb` | A | exact cherry-pick of `f3bbc14`, accepting the Request 28 state package |
| `1e9ecab` | Request 27 | inbox append plus the 247-line forwardable handover; source file SHA256 `31d15cdc...` matches the main-worktree original |
| `59613d0` | B | analyzer plus the three terminal experiment documents from `94d9c2b`; only three trailing EOF blank lines were normalized |

The assembled diff has eight paths and 1,006 added lines. `4f9c8cf` remains an
ancestor, so the twelve LTPP commits are preserved. No KAN intermediate commit,
inventory hunk or frontier hunk was imported.

Validation:

- Request 28 independent package audit passes;
- a fresh temporary observability rerun returns the same terminal negative
  verdict and all five generated outputs, including `manifest.json`, are byte-
  identical to the canonical local archive;
- both Python entrypoints pass syntax/import help checks under the project
  Miniconda runtime;
- `git diff --check e71ece3..59613d0` passes;
- the integration worktree is clean and generated bytecode was removed.

Current stop: Unit X, merge into another branch, and remote preservation remain
separate explicit gates. Nothing was pushed.

## Unit X receipt — 2026-08-18

Unit X was completed on the isolated branch as commit `15f0975` with exactly
two tracked-file changes:

- one `request28_xdem_observability_gate_20260818` negative row in
  `docs/pidl_experiment_inventory.md`;
- one concise terminal Request 28 bullet plus date update in
  `docs/research_frontier.md`.

The main working copy's 13 concurrent inventory additions and LTPP frontier
edits were not copied into this branch. They belong to other uncommitted
bundles, and three linked cross-Umax tracks are not preserved on any Git branch.
This avoids turning Request 28 integration into an implicit approval of those
records.

The untracked management-layer `docs/research_storylines.md` was updated in the
main working copy, not the integration branch. S3 is now `paused` after the
Request 28 enriched gate, same-cycle assimilation, state-conditioned transition
and autonomous timing all failed their promotion rules. Its terminal-track
reference is branch-qualified until this integration branch is merged.

Current isolated head: `15f0975`. The worktree is clean.

## Remote-preservation receipt — 2026-08-18

After explicit user approval, the branch was pushed without creating a PR:

```text
origin/codex/request28-terminal-integration
15f0975b65489a9ef19e88030d8497c3327f2571
```

The local branch tracks that remote ref, and live `git ls-remote` returned the
same full SHA. No main merge, PR, tag or release was created. Merge review
remains a separate gate.
