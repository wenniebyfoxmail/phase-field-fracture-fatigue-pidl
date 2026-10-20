# S09-E010 no-training regression rerun

2026-10-20, Europe/London. Exact commit: `010281be8045301f7e56b938de82969982c89bc9`.

## Result

One six-file pytest invocation produced **117 passed in 5.21s**, including **47 E010 tests** and **70 E009 tests**. This agrees with the owner's recorded 47/117 counts. No failed or skipped tests. Source, selected tests and six small control/reference files were exported directly from Git; all 63 exported files were byte-compared against that commit before testing.

The tests use generated 9-node/4-element fixtures, toy tensors and mock state-machine adapters. The helper fixture module was imported, not collected as an additional test suite. No real scientific arrays, packet, weights or holdout data were opened.

## Execution boundaries and wrapper status

CPU single-thread libraries; CUDA hidden; real AdamW/Adam/SGD steps and CUDA initialization rejected; external file access, network and external process launches restricted; producer numerical entry points rejected. The observed real optimizer-step and CUDA-initialization counters were both zero.

Pytest returned **0**, but the deliberately strict wrapper returned **1** because it treats any rejected audit event as nonzero. Three optional dependency probes were blocked: reading `/proc/self/maps`, `uname -p`, and `system_profiler -xml SPFontsDataType`. A separate import-only diagnostic reproduced these exact three events without running tests, accessing science inputs, or relaxing the allowlist. They are not failed test cases or producer attempts. The test suite was not rerun.

## Scope

This confirms the recorded no-training regression outcome for the exact historical commit. It does not validate real GPU replay, training performance, runtime resource limits or a scientific result, and does not authorize a producer run. Owner code, protocol, frozen run records and Obsidian were not modified.

Machine-readable receipt: [regression_receipt.json](regression_receipt.json).
