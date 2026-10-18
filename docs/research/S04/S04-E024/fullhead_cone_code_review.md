# D009 independent pre-use code review

**BOUNDED PRE-USE PASS** — source `a7186d4f1b519652c638e872cb2fcec9b4cf5a08`; no blocking finding. No real three-state diagnostic was executed by this reviewer.

Reviewed the 568-coordinate shared UV/bias radius, original E023 loader and D007 basis provenance, D/BC/window feature convention, fixed/free weak adjoint with normalized mass, AMOR engineering-shear driver adjoint, own-error normalization, active-set cone projection and unit-gradient minimum-norm hull. The derivatives of the half-normalized squared errors equal fractional relative RMS derivatives at the origin. Determinants occur once in the native strain adjoint. The radius is an infinitesimal coordinate scale, not an accepted finite correction.

Independently reran all five source tests (PASS). Added read-only near-opposed hull checks at five scales and forty deterministic random cone checks (PASS; saved `independent_geometry.json`). New normalized-direction safeguards correctly avoid relying on a tiny unnormalized hull certificate to assert strict descent. Source SHA-256 values are in the companion JSON.

The runner preserves original checkpoint hashes and model digest/gradNone, checks saved-field affine realization and unchanged outside support, records all nine analytic/finite-difference derivatives at the frozen three epsilon values, refuses a touched exact origin trace kink, and requires smallest-epsilon agreement. No optimizer step, parameter write, corrected-field acceptance, remote action, new FEM/reference or history/fatigue update is present. Resource and identity limits remain fail-closed.

Result limitations: a cone residual allowance of 1e-8 is numerical, not physical nondegradation. A boundary direction with zero guard slope need not permit any finite straight step. Strict descent requires the reported actual normalized slopes and finite-difference checks, not margin alone. A zero/unresolved projection is at most first-order evidence in the specified coordinates. Secondary driver constraints describe instantaneous elastic-error sensitivity, not damage evolution. Missing history channels remain missing; the protocol's “history admission” should be understood only as frozen asset lineage, not validated history physics. Numerical geometry does not establish an application tolerance or the legacy .001 threshold as a physical standard.

Proceed only with the already authorized offline diagnostic; independent numerical/claim review remains required after results. No source edits were made.
