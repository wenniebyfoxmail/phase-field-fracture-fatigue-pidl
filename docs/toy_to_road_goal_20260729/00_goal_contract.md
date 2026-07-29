# Toy-to-road evidence goal

## Objective

Build an auditable bridge from the normalized Hard5 mechanism benchmark to an
observation-conditioned road-fracture forecasting workflow. Completion requires
all four evidence tracks below. No single track can support a road-validation
claim by itself.

## Shared scientific contract

1. FEM is the field reference. Every reference is versioned by mesh, loading
   protocol, model form, event rule, event phase, and snapshot hash.
2. The phase-field scale is `w1 = Gc / ell`; `c_w` is applied once inside the
   energy. Runs made with `w1 = c_w Gc / ell` are quarantined.
3. `first-hit` and `confirmed` are different event phases. They may not be
   substituted solely because their physical-cycle labels match.
4. Umax 0.11/0.12/0.13 is a controlled load-amplitude sensitivity family, not
   three independent roads and not a trajectory-generalization test.
5. Forecast generalization is evaluated by holding out an entire independent
   trajectory. Node, patch, and cycle splits from the held-out trajectory may
   not enter training, normalization, model selection, or early stopping.
6. Reality-facing observations contain only measurable channels and declared
   derived estimates. Damage history, degradation, raw driver, and active
   driver remain latent unless an explicit measurement operator and uncertainty
   model are supplied.
7. Mac is development and lightweight validation only. FEM/PIDL training runs
   require an approved producer and a predeclared experiment gate.

## Track 1: dimensionless transfer

Required outputs:

- corrected scale-contract audit;
- Pi-transfer table covering `ell/L`, `h/ell`, `Gc/(E ell)`,
  `alpha_T/w1`, and `E(U/L)^2/w1`;
- F1 exact-Pi positive control;
- F2 model-form or loading-form negative control;
- normalized FEM-centred field and event-phase metrics.

Acceptance boundary:

- F1 must recover the normalized fields and event semantics within a
  predeclared numerical tolerance;
- F2 must demonstrate that matching a small scalar Pi set does not override a
  change in plane state, boundary condition, contact, or geometry class;
- the verdict is dimensionless similarity or falsification, not road validity.

## Track 2: independent FEM trajectories

Required outputs:

- versioned trajectory bundle and validator;
- field exports for damage, history, degradation, raw driver, and active driver;
- observable-channel values and masks without latent-to-sensor leakage;
- first-hit and confirmed state maps;
- immutable leave-one-trajectory-out split lock.

Readiness gate:

- at least three trajectories must differ in initial defect, material state, or
  loading history, not only load amplitude;
- all trajectories must pass provenance, state-semantics, finite-field, mesh,
  and event checks before forecast training starts.

## Track 3: forecast evaluation

The only core candidates are a matched Markov graph control, TCN, and
Transformer. No further architecture family may be added before this goal is
closed or explicitly amended.

Required tasks:

- observed-state, same-regime `h1-h3` propagation;
- autonomous transition-warning evaluation;
- observation-reset conditional propagation;
- rolling forecast and availability-aware hazard/RUL output contract.

Acceptance boundary:

- all headline results use leave-one-entire-trajectory-out evaluation;
- FEM-centred active support, mechanism fields, event phase, uncertainty, and
  calibration are reported alongside scalar error;
- a free long rollout is a stress test, not a road-life prediction.

## Track 4: reality observation and inverse interface

Allowed direct observation families:

- registered crack images and masks, crack length, width, and connectivity;
- DIC displacement or strain and strain-sensor measurements;
- FWD applied load and deflection basin;
- WIM axle/load/speed/traffic spectrum;
- temperature and elapsed time;
- maintenance and reset records.

Derived quantities such as tensile energy require a constitutive model, plane
state, tensile split, registration, and uncertainty. They must be labelled
`derived_latent_estimate`, never `direct_sensor`.

Required outputs:

- versioned measurement operators and adapters;
- units, timestamps, masks, missingness, registration, and uncertainty;
- identifiability matrix separating state assimilation, material inversion,
  and forecast updating;
- a synthetic contract smoke that makes no real-road validation claim.

## Final decision classes

- `accepted_dimensionless_transfer`
- `accepted_multi_trajectory_forecast`
- `accepted_observation_interface`
- `diagnostic_only`
- `quarantined`
- `blocked_missing_evidence`

The final road-transfer verdict is no stronger than the weakest required track.
