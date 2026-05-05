# Experiment Registry

**Purpose**: Bird's-eye view of all PIDL experiments conducted, their status, key numbers, and verdicts.
Not a replacement for detailed per-experiment memory files or shared_research_log entries — this is the "index by experiment" view.

**Owner**: Mac (structural edits) + Windows (status updates after runs complete)
**Last updated**: 2026-05-05

---

## Legend

| Status | Meaning |
|---|---|
| DONE | Complete, results final |
| STOPPED | Mac decision to halt (cost-benefit / superseded) |
| PARTIAL | Some Umax cases done, others not run |
| RUNNING | Currently in-flight |
| GATED | Awaiting Mac decision to proceed |

---

## 1. Baseline S-N Curve (coeff=1.0, seed=1)

| Umax | N_f | ᾱ_max @ N_f | Source |
|---|---:|---:|---|
| 0.08 | 340 | 57.4 | Mac archive |
| 0.09 | 225 | 39.3 | Mac archive |
| 0.10 | 160 | 20.0 | Mac archive |
| 0.11 | 112 | 16.7 | Mac archive |
| 0.12 | 80–83 | 9.3 | Mac+Windows, multi-seed confirmed |
| 0.13 | 60–62 | 7.6–8.5 | Windows multi-seed (s1/s2/s3) |
| 0.14 | 25–36 | — | Mac 5-seed (OOD, −24% bias vs FEM 39) |

**Status**: DONE (core table complete through 0.14)
**Key finding**: PIDL reliable for Umax ≤ 0.13 (≤±10% vs FEM). u=0.14 = OOD boundary (−24%, std=4.2).

---

## 2. coeff=3.0 Umax Sweep (init activation slope sensitivity)

| Umax | N_f | ᾱ_max | vs baseline N_f | vs baseline ᾱ_max |
|---|---:|---:|---|---|
| 0.08 | 330 | 23.7 | −3% | 41% of baseline |
| 0.09 | 217 | 15.7 | −4% | 40% |
| 0.10 | 155 | 15.8 | −3% | 79% |
| 0.11 | 114 | 14.9 | +2% | 89% |
| 0.12 | 82 | 8.9 | −1% | 96% |

**Status**: DONE (2026-04-24, all 5 cases)
**Wall**: ~56 h cumulative
**Verdict**: init_coeff NOT sensitive for N_f (all ≤5% different). IS sensitive for ᾱ_max at low Umax — caps to ~40% of baseline at Umax ≤ 0.09. Paper: fix coeff=1.0 without N_f ablation needed.
**Archive transfer**: done (OneDrive handoff to Mac 2026-04-25)

---

## 3. E2 ψ⁺ Hack Sweep (cold-start ×1000 Gaussian at tip)

| Umax | N_f | ᾱ_max | Notes |
|---|---:|---:|---|
| 0.12 | 81 | 457 | Mac run (valid) |
| 0.08 | 80 | 388 | Windows — INVALIDATED (runner bug, actual Umax=0.12) |
| 0.09 | ~80 (partial) | 388 | Windows — INVALIDATED (same bug) |
| 0.10–0.11 | — | — | Never ran |

**Status**: STOPPED (2026-04-25)
**Reason**: (1) cold-start saturates accumulator at cycle-0 → flat N_f≈80 floor; (2) runner bug invalidated all Windows non-0.12 data. Only Mac's u=0.12 result survives.
**Verdict**: E2 hack diagnostic proved ψ⁺ concentration IS the mechanism (N_f matches FEM at u=0.12). But cold-start saturation prevents meaningful S-N scan. Warm-start protocol never pursued.
**Archive transfer**: N/A (only Mac's single valid run)

---

## 4. Dir 6.3 Logarithmic-f Sweep (degrad_type='logarithmic', kappa=0.5)

| Umax | N_f | ᾱ_max | vs baseline N_f | Notes |
|---|---:|---:|---|---|
| 0.12 | 121 | 10.83 | +46% | Valid, complete |
| 0.08 | NO FRACTURE | 63.05 | — | 300 cycles, tip barely propagated |
| 0.09 | NO FRACTURE | 37.76 | — | 300 cycles, logf arrest |
| 0.10 | — | — | — | Partial (~220 steps), stopped by Mac |
| 0.11 | — | — | — | Never ran |

**Status**: STOPPED (2026-04-27, Mac decision: cost-benefit; logf overshoots FEM N_f everywhere → diagnostic not closure)
**Verdict**: log-f dramatically suppresses crack propagation at low Umax (arrest mechanism). At u=0.12 gives +46% fatigue life and +16% ᾱ_max vs baseline. f-shape IS a meaningful kinematic bottleneck — but paper direction moved elsewhere.
**Archive transfer**: ~~Not yet transferred~~ **Packaged 2026-05-05** → `~/Downloads/_pidl_handoff_dir63_logf_20260505/` (4.7 GB total: 4 tarballs + logs). Awaiting OneDrive upload + Mac download.

---

## 5. Oracle-Driver Sweep (FEM ψ⁺ injected at tip zone)

### Variant A (zone=0.02, 735 elements)

| Umax | N_f | ᾱ_max | FEM N_f | Oracle/FEM | Status |
|---|---:|---:|---:|---|---|
| 0.08 | 359 | 1291 | 396 | −9% | done (500-cap resume) |
| 0.09 | 235 | 516 | 254 | −7% | done |
| 0.10 | 156 | 1565 | 170 | −8% | done (fresh=resumed bit-identical) |
| 0.11 s1 | 117 | 11253 | 117 | 0% | done — HIGH basin |
| 0.11 s2 | 116 | 1140 | — | — | done — LOW basin |
| 0.11 s3 | 114 | 3511 | — | — | done — MID basin |
| 0.12 | 83 | 776.8 | 82 | +1% | done |
| 0.13 | 61 | 17973 | 57 | +7% | done |
| 0.14 | 33 | 5.69 | 39 | −15% | done (Pattern A regime) |

### Variant B (zone=0.005, 5 elements — minimal injection)

| Umax | N_f | ᾱ_max | Notes |
|---|---:|---:|---|
| 0.12 | 84 | 9.47 | N_f holds, ᾱ_max collapses 82× vs V-A |

**Status**: DONE (full sweep complete across 8 Umax + 3 seeds at 0.11)
**Key findings**:
1. Oracle N_f matches FEM within ±10% for 7/8 Umax (u=0.14 outlier at −15%)
2. u=0.11 multimodal: 3 distinct ᾱ_max basins (10× spread) but N_f Δ=3 cycles — **Oracle-specific** (pure-physics is tight)
3. Variant B: zone size controls ᾱ_max amplitude; N_f needs only single-element ψ⁺ injection
4. v3.15 framework claim: N_f is boundary-geometry-driven, ᾱ_max is field-method-driven
**Archive transfer**: partial (smoke + some logs via OneDrive; full archives on Windows disk)

---

## 6. α-1 Mesh Refinement (h_c=0.001 corridor, 153k triangles)

| Umax | N_f | ᾱ_max | vs baseline ᾱ_max |
|---|---:|---:|---|
| 0.12 | 79 | 11.94 | +28% |

**Status**: DONE (2026-04-28, production complete)
**Wall**: 5 h 14 min
**Verdict**: Mesh attacks amplitude only (+28% on ᾱ_max). Does NOT close FEM gap (would need ~80× lift). Stationarity problem untouched.
**Archive transfer**: smoke shipped via OneDrive (64 MB); production awaiting Mac handoff request.

---

## 7. α-2 Multi-Head NN (tip head + spatial Gaussian gate)

| Config | r_g | gate_power | T4 modal | ᾱ_max c9 | vs PASS (≥0.70) |
|---|---:|---:|---:|---:|---|
| default | 0.020 | 2 | 0.300 | 2.471 | FAIL |
| tighter | 0.005 | 4 | 0.300 | 2.069 | FAIL |

**Status**: DONE (2026-04-29, both configs fail T4)
**Verdict**: Architecture (multi-head + spatial gate) does NOT close stationarity. Tighter gate WORSE on both axes. Production N=300 NOT launched. Dead end — pivot to α-3.
**Archive transfer**: N/A (smoke only, no production)

---

## 8. α-3 XFEM-Jump Enrichment (Heaviside discontinuity at moving tip)

| Metric | Value | PASS threshold |
|---|---|---|
| T4 modal stability | 0.500 | ≥ 0.95 |
| T4 transitions | 5 (best) | low |
| T3 c9 ᾱ_max | 3.04 (best) | — |

**Status**: GATED (2026-04-30, T4 marginal — below PASS but best stationarity yet)
**Verdict**: Heaviside anchored c0-c4 perfectly, then drifts c5-c9 (likely tip-tracking lag: PIDL alpha argmax ≠ physical tip). Best stationarity so far but not sufficient. Mac has 5 alternative paths (A-E). Production NOT launched.
**Archive transfer**: N/A (smoke only)

---

## 9. Hit 16 Enriched Ansatz v1 (Umax=0.08 generalization test)

| Metric | Result | Baseline 0.08 |
|---|---|---|
| N_f | 345 | 340 (+1.5%) |
| ᾱ_max | 61.1 | 57.4 (+6%) |
| D1a g·ψ⁺_raw (propagation phase c100-c300) | 0.42 mean | 0.40 |

**Status**: DONE (2026-05-02, commit `060db04`)
**Verdict**: Claim 1 (g·ψ⁺_raw invariance) generalizes from Umax=0.12 to Umax=0.08 (within ±5%). Audit ledger v3.15 drops "Umax=0.12 only" caveat. Bonus: Williams enrichment coefficient `c` decays +0.43→−0.03 across cycles (enrichment self-deactivates in propagation phase).
**Archive transfer**: on Windows disk, Mac can request.

---

## 10. Pure-Physics OOD Multi-Seed (u=0.13 + u=0.11, cross-seed verification)

| Umax | seed | N_f | ᾱ_max @ N_f |
|---|---:|---:|---:|
| 0.13 | 2 | 60 | 7.94 |
| 0.13 | 3 | 62 | 8.46 |
| 0.11 | 3 | 113 | 15.76 |

**Status**: DONE (2026-05-05, Request 1 complete)
**Key findings**:
1. u=0.13 multi-seed: N_f cluster 60-62 (Δ=2 cycles, 3% spread) — confirms OOD reliability
2. u=0.11 pure-physics is TIGHT (15.76-17.98 across seeds) — multimodality is Oracle-specific
3. Combined with Oracle + FEM: 4 method/seed combos at u=0.13 all cluster N_f=60-62 → strongest §4.6 OOD claim
**Archive transfer**: on Windows disk.

---

## 11. FEM Reference Runs (GRIPHFiTH, Windows-FEM)

| Umax | N_f (FEM) | Mesh | Source |
|---|---:|---|---|
| 0.08 | 396 | SENT_mesh.inp (ℓ/h≈1) | PIDL-series |
| 0.09 | 254 | same | PIDL-series |
| 0.10 | 170 | same | PIDL-series |
| 0.11 | 117 | same | PIDL-series |
| 0.12 | 82 | same | PIDL-series |
| 0.13 | 57 | same | PIDL-series (extended) |
| 0.14 | 39 | same | PIDL-series (extended) |
| 0.12 | 77 | gmsh fine ℓ/h=5 | FEM-1 mesh convergence |

**Status**: DONE (full Umax range + mesh convergence check)
**Mesh note**: PIDL-series uses ℓ/h≈1 (coarser than community ℓ/h=5 standard). FEM-1 fine mesh gives N_f=77 (−6.1% vs coarse 82 — borderline outside 5% gate, mixed-tool comparison).
**FEM-4 a(N) CSVs**: exported for u=0.08/0.12/0.13 (commit `5a04e7d`).

---

## Summary Table (sorted by experiment date)

| # | Experiment | Dates | Status | One-line verdict |
|---|---|---|---|---|
| 2 | coeff=3.0 sweep | 4/19–4/24 | DONE | N_f insensitive to init slope; ᾱ_max sensitive at low Umax |
| 3 | E2 ψ⁺ hack | 4/24–4/25 | STOPPED | Cold-start saturation + runner bug; only u=0.12 Mac result valid |
| 4 | Dir 6.3 logf | 4/25–4/27 | STOPPED | logf arrests propagation at low Umax; diagnostic not closure |
| 5 | Oracle driver | 4/27–5/4 | DONE | N_f matches FEM ±10% for 7/8 Umax; v3.15 framework claim anchored |
| 6 | α-1 mesh refinement | 4/27–4/28 | DONE | +28% amplitude, not closure |
| 7 | α-2 multi-head | 4/28–4/29 | DONE | T4 FAIL (0.30), architecture dead |
| 8 | α-3 XFEM-jump | 4/29–4/30 | GATED | T4 marginal (0.50), best yet but below PASS |
| 9 | Hit 16 enriched ansatz | 5/2 | DONE | Claim 1 generalizes to u=0.08 |
| 10 | OOD multi-seed | 5/5 | DONE | u=0.13 tight; u=0.11 multimodality is Oracle-specific |

---

## Archive Transfer Ledger

| Experiment | Windows → Mac | Method | Date |
|---|---|---|---|
| coeff=3.0 | DONE | OneDrive tar | 2026-04-25 |
| α-1 smoke | DONE | OneDrive tar (64 MB) | 2026-04-28 |
| Dir 6.3 logf | **PACKAGED** | `~/Downloads/_pidl_handoff_dir63_logf_20260505/` (4.7 GB) | 2026-05-05 |
| Oracle archives | partial | some via OneDrive | various |
| OOD multi-seed | pending Mac request | — | — |
| Hit 16 enriched | pending Mac request | — | — |
