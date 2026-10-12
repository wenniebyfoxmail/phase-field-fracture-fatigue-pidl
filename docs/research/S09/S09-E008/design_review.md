# Independent Design Ready review

- reviewer: ChatGPT Pro through OpenCLI, authorised Haofan account
- conversation: https://chatgpt.com/c/6acd0e7b-6000-8330-8b55-afade827162e
- reviewed `experiment.md` SHA-256:
  `40017ea1694cc99d343996378a537887961c2dd364b889ece793288f9e0f5f34`
- decision: `DESIGN_READY`
- authorised scope: bounded Stage 0A/P0/P1 metadata/source-capability and code
  design only

The rereviewer found the causal peak-transition contract, fixed judgement
metric, deterministic 16-transition selection, state-sufficiency gate and
explicit Stage 0B/P2 deferral sufficient. Adaptive multi-objective weights may
change optimisation, but cannot directly change the fixed `L_judge` formula or
normalisers.

Before Code Ready, the implementation must freeze eligible-cycle quartile/tie
rules, native integration weights, float/half-ULP convention, positive finite
normalisers and the pre-update initial metric. These details are recorded in
`implementation_contract.md`.

This pass does not authorise full-path scientific-array opening, training,
autonomous rollout or a constitutive/generalisation claim. Stage 0B/P2 needs a
separate reviewed amendment.
