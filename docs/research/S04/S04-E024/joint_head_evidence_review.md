# D011 independent finite-component evidence review

**Bounded actual finite-component PASS**, source `eb09f0d9d6720c99e92f9c521cfa841e6e8b43db`. All three single proxy solves produced saved candidates; every full step k0 was rejected and the first half step k1 passed all seven actual guards. No new head solve, candidate search, parameter update or training was performed by this reviewer.

Independent raw511 encoder/D/bias/BC/window, explicit 2×2 Q4 geometry/normalized mass, component AMOR stress and engineering-strain GN reproduced the original 3D velocities, **all21 Gram/GN c/g/H models**, and the final external-head fields. Maximum saved-field difference **3.33e-16**. Exact D010 basis, theta, original33 files and six prior input hashes agree. Shared parameter radius, affine mapping, original outside/BC equality, original-ball metric/transform and finite branches agree. Only the six already visited coefficients were replayed; their actual rejection reasons and first-feasible stopping agree, including small floating-point violations.

|state|full UV %|damage UV %|background UV %|inside BG UV %|rho %|delta/theta norm ratio|
|---|---:|---:|---:|---:|---:|---:|
|c20|−.09941419|−.10737531|−.03602739|−.34874675|−.01234765|.0100000000011|
|c60|−.01285685|−.01346420|−.00653115|−.05232975|−.00039052|.000858581485|
|c83|−.01201271|−.01014834|−.10592945|−.53694578|−.07834857|.00482530618|

All values are actual own-E023-relative RMS changes. c60 improves full/damage UV over D010 r2 by .01248712%/.01343223% relative to those respective D010 errors, but own-E023 improvement remains only .0129%/.0135%; multiplying the tiny former gain by ~35 does not establish practical recovery.

K0 rejection causes: c20 both driver guards and actual budget slightly above the strict cap; c60 both driver guards and global/inside-background UV increases at numerical scale; c83 both driver guards. C60 full-step UV gain is only **.02367239%**, versus .01285685% at the accepted half step. Thus its small gain is not explained solely by the final halving. The same numerical checks were retained unchanged; no tiny positive difference was silently forgiven.

At saved proxy points only, solved for nonnegative Lagrange multipliers (not a new head) using fixed active constraints. C60's global-BG UV / inside-BG UV / weak / background-driver weights can be .3198422/0/.8221261/.1909995. Original-coordinate stationarity relative3.84e-15, inner2.18e-16; largest proxy violation3.23e-13 lies within original solver tolerance. Together with PSD this supports a near-stationary solution of **this proxy**, not an exact mathematical certificate or true nonlinear/full-head ceiling. C20 is similarly consistent at roundoff; c83 residual is larger (original1.17e-5, inner9.49e-7), so do not blanket-label all three exact optima. Detailed `saved_proxy_kkt.json` preserves active thresholds and signs.

Secondary outputs were independently rescored against physical_metrics.csv. Full/damage instantaneous driver errors now decrease in all states, but background **strain** error increases in c20/c83 by .02256880%/.05398805%, and inside-background by .05885013%/.10024115%. Guarded background UV/driver preservation therefore does not establish background strain preservation or universal physical improvement. Compared with D010, c20/c60 rho and both background-driver errors worsen while still improving relative to E023; there is no universal comparator dominance. History/maxH missingness and original large equilibrium gap remain untouched.

Observed numeric cost27.8879s CPU, peakRSS1,297,711,104bytes, three offline three-variable solves, no NN optimizer or original checkpoint/history writes. Plotting/review costs are outside that receipt. The result keeps a valid curvature-aware finite component but does not establish meaningful application tolerance, coupled crack/fatigue evolution, holdout transfer or a nonlinear/full-head optimum. Legacy .001 and original portability/warning boundaries are unchanged. Final prose/figure QA remains pending.

## Final main prose/figure/provenance QA

Read final `joint_head_decision.md`, README, sidecars and plotting/tabulation sources. Visually inspected the summary and all three state atlases. No blocking issue found. Summary old/new labels are separated and tiny values use scientific notation. Matched plot/table provenance source SHA and every listed input; separately bound the final summary-only renderer, which changes layout and faithfully recomputes the existing scored ratios rather than a physical candidate. Final SHA values for documents, all eight PNG/PDF files, four sidecars, map checks/manifest and three analysis sources are in the verdict.

The decision accurately distinguishes finite component improvement from useful recovery, actual parameter percentages from the 2% cap, exact UV curvature from approximate weak/driver proxies, actual rejection from solver success, numerical KKT support for c20/c60 from c83's larger residual, and c60's small k0 benefit from the halving cost. Background strain increases and lack of dominance over D010 remain explicit. The sole full-head/same-seven-constraints/same-budget proposal is unexecuted and does not erase the fixed-3D result or imply full-head attainability.

Field images use own-state references, shared within-state/quantity signed scales, damage/window overlays and disclosed crop/stretch/Gouraud/logfloor/symlog. Native normalized-mass node contributions sum to rho² and are correctly labelled as weak-force contributions, not strong PDE residuals or causal damage partitions. FEM nearzero-force relative summation differences remain numerically tiny in absolute units and do not become a physics acceptance test. Colour changes are explicitly not regional-integral gains or pointwise protection. No additional numerical stage, solver or candidate was run for final QA. Obsidian milestone remains for separate review when supplied.

## Obsidian closing milestone QA

Read censor section67 (line991 onward) and the single Roadmap censor line11. Both faithfully retain the actual c60 .01286%/.01346% gains as small, background UV/driver protection versus background strain costs, non-dominance over D010, frozen history/no training, and an unexecuted same-budget/same-constraint full-head proposal. The embedded figure interpretation distinguishes strong local colours from regional recovery and weak-force contribution from strong-form residual. D010's earlier record is not rewritten. Section/line SHA bindings are in the verdict.

No blocking issue remains. This closes the requested D011 review; no other task, candidate or numerical stage was resumed.
