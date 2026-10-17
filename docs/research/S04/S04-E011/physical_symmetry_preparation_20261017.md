# Physical parity diagnostic and opt-in repair preparation — 2026-10-17

Owner: one bounded S04-E011 saved-field diagnostic / compatibility repair, not a new producer Experiment or an amendment of the frozen four-arm verdict. Source producer `ad749c8bbba8120b3961add989b11427fab86254`; branch `codex/pidl-physical-symmetry-20261017`, based directly on that remote-preserved commit in its own clean worktree. In scope: physical parity helper, fit opt-in, deterministic tests, two saved-field analysis scripts and this record. No shared checkout, producer, PPT or Overleaf edits; no training/FEM/holdout access.

The earliest complete saved Q4 PIDL readout is c1s2; its inherited c1s1 damage/fatigue history is already asymmetric. This identifies observation coverage, not the causal onset order. The canonical common mesh has only373/86756 node reflection partners within1e-12, with no nearest-neighbour involution. Native Q4 reconstruction on declared paired probes is therefore explicitly separated from direct NN or native-GP reflection evidence. Original NCP exports and original FEM snapshots packaged by MCS are reused; no owner's equilibrium/optimization calculations are repeated.

On the declared front probes, parity-violating components account for20.33% of c1s2 active squared disagreement and0.0193% of damage squared disagreement. At c83, the existing display-field damage decomposition is32.94% Q4 /28.98% T3. These are orthogonal algebraic decompositions, not causal contributions or attainable repair gains. There is a substantial parity-compatible mismatch. The first proposed intervention therefore penalizes complete physical u/v only, lambda_d=0, without hard symmetry.

Method commits: `87650489` opt-in helper/integration, `fc7728a7` decomposition, `4e0a34b51ae01821e98f9522cbfaa4bbe2887b43` pre-optimizer adaptation rejection. Independent read-only review passed at the latter exact method snapshot;16 deterministic tests passed independently. Subsequent `d004bbb8` changes only a globally regular analytic test fixture and `ed44c923` changes only plot labels. Current method implementation remains byte-identical to reviewed4e0a34b5; local16 tests passed after both deltas. Review does not cover a future producer runner or imply physical/model improvement.

The explicit `physical` mode evaluates final fieldCalculation, fixed positive Uref, paired probes and declared weights. It requires all three lambda values and rejects Algo1/stale annealing weights before either optimizer loop. Legacy defaults retain their values and code path. Old damage penalty already applies alpha_constraint; the anchor compatibility defect concerns raw displacement versus the final mapped displacement. Pro text-only design advice was visibly run under the Pro option and completed; decisions and deviations are recorded with the local evidence. No production lambda has been calibrated.

Canonical local report and evidence:

- [Chinese report, reading guide and two field figures](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/physical_symmetry_diagnostic_20261017/README_analysis.md)
- [Source manifest](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/physical_symmetry_diagnostic_20261017/analysis_v2/manifest.json), [scoped code/evidence review](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/physical_symmetry_diagnostic_20261017/review_receipt.json), [Pro advice/adoption](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/physical_symmetry_diagnostic_20261017/pro_design_review.md).
- [Candidate card](physical_symmetry_candidate_card_20261017.json): original post-solve model2 and input checkpoint1 are identified, both arms use the same fresh optimizer. One fixed-history c1s2 block,200 RPROP updates per arm, max1 GPU hour, no retries or rollout. A single active-field directional observation selects the next action; u/v/d, centered width, local driver and feasibility must remain visible. The future worker is not implemented/Code Ready, and new training is **not authorized or run**.

Reproduce only the authorized local checks:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 -m pytest tests/test_physical_symmetry.py -q
```

The saved-field script requires `--root` and a fresh `--out`; it refuses overwrite. `tools/summarize_saved_error_parity.py` consumes its saved arrays plus the owner's existing c83 display arrays. Probe resolution sensitivity is retained, especially for strong near-tip driver gradients; it is not a converged physical symmetry test.

Obsidian: one concise milestone plus exact rendered PNGs appended to the existing `mesh对齐.md`; one current Roadmap entry updated, preserving other owners' text and historical links. Nightly usage checks remained above the80% remaining stop line (latest checked92%). No further work is opened once the only next action requires a new training authorization.
