# HQ-ROAD-UQ-FEAS-001 D1 read-only preflight review

Reviewed before launch on 2026-10-11. Code snapshot: `46c488c9b33f2130a499491d704c8b6276280af18fc328815314446f32b5dc87`. Data-lock SHA-256: `7223dfabfbff5087a196c9e0105f4cd4c4cb8a0bb082bdbffb21e7ae5d954435`.

The synthetic suite passed 3/3 without a backward pass or optimiser step. The independent AST contract audit passed all checks: one frozen seed, 40-epoch cap, six-hour hard deadline with a 30-minute evaluation reserve, checkpoint selection only by CRACK500 validation mean Dice, three frozen scores, fixed 29-image low-coverage gate, no network/subprocess surface, and no Road420 path argument. A separate data preflight recomputed all three archive hashes, the 118-pair/236-file CFD aggregate hash, and inventories of 1860/245 training, 341/49 validation, 200 internal-test, and 118 CFD pairs.

One issue was found and fixed before this receipt: CRACK500 full-image masks use `<image_stem>_mask.png`, unlike crop masks. All preflight checks passed after the fix. The review establishes implementation and identity readiness only; it does not establish training success, scientific validity, or any field claim.
