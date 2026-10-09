# Task, Worktree, Commit, and Archive Protocol

**Status:** mandatory for new tasks and next-touched legacy work

**Principle:** one task, one primary owner, one branch, one clean worktree

This protocol adds an execution layer beneath the scientific structure in
`docs/research/INDEX.md`. It prevents multiple agents or research directions
from accumulating in one checkout while avoiding duplicate paperwork.

## 1. Smallest useful task boundary

A task is the smallest unit that can be reviewed, committed, pushed, and later
recovered without unrelated files.

| Task class | Primary owner | Canonical record |
|---|---|---|
| Claim-changing research | one Experiment ID | `docs/research/Sxx/Sxx-Exxx/experiment.md` |
| Producer execution | one Run ID under an Experiment | compact Run receipt plus raw archive pointer |
| Dataset/measurement qualification | one Experiment ID | Experiment record, manifest and decision |
| Claim-bound analysis or figure set | the Experiment it evaluates | analysis table/figure README and decision |
| Infrastructure, cleanup, or governance | one named scope | commit history; add one durable doc only when future agents need it |
| Manuscript-only integration | one section/claim set | manuscript branch and its cited evidence pointers |

Do not create a second task record when the Experiment, Run receipt, commit, or
analysis README already carries the needed provenance.

## 2. Branch and worktree contract

Before editing:

1. Name the primary owner and task class.
2. Inspect `git worktree list`, relevant branches, and the target base commit.
3. Reuse one matching clean worktree or create a new worktree from an explicit
   `origin/<branch>` or commit SHA.
4. Record the branch, base SHA, in-scope paths, excluded paths, and intended
   validation in the task commentary or Experiment record.

Branch names:

```text
codex/s02-e004-tiff-repeatability-20261009
codex/s04-e016-request31-repair-20261009
codex/infra-task-archive-protocol-20261009
codex/writing-ch2-mechanism-20261009
```

Rules:

- Never start a new task from an uncommitted mixed checkout.
- Never let two active tasks share a worktree.
- A task may touch shared source only when that dependency is declared in
  scope. Otherwise create a follow-up task.
- If another active task changes an in-scope path, stop integration and resolve
  ownership; do not copy the newest file opportunistically.
- The shared checkout is quarantined integration/recovery space until its
  historical assets are drained. Do not add new work there.

## 3. What belongs in Git

Track:

- source, tests, small configuration and environment recipes;
- frozen protocols, amendments, code/evidence reviews and compact Run receipts;
- concise CSV/JSON tables needed to reproduce a stated verdict;
- canonical analysis scripts, figure reading guides and explicit raw-archive
  pointers.

Keep outside Git by default:

- checkpoints, arrays, raw logs, caches and downloaded datasets;
- producer run directories and bulk figures;
- private identity/annotation keys;
- temporary browser/review captures unless they are the only evidence of a
  consequential external review.

Raw and generated evidence lives under:

```text
local_archive/experiments/<experiment-id>/runs/<run-id>/
```

or a declared external producer path. Its nearby README records source commit,
Run ID, purpose, raw location, credibility, limitations and next action.

## 4. Commit units

Use the fewest commits that preserve meaningful review boundaries. Typical
claim-changing work has up to four units:

1. `Register <experiment-id> <question>` — frozen protocol and data identity.
2. `Implement <experiment-id> <runner>` — code, tests and code-review fixes.
3. `Record <run-id> <outcome>` — receipt and compact evidence.
4. `Close <experiment-id> as <verdict>` — evidence review, verdict and claim
   impact.

Combine adjacent units when the work is genuinely small; never create empty
ceremonial commits. Split whenever code review, producer execution, or evidence
interpretation can change independently.

For every commit:

- stage explicit paths, never the whole mixed tree;
- include one primary task owner only;
- keep execution status separate from scientific verdict;
- state whether the change is safe for active producer runs or needs
  coordination;
- run the smallest relevant static/unit validation and record what was not run.

Shared ledgers such as `docs/research_frontier.md`,
`docs/pidl_experiment_inventory.md`, and Storyline indexes are integrated last,
after the owning Experiment commits are stable.

## 5. Producer handoff

A producer receives exactly:

- Experiment ID and Run ID;
- reviewed commit SHA and protocol revision;
- runner/config/command and authorised producer;
- input identity and fresh output/archive/log paths;
- stop rule, minimum evidence and retrieval route.

The producer does not choose a new scientific design or silently edit source.
Any material change returns to a new Mac task commit and invalidates the prior
code-review PASS. A successful process start is execution evidence only.

## 6. Integration

Integration occurs from a clean integration worktree:

1. Fetch remote refs and verify the task branch HEAD.
2. Review the task diff against its declared base and owner.
3. Verify tests, receipts and archive pointers in proportion to risk.
4. Cherry-pick or merge only the reviewed task commits.
5. Resolve shared indexes last; do not import stale index hunks from an older
   branch.
6. Push without force and verify local and remote SHAs match.

Passing tests proves code behavior only. It does not by itself establish Run
readiness, evidence validity, physical truth, field validity or publication
claims.

## 7. Close and archive

A task is recoverably closed only when:

- its exact branch and HEAD are known;
- the remote branch contains the intended commits, or a recoverable local
  archive is explicitly recorded;
- the worktree is clean;
- raw payload location and retrieval status are recorded when a Run occurred;
- the scientific verdict and blocked claims are explicit when applicable;
- the next action or stop decision is stated.

Only then may the worktree be archived or removed. Removing a worktree never
implies deleting its branch, remote history, or raw evidence.

## 8. Minimal handoff

Every handoff needs only these fields, placed in the existing Experiment, Run
receipt, commit/PR, or task response rather than a duplicate form:

```text
Task owner / ID:
Branch and base SHA:
Current HEAD and remote state:
Status / verdict:
Changed paths:
Validation performed:
Raw archive / receipt:
Blocked claims or limitations:
Next action or stop rule:
```

## 9. Acceptance criteria

The task organization passes when all five statements are true:

1. **Ownership:** one primary task owner explains every changed path.
2. **Isolation:** the work was performed in a dedicated clean worktree.
3. **Recoverability:** exact commits are pushed or explicitly archived before
   checkout removal.
4. **Evidence separation:** raw payload, compact evidence, execution status and
   scientific verdict are not conflated.
5. **Minimality:** no duplicate ledger, hash forest, ceremonial commit, or
   secondary diagnostic is required to declare organizational success.

If any statement fails, preserve the worktree and classify it; do not clean it
by reset or bulk commit.

## 10. Current mixed-checkout migration

For the existing `codex/m2s-framework-validation` checkout:

1. stop assigning new work to it;
2. preserve active local-only S02-E004 work and any clean local-only branches;
3. wait for active S01 and Windows-FEM writers to finish;
4. extract compact assets by primary task owner into clean branches;
5. keep `local_archive/`, generated outputs and private keys local-only;
6. reconcile shared indexes last;
7. repoint or retire the mixed branch only after every remaining path has a
   recoverable destination.

### Migration checkpoint — 2026-10-09

The following compact task bundles are remote-preserved:

| Owner | Remote branch | Preserved HEAD | State |
|---|---|---|---|
| S01-E001 | `codex/s01-e001-pavetrack-20261009` | `27647a2` | later task-owned work and negative confirmatory outcome are remote-preserved |
| S02-E003 | `codex/s02-e003-negative-20261008` | `f9fab18` | isolated three-commit negative-result bundle |
| S02-E004 | `codex/s02-e004-tiff-repeatability-20261009` | `97570d0` | seven task-owned commits, including image-readiness gate and annotation-interface review, remote-preserved |
| S04-E016 | `codex/s04-e016-request31-storage-block-20261009` | `5b1eec2` | initial five-file Request 31 snapshot only; later launcher/run records remain in the mixed checkout |
| S09 | `codex/s09-neural-operator-prototype-20261008` | `95ec8fd` | remote-preserved task branch |

The 14 older commits preceding S02-E003 on the mixed branch are already
contained, with their original identities, in remote task/history branches.
The three S02-E003 and five S02-E004 commits were re-based into the isolated
branches above, so their content is preserved under new commit identities.

The two later S02-E004 commits on the mixed branch were also extracted into its
task branch and verified byte-for-byte. On 2026-10-09 at 17:24 BST, the mixed
checkout still held 23 modified tracked paths and 821 untracked files, of which
534 were under `local_archive/`. The later S04-E016 records are not covered by
its initial branch snapshot. Do not clean or repoint the mixed checkout until
every remaining dirty path has been checked against a recoverable destination.
