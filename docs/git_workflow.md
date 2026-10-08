# Git Workflow — Mac / Authorised Producer Split

**Purpose**: explicit rules for development and authorised producers on this
repo. This supersedes ad-hoc machine assumptions. Current authorisation is
resolved from `AGENTS.md`; this file defines the shared Git and execution split.

All development and evidence integration follows
`docs/task_worktree_archive_protocol.md`. The shared checkout is not a working
branch for new tasks.

## 1. Roles

| Machine | Role | Responsibility |
|---|---|---|
| **Mac-PIDL** | **Dev** | All source code changes. Analysis & writing. Local Claude memory. Only lightweight import/unit sanity; no training smoke. |
| **Taobo GPU** | **GPU producer** | Authorised PIDL/surrogate training and bounded production runs under the shared-account protocol. |
| **`gpu-server` / D-26-09** | **GPU producer** | Direct public-key SSH producer for authorised GPU/PIDL/surrogate tasks; record Windows process/job identity and retrieval paths. |
| **`citpc12-ssh` / CITPC12** | **Windows-FEM producer** | Direct public-key SSH producer for GRIPHFiTH FEM runs and exports. FEM is a declared synthetic reference, not automatic physical truth or teacher qualification. |
| **Windows-PIDL** | **Legacy/specialised producer role** | Use only when currently authorised for the named task; historical handover rules remain provenance, not standing execution authority. |
| **CSD3** | **Not a default producer** | Do not submit or use as fallback unless the user explicitly authorises the named task. |

## 2. Mac-PIDL (dev)

### What Mac CAN do
- Modify anything under `source/`, `SENS_tensile/`, `docs/`, `fem/` from a
  dedicated task worktree
- Commit + push the task branch after lightweight import/unit sanity and, when
  needed, a producer-side smoke
- Refactor / add features / change signatures — but see §5 "red lines"

### What Mac MUST do
- **Before push**: run only lightweight import/unit sanity on Mac, e.g. `python -c "from source.compute_energy import get_psi_plus_per_elem"`. Do **not** run training-loop smoke on Mac.
- **Training smoke placement**: any command that enters `main.py` training,
  even `--n-cycles 1` or `--n-cycles 30`, must run on a currently authorised
  producer after checking compute and ownership. Record Run ID, producer
  alias/hostname, commit/snapshot, dirty status, PID/job, GPU, command, cwd,
  output/archive/log paths, start time, and retrieval route.
- **Commit message**: state whether the change is **"safe during running trainings"** or **"needs coordination"**. Examples:

  ```
  Add E2 psi_hack sanity hook for ceiling-mechanism validation

  Does not affect any existing run. E2 activation is opt-in via config.
  ```

  ```
  Refactor fatigue_history loss interface (BREAKING)

  Changes Δᾱ return shape from (n_elem,) to (n_elem, 2). All callers
  must update. Coordinate with Windows-PIDL via shared_research_log
  before pulling — existing trainings will fail on restart.
  ```

- **Loss / architecture / training-loop changes**: open a `[decision]` entry in `docs/shared_research_log.md` BEFORE the push. Wait for Windows to acknowledge (reply in log) — then push.

### Mac session template

```bash
cd "upload code"
git fetch --prune origin
git worktree list
# reuse the matching clean worktree, or create one from an explicit origin/<base>
# record task owner, branch, base SHA, and in-scope paths before editing
# ... work ...
# after each atomic unit:
git add <explicit files>
git commit -m "<action> <task-id> <object>"
git push --set-upstream origin <task-branch>
# verify local HEAD == remote HEAD; integrate only from a clean worktree
```

## 3. Windows-PIDL (only when authorised for a named task)

This section preserves its specialised Git-writing rules; it is not standing
execution authorisation. Confirm current authority in `AGENTS.md` first.

### What Windows CAN do
- Materialize the exact reviewed task commit supplied by Mac in a fresh,
  attributable run directory
- Run only the training case authorised by the frozen Experiment
- Return a compact Run receipt and raw-archive pointer. Producer-side source
  edits are exceptional; normally the Mac task branch owns code and receipts.

### What Windows MUST NOT do
- ❌ Modify `source/*.py` (core algorithm files)
- ❌ Modify `SENS_tensile/config.py` defaults (add-only via shared_log handshake; see §6 escape hatch)
- ❌ Modify `fem/*.py`
- ❌ Rewrite / delete other agents' entries in `docs/shared_research_log.md`
- ❌ Refactor / rename / delete existing files
- ❌ `git push --force`, `git reset --hard`, amend pushed commits

### Windows session template

```bash
# receive: Experiment ID, Run ID, exact commit, command, producer and paths
# verify the exact commit and clean/immutable source snapshot
# run only the authorised command in the fresh Run directory
# write raw outputs to the declared archive and return the compact receipt
```

## 4. Shared files — conflict-risk matrix

| File / Path | Who writes | Conflict handling |
|---|---|---|
| `source/*.py` | **Mac only** | Impossible if rule followed |
| `SENS_tensile/config.py` | **Mac only** (defaults); Windows via [decision] handshake | Impossible if rule followed |
| `SENS_tensile/plot_*.py`, `extract_*.py`, `compare_*.py` | **Mac only** | Impossible if rule followed |
| `SENS_tensile/run_*.py` (runners) | Task branch owner | One Experiment/runner family per task branch |
| `docs/shared_research_log.md` | Legacy append-only record | New work uses Experiment and Run receipts; do not rewrite history |
| `docs/*.md` (rules, handovers) | **Mac only** | Impossible if rule followed |
| `~/.claude/projects/.../memory/` | Each agent local | Never in git — no conflict |
| PIDL archives `hl_*/` | Each agent local | `.gitignore` blocks |
| Log files `runs_*.log`, `*.log.ckpt_key_err` | Each agent local | `.gitignore` blocks |
| Figures `figures/**`, `*.png`, `*.pdf` | Generator scripts local | `.gitignore` blocks |

## 5. Red lines (neither agent, ever)

- ❌ `git push --force` / `git push -f` — especially on `main`
- ❌ `git reset --hard` to discard committed work (use `git revert` for safe undo)
- ❌ `git rebase -i` on commits already pushed to origin/main
- ❌ Amend a commit after it's been pushed
- ❌ Overwrite an existing entry in `docs/shared_research_log.md`
- ❌ Push training-loop code changes while the OTHER machine is mid-run **without prior shared_log [decision] handshake**
- ❌ Commit `paper_draft/`, result files, personal memory (those stay local; see `CLAUDE.md` "不 commit 结果")

## 6. Escape hatches (rare, with protocol)

### 6.1 Windows hits a blocking bug it must fix immediately

```
1. Windows opens [blocker] entry in shared_research_log.md
2. Windows makes the smallest possible fix in source/
3. Windows commits with message:  "HOTFIX: <bug> — Mac please review"
4. Windows pushes
5. Windows in shared_log [blocker] entry logs: "pushed hotfix <SHA>, trainings resumed"
6. Next Mac session: review hotfix, refactor if needed, add [decision] acknowledging
```

### 6.2 Mac must change training-loop semantics while Windows is running

```
1. Mac opens [decision] entry in shared_research_log.md
   "Propose: change Δᾱ accumulator to include (..). Breaks running trainings
    on restart. Will push after Windows confirms."
2. Mac waits for Windows reply
3. Windows:
   - Either: "no active trainings, go ahead" → Mac pushes
   - Or:     "Umax=0.08 running, wait ~3h until cycle 200" → Mac waits
4. After push, Mac adds [update] sub-entry: "pushed <SHA>, Windows pull before
   next training restart"
```

### 6.3 Windows really needs a config.py change

```
Option A — defer: raise [decision] in shared_log, let Mac do it
Option B — urgent: make the smallest additive change (new key only, no
           modification of existing defaults); commit with  "config: add
           <key> default <val> — Mac-PIDL please review"; push; open
           [decision] entry for acknowledgment
```

## 7. Commit message format

Per project `CLAUDE.md`:
- First line: action verb + object (Add / Fix / Refactor / Update / Remove)
- Body: what / why / impact
- **No** `Co-Authored-By` footer
- English or Chinese, either fine

Helpful prefixes for this workflow:
- `log: <agent> <summary>` — when the commit is purely a shared_research_log update
- `HOTFIX: <issue>` — when Windows takes escape hatch 6.1
- `BREAKING: <change>` — when Mac changes training-loop semantics (coordinate first)

## 8. Why this split

1. **Zero code merge conflicts** — single writer (Mac) to `source/` + `config.py`. Windows only pulls.
2. **Windows CPU fully dedicated to training** — no dev cycles stolen
3. **Mac iterates freely** — no multi-writer lock contention on core code
4. **Shared log is append-only** — conflicts extremely rare; when they occur, `git pull --rebase` auto-resolves
5. **Results flow naturally** — Mac codes → Windows produces → shared log records

## 9. What changes if scope grows (future-proof)

If a third machine or third human author joins:
- Add them to the Agent table with a clear role label
- Each has one of: `dev` / `producer` / `reviewer`
- Only one `dev` per subsystem (no multiple writers to same source path)
- Producers may specialize (e.g. Windows-FEM = FEM-only producer; Windows-PIDL = PIDL-only producer)

## 10. Related docs

- `CLAUDE.md` (project root) — general commit / memory hygiene rules
- `docs/shared_research_log.md` — cross-agent log (the communication channel)
- `.gitignore` — what never enters git (checkpoints, figures, logs)
- Each agent's `~/.claude/projects/<path>/memory/` — local per-agent understanding (not in git)
