# PIDL--FEM Diagnostic Analysis Protocol

Date: 2026-06-21

Status: Current shared PIDL/FEM diagnostic analysis protocol. Use this as the
entrypoint for new case-level evidence maps. State mapping is schedule
dependent: one-state-per-cycle runs may use `j=c-1` when verified, while
retained five-substep runs use explicit peak/unloaded step labels.

Purpose: define the analysis sequence for a PIDL/FEM case before it is used as
evidence. The protocol tests scalar crack-event timing and hidden fracture-state
evolution. Scalar agreement is necessary evidence, but it is not enough to
claim field-level mechanism fidelity.

This protocol is for analysis records and case evidence maps. It is not a
thesis prose template.

## Scope

Use this protocol for controlled phase-field fatigue comparisons between a FEM
reference and a PIDL run. Before analysis, classify the loading protocol and
saved-state cadence. The state mapping is different for one-step-per-cycle runs
and retained multi-substep runs.

The current strict alignment track uses the cyclic five-substep schedule:

```text
load factors: 0.25, 0.50, 0.75, 1.00, 0.00
```

The FEM reference is treated as the numerical reference for the controlled
benchmark. It is not treated as physical pavement truth.

## State Mapping Rule

Compare by state label, not by raw loop index. The mapping is schedule
dependent, so the loading protocol must be recorded before any FEM/PIDL field
comparison.

### One-step or one saved state per cycle

Use the `j=c-1` mapping only when the PIDL archive stores one matched state per
physical FEM cycle and the saved-state timing is verified.

```text
FEM cycle c -> PIDL saved index j = c - 1
```

This convention is valid for one-step loading or older one-state-per-cycle
archives when the FEM state and PIDL saved state represent the same stage of the
cycle, for example the same post-solve or post-history-refresh state. It does
not provide separate peak and unloaded states unless those states were exported
separately.

### Five-substep retained loading

For physical cycle `c` in the five-substep schedule:

```text
PIDL global step = 5*(c-1)+0 -> FEM cycle c, substep 1, load 0.25
PIDL global step = 5*(c-1)+1 -> FEM cycle c, substep 2, load 0.50
PIDL global step = 5*(c-1)+2 -> FEM cycle c, substep 3, load 0.75
PIDL global step = 5*(c-1)+3 -> FEM cycle c, substep 4, load 1.00 / peak
PIDL global step = 5*(c-1)+4 -> FEM cycle c, substep 5, unload
```

Useful shorthand:

```text
cN_peak     -> PIDL step 5*(N-1)+3
cN_unloaded -> PIDL step 5*(N-1)+4
```

Do not map `c1_peak` to PIDL step 4 in the five-substep schedule. For this
schedule, step 4 is the first unloaded state. Do not assume PIDL step 0 is a
true unloaded prehistory state. If a true
`state0_initial_unloaded_prehistory` export is missing, mark it as unavailable
and audit PIDL step 0 as a loaded 0.25 state.

## Tier -1: Provenance And Data Capability Gate

Goal: decide whether the case is analysable before interpreting results.

Required checks:

- PIDL run folder
- FEM reference folder
- PIDL variant name
- config file
- loading protocol and saved-state cadence
- run command or producer note, if available
- code branch and commit, if available
- generated analysis folder
- state mapping source
- available fields
- missing fields
- figure/table provenance
- whether outputs are regenerated or legacy

Required output:

- run provenance block
- data availability table
- figure/table manifest
- missing-evidence list

Decision rule:

If provenance, state mapping, or required fields are missing, the case cannot be
classified as main evidence. It may still be used as a diagnostic or appendix
case if the limitation is explicit.

## Tier 0: Setup Alignment

Goal: check whether FEM and PIDL solve the same controlled benchmark.

Required checks:

- geometry
- initial crack / notch
- phase-field model
- material parameters
- phase-field length scale
- loading amplitude
- loading schedule class: one-step or retained multi-substep
- loading cadence
- boundary conditions
- history initialisation
- coordinate/frame mapping
- mesh/grid projection method
- residual convention, normally `PIDL - FEM`

Required output:

- setup alignment table
- state mapping table
- projection/residual convention note

Decision rule:

If setup alignment is not verified, the case cannot be used as main evidence for
field-level comparison.

## Tier 1: Scalar Event Timing

Goal: check scalar crack-growth timing.

Required quantities:

- fatigue life or event cycle
- event definition
- first event
- confirmed event
- peak or unloaded state used for event detection
- event timing error
- seed or `Umax` sensitivity, if available

Required output:

- scalar event timing table
- optional S-N or `Umax` trend figure when multiple loads are available

Decision rule:

Scalar event timing agreement is useful but does not prove field-level
agreement.

## Tier 2: Damage And Crack-tip Field

Goal: check phase-field damage morphology and crack advance.

Required quantities:

- `alpha` field
- crack-tip position
- threshold used for crack-tip extraction
- whether crack tip is measured on the FEM grid or PIDL grid
- damage residual field
- matched-state comparison
- matched-event comparison, if available
- precrack/notch mask convention
- shared colour scale convention for field figures

Required output:

- `alpha` field comparison figure
- crack-tip comparison table
- damage residual map
- morphology or process-zone summary, if available

Decision rule:

Damage magnitude agreement is not sufficient. Crack advance, morphology and
spatial residuals must also be checked. Scalar agreement is downgraded if
damage morphology or crack-tip advance is inconsistent.

## Tier 3: Fatigue-history Field

Goal: check accumulated fatigue history.

Required quantities:

- `alpha_bar`
- `hist_fat`, if this is the run's stored history name
- `Delta alpha_bar`, if available
- tip-region `alpha_bar`
- process-zone `alpha_bar`
- `alpha_bar` residual field
- fatigue-history accumulation path

Required output:

- `alpha_bar` or `hist_fat` field comparison figure
- tip-region ratio table
- process-zone overlap table, if available
- history accumulation curve, if available

Decision rule:

If fatigue history is wrong, scalar event timing agreement cannot be interpreted
as mechanism fidelity.

## Tier 4: Crack-driving Field

Goal: separate raw tensile energy from the active fatigue-driving quantity.

Required quantities:

- `psi_raw`
- `g(alpha)`
- `psi_active = g(alpha) * psi_raw`
- `history_driver`
- `f_fatigue`
- tip-region raw-driver ratio
- tip-region active-driver ratio

Required output:

- `psi_raw` comparison figure
- `psi_active` comparison figure
- driver ratio table
- active-driver deficit summary

Decision rule:

Raw `psi` agreement does not imply correct fatigue driving. If `psi_raw` agrees
but `psi_active` or `history_driver` disagrees, classify the case as an
active-driver mismatch unless another verified explanation is available.

## Tier 5: Energy Accounting

Goal: check where the energy path differs before explaining why.

Required quantities:

- `E_el`
- `E_d`
- `E_hist`, if available
- `Delta E_d`, if available
- matched-state energy path
- field residual reductions connected to energy terms

Required output:

- energy comparison table
- energy history figure, if available
- incremental energy table, if available

Decision rule:

Energy accounting is an observation layer. It identifies whether the mismatch is
primarily elastic, dissipative, history-penalty-related, or incremental-path
related. It does not by itself prove the cause.

## Tier 6: Diagnostic Explanation

Goal: test possible causes of the mismatch after the field and energy evidence
has been established.

Possible diagnostic checks:

- loading cadence sensitivity
- optimiser polish
- architecture or representation variants
- boundary-condition variants
- sampling or quadrature variants
- history-driver definition variants
- oracle or mask checks, explicitly labelled
- gradient-balance diagnostics, if exported

Required output:

- diagnostic ablation table
- negative-result summary
- explanation verdict tied to available evidence

Decision rule:

If cadence, optimiser polish and representation variants do not remove the
mismatch, report the case as evidence of an unresolved coupled history-driver or
field-representation problem. Do not silently convert a diagnostic oracle into
the FEM reference.

## Required Data Availability Table

Each analysed case must include this table.

| Quantity | Available? | Source file | Notes |
|---|---|---|---|
| `N_f` / event timing | | | |
| crack tip | | | |
| `alpha` | | | |
| `alpha_bar` / `hist_fat` | | | |
| `psi_raw` | | | |
| `psi_active` | | | |
| `f_fatigue` | | | |
| `g(alpha)` | | | |
| `E_el` | | | |
| `E_d` | | | |
| `E_hist` | | | |
| `Delta E_d` | | | |
| strain/stress fields | | | |
| gradient diagnostics | | | |

## Figure And Table Manifest

Every figure or table used in the analysis must be listed.

| Figure/table | Path | Regenerated or legacy | Source data | Safe to use? | Notes |
|---|---|---|---|---|---|
| | | | | | |

Legacy figures are not main evidence unless provenance, state mapping and source
data are verified. If provenance is incomplete, mark the figure as
`legacy_only` or `do_not_use`.

## Case-level Output Template

For each case, return:

```text
Case ID:
Case name:
Purpose:
Diagnostic question:
Reference FEM:
PIDL variant:
Run folders:
Config files:
Loading protocol:
State mapping:
Generated analysis folder:

Available fields:
Missing fields:

Tier -1 provenance/data verdict:
Tier 0 setup verdict:
Tier 1 scalar verdict:
Tier 2 damage/crack-tip verdict:
Tier 3 fatigue-history verdict:
Tier 4 driver verdict:
Tier 5 energy-accounting verdict:
Tier 6 diagnostic-explanation verdict:

Key numerical observations:
Figures generated:
Tables generated:

Safe observations:
Observations that need caution:
Results that should not be used:
Missing evidence:

Limitations:
Recommended evidence classification:
Recommended next diagnostic action:
```

## Evidence Classification

Classify each case as one of:

```text
MAIN_EVIDENCE
SUPPORTING_EVIDENCE
NEGATIVE_DIAGNOSTIC
APPENDIX_ONLY
LEGACY_ONLY
DO_NOT_USE
NEEDS_RERUN
NEEDS_EVIDENCE
```

Use `MAIN_EVIDENCE` only when provenance, state mapping, source fields and
analysis outputs are all verified.

Use `NEGATIVE_DIAGNOSTIC` when the case is reliable evidence that a tested
explanation did not close the field-level mismatch.

Use `NEEDS_EVIDENCE` when the run might be useful but the files needed for a
specific claim are missing or unverified.

## Claim Rules

- Do not use scalar event timing agreement to claim field-level correctness.
- Do not use raw `psi` agreement to claim fatigue-history correctness.
- Do not treat the FEM reference as physical truth.
- Do not claim real pavement validation.
- Do not claim calibrated concrete fatigue behaviour.
- Do not use legacy figures as main evidence unless provenance and state mapping
  are verified.
- Do not infer missing fields silently.
- Do not compare PIDL and FEM by raw loop index when state labels differ.
- Do not replace the FEM reference with a masked or oracle field unless it is
  explicitly labelled as a counterfactual diagnostic.

## Final Evidence Map

After analysing a set of cases, produce:

```text
Main safe claim:
Main scalar result:
Main field-level result:
Main hidden-state mismatch:
Main negative diagnostic:
Best figure:
Best table:
Results to exclude:
Missing evidence:
Recommended next checks:
```

The final evidence map should only list observations supported by source files
and regenerated or provenance-verified outputs.
