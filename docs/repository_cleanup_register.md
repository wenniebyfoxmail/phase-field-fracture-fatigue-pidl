# Repository Cleanup Register

**Snapshot date**: 2026-08-17
**Scope**: `/Users/wenxiaofang/phase-field-fracture-with-pidl/` and the GitHub-
synced child repository `upload code/`
**Mode**: inventory only; no deletion, move, commit, merge or push is authorized
by this document.

## Execution update — 2026-08-18

- Isolated the completed RRaPINN G1/G1b/G2 bundle from the mixed checkout onto
  local branch `codex/rrapinn-mechanical-risk-g2` at commit `27b634cd`, based
  directly on `origin/codex/m2s-framework-validation@699ae79`.
- The isolated commit contains nine reviewable source/test/protocol/inventory
  files and reproduces 47 passing lightweight tests. It has not been pushed.
- Removed the two clean detached checkouts `agitated-newton-103f04` and
  `objective-cray-aec056`. Their shared commit `40dce7c` and named branches are
  retained. Their only ignored `.claude` settings files were byte-identical to
  the copies in the main checkout.
- Removed the now-branch-preserved RRaPINN modifications/untracked files from
  the mixed main checkout. No other storyline files, dirty worktrees, branches,
  generated evidence or local archives were removed.
- Reconciled Request 28 history without merging it. `e71ece3`, `fc65daf` and
  `1176250` are patch-equivalent; `e884524`/`368a7e8` are intermediate records;
  later local commits `f3bbc14` and `94d9c2b` accept the replay package and
  close the enriched observability gate negatively. The terminal branch is
  clean but has no configured upstream, so it requires deliberate preservation
  and dependency review before selective integration.
- Completed that dependency review. `f3bbc14` is a clean acceptance unit; the
  analyzer plus three experiment documents from `94d9c2b` are a clean terminal-
  evidence unit; its inventory/frontier hunks must be rebuilt in current Bundle
  X context. A live remote query confirmed that the terminal branch itself is
  not remotely preserved. No integration or publication was performed.
- After explicit approval, created clean isolated worktree/branch
  `codex/request28-terminal-integration` from `e71ece3` and assembled unpublished
  commits `a2218cb`, `1e9ecab`, and `59613d0`. The branch retains the twelve LTPP
  commits, preserves Request 27 separately, excludes shared-index hunks, and
  reproduces the terminal Request 28 outputs byte-for-byte. It has not been
  pushed or merged.
- Completed Unit X as `15f0975`, then remotely preserved the clean branch at
  `origin/codex/request28-terminal-integration` with matching full SHA
  `15f0975b65489a9ef19e88030d8497c3327f2571`. No PR, main merge, tag or release
  was created.

### Post-snapshot worktree addition

| Worktree / branch | HEAD | Dirty | Storyline | Decision |
|---|---|---:|---|---|
| `.codex/worktrees/request28-terminal-integration` — `codex/request28-terminal-integration` | `15f0975` | 0 | S3 / Request 27–28 | `remote-preserved`; no PR, review before any merge |

## Repository topology

| Path | Role | Git status | Size at snapshot | Management rule |
|---|---|---|---:|---|
| project root | local research workspace/aggregation root | not a Git repository at inspection time | dominated by archives | Do not treat as the GitHub source of truth. |
| `upload code/` | shared code and compact evidence repository | GitHub remote `wenniebyfoxmail/phase-field-fracture-fatigue-pidl` | 2.4G | Code truth; clean by storyline and asset class. |
| `GRIPHFiTH/` | independent FEM project | separate Git repository | 654M | Keep separate history and workflow. |
| `overleaf_paper_68334c/` | thesis/manuscript checkout | separate Git repository | 344M | Keep separate Overleaf history. |
| `local_archive/` | raw/generated research evidence | local-only archive | 220G | Preserve provenance; clean duplicates only after manifest/hash review. |

The parent `AGENTS.md` still describes the project root as a parent repository,
but no root `.git` repository was present in this snapshot. Treat this as
documentation drift to resolve deliberately; do not recreate or delete a root
repository without a separate decision.

## GitHub-synced repository snapshot

| Metric | Snapshot |
|---|---:|
| tracked files | 703 |
| current branch | `codex/m2s-framework-validation` at `e71ece3` |
| current upstream | `origin/codex/m2s-framework-validation` at `699ae79` |
| unpublished commits on current branch | 13 |
| tracked modified paths | 13 |
| untracked status entries | 90 |
| local branches | 48 |
| registered worktrees | 25 |
| remote-tracking branches observed locally | 27 |
| remote `main` | `389f618` from live `ls-remote` check |
| local `main` | `9c9c30f`, one commit behind its observed remote |

This is a preservation risk, not permission to bulk-commit. The 13 unpublished
commits and 103 dirty status entries belong to several storylines and must be
separated before synchronization.

## Dirty main checkout classification

| Area | Status-entry count | Likely class | Storyline routing | Required review |
|---|---:|---|---|---|
| `SENS_tensile/` | 15 untracked plus 2 modified | source/analysis/figure | S3, S4, Freeze-Then-Select diagnostics | Separate code, canonical figure and generated output. Verify figure sidecar. |
| `docs/experiments/` | 23 untracked plus 4 modified | compact research records | mainly S1, S6, S7 | Keep canonical track and dated decisions; check which are complete and internally linked. |
| `docs/reviews/` | 16 untracked | review evidence | S6, S7 | Preserve if tied to a decision; avoid treating review request as completed review. |
| other `docs/` | 18 untracked plus 4 modified | handovers, plans, inventories | S1–S5 and management | Split by storyline and verify current status before commit. |
| `scripts/` | 9 untracked plus 4 modified | source code | mainly S1, S6, S7 | Pair each runner with its experiment/decision and tests. |
| `tests/` | 9 untracked | source tests | Freeze-Then-Select and LTPP | Commit with the code they validate, not as a separate miscellaneous batch. |

Tracked modified paths at the snapshot:

- `SENS_tensile/figfiles/pidl_fem/fig_A3_SN_comparison.png`
- `SENS_tensile/generate_figs_pidl_fem.py`
- four LTPP recognition/registration experiment documents
- `docs/handovers/windows_fem_inbox.md`
- `docs/pidl_experiment_inventory.md`
- `docs/research_frontier.md`
- four LTPP acquisition/annotation scripts

No cleanup action should overwrite these edits.

## Worktree register

Decision labels below are provisional:

- `protect-dirty`: inspect and preserve uncommitted content before any removal;
- `review-merge-archive`: clean checkout, but branch purpose/evidence must be
  reviewed before merging or removing the checkout;
- `review-stale`: clean checkout whose branch is materially behind its upstream;
- `detached-review`: detached checkout; prove no unique commit/content before
  removal.

| # | Worktree / branch | HEAD | Dirty | Size | Storyline | Provisional decision |
|---:|---|---|---:|---:|---|---|
| 1 | main checkout — `codex/m2s-framework-validation` | `e71ece3` | 103 | 2.4G | mixed S1/S3/S4/S6/S7 | `protect-dirty`; split by storyline before push |
| 2 | `.codex/worktrees/data-efficient-cycle-forecast` — `codex/data-efficient-cycle-forecast` | `90cf8a3` | 0 | 21M | S2/S5 | `review-merge-archive` |
| 3 | `.codex/worktrees/fem-umax-reaudit` — `codex/fem-umax-reaudit` | `59d0b49` | 0 | 19M | S3/S4 | `review-merge-archive` |
| 4 | `.codex/worktrees/inverse-fracture-state-assimilation` — `codex/inverse-fracture-state-assimilation` | `cf22bcd` | 0 | 32M | S2/S3 | `review-merge-archive` |
| 5 | `.codex/worktrees/optimizer-cross-residual-gate` — `codex/optimizer-cross-residual-gate` | `2e145ef` | 0 | 18M | S4 | `review-merge-archive` |
| 6 | `.codex/worktrees/road-closed-loop-integration` — `codex/road-closed-loop-integration` | `762abb7` | 0 | 33M | S1/S2 | `review-merge-archive` |
| 7 | `.codex/worktrees/road-rescaling-bridge` — `codex/road-rescaling-bridge` | `022938d` | 0 | 35M | S1/S2 | `review-merge-archive` |
| 8 | `.codex/worktrees/temporal-graph-transformer` — `codex/temporal-graph-transformer` | `866b9ef` | 0 | 24M | S2 | `review-merge-archive` |
| 9 | `.codex/worktrees/toy-road-evidence-integration` — `codex/toy-road-evidence-integration` | `1c54836` | 0 | 41M | S1/S2 | `review-stale`; branch was 76 commits behind upstream |
| 10 | `.claude/worktrees/agitated-newton-103f04` — detached | `40dce7c` | 0 | 2.7M | infrastructure | `removed-20260818`; commit and branch retained |
| 11 | `.claude/worktrees/exp+f-shape-p-learnable` — `worktree-exp+f-shape-p-learnable` | `e162acd` | 3 modified | 1.4M | S4 | `preserve-patch-do-not-merge`; unique unverified prototype, no unique committed branch history |
| 12 | `.claude/worktrees/exp/alpha2-multihead` — `claude/exp/alpha2-multihead` | `187a0e0` | 0 | 7.8M | S4 | `review-merge-archive` |
| 13 | `.claude/worktrees/exp/fourier-feature` — `claude/exp/fourier-feature` | `a89765c` | 0 | 16M | S4 | `review-merge-archive`; no upstream configured |
| 14 | `.claude/worktrees/exp/inverse-alphaT` — `codex/exp/inverse-alphaT` | `4bfa57b` | 0 | 2.9M | S4 | `review-merge-archive`; negative evidence |
| 15 | `.claude/worktrees/exp/tip-local-net` — `codex/exp/tip-local-net` | `229f5a0` | 5 modified | 261M | S4 | `preserve-patch-do-not-merge`; committed branch is remote-preserved, dirty combined experiment is superseded by the closed family |
| 16 | `.claude/worktrees/hard-crack-tip-enrichment` — `claude/hard-crack-tip-enrichment` | `b2d8432` | 3 untracked | 2.3M | S4 | `extract-negative-record`; retain ratified closure/report, do not revive superseded dev plan |
| 17 | `.claude/worktrees/hybrid-patch-quadrature` — `codex/hybrid-patch-quadrature` | `88e5936` | 0 | 2.4M | S4 | `review-merge-archive`; no upstream configured |
| 18 | `.claude/worktrees/local-patch-domain-decomp` — `worktree-local-patch-domain-decomp` | `8ab4552` | 1 untracked | 3.0M | S4 | `superseded-note`; remote preserves code commit, old conditional-GO summary conflicts with later FBPINN negative result |
| 19 | `.claude/worktrees/local-spectral-tip-patch` — `claude/local-spectral-tip-patch` | `b2d8432` | 1 untracked | 2.1M | S4 | `superseded-design`; later tip-local Fourier/SIREN experiments answer the route negatively |
| 20 | `.claude/worktrees/objective-cray-aec056` — detached | `40dce7c` | 0 | 2.7M | infrastructure | `removed-20260818`; commit and branch retained |
| 21 | `.claude/worktrees/pedantic-chatterjee-10cae2` — `claude/codex-update-issue-214248` | `9c9c30f` | 0 | 2.7M | handover/infrastructure | `review-merge-archive` |
| 22 | `.claude/worktrees/sdf-discontinuity-embedding` — `worktree-sdf-discontinuity-embedding` | `1b538d8` | 0 | 2.5M | S4 | `review-merge-archive`; branch is two commits ahead of upstream |
| 23 | `.codex/worktrees/discontinuity-jump-head-design` — `codex/discontinuity-jump-head-design` | `03b64cd` | 0 | 48M | S4 | `review-merge-archive` |
| 24 | `.codex/worktrees/history-driver-diagnostic` — `codex/history-driver-diagnostic` | `70f4d23` | 0 | 48M | S4 | `review-merge-archive`; negative/diagnostic evidence |
| 25 | `.codex/worktrees/pidl-state-timing-diagnostic` — `codex/pidl-state-timing-diagnostic` | `5fa9dd6` | 1 modified | 213M | S4 | `preserve-protocol-candidate`; unique useful protocol edits, branch also two commits behind upstream |

## Dirty secondary worktree forensic audit

This audit inspected working diffs, untracked files, recent history, branch
divergence and overlap with the current integration checkout. It did not test or
run any experiment.

### 1. Learnable fatigue-degradation exponent

**Worktree**: `.claude/worktrees/exp+f-shape-p-learnable`
**Branch state**: no patch-unique committed history versus `origin/main`; the
branch base is about 180 commits behind the observed `origin/main`.
**Dirty payload**: 135 added / 7 deleted lines across:

- `SENS_tensile/config.py`
- `source/fatigue_history.py`
- `source/model_train.py`

The payload introduces a learnable Carrara degradation exponent `p`, a soft
prior around `p=2`, one p-only optimizer step per cycle, and conditional graph
attachment through `compute_fatigue_degrad`. The code is not present in the
current integration checkout. The archived shared research log says that a
bit-exact backward-compatibility smoke and a 30-cycle learnable-p smoke were
required, but no result or test receipt was found in this audit.

**Credibility**: `inconclusive implementation prototype`.
**Decision**:

- preserve an exact patch or commit on a clearly archival branch before removing
  the checkout;
- do not merge the implementation into current S4 code;
- do not call learnable-p an untried active route: S4 is paused and the prototype
  lacks its required smoke evidence;
- if ever reconsidered, it requires a new PIDL experiment gate and modern
  checkpoint/optimizer-state review.

### 2. Tip-local plus S2 warm-up combination

**Worktree**: `.claude/worktrees/exp/tip-local-net`
**Committed branch**: 22 patch-unique commits are already preserved on
`origin/codex/exp/tip-local-net`.
**Dirty payload**: 329 added / 6 deleted lines across five files. It adds:

- combined S2 + tip-local runner controls;
- tip-only same-energy warm-up with optional global freezing;
- energy and gradient diagnostic exports;
- worktree mesh fallback behavior;
- a local change from ten confirmation cycles to three;
- a stale frontier statement saying MLP follow-tip/field plots were still needed.

The current registry already closes the broader MLP/Fourier/SIREN tip-local
family as negative/diagnostic: timing changed, but fields remained
centerline/right-boundary dominated and did not close the active-driver gate.

**Credibility**: `superseded experimental code`; committed predecessor remains
useful negative evidence.
**Decision**:

- preserve the dirty patch for provenance, but do not merge it wholesale;
- do not merge the stale `research_frontier.md` edit;
- do not import the three-cycle confirmation change as part of cleanup;
- retain remote committed history and canonical result summaries, then the local
  checkout can become a removal candidate after the patch is archived.

### 3. Williams hard crack-tip enrichment records

**Worktree**: `.claude/worktrees/hard-crack-tip-enrichment`
**Branch state**: no unique committed history versus current shared history.
**Untracked payload**:

- `docs/branch_decision.md`
- `docs/branch_hard_crack_tip_enrichment.md`
- `docs/report_williams_v1v2_trajectory.md`

`branch_decision.md` records a user-ratified Option-A closure on 2026-05-14:
single/multi-scalar Williams hard injection is a paper-grade negative result and
should not continue to A1d or alpha enrichment. The longer design document is
explicitly superseded. The trajectory report contains the useful quantitative
mechanism narrative but ends with an older A1d option that conflicts with the
ratified closure.

**Credibility**: `negative`, with `branch_decision.md` as the controlling record.
**Decision**:

- extract a compact canonical negative-result record plus the quantitative
  trajectory evidence;
- mark the older development plan and A1d recommendation as superseded;
- do not preserve all three files as equally current instructions;
- after extraction, the checkout has no known unique code requirement.

### 4. Local patch/domain-decomposition summary

**Worktree**: `.claude/worktrees/local-patch-domain-decomp`
**Committed branch**: its one unique POU/two-network diagnostic commit is already
preserved on `origin/worktree-local-patch-domain-decomp`.
**Untracked payload**: `EXECUTIVE_SUMMARY.txt`, a prospective literature/design
memo recommending conditional GO before the later experiments were completed.

The current experiment inventory records the subsequent FBPINN chain as
diagnostic/negative: it changed propagation mode but left the active driver
off-location and non-FEM-like.

**Credibility**: `superseded prospective design`, not a result.
**Decision**: do not promote the old GO recommendation. Preserve at most a
lineage pointer from the completed FBPINN record; remote code history is already
safe, so this checkout can become a removal candidate after the untracked memo
is explicitly archived or discarded with approval.

### 5. Local spectral tip-patch design

**Worktree**: `.claude/worktrees/local-spectral-tip-patch`
**Branch state**: no unique committed history versus current shared history.
**Untracked payload**: `docs/branch_tip_local_spectral.md`, a 296-line pre-run
SIREN design gated on an old SDF/DENN smoke.

Later tip-local Fourier/SIREN runs were completed and are registered as
negative/diagnostic. The design therefore documents historical rationale but is
not an active experiment plan.

**Credibility**: `superseded design`.
**Decision**: retain only if its architectural rationale is needed for a methods
appendix or lineage note; do not treat its GO/NO-GO table as current. The
checkout can become a removal candidate after that decision.

### 6. PIDL result-check protocol expansion

**Worktree**: `.codex/worktrees/pidl-state-timing-diagnostic`
**Branch state**: substantial committed diagnostic history is not integrated
into the current branch, and the checkout is two commits behind
`origin/codex/pidl-state-timing-diagnostic`.
**Dirty payload**: 41 added / 5 deleted lines in
`docs/pidl_experiment_result_check_protocol_2026-06-01.md`. The current
integration checkout does not contain this file.

The edits standardize:

- cyclewise reductions for damage, raw energy, degradation, active energy,
  fatigue history and fatigue degradation;
- `g_alpha` reporting separately from `f_fatigue`;
- consistent `FEM - PIDL` residual orientation;
- region-wise min/mean/percentile/integral metrics;
- energy/irreversibility aliases and balance-parameter trajectories.

These additions are consistent with the later active-driver/process-zone claim
boundary and appear reusable beyond the original worktree.

**Credibility**: `supporting protocol candidate`; no experiment result is implied.
**Decision**:

- preserve this file before updating or removing the worktree;
- compare it with the two newer remote commits, resolve rather than overwrite;
- review it as a standalone documentation integration candidate;
- do not remove this checkout until the protocol and the branch's non-integrated
  committed history have explicit destinations.

## Dirty-worktree preservation order

1. Preserve/review the PIDL result-check protocol candidate.
2. Extract the ratified Williams negative-result record.
3. Save exact patches for learnable-p and tip-local/S2 dirty implementations,
   clearly labelled unverified/superseded.
4. Resolve the two superseded prospective memos.
5. Re-run `git status`, branch uniqueness and upstream checks before proposing
   any worktree removal.

## Non-worktree branch register

The remaining local branches are preserved by family below. Their checkout is
not currently registered as a worktree, so deletion is not implied.

| Family | Branches | Initial interpretation |
|---|---|---|
| current FEM handoff | `agent/fem-request-28` | Current S3 producer handoff; retain until Request 28 is integrated. |
| old Claude task branches | `claude/adoring-swirles-5b6b35`, `claude/cranky-jones-e9fd83`, `claude/dreamy-banach-a54f2d`, `claude/elastic-keller-ffd72a`, `claude/elastic-nobel-ce6fe4`, `claude/fervent-newton-26b757`, `claude/focused-wilson-b736e6`, `claude/gallant-fermat-5b9770`, `claude/happy-raman-beeaaf`, `claude/objective-cray-aec056`, `claude/pedantic-chatterjee-10cae2`, `claude/pedantic-thompson-5d13cc`, `claude/thirsty-albattani-4555db`, `claude/thirsty-wright-e7e4d2`, `claude/trusting-dijkstra-6258d0`, `claude/vigorous-clarke-422f8b` | Many are substantially behind `origin/main`; inspect unique commits and handover value, then archive or remove. |
| S4 experiment branches | `claude/exp/alpha3-xfem-jump`, `claude/exp/supervised-alpha-c`, `claude/sidecar-adaptive-sampling`, `codex/field-level-metric-representation`, `codex/inverse-femmesh-soft-hist0` | Closed/diagnostic PIDL families; preserve unique code and decision records, then reduce checkout/branch clutter. |
| shared tooling | `codex/figure-sidecar-validator-sync` | Candidate to integrate into the canonical development branch after diff/test review. |
| base branch | `main` | Local branch is one commit behind observed remote; do not merge dirty mixed work into it in bulk. |

## Asset-class decisions

| Asset class | Current home | Decision |
|---|---|---|
| source code, tests, small configs | `upload code/` | Track in Git, grouped with the experiment/claim they support. |
| canonical track/decision/review summaries | `upload code/docs/` | Track in Git; keep one stable track per storyline/subtrack. |
| raw checkpoints, arrays and generated result folders | `local_archive/`, Taobo or producer archives | Keep out of Git by default; add provenance README/manifests. |
| canonical paper figures | `docs/figures/` or manuscript repo | Track only when explicitly canonical and accompanied by the required sidecar. |
| downloaded references | currently about 1.0G under `upload code/references/` | Audit licensing, duplication and reproducibility; prefer manifests/DOIs over bulky duplicates where recoverable. |
| `.claude/` and `.codex/` worktrees | nested under/around the shared repo | Development workspaces, not experiment evidence. Remove only after unique-commit and dirty-state review. |

## Safe cleanup sequence

### Phase 0 — freeze and ownership

- Do not delete, move, reset, rebase, bulk-commit or force-push.
- Record an owner/storyline for every dirty path.
- Inspect the six dirty secondary worktrees before changing the main checkout.
- Treat the current 13 unpublished commits as a recoverable integration stack.

### Phase 1 — make the current checkout reviewable

Split the main dirty state into reviewed bundles:

1. S3 Request 28 / first-detect observation bridge;
2. S6/S7 LTPP registration and recognition records;
3. Freeze-Then-Select code/tests/docs;
4. PIDL/FEM canonical figure and inventory updates;
5. project-management documents.

For each bundle: inspect diff, confirm canonical track, run relevant lightweight
tests, then commit separately only after user review.

### Phase 2 — synchronize shared truth

- Confirm whether the 13-commit current branch should be pushed as an
  integration branch or split into reviewed topic branches.
- Integrate the current Request 28 remote branch without overwriting local
  handover edits.
- Bring local `main` up to the observed remote only after the dirty integration
  work is protected.

### Phase 3 — worktree and branch reduction

For each worktree:

1. inspect status, log and diff against upstream;
2. identify unique code/docs and linked archive evidence;
3. update this register with `keep`, `merge`, `archive` or `remove`;
4. remove a checkout only after its content is preserved and the user approves
   the deletion batch.

Prioritize dirty worktrees, detached worktrees, branches without upstreams, and
branches far behind upstream. Size alone is not a deletion criterion.

### Phase 4 — archive hygiene

- Add a local README to important archive endpoints missing purpose, source
  commit, settings, credibility, limitations and next action.
- Hash-check suspected duplicates before deletion.
- Keep negative results needed to prevent repeated work.
- Search path references before moving active code or canonical assets.

## Immediate next review queue

Completed inventory work:

- the six dirty secondary worktrees have forensic decisions above;
- the original 103 main-checkout entries, two cleanup documents and one
  concurrent cross-Umax track have been routed in
  `docs/cleanup_main_checkout_bundle_manifest_20260817.md`;
- the 13 unpublished commits are separated into twelve LTPP commits and one
  superseded-in-wording Request 28 commit.

Next review queue:

1. Protect concurrent Bundle-A ownership and reconcile corrected Request 28.
2. Review Bundle C Freeze-Then-Select as the smallest self-contained
   code/test/evidence package.
3. Review the Bundle-B August 12 continuation before deciding how to publish
   the existing twelve-commit LTPP chain.
4. Review Bundle-D figure provenance and stale FEM-teacher documents.
5. Integrate shared ledgers/frontier last; no deletion batch yet.
