# S03-E001: CrackMNIST mechanics-aware CV decision

**Run:** `S03-E001-R001`  
**Execution:** succeeded; retrieval verified.  
**Scientific verdict:** `mixed`.  
**Frozen decision:** `NO_GO_CRACKMNIST_MECHANICS_CV`.  
**Independent evidence review:** `PASS_EVIDENCE_READY` after relocating the
required interpretation artifacts inside the archive.

| Gate | Frozen result | Decision |
|---|---|---|
| Localisation | 4/4 physical-experiment holdouts; signed-improvement 95% interval [6.742, 6.922] px | PASS |
| Incremental SIF | >=10% gain in 1/4 holdouts; aggregate interval positive but frozen 3/4 stability rule fails | FAIL |
| Uncertainty/abstention | abstention 3/4; mean nominal-90% coverage KI 0.800, KII 0.824, T 0.714 | FAIL |

The admissible positive result is limited to strong crack-tip localisation on
the locked augmented 28x28 near-tip DIC grids. It does not establish stable
incremental KI/KII/T information or calibrated uncertainty. Raw-image vision,
chronology, future growth, RUL, hidden-state recovery and road transfer remain
outside the evidence.

The full evidence package is intentionally local at
`local_archive/experiments/S03-E001/runs/S03-E001-R001/archive/`; generated
checkpoints, predictions and figures are not committed to Git.
