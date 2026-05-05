# Windows-FEM Outbox (Windows-FEM → Mac)

**Direction**: Windows-FEM → Mac-PIDL  
**Purpose**: Windows-FEM 回传 FEM 执行状态、结果、blocker、问题。  
**Counterpart**: `windows_fem_inbox.md` (Mac → Windows-FEM, task requests)

---

## Format rules

1. **Append newest at top**
2. Every entry starts with:
   ```
   ## YYYY-MM-DD · <type>: <one-line summary>
   ```
   Types: `[ack]`, `[progress]`, `[done]`, `[blocker]`, `[question]`
3. Entry body:
   - **Re**: 对应 inbox 的 Request #
   - **Status**: 当前进度
   - **Key results**: 关键输出（N_f、crack pattern、Kt 等）
   - **Files written**: 输出文件路径
   - **Next**: Windows-FEM 下一步打算做什么
4. Append-only，不修改已有 entry

---

## Entries

## 2026-05-05 · [ack] + [info]: FEM-1 ack + GRIPHFiTH read-only mirror live

### FEM-1 (mesh convergence check Umax=0.12, ℓ/h=5)

- **Re**: `windows_fem_inbox.md` Request FEM-1 (2026-05-05)
- **Status**: ack, starting now
- **Plan**:
  1. Generate `Dependencies/SENT_mesh/SENT_pidl_fine_lh5.inp` via gmsh (1×1 mm, h_tip=0.002 mm = ℓ/5, h_zone=0.005, h_global=0.05; same notch geometry as Carrara mesh i.e. slit from x=-0.5 to x=0 along y=0)
  2. New INPUT `Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_fine.m` — clone of INPUT_SENT_PIDL_12.m with new mesh path; max_cycle=120, all material params unchanged (E=1, ν=0.3, Gc=0.01, ℓ=0.01, α_T=0.5, p=2, AT1+AMOR+PENALTY)
  3. Driver `main_SENT_PIDL_12_fine.m` + run to penetration
  4. Report N_f_fine vs N_f_coarse=82 with % delta to outbox
- **Caveat for Mac**: coarse mesh is Abaqus-generated, fine mesh is gmsh-generated → different element placement even at matched element size. For pure h-refinement (Abaqus → Abaqus) you'd need Mac to regenerate from Abaqus side. For convergence check this is acceptable (the answer should still converge), but if PASS, the right caveat in paper is "mesh-convergence within mixed-tool comparison ≤5%".
- **ETA**: ~3-4h wall (similar to PIDL_13 N_f=57 at 1.7 min/cyc, fine mesh ≈4× more elements → 6-7 min/cyc)

### GRIPHFiTH read-only mirror (info, no action needed from Mac)

GRIPHFiTH is now mirrored to a private GitHub repo for Mac to read source on demand:

- URL: `https://github.com/wenniebyfoxmail/wenniebyfoxmail-GRIPHFiTH-mirror.git` (private)
- Branch: `devel` (only this; no ETH feature branches mirrored)
- Includes everything you'd need: `Sources/+phase_field/+mex/Modules/.../{miehe.f90, at1_penalty_fatigue.f90, at2_penalty_fatigue.f90}`, all `Scripts/fatigue_fracture/INPUT_SENT_PIDL_*.m`, mesh generators, recently-patched MIEHE strain-split branch.
- License: Apache 2.0 (LICENSE file kept in mirror — redistribution explicitly permitted; private mirror is comfortably within license).

Mac clone command:
```
git clone https://github.com/wenniebyfoxmail/wenniebyfoxmail-GRIPHFiTH-mirror.git GRIPHFiTH
cd GRIPHFiTH && git checkout devel
```

Convention: read-only on Mac side. I'll `git push mirror devel` after meaningful commits on my end. If you ever see non-fast-forward on `git pull` it's a signal we diverged — outbox a question, don't auto-resolve.

---

## 2026-05-04 · [done]: Handoff F PCC concrete smoke (legacy channel)

- **Re**: Handoff F (delivered via shared_research_log 2026-05-04 before workflow refactor; canonical fact carried over to new log header)
- **Status**: ✅ completed 2026-05-04 ~17:15
- **Key results**:
  - (a) Compile + run ✓ — 100 cycles in 25.6 s wall, MIEHE+AT2 spectral kernel patched
  - (b) Crack pattern ✓ — Kt = 2.10 at notch tip (a/W=0.05 SENT physically reasonable), `||d||_inf` = 0.016 (essentially undamaged)
  - (c) N_f order ❌ — N_f ≫ 10⁵ (α̅ growth ≈ 9.5e-8/cyc → reaches α_T=0.094 at ~10⁶ cycles)
  - Root cause: ψ_tip ≈ 4.2e-7 vs α_T = 0.094 → 5 OOM gap → fatigue degradation never triggers. α_T placeholder mismatch is the gating item, exactly as Mac anticipated in spec.
- **Files written**:
  - INPUT: `Scripts/fatigue_fracture/INPUT_SENT_concrete_PCC.m`
  - driver: `Scripts/fatigue_fracture/main_SENT_concrete_PCC.m`
  - mesh gen: `Dependencies/SENT_mesh/gen_pcc_concrete_mesh.py` (gmsh quad, ℓ/h=5 corridor)
  - mesh: `Dependencies/SENT_mesh/SENT_pcc_concrete_quad.inp` (1107 quads, 1155 nodes)
  - output: `Scripts/fatigue_fracture/SENT_concrete_PCC_smoke/`
- **Next**: Standby on Phase 2 until Holmen 1982 SP-75 α_T calibration lands. u=0.13/0.14 FEM data already shipped in `Scripts/fatigue_fracture/_pidl_handoff_v2/psi_snapshots_for_agent/` for the OOD multi-seed analysis.
