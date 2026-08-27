# GPT Pro pre-launch advice: Hard5 probabilistic increment GNO

Source conversation: `chatgpt-conversation://6a8ff370-d240-83eb-b30d-a7967c7abb45`

Reviewed on: 2026-08-27

External verdict: `GO_AFTER_PROTOCOL_AMENDMENT`.

## Advice received

- U0.12 is a clean parameter-training holdout but not a pristine confirmatory trajectory because its fields and fixed origins have already been inspected.
- Use one symmetric, trajectory-wide, all-legal-pre-hit `t -> t+1` primary evaluation on all three held-out trajectories. Retain fixed U0.12 origins only as secondary diagnostic anchors.
- Treat the bounded Laplace output as a conditional residual/predictive-scale score, not a physically admissible generative distribution or calibrated interval.
- The frozen-mean then scale-only optimization is defensible, provided all uncertainty diagnostics are held out and the scale is not called pure aleatoric uncertainty.
- Native Q4 cells and adjacent cycles are correlated. Cellwise metrics are spatial ranking diagnostics, not independent replications; trajectory-level evidence remains three trajectories.
- Three-seed spread is ensemble/seed disagreement, not complete epistemic uncertainty.
- Keep persistence and constrained-linear as the fixed local-dynamics controls and make per-field results primary.
- Add an active/change-region metric so near-zero background increments cannot dominate whole-mesh MAE.
- Freeze risk-coverage orientation within channel; do not create a post-hoc combined uncertainty score.
- Apply the same legal first-hit crossing policy to every fold.

## Local decision

Adopt the advice with these experiment-specific decisions:

- Primary gate: all legal pre-hit origins on all three folds, using native Q4 whole-domain and FEM-target area-weighted top-5% true-change scopes. Reduce origin median within seed, seed median within fold, then fold median; never pool cells, cycles or folds as independent samples.
- Both primary scopes must pass the predeclared per-field comparison rule. Uncertainty cannot rescue a failed point gate.
- Secondary diagnostics: fixed representative origins remain for field maps and stage interpretation only and are non-gating.
- Retain the legal `T_hit-1 -> T_hit` target and forbid post-hit origins identically in every fold.
- Use the terms `conditional residual scale` and `ensemble disagreement`. Report nominal coverage only as uncalibrated descriptive coverage.
- Reject the suggested qualified-success branch based on fatigue-transition prediction or useful uncertainty alone: v1 has no transition head, and its uncertainty diagnostics are non-gating.
