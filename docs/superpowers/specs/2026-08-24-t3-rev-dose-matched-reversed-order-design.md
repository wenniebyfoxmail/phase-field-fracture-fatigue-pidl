# T3-rev Dose-Matched Reversed-Order Sibling Design

## Decision

Run one complete `T3_rev_loading_order` production sibling after implementation,
sealing, test qualification, and a final machine-idle check. The case reverses
the first two 30-cycle amplitude blocks from T3 and leaves every other physical,
numerical, runtime, and event setting unchanged.

```text
T3:      c1-c30 0.108, c31-c60 0.126, c61-c150 0.120
T3-rev:  c1-c30 0.126, c31-c60 0.108, c61-c150 0.120
```

T3 and T3-rev therefore have the same prescribed amplitude histogram and cycle
count over c1-c60. This is only a nominal loading-dose match: it does not assume
that dissipated energy, fatigue-history increments, degradation, or any other
constitutive accumulated quantity is equal. Those responses are outputs of the
path-dependent system. The only intended input difference is loading order.
T3-rev runs from a fresh initial state and fresh roots; it never resumes or
mutates T3.

## Scientific purpose

T3 established a numerically qualified variable-loading trajectory with
first-hit/confirmation at c68/c71, two cycles earlier than P0. The published
P0-T3 analysis found a c30-baseline-corrected history signal that persisted
after c60 and remained spatially co-located with subsequent damage. That is an
empirical stored-field observation, not a unique mechanism identification.

T3-rev is the next discriminator because it separates two explanations that
T3 alone cannot distinguish:

1. response controlled only by the multiset of amplitudes accumulated through
   c60; and
2. response dependent on the order in which the same amplitudes were applied.

The primary estimand is the T3-rev minus T3 trajectory difference after both
cases have received the same first-60-cycle amplitude histogram. A nonzero
difference at c60 and later is evidence of order/path dependence for the
qualified numerical kernel plus the separately identified T3-rev case-definition
extension. It is not, by itself, proof of constitutive correctness or a unique
physical mechanism.

Three outcome patterns are predeclared:

1. If T3 and T3-rev remain numerically indistinguishable within the existing
   tolerances after c60, the experiment does not resolve a material order effect
   for these blocks. This favors, but does not prove, an exposure-dominated
   explanation.
2. If their stored fields or event trajectories remain different after c60,
   loading-order/path dependence is observed under the qualified numerical
   kernel and declared case-definition extension.
3. If early differences appear but converge before fracture, order affects the
   intermediate stored state while the terminal fracture trajectory is
   comparatively insensitive at the measured resolution.

## Predecessor and evidence graph

```text
P0/P0R repeatability PASS
        |-- T1 initial-defect trajectory: qualified
        |-- T2 material-state trajectory: solver-qualified failure
        |-- T3 loading-history trajectory: qualified
        |     `-- independent evidence review: PASS with disclosed
        |         provenance-layer difference
        `-- T3-rev loading-order sibling: this design
```

T3-rev requires the already qualified P0/P0R producer baseline and the
independent T3 evidence review. It does not require T2 or T2-CONT success. The
Mac review receipt is non-authorizing and must be archived verbatim before the
T3-rev seal is built. The trajectory registry must record P0, T1, and T3 as
qualified and T2 as `FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4`.

## Alternatives considered

### Complete production sibling (selected)

Run with the unchanged event and confirmation rules until confirmed fracture or
the existing c150 case horizon. This produces a directly comparable event
trajectory and retains all field/history/energy shards needed for mechanism
analysis.

### Fixed-window diagnostic (rejected)

Stopping at c60, c68, or c71 would be cheaper and could show stored-field
differences, but it could not determine T3-rev first-hit and confirmation under
the sealed event definition. It would leave the main order-effect question
partially answered.

### Resume T3 and swap future blocks (rejected)

Reusing any T3 state would import irreversible damage and history from the
original order. It would no longer compare two trajectories from the same
initial condition and would invalidate the dose-matched discriminator.

## Case identity and changed-axis closure

The new case identifier is `T3_rev_loading_order`. Its physics contract must
compare recursively against both P0 and T3:

- relative to P0, the only changed leaf is `loading.blocks`;
- relative to T3, the only changed leaf is also `loading.blocks`;
- the T3/T3-rev amplitude multisets for c1-c60 must be exactly equal;
- c61-c150 must be byte/value equal to T3 and P0 at `Umax=0.120`.

The contract must reject missing or extra physics leaves, bool/integer
substitution, non-finite values, duplicate JSON keys, invalid schema/version,
and any case identity inconsistent with `T3_rev_loading_order`.

The physical-input projection must include the complete initial-state closure
and all physical/numerical allowlisted fields. It must change relative to T3
because loading order is a physical input. Source/runtime identities remain
separate from the physical hash and are equality-gated.

## Sealed base preservation and minimal producer extension

The qualified T3 producer does not expose an external loading override and
hard-codes its five case roles. A truthful `T3_rev_loading_order` role therefore
requires a new producer identity. The existing sealed producer directory and
all legacy outputs remain byte-preserved.

The extension must use the qualified T3 producer as its immutable base:

- base producer source commit `7c56ff383187cdee2f45e1b15d707f148f386302`;
- base source-manifest SHA-256
  `61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e`;
- a new versioned extension directory that contains only the files that must
  change to register and validate `T3_rev_loading_order`;
- a composite source manifest binding the base manifest, every extension file,
  and the repository commit containing the extension; and
- an explicit machine-readable diff inventory classifying every changed line as
  case registration, loading-block definition, contract data, or role
  allowlisting.

The runtime path places the extension before the sealed base and rejects any
unallowlisted shadow file. Existing P0, P0R, T1, T2, and T3 case builders must
produce value-identical expanded case physics under the extension. The sealed
base inventory must be hash-verified before and after the T3-rev run.

The new producer identity changes honestly because role allowlists, the family
driver, C5 trace role validation, contract data, and protocol validation must
recognize the new case. Tests must prove that no numerical update, Newton,
stagger, event, exporter, terminal-validation, or gate formula changes. The
unchanged runtime identities remain:

- the same physics-contract schema apart from the case-specific loading blocks;
- the same runtime lock;
- MATLAB R2025b Update 5, PCWIN64;
- the same four MEX SHA-256 identities;
- `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
  `OPENBLAS_NUM_THREADS=1`, and `MKL_DYNAMIC=FALSE`;
- the same mesh, material, initial state, recovery, event definition, loading
  substeps, Newton limits, stagger cap, and convergence thresholds.

No numerical-algorithm edit, relaxation, continuation, threshold change, MEX
rebuild, or runtime-infrastructure change is permitted. A source file whose
case-role allowlist must change receives a new hash and is bound by the
extension manifest; the receipt must not report it as byte-identical to T3.

## Execution boundary

Implementation provides a small, versioned T3-rev case-definition extension and
launcher overlay around the byte-preserved sealed base. It may validate the new
case contract and create a single launch receipt, but it must not create a
general authentication system.

Before launch it must:

1. verify the sealed base, extension/composite source manifests, repository
   commit, and qualified predecessor evidence;
2. verify the exact T3-rev physical projection and runtime identities;
3. verify fresh output, work, temp, preference, and cache roots;
4. reject resume or any existing target run root;
5. perform a final process check and refuse to launch while any MATLAB/FEM
   experiment exists; and
6. scope the action to exactly one `T3_rev_loading_order` execution.

The run is not retried or resumed automatically. It does not start T2-CONT,
full T2, another T3-rev, or any follow-on case.

## Event and terminal behavior

The sealed event logic remains unchanged. The run continues through the native
confirmation rule after first hit and stops on confirmed fracture. If confirmed
fracture does not occur by the existing c150 horizon, the absence is preserved
as a valid completed trajectory result rather than reclassified as a runtime
failure.

Allowed top-level terminal classes are:

- `PASS_CONFIRMED_FRACTURE_TRAJECTORY`;
- `PASS_NO_CONFIRMED_FRACTURE_BY_C150`;
- `FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE` with exact cycle/substep;
- `FAIL_NEWTON_NONCONVERGENCE` with exact cycle/substep;
- `FAIL_STARTUP_OR_RUNTIME`;
- `FAIL_INPUT_OR_IDENTITY`; and
- `FAIL_TERMINAL_PACKAGE_VALIDATION`.

Numerical failures must not be relabeled as runtime failures, and Newton and
coupled fixed-point failures must remain distinct.

## Predeclared evidence and analysis

Every completed cycle must preserve the same event, field, history, degradation,
raw/active driver, and energy artifacts as T3. Terminal evidence must bind the
source/runtime identities, complete input snapshot and projection, c5 gate,
sequential shard inventory, event metadata, terminal manifest, and package
validator identity.

The primary T3/T3-rev comparisons are:

- event trajectory and first-hit/confirmation deltas;
- same-cycle fields at c20, c30, c31, c40, c60, and c61;
- c30-to-c31 and c60-to-c61 transitions;
- c60 and later comparisons after equal first-60 amplitude histograms;
- own-event comparisons at both first-hit and confirmation;
- damage, history, fatigue degradation, raw and active driver fields;
- history and active-support areas;
- crack-tip and process-zone centroid, width, support, and spatial overlap; and
- energy components, with monitored aggregate `tot_en` retained as auxiliary.

If a requested cycle is unavailable because one trajectory terminated earlier,
the analysis must report `UNAVAILABLE` and must not extrapolate. Comparisons use
the predeclared numerical tolerances; observed zero differences may be reported
without changing tolerances to zero.

Interpretation is deliberately bounded:

- a post-c60 T3/T3-rev difference supports loading-order/path dependence for
  this producer;
- event timing alone does not establish mechanism correctness;
- constitutive accumulation, irreversible state evolution, and solver-path
  dependence remain possible contributors; and
- no road-scale predictive claim follows from this single discriminator.

## Evidence archiving

Before building the T3-rev seal, implementation must:

1. archive the Mac independent-review receipt verbatim in a dated evidence
   document;
2. record `PASS_WITH_DISCLOSED_PROVENANCE_LAYER_DIFFERENCE` without rewriting
   either immutable T3 evidence layer;
3. record that the OneDrive directory has 99 physical files but a declared
   97-file payload because its descriptor and checksum ledger are excluded;
4. record that Mac verified P0 through the hash-bound published analysis and
   prior qualified evidence rather than re-reading raw P0 shards; and
5. update the artifact/trajectory index with the qualified P0, T1, and T3
   trajectories plus the solver-qualified T2 failure.

The review receipt grants no production capability.

## Tests

Tests must prove:

- exact T3-rev loading blocks and case identity;
- T3/T3-rev first-60 amplitude-histogram equality and order inequality;
- recursive changed-axis closure with `loading.blocks` as the only changed leaf;
- full physical-input and initial-state closure;
- unchanged base-source/runtime/MATLAB/MEX/thread/mesh/material identities;
- exact extension file allowlist, composite manifest, and classified source
  diff inventory;
- value-identical expanded P0, P0R, T1, T2, and T3 cases under base and
  extension builders;
- unchanged numerical update, Newton, stagger, event, exporter,
  terminal-validation, and gate formulas despite required role-allowlist edits;
- unchanged event rule, c5 gates, Newton limits, and 1000-stagger cap;
- fresh roots, no resume, and rejection of an existing target root;
- final process check and refusal while MATLAB/FEM is active;
- exactly one case invocation and no automatic retry or follow-on launch;
- preservation of distinct numerical/runtime terminal classes;
- sequential shard and terminal-package inventory validation;
- no authorization capability in terminal or analysis receipts; and
- sentinel checks proving no T2-CONT or full T2 entry point is called.

## Non-goals

- No P0, P0R, T1, T2, or T3 rerun.
- No T2-CONT execution or relaxation sweep.
- No mutation of the sealed base producer or legacy output packages.
- No numerical-algorithm, runtime, MEX, event-formula, or gate-formula
  modification; only the declared case-definition/role extension is allowed.
- No raw P0 package replication solely to strengthen the already accepted Mac
  review.
- No automatic T3-rev retry, resume, or downstream experiment.
- No claim that loading order is the unique physical mechanism.

## Implementation sequence after spec approval

1. Archive the Mac receipt and update the artifact/trajectory index.
2. Add the versioned T3-rev case-definition extension, contract, composite
   source manifest, classified diff inventory, and strict validation tests.
3. Add the seal builder and single-case launcher overlay using the established
   T3 sibling pattern while resolving extension files before the sealed base.
4. Run focused T3-rev, T3, T2-CONT, and P0 protocol tests.
5. Build and independently verify the T3-rev seal.
6. Recheck that the repository is clean and MATLAB/FEM is idle.
7. Launch exactly one complete T3-rev trajectory.
8. Monitor without modifying the run; on exit validate and seal terminal
   evidence, then stop without follow-on work.
