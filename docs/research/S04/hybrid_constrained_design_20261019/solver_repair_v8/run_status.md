# R5终态：第三块方向的未接受全步触发机械pivot保护，已停止

唯一尝试`pf_hybrid_solver_v8_20261021_r5`，源f4311e0e21d52eb65a8c845308436d3e7ab4df5f，34files artifactff3dc7a9；57人工检查及原渠道准确绑定/实际准入通过后单次运行。英国2026-10-21 00:49:19.701终态failed。

train_A1/600，首步含IO31.842570630秒，case205.136913221秒，producer205.138359378秒，worker+guardian实际CPU356.267355秒，GPU0，归属树观测峰值RSS4.21GiB。第2步marker到失败trace169.993809917秒；不是成功完成step事件，非300秒超时。23次fresh完成/24次尝试、3个块方向，未达100fresh或8方向上限。

三个块方向双行真线性残差均达标；第三方向投影全步的机械首轮80innerGMRES未达目标，原CURRENT K LU返回后pivot资格不通过，根因记录`mechanics numerically near-singular`。实际pivot标量未保存，不能称已测具体比或旧接受态奇异。该全步没有fresh审查，第三方向的半/四分之一/八分之一步未尝试；按首失败停止，不自动继续回溯/重跑。

outer3949659/supervisor3949660/worker3949673/guardian3949674均已退出。完整159任务文件75154098bytes（全部runroot+archive，原输入不复制）逐SHA/size核验；无传输失败/科学重试。两个远端机械动作29.367797秒；此前一次本地目录错误发生在SSH前、0远端动作/worker，收据保留。

latest/state0001均version1，数值指纹与R4首步逐位一致；完整600轨迹/连续teacher/NN收益未取得。仅剩保存证据分析与结果复核/归档，无新科学任务。[结果与下一机制路线](result.md)／[case与step elapsed](case_elapsed_times.csv)／[保存结果独立复审](evidence_review.json)。
