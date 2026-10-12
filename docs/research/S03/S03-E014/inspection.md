# First-triplet exploratory inspection — 2026-10-12

**Correction after primary-source inspection:** connection records use zero-based
indices, so0 is valid and maps to facet ID1. The historical raw-index counts
below must NOT be used to remove node0 or qualify a mesh. See
[`operator_development.md`](operator_development.md) for the corrected finite-
support/area checks and the exact published CrackPy source.

Status: direct read-only data inspection, NOT independently reviewed structural
admission, a producer Run, FEM qualification or inversion result. No optimizer,
FEM solve, training or held-out response scoring occurred. Numeric observations
below came from bounded selected-member Python/NumPy reads, not the newly added
inspector runner. Its synthetic tests do not retroactively qualify these facts.

Data source: locked ZIP in E014 `experiment.md`, not the extracted directory or
the `.partial-preverified` file. Six selected members only: nodemaps and
connections for stages7/8/9. Nodemaps each ~9.61MB, connections each4,818,938
bytes. Actual fields, not official advertised counts, control the findings.

Interpreter: `/Users/wenxiaofang/miniconda3/bin/python3`, Python3.12.2,
NumPy2.2.6. A first bare `python3` attempt failed importing NumPy before data
access; the explicit project interpreter succeeded. No environment changed.

## Decision-facing structural table

| Item | Stage7: fit low | Stage8: fit intermediate | Stage9: held response |
|---|---:|---:|---:|
| Cycles |126873.5|126873.5|126873.5|
| Force, recorded load-cell value |4499.348163604736|9750.223159790039|15003.487586975098|
| Reference stage |1|1|1|
| Node rows / unique IDs |41603 / 41603|41603 / 41603|41603 / 41603|
| Finite xyz rows |40069|39962|39975|
| Nonfinite xyz rows |1534|1641|1628|
| Finite displacement rows |40069|39962|not converted/scored|
| Connection rows |78998|78998|78998|
| All-minus-one padding rows |722|944|881|
| Rows referencing node0 |2|2|2|
| Positive, distinct-node triangles |78274|78052|78115|
| Triangles on finite coordinate support |77398|77184|77271|

All connection Types are3; out-of-node-set IDs are -1 and0. The displayed
finite-support subsets have no duplicate canonical triangles, but area,
orientation, crack crossing and physical boundary have NOT been qualified.
Do not discard records silently or assume padding is a physical element.

ID order is identical. Coordinate differences on jointly finite ID support:

| Comparison | Joint finite nodes | max abs x / y / z difference, mm |
|---|---:|---|
|7 vs8|39891|3.4e-9 / 6.0e-9 / 1.8e-8|
|7 vs9|39886|3.2e-9 / 4.4e-9 / 2.61e-8|

Fit-only common support has39,891 nodes. Three-load coordinate intersection
has39,775; 116 nodes in fit support lack finite stage9 coordinates. The latter
is a coverage diagnostic, not an authorized target-informed fit mask.
These tiny serialized-coordinate differences support a common reference-ID
representation for this triplet; they are not independent registration-error
or metrological-accuracy measurements.

Stage7 finite view extent: x[-72.5371225565,73.6012253464],
y[-98.3003104187,92.7132416825], z[-0.6104045966,0.5640157161] mm.
The view is not the verified160mm-wide complete specimen boundary/grip domain.
Stage7 and8 finite xyz masks match their respective finite u/v/w masks exactly.
No stage9 displacement/strain values were converted, examined as fields or
scored. Full selected bytes were nevertheless read/decompressed to inspect
structure/coordinates: do not claim totally unopened target files.

## Units, reference and boundary meanings

- Actual column header: `x_undef,y_undef,z_undef,u,v,w [mm]`; `epsx,epsy,epseqv
  [%]`; `epsxy [1]`. Do not treat all strain channels as percentages or assert
  an engineering-vs-tensor shear convention without export documentation.
  In-plane displacements, not derived strain/stress, are the first target.
- All three reference headers identify stage1, name `Stufe 1`, date
  `29.10.2021 14:22`. No global reference-stage1 nodemap exists in this ZIP.
  The archived release describes a global unloaded reference; the missing
  reference load itself is not observed locally.
- Per-stage rigid-motion compensation values are supplied and differ.
  Translation-y values:0.043011381,0.089178231,0.136711090 mm. Alignment
  deviation:0.014178824,0.025502587,0.037443411. These are not automatically
  calibrated independent noise estimates. Do not apply the transform twice.
- Released dictionary defines `displacement` as cylinder position, NOT grip
  opening or DIC ROI Dirichlet boundary displacement. `force` is load-cell
  force, NOT a known nodal traction distribution on the view perimeter.
- The release describes MT160, W160mm,t2mm, AA2024-T3,L-T and a uniaxial
 4.5--15kN cycle. Actual specimen/grip geometry, boundary correspondence,
  exported compensation operation and training-only crack/patch topology are
  not yet qualified. Do not fill those gaps with assumed global BC.

Primary publication consulted through agent-reach/Jina Reader:
https://www.nature.com/articles/s41598-024-63915-x . It describes nodemaps as
surface displacement/strain results and connection files as DIC evaluation
topology. Its fracture analysis uses a constitutive assumption; displacement
data do not themselves provide stresses. The paper is contextual evidence,
not a replacement for actual archived reference/BC qualification.

## Concrete repair and next handoff

Useful component: same-cycle fields, physical coordinate units, common node
identity and nearly identical finite reference coordinates are present. The
observation-to-mechanics route is not rejected by the sentinel/NaN discovery.

Binding bottleneck: construction of a mechanically interpretable observation
operator and training-only patch/BC, not more neural-network capacity. Use a
fit-only closed local patch to avoid invented grip BC; preserve missingness and
explicitly inspect crack jumps rather than labeling invalid nodes as cracks.
Verify gauge/compensation, then freeze basis/mesh assets, perform q sensitivity,
and independently review before any solve. A normalized displacement-driven
patch can test spatial degradation, but cannot identify uniform E, Gc or fatigue
history. E014 protocol makes this reduced scope explicit.

Added reproducible structural inspector: `scripts/aa2024_triplet_structure.py`;
synthetic test file: `tests/test_aa2024_triplet_structure.py`. Six new cases pass;
combined pytest regression against E011/E012 yields62 passed in0.96s using the
explicit interpreter above. `git diff --check` passes. These are software checks,
not real-data/FEM/physical validation. It is not yet Code Ready and has NOT been
run against the real archive. Eventual inspection command:

```sh
/Users/wenxiaofang/miniconda3/bin/python3 scripts/aa2024_triplet_structure.py /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/aa2024_dic_zenodo_11945905_20261008/raw/multiscale_digital_image_correlation.zip
```

A numerical outcome figure is inapplicable at this stage: there is no mechanics
candidate or scored prediction. The two structural tables are the compact C1
decision visualization; future method validation needs actual field/error plots.
