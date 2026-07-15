# FEM Surrogate Transition Gate

**Status**: diagnose first; current single-trajectory mesh operator is quarantined and assimilation-ineligible.

## PIDL Experiment Gate

- **Mechanism question**: can a learned transition operator reproduce FEM crack-process evolution on an unseen physical trajectory, while preserving the active-driver/process-zone/fatigue-history mechanism needed for observation assimilation?
- **Claim changed if success**: a surrogate may compete with direct FEM in the locked reality-assimilation protocol, provided it improves cost without degrading probabilistic RUL, future crack geometry, parameter recovery, or FEM-centred field metrics.
- **Claim changed if failure**: direct FEM remains the transition model; the surrogate is tooling/diagnostic only and cannot be used to claim FEM reproduction.
- **Cheaper diagnostic first**: audit dataset diversity, split semantics, conditioning variables, existing checkpoints, and provenance before any training.
- **Minimal output asset**: this decision note plus, only after a valid run, one `fem_centred_metrics.csv`, `RUN_MANIFEST.json`, and locked prediction package.
- **Code/producer alignment**: Mac is import/unit/audit only. Any later training belongs on Taobo/CSD3/Windows-PIDL from a clean shared commit and reviewed run record.
- **Success criteria**: leave-one-physical-trajectory-out performance; same observation contract as direct FEM; RUL CRPS/coverage and crack-tip forecast no worse than the declared direct-FEM baseline; active-driver log-MAE/correlation/support gates from the project experiment protocol; no oracle feature leakage into deployment observations.
- **Failure criteria**: within-trajectory-only evaluation, missing physical conditioning, mixed physics families, teacher-forced test states, persistence-level rollout, field-mechanism gate failure, or missing provenance.
- **Registry destination**: `docs/research_frontier.md` after physical-trajectory evidence exists; until then keep this branch diagnostic/quarantine.
- **Decision**: diagnose first; do not launch or promote the current prototype.

## Current code audit

The existing prototype is internally coherent as a tooling experiment:

- native FEM quad graph with local and coarse message passing;
- irreversible damage/history and non-increasing degradation constraints;
- raw `psi` prediction with explicitly derived eta-zero active support;
- masked c20/c40 one-step audits, recurrent c67-to-c76 validation, and locked c76-to-c89 rollout;
- FEM-centred field errors, active-support overlap, and persistence comparison.

It does **not** yet answer the project objective:

1. The dataset builder requires exactly one complete `c1...c89` trajectory.
2. Training, validation, and test are cycle slices of that same trajectory.
3. Inputs contain state, coordinates, element area, and cycle phase, but no load spectrum, material/fatigue parameters, precrack geometry, or environment descriptor.
4. The cycle embedding is normalized to a fixed maximum of 89 and therefore encodes this particular run horizon.
5. No trained checkpoint or locked output package currently exists locally.
6. A same-trajectory c76-to-c89 rollout cannot establish unseen-load, unseen-material, or field generalisation.

The dataset and training manifests now state `claim_class=tooling-only`, `trajectory_generalization=false`, and `assimilation_eligible=false`. Dataset creation requires explicit trajectory and physics-family provenance. Training requires `--allow-single-trajectory-diagnostic`; omitting it fails before a training loop can start.

## Requirements before a surrogate can enter assimilation

An externally reviewed multi-trajectory design is required before changing the reusable architecture. At minimum it must provide:

1. three or more compatible trajectories in one declared `physics_family`, with a separate physical trajectory held out;
2. conditioning on load spectrum and every varied material/fatigue/precrack/environment parameter;
3. split by trajectory, never by elements or late cycles of the same trajectory as the headline test;
4. recurrent rollout from only observations/states available at the forecast origin;
5. uncertainty, either an ensemble or calibrated residual model, so the surrogate produces distributions rather than one deterministic field;
6. projection through the same versioned vision/DIC/AE observation operators used by direct FEM;
7. comparison against persistence, empirical fatigue, nearest/direct FEM, and a parameter-matched direct FEM library;
8. rejection if the surrogate improves scalar life while failing active-driver/process-zone support.

The missing third compatible FEM trajectory and paired DIC/AE calibration remain the cheapest next evidence. Training the current single-trajectory network would consume compute without resolving either requirement.
