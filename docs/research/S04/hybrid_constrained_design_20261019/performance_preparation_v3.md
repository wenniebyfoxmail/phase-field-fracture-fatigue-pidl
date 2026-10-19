# 成套性能准备 v3：worker退出终审修复

v2精确复审保留为MODIFY：59项人工检查及38哈希匹配，queued timely done、缺测资源null、非单位厚度修复有效；另发现worker在deadline前退出而active step缺少done时仍可能reason=null。

v3在worker退出分支再次drain IPC，保留已有消息/迟到判定，要求active为空，否则明确incomplete step completion at worker exit并按控制失败处理。新增step_start后30秒退出无done、queued done1/start2后退出无done2两个确定性负例；及时完成正常退出和真实迟到原回归仍通过。120秒与全部物理/质量阈值不变。61项人工检查通过3.10秒；仅控制替身与人工Q4，无Linux/真实状态/profile/训练/preflight/SSH/重跑。

完整机制与预算仍沿用v1/v2，同一关闭执行准备卡、无RunID；原R1停止不变。新manifest_v3绑定该差异，再做聚焦独立终态复审。
