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

*(empty — awaiting first Mac inbox request)*

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
