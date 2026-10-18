# S09-E011-A002 — zero-step gamma 4096

- Status: `accepted_for_code_review`; no training performed.
- Change from A001: one fixed `gamma_R=4096`, chosen as the next power of two
  above the largest observed wrong-pair zero-crossing requirement; no scan.
- Exact direction result: 8/8 wrong margins have positive merged-gradient
  descent derivatives, versus 0/8 for the control.
- Next-AdamW replay: 8/8 wrong margins improve; 17/17 correct margins narrow,
  but 0/17 are predicted to cross zero in the next first-order step.
- Median wrong-pair predicted margin change is `8.42359e-7` for R25 versus
  `4.04581e-7` for the control.
- Trade-off: median predicted `L_D` change is positive for both arms at the
  inherited momentum state; median `L_P` improves on wrong pairs but slightly
  worsens on correct pairs for R25. These remain explicit result diagnostics.
- Evidence: `docs/research/S09/S09-E011/no_step_preflight.json`.
