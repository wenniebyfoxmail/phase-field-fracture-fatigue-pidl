# R4终态：第2子步Schur线性方向失败，已停止

唯一科学尝试`pf_hybrid_solver_v7_20261020_r4`，准确源`bb07b014e6474b3038a0b135e2da4d21c2083e31`。后续HQ人方托管/计算授权单独限定为一次train_A连续600步；不是复用R3许可，也不是原3600步比较。2026-10-20 23:01:50.784 UTC（英国10月21日00:01:50.784）失败；outer3850243、supervisor3850244、worker3850251、guardian3850252均已核实退出。

train_A接受1/600，首步含IO30.404763492秒；case phase150.707971405秒、producer150.709453185秒、worker+guardian实际CPU228.202542秒、GPU0。第2步最后fresh101.635466826秒，最后Schur失败记录116.951713167秒；非300秒超时。首科学失败是`Schur linear solve failed original true-residual target`，guardian的incomplete step仅为worker失败的后续记录。

全部29份选定取回文件92014104bytes逐SHA核验，33源文件终态哈希与签名包一致；传输错误/部分流及修复收据保留，不当作科学重试。durable/latest均version1，未接受候选不作标签。没有其他case、NN训练、自动重试或新科学任务。

[完整数值解释与下一方案](result.md)／[逐case与step elapsed](case_elapsed_times.csv)／[独立保存证据审核](evidence_review.json)。静态163项通过只适用于实施检查，不能改变实际连续轨迹失败。
