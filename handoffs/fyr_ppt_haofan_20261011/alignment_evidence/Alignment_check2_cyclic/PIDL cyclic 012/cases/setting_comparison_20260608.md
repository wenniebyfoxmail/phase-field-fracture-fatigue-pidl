# PIDL cyclic 0.12 case setting comparison

## Cases included

- `one_peak_femmesh_softHist0_N100`
- `explicit_cycle_0_0p5_1_0p5_0_Nphys40_Nstep200`
- `stateTiming_onepeak_untilFrac_Nphys100_Nstep100`
- `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`

## Common setting

All four cases are PIDL / Deep Ritz neural phase-field fatigue cases for cyclic `Umax=0.12` with reverseBC-style displacement loading.

The strict aligned cases use the FEM-derived soft-history-0 mesh and are intended for FEM-PIDL comparison.

## Main differences

| Case | Loading timing | Run length | Mesh/alignment detail | StateTiming scratch | Fracture outcome |
|---|---:|---:|---|---|---|
| `one_peak_femmesh_softHist0_N100` | one retained peak state per cycle | nominal `N100` | strict FEM-derived soft-hist0 mesh | no full stateTiming export | first boundary hit around c82, confirmed around c85 |
| `explicit_cycle_0_0p5_1_0p5_0_Nphys40_Nstep200` | `[0, 0.5, 1, 0.5, 0]` per cycle | `Nphys=40`, `Nstep=200` | timing diagnostic; not the full latest until-fracture rerun | no full stateTiming export; copied TBruns/intermediate folders are empty | no fracture by 40 physical cycles |
| `stateTiming_onepeak_untilFrac_Nphys100_Nstep100` | one peak per physical cycle | `Nphys=100`, `Nstep=100`; stopped at c85 | latest FEM-aligned PIDL setting; FEM-derived soft-history-0 mesh | yes: 48 `.npz` snapshots plus gradient balance | first detected c82, confirmed c85 |
| `stateTiming_substeps025_untilFrac_Nphys120_Nstep600` | `[0.25, 0.5, 0.75, 1.0, 0.0]` per cycle | `Nphys=120`, `Nstep=600`; stopped at idx 411 | latest FEM-aligned PIDL setting; FEM-derived soft-history-0 mesh | yes: 102 `.npz` snapshots plus gradient balance | first detected idx 408, about physical cycle 81.6; confirmed idx 411, about physical cycle 82.2 |

## Interpretation

The cleanest baseline PIDL case is `one_peak_femmesh_softHist0_N100`.

The cleanest new instrumented version of that baseline is `stateTiming_onepeak_untilFrac_Nphys100_Nstep100`: same one-peak physical-cycle idea, but with stateTiming snapshots and gradient-balance scratch saved.

The cleanest loading-step/timing test is `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`: it changes the load path resolution within each physical cycle, not the main solver family. Its fracture occurs at almost the same physical-cycle window as the one-peak case, around cycle 82.

The older `explicit_cycle_0_0p5_1_0p5_0_Nphys40_Nstep200` case is useful as an earlier timing diagnostic, but it did not run long enough to fracture and does not contain the same full stateTiming artifact set.

## Practical comparison groups

- Baseline vs instrumented baseline: compare `one_peak_femmesh_softHist0_N100` with `stateTiming_onepeak_untilFrac_Nphys100_Nstep100`.
- One-peak vs substep timing: compare `stateTiming_onepeak_untilFrac_Nphys100_Nstep100` with `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`.
- Earlier diagnostic vs latest substep: compare `explicit_cycle_0_0p5_1_0p5_0_Nphys40_Nstep200` with `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`, but note the earlier diagnostic stops at 40 physical cycles and has no fracture.
