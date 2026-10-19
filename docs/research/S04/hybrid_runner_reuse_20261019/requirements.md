# 完整混合运行包复用验收范围（2026-10-19）

目标：继续PIDL实质接近FEM的受约束混合路线，复用原owner的已审库与唯一runner实现，补齐可审阅的完整运行卡和独立代码复审；本对话不训练、不新增FEM、不执行补充FP64。

当前D8：整套producer编排及准确运行卡准备/复核。原D7库/API审核不自动等于producer-ready。
原owner为「PIDL 上翘诊断与改善：完整物理场」（01a14bbc-c8fd-7bd2-85fe-e0d6cbadc85d），
工作区 `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018`。
继承已审库 a76825eb2fdc750557b5a4c0bb2d542d2ee11c60、交付文档e59a0643，
不另写重复producer，不修改原owner工作区。用户已逐字批准一次内部协调消息并已发送；该消息没有授权新计算。

## 最终交付核对

1. **代码/身份**：runner、数据适配、训练/推理入口（未来执行）、监督器、恢复、成本账本及准确卡绑定同一不可变commit/文件SHA。旧库未改部分复审结论沿用；改动需焦点审查。默认只检查/准备，不能因打开卡或调用help进入求解/训练。
2. **原生算子与初态**：固定已见common_initial及5个c1候选来源；输入完整hash、mesh/GP顺序、crack和state0指纹。原生位移/力为blocked布局，新后端交错布局，显式排列转换并核对BC。operator回放只重装配已保存场，不新求状态；通过不自动认证标签或疲劳反馈。原state0角色和资格与学习标签分开。
3. **物理尺度**：E1/nu.3/Gc.01/ell.01/thickness1、AT1/Amor、eta0、alpha_T.5/p2、w1=Gc/ell=1。说明坐标/位移/能量/力/梯度单位及固定normalization，不能只填无来源的scale=1。匹配旧FEM的参照与新节点K问题分开。
4. **接受标准**：继承D7工程候选 force_scaled≤1e-8、KKT及projected≤1e-7、bounds/BC≤1e-10、fatigue一致性≤1e-8、QP eps1e-10；最终卡须明确force_scale/damage_gradient_scale的物理来源和最终适用范围。保留原始残差。不能把新标准改写旧协议、把metadata通过当数组资格，或让结果后调阈值。
5. **历史/提交**：trial每次从同一不可变接受前态重建A/r/f，节点lower固定为前态d；只有最终同u/d/f的fresh力/KKT/边界/疲劳检查通过才单次CAS持久化。opaque原样保留。卸载driver不是历史峰值。
6. **失败/恢复**：solver/时间/内存/存储/身份失败停止受影响路径，无自动重试、eta/容差/步长/轨迹改变。替换前写失败保留旧态；replace后fsync失败为outcome uncertain，先核对durable指纹/version/CAS与预算日志，不假报回滚、不盲重跑。锁不自动删。恢复须相同代码/卡/数据及累计预算，不重新计时。
7. **三组对照**：NN-off直接受约束FEM（前态初值）、经典可行外推、冻结NN初值，统一后端/硬件/精度/接受标准。经典外推的公式、卸载/零delta处理须准确固定；后两组各用自己的接受history，不能参考轨迹teacher forcing。随机/无训练manifest模型不得当NN组；回退次数、原因和成本显式记录。
8. **完整阶段**：先同问题NN-off标签/参考，再单fit/validation选择，再测试的三组完整自演化及评价；数据依赖与输出hash逐阶段锁定。当前0已认证标签、0训练模型是实在前置缺口。运行器要包含未来训练编排和明确的训练loss/归一化/mini-batch策略，或如实标注尚未具备；不能将仅有NN-off运行器称完整方法验证。
9. **分组/评价**：沿用预算v2四幅值0.8/1.2 train、1.0 validation、0.9 test，各≤120×5子步；单fit/seed、≤20000updates，不扫描、不用test选模。闭合字段、疲劳f<1覆盖、分支差异、裂纹形态与全成本一起报告。NN附加价值必须相对同问题直接FEM及经典外推，不能把物理校正收益归给NN。质量匹配与成本比较规则在开test前固定。
10. **总预算**：≤3600数值子步、数值CPU120wall h＋setup/IO/analysis4h＋GPU阶段host12h=136wall h，单共享≤16core池/≤2176core h；GPU训练8h＋特征/冻结推理4h=12GPU h，同期≤1卡/24GiB；RAM64GiB、主/归档各128GiB。是未profile的上限，不承诺完成。记录实际wall/CPU/内存/GPU峰值/存储及失败开销，不能只计NN forward或重置账本。
11. **外部硬限**：原生稀疏调用不可中断，必须producer外部watchdog覆盖总预算、超时、descendants及durable恢复；kill宽限也纳入上限。监控只管理本任务新建进程组，不碰共享账号其他进程。资源可用性需未来现场核查，本轮不SSH占用。
12. **当前权限**：runner和卡可完整准备/轻量mock单测/独立复审，但本对话execution_enabled=false。准确执行包的参数、状态、数据、producer与预算确认后也不能自动启动；另一对话的运行许可不在本对话复用。

最终记录应区分：工程检查/算子回放/标签资格/producer-ready/科学执行与收益。已有5个候选且0合格标签不是新增FEM需求已经获批；任何执行缺口都要明写，不靠占位符或随机网络补齐。

## 焦点代码复审要检查的执行风险

- 求解器缓存首次公共mechanical predictor作为训练特征来源时，保存其真实u_pred/psi_pred而非另解或使用最终/参考位移；记录context额外组装/IO成本。任何额外数值工作必须进入总成本。
- 失败phase、watchdog宽限、setup/admission/IO及监督器开销不能在成功返回前才记账，导致失败时累计预算消失；峰值RAM/GPU/磁盘和受影响durable版本都要留存。
- 原生Sparse调用的软wall检查不能代替外部硬上限；总时间与kill宽限的关系要明确。
- 三组对照都要显示质量/branch/fatigue覆盖和全字段；不能只给NN组J门槛，再用质量不匹配的经典组成本作同精度速度结论。
- 复审绑定代码closure、卡、输入manifest与运行环境，不仅是hostname或可任意删减的source列表。read-only check不得启动物理worker。
- 不把运行器只有NN-off/无模型占位阶段称“完整三组”；只要缺fit、训练标签和冻结模型，准确卡必须以明确阶段依赖关闭NN执行。

这些是待最终不可变代码包核验的风险，不是对原owner尚在编写的草稿给出的故障结论。
