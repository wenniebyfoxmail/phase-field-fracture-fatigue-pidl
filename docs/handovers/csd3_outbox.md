# CSD3 Outbox (CSD3 → Mac)

**Direction**: Cambridge CSD3 HPC agent **→** Mac-PIDL (this repo, dev machine).  
**Channel purpose**: CSD3 reports status / job IDs / results / blockers / questions about requests from `csd3_inbox.md`.

**Counterpart**: `csd3_inbox.md` (Mac → CSD3, instructions).

---

## Format rules

1. **Append newest at top** of the "Reports" section.
2. Every entry starts with:
   ```
   ## YYYY-MM-DD · <Tag> Request <N>: <one-line summary>
   ```
   Tags:
   - `[ack]` — starting work on Request N
   - `[progress]` — interim update (long-running jobs)
   - `[done]` — Request N completed; results attached
   - `[blocker]` — something prevents CSD3 from fulfilling the request
   - `[question]` — need clarification from Mac
   - `[note]` — unsolicited observation or side-finding
3. Required content depends on tag:
   - `[ack]`: slurm job ID, estimated wall time, sbatch file committed path
   - `[progress]`: current cycle / step, key metrics, remaining est. wall time
   - `[done]`: archive path on CSD3, rsync location on Mac (if applicable), summary metrics table, final log snippet, sha of commit containing new runner/code
   - `[blocker]`, `[question]`: precise problem, what CSD3 tried, minimal reproducer if possible
4. CSD3 commits + pushes after writing. Mac `git pull` reads.
5. Don't edit historical entries. Add `### [update] YYYY-MM-DD` sub-entry to amend / correct.

---

## Reports

## 2026-04-24 · [ack] Request 1: E1 Enriched Ansatz S-N sweep — 5 jobs submitted

**All 5 jobs submitted in parallel at ~03:10 UTC+1:**

| U_max | Slurm Job ID | Status |
|---|---|---|
| 0.08 | `28314349` | PENDING |
| 0.09 | `28314350` | PENDING |
| 0.10 | `28314351` | PENDING |
| 0.11 | `28314352` | PENDING |
| 0.12 | `28314353` | PENDING |

**sbatch scripts**: `~/rds/hpc-work/code/phase-field-fracture-with-pidl/sbatch_e1_u{008,009,010,011,012}.sh`  
**Logs**: `~/rds/hpc-work/code/phase-field-fracture-with-pidl/logs/pidl_e1_U{UMAX}-{JOBID}.out`  
**Expected wallclock**: 6–12 h per job (A100, ampere partition, `SHEIL-SL3-GPU`)

**Path correction applied**: inbox template had `upload\ code/SENS_tensile` — on CSD3 the repo root IS the upload-code content, so all sbatch scripts use `cd .../SENS_tensile` directly.

Will update with `[done]` entries per job as each completes with N_f.

---

## 2026-04-24 · [ack] Request 0: Environment bootstrap — in progress

**Started by**: CSD3 agent (Claude), 2026-04-24

**Steps completed so far:**

| Step | Status | Notes |
|---|---|---|
| SSH + MFA | ✅ | ControlMaster configured on Mac; login-icelake.hpc.cam.ac.uk |
| Storage layout | ✅ | `~/rds/hpc-work/{code,envs,archives,logs}` all created |
| Clone repo | ✅ | `~/rds/hpc-work/code/phase-field-fracture-with-pidl/` at HEAD `56f8412` |
| Conda env | ✅ | `~/rds/hpc-work/envs/pidl` — torch 2.5.1+cu121, Python 3.11 |
| Deps installed | ✅ | gmshparser, matplotlib, numpy, tqdm (NOT torch — already newer version) |
| Import test (login node) | ✅ | `compute_energy`, `config` import OK |
| Smoke test (ampere GPU) | ⏳ | Slurm job `28308465` submitted — still PENDING after 3.5h (208 jobs ahead). Login-node env fully verified; proceeding with R1 in parallel. |

**Decision**: After 3.5h pending (208 jobs ahead), proceeded with Request 1 submission in parallel rather than blocking further. Login-node verification (torch 2.5.1+cu121, all imports OK) gives high confidence. Smoke test `28308465` still running — will report result when it completes.

**Path correction**: inbox sbatch template uses `upload\ code/SENS_tensile` (Mac path). On CSD3 repo root IS upload-code content → correct path is `SENS_tensile` directly. Applied in all E1 sbatch scripts.

---

## Environment state — CSD3 agent please fill this out on first session

| Item | Expected / Asked | Actual | Notes |
|---|---|---|---|
| Code root | `~/rds/hpc-work/code/phase-field-fracture-with-pidl/` | ❓ | Clone URL: `git@github.com:wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git` (main is the single source of truth) |
| PyTorch env | `~/rds/hpc-work/envs/pidl/` with torch 2.x + CUDA 12.x | ❓ | `conda env list` output here |
| Archive staging | `~/rds/hpc-work/archives/` | ❓ | For rsync from Mac |
| Logs dir | `~/rds/hpc-work/logs/` | ❓ | For sbatch `-o` / `-e` |
| `mybalance` snapshot | `SHEIL-SL3-GPU = 2,999 h`, `SHEIL-SL3-CPU = 200,000 h` (as of 2026-04-23) | ❓ | Refresh if > 2 weeks old |
| CSD3 agent commit identity | `user.email`, `user.name` set? | ❓ | For git commit from CSD3 |

After filling: commit + push this entry. Mac will ack in inbox if anything needs to change.

---

## How Mac will ack

When CSD3 writes `[done]`, Mac will:
1. `git pull` and read the outbox entry
2. If results match acceptance criteria: Mac adds `### [archived]` note to the original inbox request and moves it to Archive section
3. If results have issues: Mac writes a follow-up inbox entry or cancels the request

---

## Note on large data transfers

- Archives (PIDL checkpoints, > 100 MB) **never** go through git. Use rsync directly:
  ```
  # Mac → CSD3 (Mac side)
  rsync -avz "upload code/SENS_tensile/<archive>/" \
    xw436@login-icelake.hpc.cam.ac.uk:~/rds/hpc-work/archives/<archive>/

  # CSD3 → Mac (Mac side, pulling)
  rsync -avz \
    xw436@login-icelake.hpc.cam.ac.uk:~/rds/hpc-work/archives/<archive>/ \
    "upload code/SENS_tensile/<archive>/"
  ```
- In the outbox entry, reference the archive path and rsync command — don't upload the archive contents to git.
- Log files from CSD3 that are useful for Mac's analysis can either be rsync'd or (if small) quoted inline in the outbox entry.
