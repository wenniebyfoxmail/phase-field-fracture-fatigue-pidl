# Current-field audit of E011 c1/c11

2026-10-20 Europe/London. Four explicitly authorized already exposed original-Q4 snapshots only: c1/c11 at s4 peak and s5 unloaded origin. This extends the prior scalar-only audit. No future snapshot/target, new holdout, model, FEM solve, autograd or training was read/executed. Only h5py and ordinary NumPy geometry/difference reductions were used.

## Source/schema binding

Read the existing owner source binding at `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/q4-material-inverse-20261020/docs/research/inverse_fem_A/source_observation_binding.json:252–489` before decoding. Also read `capture_post_commit_state.m:22–67` under `.codex/worktrees/hard5-native-mesh-pidl-20260929/tools/`: native MATLAB node_coords/u_node are N×2, d_node N×1, connectivity E×4; HDF storage reverses those axes. d_elem is the arithmetic average of its four nodal values, checked here against the saved array to <1e-14. Source timing is post-convergence/post-damage-commit/post-history-commit/post-cyclemax-update. This is original-solver provenance, not certification against the new nodal-K/fresh joint contract.

The archived producer `local_archive/experiments/S04-E011/endpoint_replay_preparation/source_minimal/Scripts/fatigue_fracture/solve_fatigue_fracture.m:183–194,236–279` confirms commit and the request28 snapshot layout. No guess of displacement blocking or history semantics was needed.

## Exact read scope and identity

| File | Bytes | Cycle/substep | load_factor | damage/history/cyclemax committed |
|---|---:|---|---:|---|
| `c0001_s004_post_commit.mat` | 29620256 | 1.0/4.0 | 0.99999900000000008 | 1/1/1 |
| `c0001_s005_post_commit.mat` | 31487788 | 1.0/5.0 | 1.1564823173178715e-16 | 1/1/1 |
| `c0011_s004_post_commit.mat` | 31833005 | 11.0/4.0 | 0.99999900000000008 | 1/1/1 |
| `c0011_s005_post_commit.mat` | 31734797 | 11.0/5.0 | 1.1564823173178715e-16 | 1/1/1 |

All files are under `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_Q4_C120/request28_post_commit`. Fields decoded: node_coords, connectivity, node_ids, element_ids, d_node, d_elem, u_node plus listed scalar identity/commit flags. Other GP/history fields were only inventoried in schema, not decoded for this follow-up.

All four have86756nodes and86408Q4 elements. Coordinates, connectivity and native IDs match exactly bit for bit. No interpolation, remapping, coordinate fitting or array reordering other than HDF transpose and explicit1-based→0-based connectivity was applied. Total polygon area=1; min/max cell area=1.51164367607955e-06/0.00187244253570366. Loaded flags equal1 do not alone imply numerical or physical qualification.

## Reduction definitions

- Primary reported relative norm is symmetric: `||b-a|| / max(||a||,||b||)`; both ordinary nodal Euclidean and geometric area-lumped versions are supplied. Area weights are cell polygon areas distributed equally to their4nodes; this is an explicit geometric lumping, not a recomputed consistent FEM mass norm.
- Threshold support uses the saved cell mean damage `d_elem>=t`, t=.3/.5/.7, and exact polygon cell areas. It reports area IoU and symmetric-difference area. These are descriptive synthetic phase-field supports, not visible crack truth, physical width or acceptance thresholds.
- Rigid-difference diagnostic fits the displacement difference to translation plus infinitesimal rotation in identical coordinates with area-lumped weights, then reports the residual. It is diagnostic only; raw results are not replaced by aligned fields. Zero-load displacement is near numerical zero, so its relative difference is not physically interpretable.

## Current field comparison

| Phase | d nodal relative L2 | d area-lumped relative L2 | max abs d difference | u nodal relative L2 | u area-lumped relative L2 |
|---|---:|---:|---:|---:|---:|
| s4 | 0.127417417 | 0.129702174 | 0.941239133 | 0.0272632093 | 0.0142536768 |
| s5 | 0.127417242 | 0.129702015 | 0.941239133 | 0.0500597436 | 0.0219451762 |

| Phase | Cell mean d threshold | Support areas c1 / c11 | Area IoU | Symmetric-difference / union |
|---|---:|---|---:|---:|
| s4 | 0.3 | 0.0106320823 / 0.0109003824 | 0.975386177 | 0.0246138228 |
| s4 | 0.5 | 0.00716770108 / 0.00737270777 | 0.97219384 | 0.0278061603 |
| s4 | 0.7 | 0.00477147651 / 0.00494549667 | 0.964812398 | 0.0351876019 |
| s5 | 0.3 | 0.0106320823 / 0.0109003824 | 0.975386177 | 0.0246138228 |
| s5 | 0.5 | 0.00716770108 / 0.00737270777 | 0.97219384 | 0.0278061603 |
| s5 | 0.7 | 0.00477147651 / 0.00494549667 | 0.964812398 | 0.0351876019 |

Peak u difference: fitted translation=[-3.4742172582233796e-05, -8.925621875899168e-07], infinitesimal rotation=4.7543465e-06; after that fit99.95%of the weighted difference norm remains. Residual / field norm=0.0142465473. Thus coordinate/ID mismatch is excluded, and the field difference is not explained purely by rigid translation/rotation.

Within-cycle d peak→unloaded max differences: c1=0.00097508947, c11=0.000124130628. Unloaded max |u| is c1=1.38777878e-17, c11=2.22569183e-17; do not use their relative u norm as a meaningful mechanical mismatch.

## Interpretation

This pair is a scalar-summary candidate, not an established equal-current-state pair. The full current damage/support and peak-displacement differences below expose the residual confound. Whether they are small enough for a particular observation system requires an externally motivated observation operator/noise scale; this audit sets no equivalence or acceptance gate. Equal future prescribed loading and different accumulated history do not isolate history causally when current geometry/response also differs. A future paired-history experiment must match the declared observable representation within justified resolution, include current state and known exposure/cycle in the baseline, and then test future outcomes. This audit computes no future outcome and provides no teacher qualification.

## Machine-readable exact reductions

```json
{
  "scope": "current four snapshots only; no future targets/no solve/no teacher acceptance audit",
  "mesh": {
    "nodes": 86756,
    "elements": 86408,
    "coordinates_connectivity_ids_exactly_equal": true,
    "total_polygon_area": 1.0,
    "element_area_min": 1.5116436760795454e-06,
    "element_area_max": 0.001872442535703657
  },
  "files": [
    {
      "path": "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_Q4_C120/request28_post_commit/c0001_s004_post_commit.mat",
      "bytes": 29620256,
      "cycle": 1.0,
      "substep": 4.0,
      "load_factor": 0.9999990000000001,
      "damage_committed": 1,
      "history_committed": 1,
      "cyclemax_updated": 1,
      "num_gauss_points": 4.0
    },
    {
      "path": "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_Q4_C120/request28_post_commit/c0001_s005_post_commit.mat",
      "bytes": 31487788,
      "cycle": 1.0,
      "substep": 5.0,
      "load_factor": 1.1564823173178715e-16,
      "damage_committed": 1,
      "history_committed": 1,
      "cyclemax_updated": 1,
      "num_gauss_points": 4.0
    },
    {
      "path": "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_Q4_C120/request28_post_commit/c0011_s004_post_commit.mat",
      "bytes": 31833005,
      "cycle": 11.0,
      "substep": 4.0,
      "load_factor": 0.9999990000000001,
      "damage_committed": 1,
      "history_committed": 1,
      "cyclemax_updated": 1,
      "num_gauss_points": 4.0
    },
    {
      "path": "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_Q4_C120/request28_post_commit/c0011_s005_post_commit.mat",
      "bytes": 31734797,
      "cycle": 11.0,
      "substep": 5.0,
      "load_factor": 1.1564823173178715e-16,
      "damage_committed": 1,
      "history_committed": 1,
      "cyclemax_updated": 1,
      "num_gauss_points": 4.0
    }
  ],
  "phases": {
    "4": {
      "d_nodal": {
        "relative_l2_symmetric": 0.12741741666278036,
        "absolute_l2": 4.788177496175366,
        "max_abs": 0.9412391332759801,
        "rms": 0.016256254177566817,
        "l2_a": 37.03750630103289,
        "l2_b": 37.57867347795657
      },
      "d_area_lumped": {
        "relative_l2_symmetric": 0.12970217441599619,
        "absolute_l2": 0.009645457370922327,
        "max_abs": 0.9412391332759801,
        "rms": 0.016256254177566817,
        "l2_a": 0.07326398315824426,
        "l2_b": 0.0743661963598719
      },
      "d_bounds": [
        0.0,
        1.0,
        0.0,
        1.0
      ],
      "u_nodal": {
        "relative_l2_symmetric": 0.027263209343662654,
        "absolute_l2": 0.40702958188481875,
        "max_abs": 0.08137771527039428,
        "rms": 0.0009771499540249403,
        "l2_a": 14.904690302778235,
        "l2_b": 14.929628304359294
      },
      "u_area_lumped": {
        "relative_l2_symmetric": 0.014253676834909098,
        "absolute_l2": 0.0011006526368418884,
        "max_abs": 0.08137771527039428,
        "rms": 0.0009771499540249403,
        "l2_a": 0.07694687066892926,
        "l2_b": 0.07721885725276496
      },
      "rigid_difference_fit": {
        "translation": [
          -3.4742172582233796e-05,
          -8.925621875899168e-07
        ],
        "infinitesimal_rotation": 4.754346498433699e-06,
        "remaining_fraction_of_diff_norm": 0.9994998135695166,
        "remaining_relative_to_field": 0.014246547339171781
      },
      "support": [
        {
          "threshold": 0.3,
          "a_elements": 2705,
          "b_elements": 2772,
          "a_area": 0.010632082306422298,
          "b_area": 0.010900382387355393,
          "area_iou": 0.9753861771634428,
          "symmetric_difference_area": 0.0002683000809330943,
          "symmetric_difference_over_domain": 0.0002683000809330943,
          "symmetric_difference_over_union": 0.02461382283655722
        },
        {
          "threshold": 0.5,
          "a_elements": 1828,
          "b_elements": 1879,
          "a_area": 0.007167701078982484,
          "b_area": 0.007372707772891211,
          "area_iou": 0.9721938397365323,
          "symmetric_difference_area": 0.00020500669390872712,
          "symmetric_difference_over_domain": 0.00020500669390872712,
          "symmetric_difference_over_union": 0.02780616026346771
        },
        {
          "threshold": 0.7,
          "a_elements": 1219,
          "b_elements": 1262,
          "a_area": 0.004771476505324877,
          "b_area": 0.004945496673260564,
          "area_iou": 0.9648123981405985,
          "symmetric_difference_area": 0.0001740201679356876,
          "symmetric_difference_over_domain": 0.0001740201679356876,
          "symmetric_difference_over_union": 0.03518760185940155
        }
      ]
    },
    "5": {
      "d_nodal": {
        "relative_l2_symmetric": 0.1274172419482893,
        "absolute_l2": 4.788185055396451,
        "max_abs": 0.9412391332759801,
        "rms": 0.0162562798417406,
        "l2_a": 37.03773561441647,
        "l2_b": 37.5787843323408
      },
      "d_area_lumped": {
        "relative_l2_symmetric": 0.12970201507588827,
        "absolute_l2": 0.009645472623251673,
        "max_abs": 0.9412391332759801,
        "rms": 0.0162562798417406,
        "l2_a": 0.07326441569167817,
        "l2_b": 0.07436640531458308
      },
      "d_bounds": [
        0.0,
        1.0,
        0.0,
        1.0
      ],
      "u_nodal": {
        "relative_l2_symmetric": 0.05005974357173785,
        "absolute_l2": 7.97008121119789e-17,
        "max_abs": 1.6478852176119602e-17,
        "rms": 1.9133657197674878e-19,
        "l2_a": 1.587602977430177e-15,
        "l2_b": 1.5921138708544137e-15
      },
      "u_area_lumped": {
        "relative_l2_symmetric": 0.0219451762278333,
        "absolute_l2": 1.8574446368694589e-19,
        "max_abs": 1.6478852176119602e-17,
        "rms": 1.9133657197674878e-19,
        "l2_a": 8.434425037799739e-18,
        "l2_b": 8.464022423814679e-18
      },
      "rigid_difference_fit": {
        "translation": [
          -9.516247599370579e-21,
          -1.4491276541131525e-21
        ],
        "infinitesimal_rotation": -7.597470145078424e-21,
        "remaining_fraction_of_diff_norm": 0.9985165500252482,
        "remaining_relative_to_field": 0.021912621656712195
      },
      "support": [
        {
          "threshold": 0.3,
          "a_elements": 2705,
          "b_elements": 2772,
          "a_area": 0.010632082306422298,
          "b_area": 0.010900382387355393,
          "area_iou": 0.9753861771634428,
          "symmetric_difference_area": 0.0002683000809330943,
          "symmetric_difference_over_domain": 0.0002683000809330943,
          "symmetric_difference_over_union": 0.02461382283655722
        },
        {
          "threshold": 0.5,
          "a_elements": 1828,
          "b_elements": 1879,
          "a_area": 0.007167701078982484,
          "b_area": 0.007372707772891211,
          "area_iou": 0.9721938397365323,
          "symmetric_difference_area": 0.00020500669390872712,
          "symmetric_difference_over_domain": 0.00020500669390872712,
          "symmetric_difference_over_union": 0.02780616026346771
        },
        {
          "threshold": 0.7,
          "a_elements": 1219,
          "b_elements": 1262,
          "a_area": 0.004771476505324877,
          "b_area": 0.004945496673260564,
          "area_iou": 0.9648123981405985,
          "symmetric_difference_area": 0.0001740201679356876,
          "symmetric_difference_over_domain": 0.0001740201679356876,
          "symmetric_difference_over_union": 0.03518760185940155
        }
      ]
    }
  },
  "within_cycle_peak_to_unload": {
    "1": {
      "d_maxabs": 0.0009750894703197677,
      "u_unloaded_maxabs": 1.3877787807814457e-17
    },
    "11": {
      "d_maxabs": 0.0001241306275232794,
      "u_unloaded_maxabs": 2.2256918309012015e-17
    }
  }
}
```
