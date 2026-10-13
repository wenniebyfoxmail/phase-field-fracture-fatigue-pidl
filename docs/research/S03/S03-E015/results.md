# E015 boundary/basis diagnostic — cycle225211.5

Status: real frozen solve and held validation completed; independent
PASS_EVIDENCE accepted for exact numeric packages and corrected figures. This is a conditional static response diagnostic, not recovered
true phase field, material properties, fatigue state or future-cycle prediction.

## Execution and common comparison

Plan v2 PASS_PLAN, exact source b8edbcf PASS_CODE, training-only actual assets
PASS_ASSETS. Figure-only asset repair was reviewed before launch. R001 prepared
646 training observations; R002 GPUServer8 PID2594884 completed all 254 solves
in 37.6140847s, below the soft600s completion budget. Residual maximum across
252 candidate solves <=2.32351e-15 (kernel requirement <=1e-8).

All five fit artifacts and receipt were retrieved and verified before stage12
extraction or displacement conversion. Separate R003 validation uses one held
support for all nine frozen predictions: 643/646 observations, area coverage
0.9983948181162807, missing IDs20545/21814/22030. Reference-coordinate eligibility
and training area weights unchanged; no high-load parameter/arm selection.

Apple NumPy emitted matmul divide/overflow/invalid RuntimeWarnings during rigid
projection despite finite written residuals/metrics. Independent scalar
fsum/hypot rigid projection and analytic two-column Gram singular values
(no matmul/lstsq/SVD calls) confirmed training MAEs within4.34e-19mm, held
residuals within5.64e-18mm and SVD within5.42e-20mm/q. No detectable output
deviation was found; warning retained rather than suppressed or used to rerun.

## Frozen selected arms

| Boundary | Basis | qR | qL | Training MAE mm | Held MAE mm |
|---|---|---:|---:|---:|---:|
| B0 inner | K0 right | 0.665 | 0 | 0.001006252845082 | 0.002505029230826 |
| B0 inner | K1 two tips | 0.665 | 0 | 0.001006252845082 | 0.002505029230826 |
| B1 outer | K0 right | 0.38 | 0 | 0.001180278028386 | 0.002897719039277 |
| B1 outer | K1 two tips | 0.38 | 0 | 0.001180278028386 | 0.002897719039277 |

| Baseline | Held MAE mm |
|---|---:|
| B0 d0-only prior | 0.002589638658036 |
| B0 intact | 0.003305377124196 |
| B1 d0-only prior | 0.002971117394953 |
| B1 intact | 0.003786344905177 |
| Secant | 0.001592145038993 |

Descriptive contrasts: boundary-only gain -0.000392689808451mm; basis-only gain
0; combined gain -0.000392689808451mm; interaction0; primary boundary-only minus
basis-only loss D=+0.000392689808451mm. Frozen classification is
`neither_single_change_improves`; none of four selected factorial arms beats
secant. This does NOT say all components failed or the whole route is impossible.

## Component-level progress and interpretation

B0 selected q reduces held error 3.26723% versus fixed d0 and 24.21351% versus
intact; it is nevertheless 57.33675% worse than secant. B1 exterior procedure is
15.67606% worse than B0. Both nested K1 selections land on qL=0 and exactly reuse
K0; extra left-tip freedom is not used by this training information set.

Sensitivity is not numerically zero or a pair of duplicate directions:

| Boundary | Weighted finite-secant singular values mm/q | Cosine | Isolated qR/qL span mm |
|---|---|---:|---|
| B0 | 0.000281528613122 / 0.000272242521649 | -0.01023990358 | 0.000194406977535 / 0.000181766073858 |
| B1 | 0.000420115230169 / 0.000382269727431 | +0.02740979677 | 0.000319481982786 / 0.000272281731073 |

All isolated spans exceed the frozen1e-10 numerical-unresolved threshold. This
establishes only numerical sensitivity of this model on this observed support,
not noise-qualified identifiability or uncertainty bounds. Boundary-dependent
qR (0.665 vs0.38) reinforces its status as a conditional model parameter, not a
stable measured material/state property.

The tested boundary enlargement and added left-tip amplitude do not resolve
the held response gap. They do not isolate a true BC error, prove the whole
damage basis adequate, or rule out better physically grounded geometry/BCs.
Next proposed direction: training-side registration and crack-prior geometry
qualification (especially assumed tips) before richer amplitudes; separately
ask whether reference/load response or a calibrated mechanical model is needed.
Freeze a new experiment and genuinely new response holdout before any such
adjustment; stage12 is consumed and cannot be reused for development selection.
No further fit or sweep authorized/started by this result.

## Evidence pointers

Raw: local_archive/experiments/S03-E015/runs/S03-E015-R001/prepare,
R002/fit and logs, R003/held_input and validate. Exact-source figures:
R003/figures_v2/factorial_errors.png, parameter_profiles.png, held_residuals.png
(same-basename PDFs/analysis sidecars). All nine residual maps share frame and
scale; no smoothing, node bootstrap, outlier deletion or preferred examples.
See review_status.md and run_receipts.md for approvals, source and machine.

Producer adopted independent PASS_CODE + PASS_EVIDENCE for delivery commit
79fd9266322c447fcc9d364a2d14c436e84f52f1. Numeric solve source remains b8edbcf;
only figure/sidecar repairs followed validation. Original figures retained.
All252 profiles, selections/states, sensitivity, nine held scores, common mask,
contrasts and receipt bindings independently matched. Receipt chronology
supports freeze-before-validation but is a recorded history, not independent
authentication of historical execution. Allowed claim: completed conditional
bridge and component-level gains; the two prescribed repairs do not close its
secant gap. Disposition: descriptive negative diagnosis, preserve progress,
design training-side geometry/model qualification with a new holdout next.
