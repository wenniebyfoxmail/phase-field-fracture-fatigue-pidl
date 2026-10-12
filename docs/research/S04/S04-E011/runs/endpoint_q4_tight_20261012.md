# C83 Q4 bounded solver-control sensitivity — completed 2026-10-12

Outcome: **EXTRA_BUDGET_EXHAUSTED**. Fresh original20-iteration baseline passed;10 additional outer iterations completed, but none reached fresh projected residual sum≤4e-6. No inner failure, nonfinite endpoint or predecessor change was observed. Zero history commits; no new cycle or subsequent substep. Last completed iteration30 is **not** a tightened converged solution.

Run: `pf_s04e011_endpoint_q4_tight_0c21f70_20261012T170257Z`. Producer CITPC12 CPU one thread; launchcommit `0c21f7013a9741673cf0382ea17d551c7a147384`, branch `codex/hard5-q4-t3-2x2-20261005`, runner SHA256 `fa810e268238320747ed21a805e969108947c3c43f44af35165c2832e2229d72`. Started2026-10-12T17:03:31.7829540Z; terminal result written2026-10-12T17:11:19.4065399Z, roughly468seconds. Worker11032 and matching run processes are absent at2026-10-12T17:27:03.0514195Z. Windows root `C:\Users\xw436\jobs\E011_TIGHT_0c21f70_20261012T170257Z`.

Controls: inner u1e-6→1e-8; phase4e-4→4e-6; freshly reassembled displacement free L2 plus nodal-monotone feasible damage L2 screen4e-6. Fixed c83s3 history, native-Q4 GP4, U=.11999988, eta0, innercaps250/250, extra outer cap10. A combined-control sensitivity, not isolated outer tolerance.

| Metric | Verified baseline, outer20 | Last complete, outer30 |
|---|---:|---:|
| Fresh free-u residual L2 |2.729217e-4|3.668840e-4|
| Feasible damage residual L2 |2.767437e-5|2.581167e-5|
| Fresh projected sum |3.005961e-4|3.926957e-4|
| Active integral, FEM |7.054856e-4|5.768122e-4|
| Active integral, unchanged PIDL |7.464689e-4|7.464689e-4|
| PIDL/FEM active integral |1.05809|1.29413|
| Weighted active relative L2 vs PIDL, current FEM denominator |0.476394|0.899773|
| Weighted active correlation vs PIDL |0.887457|0.578380|

The best residual sum is2.660760e-4 atouter21; final sum is1.30639×baseline and98.17×screen. Active absolute weighted gap grows1.99032×; the worsening is not solely a denominator artifact. Compared withbaseline, uv nodal relative change4.0031%, damage7.3763%, native weighted active relative change68.0470%; nodal maxabs damage change0.607919. Relative nodal changes use ordinary Euclidean norms; active metrics use native GP integration weights. Original PIDL state is **Q4 c83 peak step414**, unchanged. Every FEM extra point is a complete outer iterate atc83s4, frozen accepted s3 predecessor, not an accepted post-history state.

Verification:20 downloaded files, 270853342bytes total; all remote/local SHA256 and sizes match.11 endpoints pass finite u/d/raw/residual checks, d_old≤d≤1, exact immutable damage/history/load equality, file/iteration continuity. Native AMOR raw/common Q4 replay relative L2 stays below1e-10 (baseline4.58e-15). Independent source and result/figure reviews PASS; separate projected screen is not a GP KKT or physical certificate.

Evidence: local `retrieved/`, `retrieval_verification.json`, `completion_process_verification.json`, `analysis/summary.json`, `analysis/metrics.csv`, `analysis/endpoint_tight_comparison.png` with same-stem sidecar. Tracked supplementary protocol: [endpoint_tight_protocol_20261012.md](../endpoint_tight_protocol_20261012.md).

Claim verdict: inconclusive for a tightly converged endpoint; diagnostic negative for improvement within this fixed budget. Disposition: stop this budget, preserve original E003/E011 outputs. This does not support “tighter controls alone remove the discrepancy”; it does not establish baseline or PIDL as truth, exclude eventual convergence, or explain allcycles. Fixed committed-f/trial-f and joint Deep-Ritz/staggered differences remain.

Next discriminator (proposed, not launched): use the saved outer20–30 fields to localize damage updates and their induced mechanical residual, then preregister a bounded coupled damping/line-search control from the same predecessor. Do not extend this run or silently change caps/tolerances.
