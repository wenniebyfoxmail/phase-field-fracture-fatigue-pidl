# E024-D006 focused independent physical-observable review

**PASS_WITH_PRESERVED_SCOPE_AND_NUMERICAL_LIMITATIONS**, source `273e413737dd24a9994cbacce3de86c6a60cc887`, results in physical_observables_v2. No blocking definition/numerical mismatch in the reviewed finite static diagnostic. This does not establish joint physical success, net damage evolution, history/fatigue correctness or new teacher qualification.

## Definitions and admission

Native four-GP Q4 engineering strain is [exx,eyy,gamma_xy], not neural coordinate gradients or tensor-shear with a different norm. Material AMOR plane-strain constants are E=1,nu=.3,eta0. Undegraded tensile energypsi0 includes deviatoric energy plus positive trace volumetric energy; active energy=(1−d_GP)^2psi0. `elastic_damage_driver` is the instantaneous nonnegative elastic-conjugate amplitude2(1−d_GP)psi0, not the signed derivative, full netAT1 force, irreversible maximum-history force, fatigue driving quantity or a damage update. GPdamage>.1 and physical-window core+.02 define regions. All-node UV region metrics from D005 are distinct from these GP quantities.

Weak force uses undegraded compression plus degradedAMOR tension, native quadrature and unchanged top/bottom-excluded free nodes. rho_u = mass-dual free-force norm/(area absUs), with mass normalized to sum1, matching the old normalization. Force difference to the same FEM field is separately reported; it is not an independently qualified alternative teacher or a fabricated equilibrium target. Integrated active energy is explicitly named and not confused with total elastic energy including undegraded compression. Recomputed FEM active_after matches about1e-14.

The initialv1 run stopped before any score because c20/c83 do not contain fatigue/prior_damage; that failure is preserved. V2 correctly records optional presence and hashes without assigning zeros: c20/c83 neither present, c60 both present, all three no maxH/history field. AbsentmaxH prevents reconstructing net history driving or validating irreversibility/evolution. Rechecked33 originalE023 file hashes,3reference file hashes,3D005 UV input hashes and all present optional-channel byte hashes. No model, frozen damage, fatigue/history array or original file was updated.

## Independent numerical route

Used raw xy/conn/UV/damage, **explicit2×2 Jacobian inverse**, manual engineering strains, independent component AMOR deviatoric/volumetric stress and per-node `np.add.at` force/mass assembly. No imports of originalweak_form.assemble or q4_strain. This independently checks FEM/E023/shrink02 for three states,36 saved physical arrays,96 regional relative errors,6weak residual/force-gap/energy/trace-sign rows. All are consistent; original vs independentrho differences<=6.40e-14, force-gap<=5.69e-14. Original FEMrho is about4.4–5.0e-11; independent near-cancelled FEM force differs at floating-point level, so no bit-exact claim or strictMacrho waiver follows.

The reviewer initially imposed an arbitrary pure absolute1e-10 comparison onpsi0 and hit a maximum1.41e-10 difference on a field with magnitude around8.7e3. That failed log is retained. Explicit-scale allclose(rtol1e-11,atol1e-10) and independent regional reductions establish agreement; regional-relative values differ<=1.52e-10 even when reference denominators are tiny. This is a declared supplemental comparison, not a change to any original experiment threshold or strictMac check. No nonfinite independent values or numerical warnings occurred.

Additionally checked all96 absolute error/reference conditionalRMS/GP area fraction rows against their saved physical arrays; maximum absolute difference2.23e-16. Original assembler NumPy warnings remain in stderr, root cause unproven and not repaired/erased by alternate-route agreement. The first reviewer attempt againstv1 found no result table and performed no numerical audit; its log remains withv1.

## What improved and what did not

|State|Full strain relative-error change|Full elastic-amplitude error change|rho_u before→after|
|---|---:|---:|---:|
|c20|−.157180%|−.305723%|47.18533538→47.18534701|
|c60|−.229974%|−1.324053%|57.72117463→57.91603275|
|c83|−.040296%|−.109852%|51.58341592→51.72830399|

Full/damage-region strain and instantaneous elastic-amplitude fitting component gains can be retained. They do **not** mean weak equilibrium improved: rho_u increases in all three states (c20 minutely), while the same FEMfieldrho is near5e-11. These different diagnostics are not interchangeable. Background driver/energy error also increases in relevant regions despite D005 backgroundUV RMS decreasing. Thus fourUV metrics improving does not establish background physical-observable preservation.

For c83 background elastic amplitude, FEM conditionalRMS1.57e-7 versus error1.036e-4→1.048e-4; interior reference3.94e-7 versus error4.444e-4→4.505e-4. Near-zero reference amplifies the relative error, but the nonzero false elastic excitation is not merely a denominator illusion. Its absolute scale is small relative to full-field error, which is not evidence of acceptable downstream risk. Without maximumhistory, coupled solve and application budgets, neither reviewer nor algorithm can decide whether it changes damage/fatigue behavior. Spatialtrace-sign mismatch is descriptive of the constitutive split, not a reconstructed history switch.

The only supported scope is same exposed states/currentFEMdamage, nativeQ4 derivative observables and same-host weak-force comparison. No NN-continuous derivative/perturbation/generalization/irreversibledamage/coupledFatigue certification. .001 remains historicalUV diagnostic; physical/background tolerances undefined. Original historical verdicts and strictMacLR/mass/D/rho exceptions remain. No training, SVD/fit, FEMsolve, damage/history/fatigue update, checkpoint write, newstate/holdout or remote action was performed. NormalCodex remaining84% before and83% after the bounded numerical phase; no new research stage was opened.

Main decision prose and figures were subsequently reviewed in the following final addendum. No next candidate or experiment is authorized by this report.

## Final physical decision and figure review

Reviewed repaired `physical_decision.md`, both requested PNGs and sidecars, and display binning source. No remaining blocking definition/interpretive issue. The mixed conclusion retains staticstrain/elastic-amplitude fitting progress while reporting weak-equilibrium/background costs and refusing claims of subsequent damage/crack/fatigue benefit. Optional channels/maxHabsence, engineeringstrain/GP masks, active_after identity, same-hostrho normalization, absolute near-zero-background reference values, warnings and scale-aware independent comparison are explicit.

One wording error in the first decision draft denied that20% of the parameter direction also gives20% of its UVcorrection; corrected final text now states the fixed-feature affine identity and distinguishes it from total displacement/error changing20% or physical quantities changing2%. This matches the already verified D005 algebra.

Decision bars have correct signs and expose c20's tinypositive rho change with scientific notation rather than roundedzero. GP-driver localfields display all three states in matched physical windows, shared per-state error scales, fixed260×80 det-weighted RMS bins, signed difference of binRMS, explicit vertical stretch/displayfloor and white emptybin explanation (not physical cracks or voids). No random GP sampling or unbinned metric change is introduced by display binning. Such regional mixed maps do not imply every GP benefits.

The sole next proposal—prepare an own-state fixed-damage small-head correction with weak-equilibrium non-degradation checked alongside UV/driver/background—follows the observed gap and remains **unexecuted**. Relative non-degradation is not a new physical acceptability threshold; missinghistory and application requirements cannot be manufactured by adding that constraint. This review does not implement or authorize another correction, solve, training or coupled update. The present task can close with its audited mixed result.
