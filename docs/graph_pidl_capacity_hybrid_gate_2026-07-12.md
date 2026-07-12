# Graph-PIDL Capacity and Hybrid Gate

- Mechanism question: can graph neighbourhood information improve the accepted 8x400 PIDL without introducing the fan-shaped native-field regression seen in reduced models?
- Full branch: 8x265 MeshGraphNet, 1,127,322 parameters versus 1,125,211 for the baseline (+0.19%).
- Hybrid branch: accepted 8x400 coordinate MLP plus a zero-initialized 2x32 graph correction.
- Physics: unchanged eta=0 hard-recovery objective; FEM supplies validation fields only.
- Cheaper diagnostic: one physical cycle with all five loading states plus recovery, before any multi-cycle run.
- Minimal assets: native peak/unloaded montage, FEM-projected field metrics, runtime/closure table, decision note.
- Satisfaction gate: no visible/native fan regression relative to baseline; improve at least two mechanism metrics including active-driver morphology; stable finite optimization; runtime compatible with a three-cycle follow-up.
- Failure gate: fan artefacts, scalar improvement with worse morphology, unstable gradients, OOM, or prohibitive runtime.
- Producer: parallel Taobo runs on separate free GPUs.
- Registry: diagnostic until a branch passes and survives additional seeds/cycles.
