# CSD3 Inbox (Mac → CSD3)

**Direction**: Mac-PIDL (this repo, dev machine) **→** Cambridge CSD3 HPC agent.  
**Channel purpose**: Mac deposits concrete instructions / experiment requests / config / sbatch templates for the CSD3 agent to execute. CSD3 agent reads here after `git pull` and acts accordingly.

**Counterpart**: `csd3_outbox.md` (CSD3 → Mac, status + results + questions).

---

## Format rules

1. **Append newest at top** of the "Requests" section; keep completed requests below a `---` separator under "Archive".
2. Every request starts with:
   ```
   ## YYYY-MM-DD · Request <N>: <one-line summary>
   ```
3. Request body must contain:
   - **Goal**: one sentence of what this run should prove / measure
   - **Config**: precise toggles (file:line or key path)
   - **Data inputs**: archive paths, baseline checkpoints needed, rsync sources
   - **sbatch template**: full usable script (project `SHEIL-SL3-GPU`, partition `ampere`, wallclock, etc.)
   - **Expected outputs**: what CSD3 should rsync back + where + what to report in outbox
   - **Acceptance criteria**: how Mac will decide success/failure
4. Mac commits + pushes after writing. CSD3 agent `git pull` reads.
5. If Mac needs to cancel / modify a request, **append a new dated sub-entry** `### [update] YYYY-MM-DD` — don't edit historical text.
6. When CSD3 acknowledges (via outbox), Mac may move the request block under "Archive" (preserve fully, add `### [archived] reason` note).

---

## Active requests

*(none yet — first real request will be E1 Enriched Ansatz 5-U_max S-N sweep after E2 on Mac concludes)*

---

## Archive

*(empty)*

---

## Environment assumptions (CSD3 side)

These are what Mac expects to be already installed / configured on CSD3. If any item is not yet true, CSD3 agent must flag in `csd3_outbox.md` before starting work.

| Item | Value (target) | Status |
|---|---|---|
| CRSid | `xw436` | ✅ known |
| Login node (for dev) | `login-icelake.hpc.cam.ac.uk` | ✅ |
| MFA | TOTP on phone | ✅ (as of 2026-04-23) |
| Project allocation | `SHEIL-SL3-GPU`, `SHEIL-SL3-CPU` | ✅ (2,999 GPU-h avail) |
| Code root | `~/rds/hpc-work/code/phase-field-fracture-with-pidl/` | ❓ unknown — flag if missing |
| Conda env | `~/rds/hpc-work/envs/pidl` with PyTorch 2.x + CUDA 12.x for A100 | ❓ unknown — flag if missing |
| Archive transfer staging | `~/rds/hpc-work/archives/` | ❓ unknown |

---

## Sbatch template skeleton (Mac's default suggestion; CSD3 may adjust)

```bash
#!/bin/bash
#SBATCH -J pidl_<RUN_TAG>
#SBATCH -A SHEIL-SL3-GPU
#SBATCH -p ampere
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --time=11:55:00                # under 12h SL3 limit
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err

set -euo pipefail

module purge
module load rhel8/default-amp
# conda env with pytorch + cuda
source ~/rds/hpc-work/envs/pidl/bin/activate

cd ~/rds/hpc-work/code/phase-field-fracture-with-pidl/upload\ code/SENS_tensile

# Example: run with override via env vars
export PIDL_UMAX=0.12
python main.py 8 400 1 TrainableReLU 1.0 \
  2>&1 | tee logs/pidl_<RUN_TAG>_$(date +%Y%m%d_%H%M).log
```

This is a skeleton only — each request's sbatch block must override `-J`, `--time`, `PIDL_UMAX`, config toggles, etc.

---

## Quick reference: how CSD3 agent should respond

After acting on a request:

1. **Ack**: in `csd3_outbox.md`, add `## YYYY-MM-DD · Ack Request <N>: starting` entry with PID / job ID
2. **Progress** (optional, for long jobs): periodic short updates (e.g., "cycle 50/300, ᾱ_max=X")
3. **Done**: final entry with archive path + summary metrics + any artifacts rsync'd back to Mac
4. **Block / question**: if something in the request is ambiguous or fails, add `[blocker]` / `[question]` entry in outbox and halt — wait for Mac to reply via new inbox update
