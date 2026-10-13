# FATACRACK 固定1000cycles历史增量验证——条件协议草案

状态：`DRAFT_BLOCKED_QUALIFICATION`。2026-10-13。未分配producer/Run，未拟合或训练。
用户要求“条件满足后”形成可审核协议；本次裂尖误差与试样谱系条件未完全满足，因此本文件是可供审查的设计候选，不能作为已冻结执行协议。
冻结前须解决`fatacrack_qualification.md`的谱系、相位/参考、目标误差与cycle导出问题，并独立审查新的Experiment ID、代码/data/protocol绑定。保持既有来源审计的development曝光事实。

## 一个有界问题

在当前DIC裂尖投影位置、最近增长率、当前boundary幅值和名义载荷相同的信息基础上，增加两次更早的boundary幅值历史，能否降低同记录未来1000cycles的tip-x预测误差？
证据域controlled-experiment；C3候选。目标是发布标签的x投影，不是曲线路径弧长、裂缝萌生、RUL、相场损伤、道路或独立试样总体准确度。

## 信息与样本

- 预测起点为cycle N的min/max图像对及DIC处理完成后；完整允许信息均截至N。
- 目标Δx=x(N+1000)−x(N)，mm。实际cycle键连接，不使用行号替代cycle，不把999跨度改为1000。
- 可用窗口须在N−2000、N−1000、N、N+1000都有finite直接target与四个boundary通道。不插值未来标签，不补初始无标注cycle列。先按结构锁全eligible列表，不按目标大小/预测误差剔除。
- 当前结构候选F379、FF107origins。强重叠窗口是同记录相关数据，不是486独立样本。两种load与记录身份完全混杂；不宣称分离材料与load的因果作用。
- future load只允许明确持续的名义恒幅协议。未来实际测量值、CGR/SIF、完整trajectory标准化、双侧滤波及未来tip驱动ROI都禁止。

## 候选固定表示

每个记录使用固定x∈[1,49]mm的top/bottom节点，无需插值跨记录网格。
两项response：c_open=(mean(Δuy_top)−mean(Δuy_bottom))/ΔF；c_shear=(mean(Δux_top)−mean(Δux_bottom))/ΔF，mm/kN。该表示消除共同平移但不自动消除旋转或view高度差，参考/刚体操作需在冻结前确认；它是响应特征，不是可辨识的物理刚度。
F/FF分别名义ΔF13.5/20.25kN，仅在实际load声明确认后使用。

M0输入：当前x,y；最近gx=[x(N)−x(N−1000)]/1000；cycle N；当前c_open,c_shear；名义load。
M1在M0上增加c_open/c_shear的两段因果差分（N对N−1000、N−1000对N−2000）。不得额外增加过去tip-x而将收益混称为response历史收益。
同一低容量ridge候选：训练前缀内zscore，常数列剔除规则固定，intercept不惩罚；候选lambda=1、无搜索。仅预测Δx，不clamp/强制单调。冻结时说明该选择不是从F/FF新预测结果优化而来。

## 必需对照和时间切分

- B0 persistence：Δx_hat=0。
- B1 last-segment secant：Δx_hat=x(N)−x(N−1000)。
- M0 vs M1同origin、同split、同预处理/惩罚规则；只改变更早response输入。
- 候选按每条完整记录的eligible target-cycle排序，前70%为fit前缀、后30%为rolling评估尾段，边界算法使用floor并在冻结时给出exact origin清单。没有随机帧split、bootstrap窗口或跨记录混合。
- 尾段内过去的实测观测仅在其cycle已经到达后可进入下一origin；这是rolling one-step，不是自主rollout。
- 两条记录分别拟合/评估，仅作两个描述性within-record结果。来自不同载荷的另一个记录不充当“独立重复证据”。当前尾段已development-exposed，不标为blind confirmatory。

## 主criterion和结论

一个主描述量：每条记录MAE(M1)−MAE(M0)，并报告两记录等权均值；给出B0/B1和全部尾段轨迹作为同信息control与failure view。若M1仍劣于persistence/secant，不宣称有实际预测价值。
物理意义的success margin必须从独立reference/repeatability与可达到误差量级事先校准；当前没有这个信息，**不定义物理PASS阈值**。不能把负号或大量窗口形成的窄CI当成一般科学支持。
只有两记录不提供总体显著性、可信跨specimen置信区间或泛化证明。标签预测改善不等于超过物理测量误差，也不证明Takens完整嵌入。

## 停止与最小证据

身份/相位/时间/参考不清→不执行；误差没有资格化→保留当前草案或另行明确降级，不默认为通过。
正式执行前：新Experiment ID与protocol revision、fixed data identity、exact origin/split表、origin-only特征验证、最小静态测试、绑定commit的独立只读代码审核、训练producer授权。
将来允许执行时证据至少包含全origin predictions、两record MAE表、scope/exposure/units明确的对照轨迹图、README_analysis、Run receipt与独立evidence review。
失败后不得对尾段增加lag/模型/clip或改split来救结果；新问题须新revision/Experiment。当前训练次数为0。
