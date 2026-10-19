# 43af risk delta baseline

只读差异基线；不是新包复审或执行许可。精确 `43af56d43150f4ae8cf8799ceec4669564d67ef0`，artifact `6b0ef3bf36ffbedf3c33170b2f641c06873684276a18be3f6726537e4d7c4585`，cardv2 SHA `da119752c2ee81443dcee43b31cbe1fe2942ae70b39acf115dc1712005d8a125`。对照另一 owner 的 d05 审阅，结论如下。

| 风险 | 43af状态 | 已修 | 仍未闭合 |
|---|---|---|---|
| R1 监控阻塞、退出终审与清理 | 部分修复 | Popen后全生命周期finally；parent-death保护；GPU查询2s；monotonic步标记；45s总预算清理预留；共享replay/analysis账本 | 监控仍同步递归扫描/文件读写/fsync/GPU查询；无独立时限控制器；成功退出后无最终时限审查；120s子步触发后清理另耗时。卡的实时性限制披露不等于修复这些缺口。 |
| R2 失败peak丢失 | 未修 | 失败wall/childCPU及监督开销入账 | RAM/VRAM/storage保存在supervise局部，异常不返回，最终usage缺已测peak；旧monitor不能替代终态测量收据。 |
| R3 classical质量与speed联合 | 未修 | 两种候选均计算质量指标；完整worker计时 | quality只取neural，speed却用min(CF,CC)，联合结论未要求classical满足相同参考质量合同。 |
| R4 完整场演化证据 | 未修 | 封存状态、证书、返回后的work、u/v/d/A/r/f/J/反力标量比较 | raw/active、能量/分支、front/形态、负damage/回退、correction/fallback及同尺度场图未派生；外杀前内部块计时不持久。存了原态不等于已经生成所承诺分析。 |

源码定位：R1 supervisor119–177、worker16–26；R2 supervisor120、143–162、250–268；R3 supervisor180–203和worker134–155；R4 common60–73、worker78–117及129–158。行号均指43af git对象。

后续精确包需分别验证：独立时限路径与成功退出终审；所有失败路径资源/清理收据；两比较臂同质量合同的联合判定；完整但不替代主判据的后处理交付和可在外杀前保留的块计时。不得用缺测peak=0，不得事后丢弃classical或放宽阈值。

原v4是portable Q4核/身份迁移的历史聚焦复审，不能转述为这四项已全部解决；停止证据PASS也只确认那次停止记录的一致性。本次未检查新实现，没有tests/profile/预检/SSH/数组读取/训练/新FEM/重跑。
