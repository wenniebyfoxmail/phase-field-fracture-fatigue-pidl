# S01-E028 实现与可行性记录 — 2026-10-19

最新执行状态：R001停止包及R002完整原包已接收归档；全部逐项复算、五张原图及6.1 sol / High独立证据审查通过。冻结主标准支持1638+2027原pair，24负向保留；两次实际合计1203.085秒。D7限定目标定位完成；选择器/OOF/保留率/净益仍未验证。见[执行状态](execution_status.md)。以下为历史记录。


设计2b38766a经用户指定gpt-6.1-sol / High独立审查通过，主候选/范围/预算未改。实现与纯工程测试已完成；精确源码b045170988b3f2a8fc641b7a7b89c617bb6c9e41经同一独立6.1 sol / High代码审查通过。当前不是实际定位或检测结果。

## 为什么这次能改变路线判断

不再把细裂缝的像素占比直接当作格内存在概率，也不默认128裁块保留了全部原始纹理。用同一冻结外部模型，在三个既有资格地点的全部338原图/12238上下文上比较原生图分块与旧128输入，再用共同R_any-FG集合检查mean/max和center/any观测算子。原生同时改变尺度和可见上下文，因此只对这一整体改动作结论，不把成功或失败只归因于分辨率。

唯一主候选native/max/.5/any，六比较器逐context最强值→image→site增益，至少一个原qualification pair的两个地点均严格胜基线。其它组合保留自己的组件成绩，不替换主候选。部分包络不等于精确像素真值，outside不等于真负；资格通过仍不能自动接选择器。

## 工程验证与实际限制

46项-Werror回归通过（含22项E028，另24项复用E027/E026；本方1.35秒，独立1.16秒），覆盖空间边缘、窄bin、表示/参考算术、图/地点等权、共同支持、LOO与错配、部分pair、主候选不能被其它组合救结论、冻结后才GT、预测篡改拒绝、scope与案例身份、Windows数据白名单、预算与Mac拒绝。另在bundled Pillow12.3.0上用纯合成polygon验证真实reference loader与旧center逐格一致、旧mask不一致拒绝、无关容器标签不访问polygon；未载入Torch。Conda Pillow10.4仅做非栅格单测/绘图，不能替代生产12.3参考核验。

all_final与missing_final各5张合成图和README在owner local_archive/experiments/S01-E028/implementation_QA/，显著标SYNTHETIC ENGINEERING ONLY。缺参考F00保持null/inconclusive，不填0；图仅证明分析与展示机制。新方法真实forward=0，真实训练/梯度=0，源RGB解码=0，新方法真实资格分数=未计算。仅旧保存参考在身份打包时读取24476重复引用，合为12238唯一行；无新GT标注。

未来固定预算：1checkpoint，25758 forward=13520 native512tile+12238 cached128，338原图首次解码，0拟合/更新，GPU1/CPU1、3600s，RSS/allocated/reserved各4GiB，输出/固定包各6GiB，临时盘>=16GiB。不可为了补齐结果放宽上限或自动重试。原生float字段2.8035GB，cached字段.8020GB，32字段/参考约.276GB，另有6案例/表格/图与冻结收据；旧1.531GB RGB仅mmap，不复制进输出。流式解码/分块/逐图归约避免全数组驻RAM；全部预测与权重先冻结再解码参考。

512tile显存与总吞吐只是估计，尚未实测；服务器原图存在性、运行环境/共享GPU、磁盘与全部私有输入仍需执行前核验。Code Ready不等于Run Ready，也不构成实际执行授权。本轮未SSH、传送、公开推送或真实producer执行。E003/容量/弃权/正面积交集及封存地点保持；OOF/保留率/净收益为未执行，不写0或100%。

## 最终准备状态

24项源码绑定全部核验；manifest SHA256 `11c67539cadac809aa22efc8b74689fd3f54fe5b719be93c1f5df4b400d5a76b`。源码25成员包55074字节/SHA256 `2f6b9f39ad1498af02ee0fbe7e8b09ccba8e62a49877ac74f0ae56592bf5c3e0`已本地准备，9私有输入大小/摘要均核验，尚未传送或推送。精确包位置与拟执行约束见execution_preparation.md。当前active D7仍是待真实地点资格证据；不把设计/代码PASS作为定位PASS。
