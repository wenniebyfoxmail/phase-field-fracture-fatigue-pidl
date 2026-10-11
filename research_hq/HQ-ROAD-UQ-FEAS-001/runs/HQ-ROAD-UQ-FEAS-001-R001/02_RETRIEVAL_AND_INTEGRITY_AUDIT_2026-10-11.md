# HQ-ROAD-UQ-FEAS-001-R001 retrieval and integrity audit

The Windows scheduled task completed with result 0, `scheduled.exitcode.txt` is 0, stderr is empty, and the formal receipt is `succeeded`. Receipt identity matches `D-26-09`, GPU 0, PID 49712, code snapshot `46c488c9b33f2130a499491d704c8b6276280af18fc328815314446f32b5dc87`, and data-lock `7223dfabfbff5087a196c9e0105f4cd4c4cb8a0bb082bdbffb21e7ae5d954435`.

The remote original remains in place. The retrieved archive SHA-256 is `e9d69bdc52751868052eca2f370276b98db27c39ca6ba1e69bf30bea94b3a9a7`; its 12 files total 8,427,733 bytes. All 12 extracted files match the remote byte counts and SHA-256 manifest. The run contains 40 complete selection rows, a valid best checkpoint from epoch 29, 341 A-validation rows, 200 A-test rows and 118 CFD rows. Every Dice, error and frozen uncertainty score is finite. The PNG risk figure is readable and depicts the same three curves as the JSON.

Independent recalculation reproduced the selected epoch, A-validation mean Dice, CFD full risk, positive-Dice and degenerate counts, all three stable score orderings, every cumulative risk point, risk@29 and AURC to floating-point precision. Integrity verdict: `PASS_RUN_COMPLETE_RETRIEVED_AND_RECOMPUTED`.

One non-decisive packaging defect is recorded: `all_failures.json` contains the 50 catastrophic rows with error at least 0.9, rather than all 118 imperfect CFD rows. The full 118-row inventory is present in `cfd_metrics.csv`, so no gate input is missing and no rerun is justified. The filename must not be interpreted as an exhaustive failure list.
