# Hard5 eta0 Umax and event-phase reaudit

The controlled five-step FEM trajectories give first-hit/confirmed cycles of `122/125`, `83/86` and `59/62` for `Umax=0.11, 0.12, 0.13`.

The older Umax=0.12 baseline used eight substeps and gave `86/89`. The mesh is identical. At own first hit, new c83 and old c86 remain close (active log-MAE 0.0834, correlation 0.9933, absolute-p99 IoU 0.6929), so the difference is mainly a three-cycle protocol-dependent timing shift rather than a different crack path.

The old FEM-PIDL c89 comparison mixed PIDL first hit with FEM confirmed/post-hit state. The corrected five-step comparison is FEM first-hit c83 versus Formal PIDL first-hit c89. PIDL active p99 is about 33 times lower; FEM-p99 active IoU is zero and support-area ratio is 0.0067. In the FEM active top-1% zone, PIDL raw-driver median is about 74 times lower while the degradation-survival median is 0.843 versus FEM 1.0. The current evidence therefore points first to raw-driver localization/amplitude failure at the FEM process zone, with degradation as an additional suppressor.

The old PCC scaling helper did contain an independent error: it used `w1=c_w Gc/ell` even though the implemented energy already divides by `c_w`. This affects PCC/road runs that called the helper, not normalized Hard5 runs that directly use `w1=1`. The corrected scaling branch uses `w1=Gc/ell` and `w1_norm=1`.

Full local decision package:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/hard5_eta0_umax_011_012_013_reaudit_20260729`
