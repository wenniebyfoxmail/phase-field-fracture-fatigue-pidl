# 预裂纹与初始场对齐：最小准备方案（2026-10-18）

目标是使PIDL的完整位移/损伤场更接近既有同状态FEM数值结果。对称只作诊断，不以“更对称”判成功。当前只准备/检查/复审，未授权也未启动新训练或FEM；旧200步结果和旧E011判据均保留。

## 已实现的具体改动

`source/nodal_damage_alignment.py`新增一个默认关闭的节点映射，`SENS_tensile/field_computation.py`只增加可选入口。原网络、u/v边界映射、原能量/不可逆罚/优化器均未修改。

1. **硬预裂纹线。** 每次计算damage时，将原生网格中y=0、x∈[-.5,0]的251个节点设为1。其输出对网络damage的导数为0；线外仍可学习。FEM固定damage DOF集合必须与几何mask完全相同。
2. **相同初始二维场。** C臂只读已有FEM零载恢复场d0，不读c1s1/s2目标场。FEM共用初始包与原始state0逐点差≤2.78e-16，u=0、H/alpha_bar/q_prev=0、f=1。C初始输出及输入hist_alpha均为该d0；不继续使用已经回退的PIDL历史。
3. **可演化的初始场表示。** 固定原PIDL零载模型θR的raw输出rR，设a0=4d0−2，用旧nonsmooth函数s定义：

   `dθ = d0 + [s(a0 + (rθ−rR)) − s(a0)]`，最后在裂纹线上强制1。

   差值必须先算，确保θ=θR时初态在声明float32下逐点精确一致。d0/rR不随训练重新锚定。线外可以偏离甚至低于d0，原soft tails仍在；没有暗中加hard box或整场硬不可逆，也不把整个初始场永久冻结。

该表示含一个已知FEM初始空间场，**C−B是初始场/历史/参数化包的条件效应，不是纯粹换优化器初值**。初始自由点对raw的导数变为.25，和旧tail的.001可能不同，必须显式报告。若以后要进一步分离表示/梯度条件与初值，另设对应控制；当前不扩臂冒充已经识别这些贡献。

映射只接受相同顺序、坐标、dtype和device的完整原生节点。物理能量中的damage及其梯度都从映射后的Q4节点值重建，不能使用NN raw导数。未来独立空间探针和对称项也必须从相同Q4节点重建，不能直接套用旧direct-NN probe helper；当前已将这种误用拒绝。

所有坐标、mask、d0和rR必须随NN保存。只存旧net.state_dict会丢失这个表示，因此现有训练runner不能直接拿来执行；本包只有只读准备脚本，没有训练/启动入口。

## 已完成的零步检查

- 原始post-U0模型和checkpoint已读取；hist_fat、psi_plus_prev和psi_history_elem均为0，Q4 GP4/current_active/previous_accepted_nodal语义一致。
- 86756节点/86408Q4；B和C的251线节点均严格为1。C的初始输出与hist_alpha对FEM float32场L∞=0。
- 原FEM float64转float32的最大差2.97e-8；不同于“数值误差绝对为0”的物理/跨精度宣称。
- 线梯度0；自由节点初态梯度.25且可下移；默认u/v/d输出不变；错序/子集/任意探针/错误目标/错误映射被拒绝；锚定buffer独立复制并可序列化。
- 已运行38项确定性检查，无优化器循环。原PIDL零载hist与CPU重放输出差约6.88e-6，原值保留，不静默改写baseline。

[静态收据](runs/precrack_alignment_static_20261018.json)。静态图是按构造匹配初值的证明，不是加载后训练收益。

## 拟议最小验证：三个臂，全部关闭对称

|臂|裂纹线|初始输出/输入history|对称|
|---|---|---|---|
|A|原PIDL软约束|原PIDL post-U0保存状态|0|
|B|永久d=1|A，仅将线上的输出/history设1|0|
|C|永久d=1|FEM零载d0 + 锚定表示|0|

同一网络θR、u/v参数、网格、seed、原物理系数、正则和fresh RPROP；只拟议从U=0到**c1s1单个加载块**（U=.02999988），不走c1s2、卸载或完整轨迹。每臂最多200更新、三臂总预算建议≤1 GPU小时；这些是待批准的新预算，不继承旧两臂许可。history固定，各臂history commits=0，新增FEM=0。

A→B看硬线条件的条件收益；B→C看初始场/历史/表示包的条件收益；C→A看组合收益。顺序比较足够回答当前修复问题，不宣称相互独立的因果份额或交互项。

每臂保存目标载荷下update0与200的完整场、首步能量跳升及最大物理能量。离线评分同时显示两端：区分初始构造带来的接近与追加优化保留/扩大/破坏的接近。按固定200终点评分，不用FEM误差挑best checkpoint。RPROP不能保证单调下降或200步收敛，保留所有有限负结果。非有限、输入/线条件破坏或时间上限停止，不自动重试/加步数。

FEM c1s1只用于已保存输出的事后评分，不进入训练loss、梯度、buffer、初始化或终点选择。原FEM trial-f/staggered与PIDL committed-f/joint目标、不可逆实现仍不同；本次不称完整方程/历史算法已相同。

如果以后需要单测对称，再单列D=C+位移对称，与C保持其他条件完全相同，D−C就是对齐以后对称项的条件增量。当前D权重和native-Q4 symmetry runner未实现/未批准，不作为最小三臂验证的隐藏第四臂；不重用旧1%梯度配重为已验证规则。当前三臂全部sym=0，初始化收益没有混入对称。

## 以FEM接近为核心的评分

主读数为固定物理尺度下的联合u/v/d质量加权距离：

`Jfield = sqrt(sum_i m_i[(Δu/.12)^2+(Δv/.12)^2+(Δd)^2]/(3 sum_i m_i))`。

m是原生Q4正的lumped节点质量，Uref=.12、damage尺度1、三通道等权在测试前固定。这是透明的探索评分约定，不是物理真理或正式通过阈值。同时逐项展示u/v/d误差和贡献比例，分开线节点/自由节点damage误差，列固定前区x[0,.08]、|y|≤.04及x=-.25/0/.01/.02剖面。原生GP4 raw/active相对FEM L2、能量/力残差、box/回退与耗时保持可见，防止合成评分掩盖代价。

必须给FEM/A/B/C同状态u/v/d场、共同色标及有符号差。镜像残差是辅助解释，不选模、不替代FEM误差。已有状态均为已见synthetic development，不能称独立holdout或泛化/物理有效性结果。

## loss权重可以怎样改

当前最小三臂均固定 `log10(Eel+Ed+Ehist)+1e-5*R`，sym=0，FEM监督=0，PIDL gamma=16875。先分清边界/初始场影响，不同时扫权重。

|权重|能否改|应如何解释|
|---|---|---|
|对称、权重衰减|可单独对照|优化先验/正则；只有FEM场误差改善才有用|
|不可逆罚gamma|可单独对照|数值约束近似；向FEM421875靠齐可作为后续候选，但相同gamma仍不等于相同硬可行域|
|Eel与Ed相对系数|可改，但改变模型|相当于改变等效Gc/材料能量比例，不能仍宣称相同物理参数|
|整体物理缩放|需看写在何处|同倍数放进log只添常数，不加强梯度；乘在log外才改变它对其他罚项的相对作用|
|FEM场拟合项|可以成为另一条明确路线|直接监督/混合校准；不能训练并验证同一目标场，需独立评价；跨轨迹泛化需按完整trajectory划分|

若最终目的就是模仿FEM，显式FEM监督比盲调能量更直接，但必须单列监督信息边界。此次不把FEM c1s1/s2加入loss，也不加一个持续拉回d0的初始场loss，以免抑制正常损伤演化。任何新权重试验都在初始对齐后，固定其余设置，仅改一项，并事先写清参考信息/预算/输出。

## 复审与当前边界

Pro只审提交的设计文本，独立Codex只审精确补丁、测试和静态数据。复审可以确认准备内容是否自洽，不能证明加载后一定更接近FEM；本卡没有执行授权。结果位置和复审收据随后附入同一准备目录。

## Pro首轮意见后的明确补充（r2）

旧映射完整定义：r<-2时s=.001(r+2)，-2≤r≤2时s=r/4+.5，r>2时s=1+.001(r-2)。中心导数.25，尾部.001；r=±2在实际代码中归中心分支，autograd取.25，两侧导数不同。FEM d0必须有限且在[0,1]，不适用则停止而非clip；所以a0=4d0-2在中心分支，s(a0)=d0的实数恒等成立，数值仅有普通浮点舍入，中心差值保持初态精确。已补d0=0/1折点双侧响应、实际8x400网络代表性自由节点对output bias的逐节点梯度测试，而非仅看全域总梯度。

A/B/C物理梯度一律沿既有native-Q4 compute_energy路径：d_gp=N*d_nodes，grad_d=B*d_nodes；冻结d0/rR只是不对它们求参数梯度，空间梯度不能丢掉这两张节点场。小Q4单元测试验证raw恒定但映射d0非均匀时，实际grad_d仍非零且等于d0的Q4梯度。

原raw网络输入仅XY，Williams/enrichment/symmetry-prior/local-patch均关闭；加载量只在u/v物理边界映射。CPU静态检查改为捕获实际完整node batch的FieldComputation前向，不混用1024小批raw参考；非零U=.02999988下验证A/C的u/v逐位相同，C的damage与FEM float32 d0逐位一致。未来producer须在immutable θR、真实device/dtype/full-forward方式下首次生成并验证锚点，然后保存；恢复已训练checkpoint只恢复buffer，不在当前θ上重新锚定。CPU结果不是GPU同位证明。

三臂共同保留原零载hist_fat=0、psi_plus_prev=0、H=0、f=1；仅hist_alpha随三臂定义而异。固定history不固定当前g(d)，当前g和空间梯度仍随当前mapped d变化。原物理E=1,nu=.3,Gc=.01,ell=.01,w1=1,AT1,Amor split,eta=0,alpha_T=.5,p=2全部固定。完整损失为log10(Eel+Ed+Ehist)+1e-5*sum(weight²)，Ehist内含gamma16875；log内没有epsilon，非正能量停止。

评分固定Q4面积lumped节点权、物理u/v变换、既定窗口/剖面；raw/active按原定义用GP4/Jacobian权。若FEM参考范数为0，相对误差未定义并另报绝对误差，不暗加epsilon。所有输出不clip、不裁剪尾部、不按预测裂尖移动窗口。未来D必须与C从同一theta_R/anchor/history/fresh optimizer独立启动，不能从C终点追加训练后称D−C。

## 最终准备复审收口

- Pro文本设计复审：首轮要求补齐三个契约，r2关闭后REVIEW_PASS_SCOPED_TO_DESIGN；只审实际提交文字，未访问本地代码/数据。[原文](https://chatgpt.com/c/6ad4aa74-fe44-8328-80a4-1eb9982fdda0)。
- 独立Codex：精确实现2ecd8e78ea5ea149a3461ac861438702032f15e3，38项测试独立复现，实际static_v3和新完整forward锚定检查一致；REVIEW_PASS_SCOPED_TO_PREPARATION。[代码复审](runs/precrack_alignment_code_review_20261018.json)。
- 两项结论均不签producer-ready，不证明加载后FEM误差改善，也不是运行批准。训练runner未实现/未送审；本轮没有训练更新、history提交、新FEM或轨迹扩展。
- [静态构造图及阅读说明](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/precrack_alignment_preparation_20261018/static_v3/README_analysis.md)。
