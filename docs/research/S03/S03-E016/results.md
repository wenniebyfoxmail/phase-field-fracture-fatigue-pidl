# E016 — completed conditional high-load comparison, 2026-10-15

## Decision and claim boundary

Protocol v2 primary descriptive contrast is positive: the frozen
training-opening-defined prior procedure reduces stage15 response error versus
the old transferred prior by1.3042%. It remains9.6783% worse than direct secant.
Independent read-only Codex acceptance: PASS_EVIDENCE, see evidence_review.md.

Experiment verdict: supports the bounded descriptive procedure improvement.
Research disposition: repair model/observation adequacy in a separately reviewed
diagnostic; no further execution authorized here. This is not current physical
phase-field/tip/material recovery or future-cycle prediction. No noise model or
independent replicates support significance or physical identifiability claims.

## Exact completed comparison

Controlled experiment, one specimen/cycle292018.5, reference1, stage13/14 train,
stage15 held high load15001.544952392578. Target is stage15-stage13 planar
displacement increment. R002 four predictions were frozen before conversion;
R003 consumes that held response, which is no longer an untouched tuning holdout.

| Frozen method | Area-weighted global-rigid-quotient vector MAE, mm |
|---|---:|
| old | 0.0023730180878627173 |
| proxy | 0.0023420692196045264 |
| intact | 0.0031310389775165495 |
| secant | 0.0021353985113825966 |

Authoritative Delta old-minus-proxy=3.0948868258190865e-05mm, outcome improves.
Proxy reduces intact error25.1983%, but exceeds secant by0.00020667070822192983mm.
646 of648 frozen points retained; IDs20545/21607 have missing XYZUVW, excluded
only by the frozen finiteXYUV rule. Common inherited area425.5812202mm2,
coverage99.896347%. No point selection, newweights or per-side rigid alignment.
All four use the same global planar rigid subspace and vector norm aggregation.

## Execution and numerical warning

User approved the exact validation_approval.md hash
16432606d302f5777ebaf2cf39287ec15a7aae6f00c41ed1a4055b97e41b3e13.
One complete command block ran locally15:19:23.540414Z–15:19:27.143535Z,
3.603s/exit0; numerical validate PID17203 took0.106136292s. No retry, new solve,
fitting, tuning, producer connection, push or external message/file.
Reviewed source b702430e3de98226ccf4a799c613b8df181fc9d4; invocation HEAD
8e88b483af1cea4bbcf34a5de8a8d07e9490f8b9 was clean and documentation-only later.
Python3.12/NumPy2.2.6, single-thread CPU. Original numerical source unchanged.

The unchanged R@coeff projection emitted divide/overflow/invalid RuntimeWarnings,
retained in validate.log. No rerun or source patch. Renderer scalar crosscheck
max component difference4.12e-18mm. Independent reviewer reconstructed target
from raw member and used math.fsum/math.hypot scalar formulas: max component
difference<=3.69e-18mm, all actual arrays finite, same scores/contrast direction.
Thus no detected effect on these saved results; warning root cause remains
unidentified and is not declared generally harmless. Future reuse must retain
this limitation rather than suppressing warnings.

## Minimum decision figures and source bindings

Local endpoint:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R003/`.
Under figures/: held_scores, held_residuals, held_increment_fields, eachPNG/PDF
and same-stem explanation; scores.csv, arithmetic_crosscheck.json and source/
artifact receipt. Whole common support/fixed axes/shared scales, no smoothing
or selected examples. Main and reviewer opened3PNGs; PDFs generated/hashchecked,
not separately rendered. Sixformats/three sidecars checked,12render hashes agree.

- Stage15 member SHA:7148b8544294eff0aea25ff1e903a7acd66c5a68bdc3a2d7139b4e4f75096b16.
- Validate receipt:a243775f639c41fa3fd2843b1f0efd8ffb42e346836dba5a62616b64bb29a296.
- Metrics:8340dfbe1350190b7eab650144eaa065e6fca64efd9605d73bb915c7ffcb8822.
- Fields:f8185c22d1cbc422d54a440c0a7a1c66cbc1ed614f7e1ad51a7f01989956716b.
- Render receipt:72f64d82b06237f0b160d791562813a9df243659925806a965e54674ebe4bdcf.
- R001→R002→R003 receipts/artifacts/source lineage verified; all four original
  R002 artifact hashes unchanged before/after and independent acceptance.

## What worked, remaining bottleneck, next lever

Component progress: complete real-DIC→training opening→deterministic prior→
static response→untuned high-load evaluation path; admitted training support,
finite three-solve mechanics, small held improvement over old prior and clear
gain over intact. These do not establish a uniquely inferred damage state.

Measured limiting comparison: even the updated fixed static procedure trails
secant. Geometry repair alone has not closed the gap. Auxiliary interpolation
and source anomalies, non-negligible W, exporter compensation uncertainty and
2D/static assumptions remain. These are hypotheses about the gap, not an
identified physical cause; q=0 here does not test additional amplitude inversion.

Smallest next proposal (not executed): freeze a read-only decomposition using
existing frozen fields to separate the mechanics-minus-secant correction from
the secant-minus-target discrepancy, with a predeclared spatial aggregation.
Use it only to specify a controllable model/observation diagnostic, not tune
anything on stage15. Any changed model, new solve or confirmatory comparison
requires a new reviewed experiment, fresh held response and separate approval.
E016 itself stops here; no broad method-wide failure or future-prediction pass.
