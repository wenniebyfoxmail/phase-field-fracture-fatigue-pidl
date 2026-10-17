# GPT Pro Planning Gate: Freeze-Then-Select Stage A

## Question

How should the project implement a minimal frozen-field, stability-validated
weak selector without changing known phase-field physics or overstating
synthetic/FEM evidence as road validation?

## Advice adopted

- Make the first mechanism question whether frozen snapshots can recover a
  declared residual support more reliably than one sparse solve.
- Keep the implementation separate from PIDL training code and run only
  deterministic analysis on Mac.
- Treat known phase-field terms as fixed; select only a declared correction
  slot with at most 10--14 traffic, temperature, moisture, and interaction
  candidates.
- Split repeated trials by trajectory and time block; report selection
  frequency, sign consistency, condition warnings, and held-out weak-residual
  error.
- Start with 64 trials, stable frequency 0.75, sign consistency 0.85, and at
  least 5% held-out improvement over the no-correction residual. Treat these as
  sensitivity-tested protocol values, not universal constants.
- Require explicit `claim_class`, `physics_family`, frozen-field provenance,
  and oracle-column rejection for reality-facing inputs.

## Advice modified or deferred

- The first weak assembler supports algebraic residual correction terms only.
  Spatial derivative candidates and integration-by-parts boundary terms are
  deferred until a separately declared spatial-correction slot is justified.
- Parquet is deferred; CSV is used for the tooling gate so dependencies and
  hashes remain transparent.
- Existing FEM/PIDL exports and the joint-training baseline are protocol stages,
  not part of the manufactured Stage A result.

## Claim boundary

Passing Stage A proves only that the software can recover declared terms on a
manufactured frozen-field problem. It does not prove a road mechanism, improve
PIDL training, discover the governing PDE, or beat the observation-first
digital-twin branch.
