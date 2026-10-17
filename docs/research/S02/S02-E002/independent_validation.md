---
experiment_id: S02-E002
run_id: S02-E002-R001
protocol_revision: v0.2
reviewed_at: 2026-10-01T00:53:25+01:00
reviewer: independent_validator
verdict: FAIL
scope: WP2_G1_analytic_construction_only
---

# Independent verification of S02-E002 G1

G1 fails independent review. The nine supplied tests pass, the stored manifest
passes its validator, and the frozen analytic calculations are reproducible.
However, the images contain an unintended border cue that reveals the slit
endpoints, and the manifest validator accepts missing fixture cases and an
incorrect promotion of ambiguous targets to resolved. These are blocking
construction and state-semantics defects, not evidence against the broader
research idea.

## Bound scope and evidence

The reviewer did not implement WP2 and did not change its code or stored run.
This review read the full v0.2 `experiment.md`, `S02-E002-R001.md`, all four
files in `scripts/synthetic_fracture_cv/`, both files in
`tests/synthetic_fracture_cv/`, the generated manifest and renderer config, all
mechanics and geometry JSON files, and the figure-set `README_analysis.md`.

Repository root:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code`.

The observed base HEAD was
`ca8b9a24ebf4f405c096ceb6e07a871e70d7a561`. The reviewed implementation and
experiment files were new, untracked files; HEAD alone does not identify their
contents. This verdict applies to the source observed on 1 October 2026 before
any repair, including the line references below. A changed implementation
requires a new review and a fresh run receipt.

Run root:
`local_archive/experiments/S02-E002/runs/S02-E002-R001/`.

Visually inspected image:
`local_archive/experiments/S02-E002/analysis/figures/g1_analytic_verification.png`.

Interpreter: `/Users/wenxiaofang/miniconda3/bin/python3`.

## Reproduction and checks that passed

The exact documented commands were rerun from the repository root:

```sh
/Users/wenxiaofang/miniconda3/bin/python3 -m pytest -q tests/synthetic_fracture_cv
/Users/wenxiaofang/miniconda3/bin/python3 scripts/synthetic_fracture_cv/validate_manifest.py local_archive/experiments/S02-E002/runs/S02-E002-R001/manifest.json
```

Observed output: `9 passed in 0.19s`; manifest `PASS` with no errors.

| Check | Independent observation | Local outcome |
|---|---|---|
| Frozen fixture | 128 x 128; seeds 1701 and 1702; all seven prescribed cases; 14 images, below the 96-frame limit | Pass |
| Replicate identity | One analytic lineage; all 14 records have `verification_only`; the case index is not physical time | Pass for G1 only |
| Zero displacement | Exact equality in the declared valid interior; no optical support | Pass for the stated interior tolerance |
| Integer translation | Exact copied pixels for offset (+3,-2) in the tested valid interior; no optical support | Pass |
| Affine coordinates | Independent triangular-matrix calculation gives a maximum error of `1.4210854715202004e-14` pixels | Pass against `1e-9` |
| Resolved geometry | Independent rectangle/pixel intersection reference matches support exactly; tip, length and resolved width meet the <=1 pixel test | Pass |
| Reference independence | The test reference uses a separate overlap calculation and does not call the renderer's rasteriser | Pass for construction; not image estimation |
| Byte determinism | Two fresh temporary generations have identical bytes for all 46 files; all 46 files also match the stored run | Pass |
| Pre-render metadata independence | Changing `case`, `status`, `event_first_detect` and `provenance` in each input case leaves pixels and support identical for all 14 seed/case combinations | Pass in this independent check |
| Stored target statuses | Four resolved, two ambiguous and eight closed records; 0.25-pixel cases have fractional support and remain ambiguous | Correct as generated; validator does not protect this |
| Direct annotations in image input | No timestamp, mesh, colour bar or written event label is drawn in the source image files | Pass for these cue types |
| Border cue | Slit endpoints can be read exactly from the far bottom image border in all six nonzero-opening images | **Fail** |
| Manifest negative controls | Missing fixture cases, ambiguous-to-resolved relabelling and all-record split changes are accepted | **Fail** |

The stored geometry tip/length values for ambiguous and closed cases are
geometry truth, not valid ordinary image accuracy labels. No image estimator
exists in G1. The manifest's status must therefore remain a strict downstream
exclusion rule.

## Blocking finding B1: the far border reveals slit geometry

`render_analytic_sequence.py:77` requires the next interpolation neighbour to
exist even when its interpolation weight is zero. As a result, an identity
warp sets the last row and column to black. The closed-slit branch at
lines 108-109 instead returns the untouched texture. The nonzero-opening
branch at lines 112-118 moves source coordinates over the full-height interval
from x=32 to x=96. On the bottom row, that interval becomes valid while the
rest remains black.

For both texture seeds and all three nonzero openings, the nonzero bottom-row
pixels begin at column 32 and end at column 95. Thus the far border alone gives
tip x=96 and length=64, although the intended slit is near y=64 and has no
optical support at y=127. This includes the 0.25-pixel case marked ambiguous.
It is an interpolation/domain cue, not an observed slit boundary.

The verification figure visibly shows the inconsistent black border between
the zero and closed-slit panels. Numerical inspection identifies the exact
geometry cue. This violates the v0.2 requirement to remove border shortcuts
and the G1 condition that visual inspection find no label-coded cue.

Required repair: use one explicit, consistent image-domain/validity policy
across all branches; remove the artificial dependence of the far border on
slit endpoints; add a regression check that would fail on this observed cue.
Preserve the frozen numerical tolerances. Do not simply delete the ambiguous
case or relabel this output as a recoverability result.

## Blocking finding B2: the manifest gate accepts invalid fixture semantics

`validate_manifest.py:21-25` checks only an upper frame limit and the presence
of the two seed IDs. Lines 38-39 accept any of the three status strings, without
checking the prescribed case or referenced geometry/support. Lines 49-51 only
check that each lineage occurs in one split.

Three read-only mutations were passed to `validate_records` in memory:

1. Keep only the two zero-displacement records: result `[]` (accepted), despite
   removing every mandatory nonzero test case.
2. Change both `opening_0p25px` records from `ambiguous` to `resolved`: result
   `[]` (accepted), despite violating the frozen status rule and disagreeing
   with the referenced geometry.
3. Change every split from `verification_only` to `train`: result `[]`
   (accepted), despite this being a G1-only verification fixture.

The original generated package has the intended contents. The defect is that
the proposed release validator cannot enforce the frozen fixture or prevent
invalid target promotion. Required repair: check the expected seed/case set,
G1 split restriction, state/status agreement and the referenced label
semantics; add negative controls that reject these mutations.

## Reproduce the blocking findings without changing the run

```sh
/Users/wenxiaofang/miniconda3/bin/python3 - <<'PY'
from pathlib import Path
import copy, json
import numpy as np
from PIL import Image
from scripts.synthetic_fracture_cv.validate_manifest import validate_records

root = Path('local_archive/experiments/S02-E002/runs/S02-E002-R001')
records = json.loads((root / 'manifest.json').read_text())
for row in records:
    if row['target_status'] in {'resolved', 'ambiguous'}:
        pixels = np.asarray(Image.open(root / row['image_path']))
        columns = np.flatnonzero(pixels[-1] > 0)
        print(row['render_id'], int(columns.min()),
              int(columns.max() + 1),
              int(columns.max() + 1 - columns.min()))
# All six lines return: start=32, tip=96, span=64.
print('incomplete', validate_records(
    [row for row in records if row['state_id'] == 'zero'], root))
changed = copy.deepcopy(records)
for row in changed:
    if row['state_id'] == 'opening_0p25px':
        row['target_status'] = 'resolved'
print('wrong_status', validate_records(changed, root))
changed = copy.deepcopy(records)
for row in changed:
    row['split'] = 'train'
print('wrong_split', validate_records(changed, root))
# All three validator results are [].
PY
```

## Test weakness C1: the supplied metadata check is vacuous

`test_renderer_invariants.py:109-117` edits the manifest after image generation
and then checks that the untouched image files remain unchanged. This would
pass even for a renderer that had used metadata during generation.

The independent review instead altered audit/status fields before calling
`render_case` and compared both image and support arrays. All 14 combinations
were invariant, consistent with the inspected pixel-generation code. This
closes the current observation but does not repair the regression test. Replace
the supplied check with a pre-render intervention before re-review.

## Scope of the verdict and next action

Execution is reproducible. G1 is **FAIL** pending correction and a fresh,
independently reviewed analytic run. Preserve R001 and this failed verdict.
Neither passing the nine tests nor this review authorizes FEM integration,
G2, model fitting, training, physical validation, real-image transfer or
forecasting. The next permitted action is a bounded repair of these G1
construction and validation defects, followed by independent re-verification.

## Re-review A1 — 1 October 2026, 00:59 BST

**Final current verdict: PASS for the repaired G1 analytic construction
fixture only.** B1, B2 and C1 above are closed for the implementation and
regenerated files described in Amendment A1 of `S02-E002-R001.md`. The original
FAIL and its observations remain part of this record.

The reviewer independently read Amendment A1 and the repaired renderer,
validator and tests. The implementation files remain untracked, so ordinary
`git diff` is empty for them; this re-review compared their full current text
with the source previously read. The repair changes interpolation to one
edge-replication policy, confines the prescribed face displacement to a local
slit neighbourhood, checks the complete fixture and target semantics, and
intervenes on metadata before rendering. It does not change the prescribed
seven cases, two seeds, 128 x 128 image size, or frozen numeric tolerances.

These exact commands were rerun from the same repository root and interpreter:

```sh
/Users/wenxiaofang/miniconda3/bin/python3 -m pytest -q tests/synthetic_fracture_cv
/Users/wenxiaofang/miniconda3/bin/python3 scripts/synthetic_fracture_cv/validate_manifest.py local_archive/experiments/S02-E002/runs/S02-E002-R001/manifest.json
```

Observed output: `13 passed in 0.28s`; manifest `PASS` with no errors. The
retained tests still check the independent affine/reference calculations,
geometry tolerances, exact registration and byte determinism. The zero case
now equals the reference over the entire image, including the edges.

The unchanged read-only reproducer under “Reproduce the blocking findings”
was rerun against A1. Its results are now:

| Prior reproducer | Result on A1 | Finding status |
|---|---|---|
| Bottom-row nonzero extent, all six opening images | start=0, tip=128, span=128; it no longer gives the slit endpoints | B1 closed |
| Keep only two zero records | Two errors: wrong record count and missing frozen case/seed pairs | B2 closed |
| Relabel both ambiguous records as resolved | Two errors, one for each status mismatch | B2 closed |
| Change all splits to train | Fourteen `G1 split must be 'verification_only'` errors | B2 closed |
| Change case/status/event/provenance before rendering | The new supplied test compares pixels and support before/after intervention for both seeds and all cases | C1 closed |

An additional read-only check compared all four edges of each stored
nonzero-opening image with its stored reference texture. All six images were
exactly equal on all edges. The following command also confirms whole-package
byte determinism and the identity of the stored amended package:

```sh
/Users/wenxiaofang/miniconda3/bin/python3 - <<'PY'
from pathlib import Path
import json, tempfile
import numpy as np
from PIL import Image
from scripts.synthetic_fracture_cv.render_analytic_sequence import generate_fixture

root = Path('local_archive/experiments/S02-E002/runs/S02-E002-R001')
for row in json.loads((root / 'manifest.json').read_text()):
    if row['target_status'] not in {'resolved', 'ambiguous'}:
        continue
    image = np.asarray(Image.open(root / row['image_path']))
    texture = np.asarray(Image.open(
        root / 'textures' / (row['reference_texture_id'] + '.png')))
    edges = ((image[0], texture[0]), (image[-1], texture[-1]),
             (image[:, 0], texture[:, 0]), (image[:, -1], texture[:, -1]))
    print(row['render_id'], all(np.array_equal(a, b) for a, b in edges))
with tempfile.TemporaryDirectory(prefix='s02e002-a1-review-') as temp:
    first, second = Path(temp) / 'first', Path(temp) / 'second'
    generate_fixture(first)
    generate_fixture(second)
    one = {p.relative_to(first).as_posix(): p.read_bytes()
           for p in first.rglob('*') if p.is_file()}
    two = {p.relative_to(second).as_posix(): p.read_bytes()
           for p in second.rglob('*') if p.is_file()}
    print('full_package_deterministic', one == two, 'files', len(one))
    print('stored_matches_current_rerender',
          all((root / name).read_bytes() == data for name, data in one.items()))
PY
```

Observed output: all six edge comparisons `True`;
`full_package_deterministic True files 46`;
`stored_matches_current_rerender True`.

The regenerated
`local_archive/experiments/S02-E002/analysis/figures/g1_analytic_verification.png`
was inspected visually. The inconsistent black border is absent. The
prescribed resolved slits, no-opening case and fractional ambiguous case are
visible as expected; annotations remain outside the source image files.
Edge replication in the translation panel is a declared sampling convention.

This is an analytic construction fixture with prescribed local displacement;
its abrupt local displacement support is not a qualified fracture mechanics
field. No image-only estimator, realistic image visibility result, or causal
prediction was evaluated. A1 regenerated the shared R001 output path, so that
path now contains the repaired package; the prior FAIL remains documented here
but the old raw pixels are not retained at that same path.

This bounded PASS closes WP3 for A1. It does **not** authorize FEM integration,
G2, model fitting or training, and does not establish physical realism,
image recoverability, sim-to-real transfer or forecast skill. No implementation
or run data was changed by the independent reviewer.
