# Git Workflow — Mac / Windows Dev/Producer Split

**Purpose**: explicit rules for the two-machine collaboration on this repo.
This supersedes any ad-hoc conventions. Both machines' Claude agents MUST
follow these rules.

## 1. Roles

| Machine | Role | Responsibility |
|---|---|---|
| **Mac-PIDL** | **Dev** | All source code changes. Interactive experiments. Analysis & writing. Local Claude memory. |
| **Windows-PIDL** | **Producer** | Pull Mac's code. Run training cases. Report results via `docs/shared_research_log.md`. May add NEW runner scripts, but must not modify core. |
| **Windows-FEM** | **Reference producer** | GRIPHFiTH FEM runs. Produces ground-truth data in `~/Downloads/_pidl_handoff_*/`. Reports via shared_research_log. |

## 2. Mac-PIDL (dev)

### What Mac CAN do
- Modify anything under `source/`, `SENS_tensile/`, `docs/`, `fem/`
- Commit + push freely after local smoke test
- Refactor / add features / change signatures — but see §5 "red lines"

### What Mac MUST do
- **Before push**: local smoke test (at minimum: `python -c "from source.compute_energy import get_psi_plus_per_elem"`-level import test; ideally run 1-2 training cycles)
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
git pull --ff-only origin main                # start
# read docs/shared_research_log.md top entries
# ... work ...
# after each atomic unit:
git add <files> && git commit -m "<message>"
git push origin main
# end of session: final pull + push
```

## 3. Windows-PIDL (producer)

### What Windows CAN do
- `git pull` from origin/main (fast-forward; almost always works since Windows doesn't diverge)
- Run any training case on pulled code
- **Add** new runner / driver scripts:
  - `SENS_tensile/run_*.py` (e.g. `run_only_Umax_008_fast.py`)
  - `SENS_tensile/*_sweep.py` (e.g. `run_sequential_coeff3.py`)
  - `*.sh` launcher scripts
  - These are **new files**, not modifications of existing ones.
- **Append** to `docs/shared_research_log.md`:
  - New dated entry at top of findings section, or
  - `### [reply] Windows-PIDL · YYYY-MM-DD` sub-section under an open `[question]` entry
  - Never edit existing entries (except to add a `### [update]` sub-section)
- Commit + push its own new runner scripts and shared_log entries

### What Windows MUST NOT do
- ❌ Modify `source/*.py` (core algorithm files)
- ❌ Modify `SENS_tensile/config.py` defaults (add-only via shared_log handshake; see §6 escape hatch)
- ❌ Modify `fem/*.py`
- ❌ Rewrite / delete other agents' entries in `docs/shared_research_log.md`
- ❌ Refactor / rename / delete existing files
- ❌ `git push --force`, `git reset --hard`, amend pushed commits

### Windows session template

```bash
cd "upload code"
git pull --ff-only origin main                # always ff, never diverges
# read docs/shared_research_log.md top entries (especially any [decision] from Mac)
# ... run training cases ...
# after a run completes:
# add entry to shared_research_log.md
git add docs/shared_research_log.md [any new runner scripts]
git commit -m "log: Windows-PIDL Dir 6.x Umax sweep results"
git push origin main
```

## 4. Shared files — conflict-risk matrix

| File / Path | Who writes | Conflict handling |
|---|---|---|
| `source/*.py` | **Mac only** | Impossible if rule followed |
| `SENS_tensile/config.py` | **Mac only** (defaults); Windows via [decision] handshake | Impossible if rule followed |
| `SENS_tensile/plot_*.py`, `extract_*.py`, `compare_*.py` | **Mac only** | Impossible if rule followed |
| `SENS_tensile/run_*.py` (runners) | Either — but NEW files only, no same-named collisions | Use prefix convention: `run_{who}_{desc}.py` if ambiguous |
| `docs/shared_research_log.md` | Both append-only | `git pull --rebase` auto-resolves append-at-end conflicts |
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
