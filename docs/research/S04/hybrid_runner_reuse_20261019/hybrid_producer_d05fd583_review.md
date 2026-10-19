# Independent hybrid producer review

Verdict: MODIFY_AND_REREVIEW. Exact commit `d05fd5834468f04e200d70e7f4dce7873241af6d`; artifact `73f617acd9d23fc6706c6493665e3d92035d29f4e317bc3e3b3566a43c62d276`; card SHA256 `5603ff641bd8d4fdf97dd8e208447785cc1dff2bc0a78e40157cb6dc74486097`.

All25 manifest files verified against immutable commit bytes; no missing static local imports. Full hashes and material access are in `hybrid_producer_d05fd583_review.json` and `hybrid_producer_d05fd583_review_materials.json`.

## R1 [P1] Hard budgets and worker cleanup are not independent of blocking monitor work

`tools/run_hybrid_producer.py` lines 76,78,110,160,236,239. GPU query may block15s; os.walk/fsync have no deadline; guard checks only before these operations; successful child exit has no final deadline audit. stop_owned adds up to20s beyond already reached caps. After Popen and before supervise, append_event/SIGTERM exceptions have no unconditional child cleanup and can leave the detached worker running.

Minimal fix: Own each spawned PGID in a try/finally from Popen onward. Use an independent hard deadline controller, reserve termination grace within substep/phase/global/GPU caps, keep resource sampling bounded/off the deadline path, and recheck all elapsed caps after wait before success.

## R2 [P2] Failed or killed phases drop measured peak resource evidence

`tools/run_hybrid_producer.py` lines 119,160,233,251. supervise keeps peak_rss/gpu_peak/storage in local variables and rethrows without returning them. Outer usage remains{} and records only wall/cpu/completedFalse, so failure cost ledger omits measured RAM/VRAM peaks and storage state; monitor.json may retain only an earlier sample.

Minimal fix: Maintain a shared phase usage record updated at each measurement and finalize it for every exception/kill; preserve reason, measured peaks, last storage and termination overhead in the durable phase/cost receipt.

## R3 [P2] Joint matched-quality speed verdict does not qualify the classical comparator

`tools/run_hybrid_producer.py` lines 163,186. quality reads only comparisons[test_hybrid], while speed compares CH to min(CF,CC); classical error metrics can violate every frozen field/history/reaction criterion without blocking supports_neural_online_acceleration.

Minimal fix: Compute and report the same quality contract for test_classical and test_hybrid. Freeze how a failed classical quality check limits the matched-quality joint claim; do not silently discard it or change thresholds after results.

## R4 [P2] Complete planned field/evolution evidence is not produced

`tools/hybrid_producer_worker.py` lines 78,114,117,146. Analysis computes only u/v/d GP RMS, A/r/f and reaction errors. The reviewed design/validation contract additionally requires raw/active, energy/branch, front/morphology, negative-damage/healing and fallback/correction diagnostics plus decision-facing fields. Raw states/work records are saved but the required derived reports/figures and fallback summary are absent.

Minimal fix: Add bounded common posthoc analysis from the exact sealed states, with per-channel field/energy/raw-active and feasibility/retreat/correction/fallback summaries and fixed-rule common-scale decision figures/README. These diagnostics must not rescue or replace frozen primary criteria.

Preparation card authority isolation/bindings checked: execution_enabled=false, non-runner schema, no inherited owner execution authority. No scientific execution, tests, SSH/GPU, newFEM or edits performed. Owner41-check receipt reused. Unfrozen detached launcher and later worktree changes are excluded.
