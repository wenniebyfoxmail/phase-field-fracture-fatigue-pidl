# LTPP main-grid geometry tooling MVP — revised preregistration, 2026-08-10

## Status and immutable boundary

`TOOLING_ONLY_EXPLORATORY_MVP__PENDING_EXTERNAL_REVIEW`

This is a new development-only image-geometry diagnostic. It does not replace or reopen the completed v1 spatial-registration audit, whose result remains `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`. It cannot create v2 controls, crop a scientific image, estimate a transform, compute registration residuals, disclose final controls, run the v2 one-shot gate, or authorize a 2-D crack model.

The only permitted output after approval is an all-candidate geometry report and a single purple outer-frame candidate or `NO_CANDIDATE` for each already-seen development page.

## Mechanism question

Can a fail-closed, no-OCR extraction of a complete `11 × 6` printed ruled lattice identify a plausible main road-grid frame while rejecting page summaries and isolated rectangles by geometry alone?

## Frozen input and prohibited information

- Input for the later real-data run: each official, white-composited source `<date>/segment_0_50_white.png` from the frozen LTPP source archive; no crop, deskew, perspective correction, scaling, or cross-date information is permitted.
- Permitted: source-pixel intensity and geometry of visible printed horizontal/vertical strokes.
- Prohibited: cracks, crack labels, WIM/repair/distress boxes, handwritten or printed text content, OCR, page/table semantics, manual corners, previous purple/orange/green overlays, and any date-specific fallback.
- All eight dates are development-only. They are not independent validation and cannot furnish v2 final controls.

## Frozen geometry implementation

### Dependency receipt

- `img2table==2.0.0`, macOS arm64 wheel SHA-256: `d1fa566deda469e88363bbcee5bdc5c81b7414691bd803d72170a0fe53f85848`.
- Frozen upstream source file: `img2table/tables/bordered/lines.py`, SHA-256 `6e191089435a4032909d5ad4f2ab84c867afd23a5b5cbfcd9979d9ed7e4237c4`.
- `opencv-contrib-python-headless==4.13.0.92` (reported `cv2.__version__ == 4.13.0`; `ximgproc` available). The final package receipt must record the actual wheel hashes and `pip freeze`.
- Exact entrypoint: `img2table.tables.bordered.lines.identify_straight_lines(thresh, min_line_length, char_length, vertical)`.

The public `Image.extract_tables` / `TableExtractor.extract_tables` API is explicitly **not** called. Therefore its OCR argument, `detect_rotation`, `borderless_tables`, implicit-row and implicit-column options are `NOT_CALLED`, not silently defaulted. The chosen function has no OCR input or text output, and no borderless or implicit-line branch.

### Fixed pre-processing and line calls

For every image, read BGR pixels with `cv2.imread(..., cv2.IMREAD_COLOR)`, convert once using `cv2.COLOR_BGR2GRAY`, and create `thresh` with:

```python
cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV, 51, 9,
)
```

Call the frozen entrypoint twice, once with `vertical=True` and once with `vertical=False`, with `char_length=11` and `min_line_length=max(64, round(0.08 * min(gray.shape)))`. No line is added, repaired, extrapolated, inferred, or supplied manually.

## Candidate definition, eligibility, and ranking

Detected horizontal and vertical separators intersect only when both finite detected line segments cover the crossing within a fixed `3` source-pixel tolerance. The bipartite separator-intersection graph is split into connected components. A candidate is the *whole component*: the implementation must never select a subset of a denser component to obtain a preferred count.

For a component, `Nv` and `Nh` are its counts of detected vertical and horizontal separators; `I` is its number of actual graph intersections. Let `gx` and `gy` be the strictly positive sorted coordinate gaps between adjacent vertical and horizontal separator centres respectively. Let `r=(max_x-min_x)/(max_y-min_y)` and `r0=15.24/5.00=3.048`.

A candidate is eligible if and only if every condition holds:

1. `Nv == 11`, `Nh == 6`, and `I == 66`.
2. Every separator covers at least `0.96` of the candidate span in its own direction, measured from its detected endpoints; this includes all four outer separators.
3. `max(abs(gx / median(gx) - 1)) <= 0.20` and `max(abs(gy / median(gy) - 1)) <= 0.20`.
4. `2.4384 <= r <= 3.6576` (the physical target ratio ±20%).
5. All comparisons use source-pixel values; `r` and `abs(log(r/r0))` are quantised by `round(value * 1_000_000)` before ranking.

The eligible candidates are ranked lexicographically by:

```text
(-I, -(Nv + Nh), -area_px, round(abs(log(r/r0)) * 1_000_000))
```

where `area_px=(max_x-min_x)*(max_y-min_y)` is an integer source-pixel product. If there are no eligible candidates, or two or more candidates share the entire ranking tuple, output `NO_CANDIDATE__FAIL_CLOSED`. Otherwise the selected four corners are the mechanically defined intersections of its extreme detected separators. No subsequent adjustment is permitted.

This rule rejects a dense side summary because its entire component has the wrong separator counts and/or ratio; it rejects disconnected disease/WIM/repair rectangles because they do not form the required complete 66-intersection lattice. It does **not** claim that a deliberately road-like non-damage-independent drawing could be distinguished without semantic information; that limitation is explicit.

## Synthetic suite frozen before real data

The suite creates only artificial black-on-white ruled drawings. Its expected decisions are frozen before any real source page is passed to the code:

| Fixture | Required outcome |
|---|---|
| canonical `11×6` lattice | one candidate selected |
| translated and isotropically resized canonical lattice | one candidate selected |
| canonical road lattice plus a larger wrong-ratio summary table | road candidate selected |
| canonical road lattice plus a denser summary table | road candidate selected |
| isolated / disconnected repair-like rectangles | `NO_CANDIDATE__FAIL_CLOSED` |
| any one outer separator interrupted beyond coverage criterion | `NO_CANDIDATE__FAIL_CLOSED` |
| broken internal separator | `NO_CANDIDATE__FAIL_CLOSED` |
| page frame or nested double border only | `NO_CANDIDATE__FAIL_CLOSED` |
| two spatially separate equal canonical lattices | `NO_CANDIDATE__FAIL_CLOSED` |
| lattice with wrong outer ratio | `NO_CANDIDATE__FAIL_CLOSED` |
| no ruled grid | `NO_CANDIDATE__FAIL_CLOSED` |

The synthetic suite must also assert that no OCR module, public table-extraction API, borderless-table path, crop, deskew, transform, crack mask, or manual-coordinate input is invoked.

## One-shot real-data rule and stopping condition

Only after external approval of this exact revision and a passing synthetic suite may one deterministic real-data execution process all eight development images once. No threshold, version, candidate rule, page, metric, or output definition may then change. A missing candidate is a reported failure, not an invitation to rerun with a different parameter.

The real-data package must contain source/code/dependency SHA-256 receipts, candidate metrics, full-resolution purple overlays, contact sheet, `decision.md`, and `manifest.sha256`. Its only possible status is `EXPLORATORY_MAIN_GRID_TOOLING_MVP__NOT_QUALIFIED`.

## PIDL Experiment Gate

- Mechanism question: whether a strict complete-lattice geometry detector can expose a plausible main-grid candidate without semantic damage information.
- Claim changed if success: the deterministic image-geometry recipe is feasible on the seen development pages only.
- Claim changed if failure: this exact no-OCR complete-lattice recipe is quarantined; v1/v2 gate status is unchanged.
- Cheaper diagnostic first: isolated dependency compatibility probe and the frozen synthetic adversarial suite.
- Minimal output asset: full-resolution purple candidate/`NO_CANDIDATE` panels and a structural-metrics table.
- Code/producer alignment: deterministic local image diagnostic; no training and no registration transform.
- Success criteria: synthetic suite passes; real pages are reported once with no unplanned fallback.
- Failure criteria: any synthetic contract failure, missing candidate, or protocol deviation.
- Registry destination: spatial-registration track after the one permitted real-data run.
- Decision: await re-review; do not run real data.
