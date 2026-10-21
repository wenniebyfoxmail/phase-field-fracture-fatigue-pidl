# Frozen-profile saved coefficient attribution

Goal: explain the common PIDL Q−FD mismatch before further hidden optimization, preserving fixedFEM c20s4 damage/sourcePIDL history/B0/UV/Phi/T0/seed173/scales/h1e-6. Continue E011; use only original R002 arrays and linear journals. HQ-MESH-SAVED-COEFFICIENT-ATTRIBUTION-20261021 is new prospective human-delegated authority, not a producer retry. Whole00:35–00:55UTC1200s; total CPU300s, remote220/client15/SSH10/localplot25/reviewer10/metadata reserve20; ≤4threads (actual1), AS/RSS16GiB,0GPU. Only10 independent vector solves/20triangular solves,0newfactor; no model/checkpoint/AD/physics/FEM/SVD/precision/h scans or new optimization.

## Derivation and independent observations

All q/r/B values below mean the original free UV order, unweighted Euclidean norm; heads retain original772 coordinates. q_s=r_s+B_s z_s, source head z0 is read per arm (zero-root z0 is not zero). δx=(x+−x−)/(2h), xbar=(x++x−)/2, w_s=z_s−z0.

The code's logged RHS is initial objective gradient d_s(z0), **not global b**. Define a_s=−d_s(z0) from the authentic original Newton solve log, and e_s=H_s w_s−a_s. Ideal quadratic coefficients would obey a_s=b_s−H_s z0; we do not fabricate b_s from H_s z_s and do not call e_s zero by construction. No independent absolute global b was saved. RHS identification requires the old source-code flow, journal role/H/L, exactly one accepted alpha1, and exact z_s=z0−recorded_solution; absence or ambiguity stops attribution. Initial defect has no separate duplicate file, so its identity rests on that logged producer provenance, not recomputed force.

Let J_sec=δr+δB z0, cH=(Hbar−H0)δw+δH wbar. The product identity δ(Hw)=Hbarδw+δH wbar gives H0δw=δa+δe−cH. Thus:

FD = J_sec+B0 H0^-1 δa +[(Bbar−B0)δw+δB wbar]−B0 H0^-1 cH+B0 H0^-1 δe+δe_field,

where e_field,s=q_s−(r_s+B_s z_s), using recorded q_s and independent CPU products of recorded r/B/z. This is a chosen floating arithmetic reconstruction of an exact real algebra identity; its residual is retained.

For Q_rec=J_AD−B0H0^-1U, the mismatch Q_saved−FD decomposes into:

1. Q_saved−Q_rec (independent source reconstruction defect),
2. J_AD−J_sec,
3. B0H0^-1(−U−δa),
4. −[(Bbar−B0)δw+δB wbar],
5. +B0H0^-1 cH,
6. −B0H0^-1 δend_defect,
7. −B0H0^-1 δ(e−end_defect),
8. −δe_field (includes new offline CPU product arithmetic relative to original GPU field; not pure old producer error),
9. measured closure remainder.

Term7 is observed affine-consistency discrepancy of the stored Hessian/gradient/update arithmetic, not automatically pure roundoff. Each vector is saved with L2 norm and signed projection onto the original mismatch; component norms can cancel and are not additive causal percentages. Reconstructing an algebra identity is not independent causal proof. No complete force/assembly forward bound is created by these equalities.

Actual rounded parameter endpoint tensors were not saved; nominal direction/scales and the float64 producer contract cannot establish their effective secant direction. No checkpoint will be loaded to invent these endpoints.

## Execution and output boundary

Local source/JSON/AST and one same original reviewer static check; no new mathematical fixtures required. LargePhi absent from local mirror, so one SSH stdin CPU-only script reads original GPUServer8 run/archive, checks original manifest/outer return and74 selected immutable hashes/identity within hard60s, no GPU probe. It writes only fresh attributable analysis output, leaves old files unchanged, chunk/memmap readsPhi, returns <100MiB selected arrays and metadata. CPU220/AS16GiB hard and wall alarm cover remote work; output/temp ≤512MiB. Unknown/IO/permission/resource/connection failure is terminal, no reconnect/fallback or newcase. All old failure/cost/UNKNOWN retained. Analysis only; no new physical solution or architecture limit claim.
