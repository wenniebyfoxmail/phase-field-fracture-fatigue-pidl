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

## 2026-04-24 · Request 1: E1 Enriched Ansatz S-N sweep at 5 U_max

**Goal**: produce a full S-N curve (N_f vs U_max) for the **Enriched Mode-I Ansatz** PIDL method across `U_max ∈ {0.08, 0.09, 0.10, 0.11, 0.12}`. This tests whether the fixed-tip r^(1/2) output singular enrichment architecturally closes the PIDL-FEM S-N gap. This is the **primary data for Ch2 paper**.

**Scientific context** (read first if starting cold): see `docs/shared_research_log.md` — Apr 23 E2 ψ⁺ hack finding confirmed ψ⁺_raw concentration is the root cause of PIDL's ᾱ_max ceiling and the low-U_max N_f gap. E1 is the architectural follow-up: Enriched Ansatz bakes a r^(1/2) singular term into the NN output at a pinned tip, which should partially concentrate ψ⁺ without resorting to the E2 hack.

**Baseline numbers to beat** (from `figures/compare_umax/summary_umax_sweep.txt` on main):

| U_max | FEM N_f | PIDL Baseline N_f | ΔN_f | % gap |
|---|---|---|---|---|
| 0.08 | 396 | 341 | −55 | **−13.9%** (worst gap) |
| 0.09 | 254 | 230 | −24 | −9.4% |
| 0.10 | 170 | 160 | −10 | −5.9% |
| 0.11 | 117 | 112 | −5 | −4.3% |
| 0.12 | 82 | 80 | −2 | −2.4% (best point) |

Enriched at U_max=0.12 already known: **N_f=84**, ᾱ_max=10.33, peak Kt=28.9 (vs FEM 15.3). Need the other 4 points to build the full S-N.

### Prerequisites (Mac provides)

Mac will push a runner script `SENS_tensile/run_enriched_umax.py <umax>` that sets the correct config overrides (ansatz enable, Carrara accumulator, spatial_alpha_T off, psi_hack off, seed=1, coeff=1.0) and invokes training. **CSD3 agent: wait for commit with subject containing "run_enriched_umax.py" before starting Request 1.** If not seen after Mac's outbox ack, raise `[blocker]` in outbox.

Until the runner is committed, CSD3 can do Request 0 (env bootstrap) in parallel.

### Config (what the runner will set — CSD3 should NOT hand-edit config.py)

```python
ansatz_dict = {
    "enable"   : True,           # ★ this is what we're testing
    "x_tip"    : 0.0, "y_tip"  : 0.0,
    "r_cutoff" : 0.1, "nu"     : 0.3,
    "c_init"   : 0.01, "modes" : ["I"],
}
williams_dict  = {"enable": False, ...}       # OFF
fatigue_dict["accum_type"]        = "carrara" # baseline (NOT golahmar)
fatigue_dict["spatial_alpha_T"]   = {"enable": False, ...}  # OFF
fatigue_dict["psi_hack"]          = {"enable": False, ...}  # OFF
fatigue_dict["disp_max"]          = <U_MAX>   # per-job argument
fatigue_dict["n_cycles"]          = 700       # plenty for low U_max runs
fatigue_dict["enable_E_fallback"] = False     # primary α-boundary criterion only
network_dict["hidden_layers"]     = 8
network_dict["neurons"]           = 400
network_dict["seed"]              = 1
network_dict["activation"]        = "TrainableReLU"
network_dict["init_coeff"]        = 1.0
```

### Per-Umax job table

| Job | U_max | Expected wallclock (A100) | Archive tag prefix |
|---|---|---|---|
| 1 | 0.08 | ~10–12 h | `..._Umax0.08_enriched_ansatz_modeI_v1` |
| 2 | 0.09 | ~8–10 h | `..._Umax0.09_enriched_ansatz_modeI_v1` |
| 3 | 0.10 | ~6–8 h | `..._Umax0.10_enriched_ansatz_modeI_v1` |
| 4 | 0.11 | ~5–7 h | `..._Umax0.11_enriched_ansatz_modeI_v1` |
| 5 | 0.12 | ~4–6 h | `..._Umax0.12_enriched_ansatz_modeI_v1` (already exists on Mac; rerun for consistency check or skip + rsync from Mac — CSD3 decides) |

All 5 submittable in parallel (4 GPUs/node × concurrent jobs). Total ~15–18 GPU-h per job × 5 = 60–90 GPU-hours. Budget: 2,999 GPU-h available. Fine.

### sbatch template (per job — substitute `<UMAX>`)

```bash
#!/bin/bash
#SBATCH -J pidl_enriched_U<UMAX>
#SBATCH -A SHEIL-SL3-GPU
#SBATCH -p ampere
#SBATCH --nodes=1 --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --time=11:55:00
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err

set -euo pipefail
module purge
module load rhel8/default-amp
source ~/rds/hpc-work/envs/pidl/bin/activate

cd ~/rds/hpc-work/code/phase-field-fracture-with-pidl/upload\ code/SENS_tensile
python run_enriched_umax.py <UMAX> 2>&1 | tee logs/pidl_enriched_U<UMAX>_$(date +%Y%m%d_%H%M).log
```

### Expected outputs (per job)

Under `SENS_tensile/hl_8_..._Umax<UMAX>_enriched_ansatz_modeI_v1_cycle<N>_Nf<NN>_real_fracture/`:
- `best_models/` — checkpoints + `*_vs_cycle.npy` arrays
- `alpha_snapshots/` — periodic α-field PNG + .npy
- Logs under `logs/`

### Acceptance criteria

For each job:
- Reaches fracture (`α > 0.95 at x=0.46 boundary`, primary criterion) within wallclock — archive auto-renamed with `_cycle<N>_Nf<NN>_real_fracture` suffix
- If job hits 12h wallclock without fracture: acceptable for low-U_max if at least `cycle ≥ 300` reached; escalate in outbox if stopped earlier
- Final `alpha_bar_vs_cycle.npy`, `Kt_vs_cycle.npy`, `psi_peak_vs_cycle.npy` present
- No NaN / divergence in last 10 cycles

For the sweep as a whole:
- N_f reported for all 5 U_max
- Can compute S-N fit `N_f = A · U_max^b`; Mac will compare `b` to FEM's −3.876 and baseline's −3.571
- **Success signal**: Enriched's `b` exponent lies between baseline (−3.571) and FEM (−3.876), i.e. some S-N gap closure. Full closure unlikely (Enriched is not as strong as E2 hack) but any shift toward FEM is a positive result

### Rsync back (to Mac)

```bash
# From Mac (when CSD3 reports [done] in outbox):
BASE='xw436@login-icelake.hpc.cam.ac.uk:~/rds/hpc-work/code/phase-field-fracture-with-pidl/upload code/SENS_tensile'
for u in 0.08 0.09 0.10 0.11 0.12; do
  rsync -avz --progress \
    "$BASE/hl_8_Neurons_400_*_Umax${u}_enriched_ansatz_modeI_v1_cycle*_Nf*_real_fracture/" \
    "$(dirname "$0")/hl_8_Neurons_400_*_Umax${u}_enriched_ansatz_modeI_v1_cycle*_Nf*_real_fracture/"
done
```

CSD3 is responsible for ensuring archives are at the expected path before writing `[done]` in outbox with rsync instructions.

### Preferred execution order

1. Submit all 5 jobs at once (parallel). Slurm scheduler handles GPU availability.
2. As each finishes, write `[done] Request 1 (Umax=XYZ)` in outbox with N_f and summary.
3. After all 5 done, write a single `[done] Request 1 (all)` roll-up entry with the complete S-N table.

---

## 2026-04-24 · Request 0: One-time CSD3 environment bootstrap

**Goal**: make CSD3 ready to run Python PIDL training. This is a prerequisite for Request 1 and all future requests. Do once; report state in `csd3_outbox.md`.

### Steps (CSD3 agent executes)

1. **Storage layout**:
   ```bash
   mkdir -p ~/rds/hpc-work/{code,envs,archives,logs}
   ```
2. **Clone repo**:
   ```bash
   cd ~/rds/hpc-work/code
   git clone git@github.com:wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git phase-field-fracture-with-pidl
   # Note: the repo's main branch is the single source of truth. Do NOT create
   # local branches; CSD3 is a producer, not a dev (see upload code/CLAUDE.md +
   # docs/git_workflow.md).
   ```
3. **Conda env** (PyTorch 2.x + CUDA 12.x for A100):
   ```bash
   module load miniconda/3
   conda create -p ~/rds/hpc-work/envs/pidl python=3.10 -y
   conda activate ~/rds/hpc-work/envs/pidl
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   pip install -r ~/rds/hpc-work/code/phase-field-fracture-with-pidl/requirements.txt
   # sanity check:
   python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no GPU on login node — OK, run check inside sbatch')"
   ```
4. **Smoke test** (short sbatch job, 30 min, 1 cycle forward pass only):
   - Submit a minimal 30-min sbatch that activates env + runs `python -c "from source.compute_energy import get_psi_plus_per_elem; print('import OK')"` on a compute node
   - Ensures PyTorch + CUDA + repo path all wire correctly on ampere GPU
5. **Report state** in `csd3_outbox.md` with:
   - `Environment state` table filled out (actual paths / versions)
   - `mybalance` refresh (even though Mac has a snapshot, CSD3 should confirm)
   - Any issues encountered

### Acceptance

Outbox entry `[done] Request 0` contains:
- Repo cloned, commit SHA at HEAD
- Conda env torch version + CUDA available inside sbatch
- Smoke test stdout captured

Until Request 0 is `[done]`, Request 1 cannot proceed.

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
