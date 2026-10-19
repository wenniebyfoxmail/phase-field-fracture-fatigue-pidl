# S09-E016 result review

Reviewer: ChatGPT Pro, Haofan account
Run: `S09-E016-R001-factorisation-readiness`
Implementation commit: `f9db7db49dee5d88914a2ea22e38a2c9249b3a48`
Verdict: `E016_RESULT_REVIEW_PASS`

The reviewer accepted the result consistency, numerical-readiness
interpretation, and preparation of an E017 three-arm pilot card. It did not
authorise E017 execution.

## Independently checked evidence

- Receipt status is `SUCCEEDED` with `output_validation=PASSED`, zero optimizer
  steps, zero model forwards, and no new-data access.
- The two recorded source hashes match the frozen E015 field archive and E010
  A25 scalar table identities.
- The CSV has 16 rows and 44 unique columns; all cycle identities are complete.
- `C_F=C_B=C_J` contains all 16 cycles. All 640 numeric CSV cells are finite.
- The reviewer recomputed all seven 25-pair groups: 175 pair identities,
  margins, outcomes and counts match the decision JSON.
- All reported round-trip relative errors are below the frozen
  `64*eps_float64` tolerance.

The core observed baseline is also reproduced: B25/FEM hazard-amplitude ratio
has median `0.012572`; shape half-L1 median `0.999840`; shape cosine median
`3.998e-5`; target-support capture median `0.001510`. This means the B25 field
is badly mismatched in both amount and spatial allocation, while each field's
own factorisation remains numerically valid.

## Interpretation constraints

- Hazard amplitude and weighted-mean absolute increment remain different
  observables. FEM scores `44` on hazard-amplitude ranking and `50` on absolute
  increment ranking; those labels cannot be silently interchanged in E017.
- A25 remains scalar-only. No A25 hazard, shape, centroid or nodewise claim was
  created.
- The real E016 packet contains no zero event, so strict-zero behavior remains
  implementation evidence rather than a new real-data observation.
- The reviewer did not receive `factorisation_arrays.npz`; it checked the
  authoritative CSV/JSON and did not independently recompute every nodal
  capacity inequality.
- The browser upload re-encoded the PNG to a different size. Visible curves and
  annotations were checked, but the PASS does not authenticate the uploaded
  PNG byte-for-byte against the local 458,432-byte original. The local CLI
  decoded the original and closed it in the receipt; no rerun is required.

## Mechanism implication for E017

Use three matched arms: existing direct damage head, a true amplitude-only
factorised ablation with `S` frozen, and an amplitude-plus-shape factorised
head. The amplitude-plus-shape versus amplitude-only contrast isolates the
value of a learnable spatial distribution; the factorised full arm versus the
direct arm assesses the whole representation intervention. All arms must use
the same data, information, beta `0.25` equilibrium constraint and predeclared
budget. The result permits card preparation only; it does not establish
training success, rollout, holdout generalisation, full phase-field physics,
or physical-teacher truth.
