# D010 r2 independent actual-field evidence review

**Bounded finite-component PASS**, source `1772aa630021a63fa454f4330b5713598575a29d`. All three states accept the first predeclared analytic seed (k0), and all **21 actual guards** independently improve. R1 remains the immutable negative result with exact-original fallback. No new step, direction search, fit or training was run by this reviewer.

Reused independent raw checkpoint encoder at chunk511, actual D/bias and explicit BC/window, SciPy dgemm, explicit 2×2 Q4 geometry/normalized mass/component AMOR force and energy. Maximum independent realization discrepancy was **4.65e-16**. Original 33 files and six D009/D008 inputs match hashes; original theta/B/v identity, enriched reconstruction, coefficient increment, actual parameter budget, exact outside/BC identity and affine field mapping all pass. Four UV quadratic crossings independently reproduce the sole seed; only seven rows per state exist and k0 passes, confirming first-feasible stopping rather than retrospective best selection.

|state|actual fraction|delta/theta norm|full UV RMS %|damage UV RMS %|background UV RMS %|inside-background UV RMS %|rho %|
|---|---:|---:|---:|---:|---:|---:|---:|
|c20|.000800270622|1.60054e-5|−.00906294|−.00685015|−.02668935|−.25824911|−.02161527|
|c60|.000029948453|5.98969e-7|−.00036978|−.00003197|−.00388833|−.03115169|−.00095201|
|c83|.000434496556|8.68993e-6|−.00212633|−.00045684|−.08622212|−.43687525|−.02230311|

Global/inside-background elastic-driver RMS error decreases respectively .036982/.062283%, .001970/.003443%, and .055402/.067358%. This realises a finite compatible component, but the full/damage UV gains are very small, especially c60. Delta/theta values above are **ratios**, not percentages; the largest is only .00160054% of original head norm, far below the 2% maximum. It is incorrect to describe this as a realised 2% correction or material solution of the FEM mismatch.

Secondary costs remain: c20 full/damage instantaneous-driver errors increase .001355/.001495%; c83 increase .000932/.000932%, with slight strain/active-energy increases too. c60 secondary errors improve at tiny scale. Branch fractions change .0005150/.00006076/.00016492; actual nonlinear force was recalculated, so fixed-origin tangent assumptions are not used for admission. Regional averages do not imply every node improves. Driver remains instantaneous 2(1-d)psi+, not net fracture/history/fatigue drive; huge old equilibrium gap and missing history channels remain.

Receipt cost is r2 CPU numeric wall20.5623s, peakRSS1,040,302,080bytes; r1+r2 numeric wall56.7822s remains below combined600s. These are observed diagnostic costs, excluding subsequent plotting/review, not a training speedup. All original checkpoint writes, NN optimizer steps and history/fatigue/damage updates remain zero.

This result supports keeping the finite mapping/guard component while choosing a better benefit-to-curvature direction if further work is authorised. It does not establish a 3D optimum, useful application margin, physical equilibrium, damage evolution or transfer. No further multiplier, step or optimisation is authorised by this review. Final prose and figure QA remains a separate addendum.

## Final prose, maps and figure QA

**Final QA PASS**, with no new candidate or physical computation. Read `three_head_decision.md`, case README and atlas sidecars; visually inspected both summary/calibration figures and all three state atlases. Verified current plotting-source SHA against the map manifest and every listed input hash. The companion verdict now binds final document, five PNG/PDF/sidecar sets, map checks/manifest and plotting source SHA-256 values.

The final text correctly separates r1's 0 accepted outcome from the prospective r2 result, fixed 2% cap from actual tiny parameter use, exact analytical UV curvature from authoritative nonlinear guard acceptance, and finite component success from application/evolution validity. c60's tiny .000370%/.000032% full/damage UV improvements are not described as recovery; the red/blue atlas redistribution is explicitly qualified against the regional scores. c20/c83 secondary driver/energy/strain costs remain visible. The proposed same-3D curvature-aware joint-coordinate selection is unimplemented; the audit grants no new solve or training.

Maps use normalized native Q4 mass sum1 and C=absUs/energy_scale, with zero contributions at prescribed Dirichlet nodes and full-mesh sum equal to rho². Node force contribution is correctly distinguished from strong-form PDE residual or causal damage attribution. FEM sum-relative discrepancies up to 1.12e-6 occur around rho²~2.46e-21 with absolute gap~2.75e-27; no new tolerance or physics acceptance is inferred. Native NN sum checks are at roundoff scale. Damage overlays, window outer support, Gouraud display interpolation, crop/stretch, log floor and shared within-state signed symlog ranges are disclosed. The c60 D008 exact-original fallback is clearly labelled.

All five figures are readable without claiming pointwise protection or large gains from strong signed colours. No blocking numerical, wording, normalization or visual issue remains.

## Final administrative caption/provenance refresh

Confirmed the final wording correction about no slack in actual physical checks preserves the scientific meaning. Reviewed appended Data provenance / How to read / Limitations sections and matching generator text. Both updated provenance manifests match their current plotting/calibration source hashes and all recorded inputs. All ten previously bound PNG/PDF files and the numerical map-check table are byte-identical; no result or figure was recomputed for this audit. Refreshed final SHA bindings and added `analysis_source/calibration.py` and root `calibration_inputs.json`.

Read Obsidian censor section66 (line958 onward) and the single Roadmap line11. They faithfully report r1 negative, r2 finite but tiny improvement, c60 not recovered, unguarded full/damage driver costs, no history/evolution validation and an unexecuted same-3D joint-coordinate proposal. The two image interpretations correctly avoid pointwise or strong-form residual claims. No blocking wording or provenance issue remains. Task may close; no other task or candidate was resumed.
