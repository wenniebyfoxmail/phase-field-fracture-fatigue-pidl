# Response-state information value v0.2 — approved exploration

2026-10-19. User explicitly authorises prepare, check implementation/package, then execute and archive results in Obsidian. Original physical observation-UQ goal remains unvalidated. Continue the R001 published-DIC increment branch, not a new road or physical-reference claim.

D1: reuse R001 runner, 19 development-exposed groups, 1144 origins / 2288 cases, metadata/180 selected inputs, nested group folds, ridge family, native current-field anchor, 16x16 increments, primary score and exact-window exclusions. No new data, protected holdout, author predictions, XLSX or raw CSV are used. D4 active: distinguish response information from release-progress proxy and present-state from history information in one grouped comparison.

Primary score: unchanged mean of full/native-grid and first-frame local-row-band normalized MAE, channels normalized by development-group future increments, release-group/horizon equal weights. H10/H40 are release steps, not verified machine cycles. P/S are native persistence/secant. Oracle output projection is future-informed diagnostic only, neither competitor nor mathematical MAE lower bound.

Arms and origin-available information (all share metadata: C/E, angle, stress code; repeat ID absent):

| Arm | Features | Dimensions |
|---|---|---:|
| span_only | three-history span and span squared; R001 scalar replay | 10 |
| span_progress | span_only + origin release-stage/1000 and square | 12 |
| current_response | span_progress + current full/local channel means and stds | 20 |
| history_response | span_progress + same response stats at all three history stages | 36 |
| global_history | span_progress + full-field channel means at all history stages | 18 |
| centered_history | span_progress + full std, local-minus-full mean, local std at all history stages | 30 |
| rich_history | span_progress + all-history compact and 8x8 pooled field | 420 |
| compact_noclock | exact R001 compact replay | 34 |
| rich_noclock | exact R001 rich replay | 418 |

Release progress is absolute origin stage, no final-stage/Nf scaling or future range. Current_response sees all scalar history but no past response statistics. A common current native field remains in every output skip connection, so comparisons concern what the increment predictor can encode. Global/centered blocks split compact information: they do not correct physical motion, identify camera drift, or distinguish true loading from processing artefacts. Centered features are uniform-channel-translation invariant, but shared span proxy and native output anchor remain. Fewer/more features have unequal parameter counts; identical learner family, 3 alpha candidates, weights/folds and total candidate fits per arm, not a false equal-capacity claim. Reparameterisation also changes ridge penalty geometry; do not claim a causal necessity proof from block ablations.

Main predeclared contrasts: history_response minus span_progress (response value beyond progress), current_response minus span_progress (current response), history_response minus current_response (additional history). Report raw group/horizon scores, paired group signs/magnitudes and full/local metrics; no fabricated success percentage or physical significance threshold. Progress contrasts span_progress vs span_only, history_response vs compact_noclock, rich_history vs rich_noclock. Global/centered explain component utility; rich is a strong richer comparator, not an architecture sweep. Keep P/S throughout. Early/mid/late thirds are descriptive release positions, never physical lifetime, model input or an adaptive selector.

Outcome: if response adds across-group/horizon value beyond progress, retain the useful block; history helps beyond current -> retain temporal state; current suffices -> prefer simpler representation. If progress explains most old gain or global means dominate, narrow to that published response/proxy effect and investigate semantics before physical claims. If P/S remain stronger in strata, preserve those failures rather than select favourable periods. All 19 groups remain development-exposed; this cannot establish untouched-asset generalisation or true crack/physical uncertainty.

Budget: one Taobo CPU thread, 4h wall, 8GiB address space, 8GiB outputs, 0GPU; one fresh R002 run, no model retry or budget extension. Input bytes reuse R001 immutable read-only store, validated again before model fit. Exact code/config committed then copied to fresh run root. Local and producer synthetic-array checks; producer input hash/tensor/manifest verification; complete saved predictions re-scored separately, replay arms compared against R001, all outputs/figures retrieved. Relevant checks are implementing-agent checks for exploratory work, not formal independent review. SCB email remains for the user to send personally; no mailbox action.
