# E011 c20：隐藏物理度量／头部消元的真实接口适配准备

2026-10-20，延续[数学组件](pidl_profiled_hidden_preparation_20261020.md)，不替代原结果。
**本轮已实现本地适配代码，不是新的真实c20结果。** 没有SSH、真实数组诊断、真实训练网络实例化／forward／autograd／optimizer、新FEM或新留出。

目的：把已有方向诊断落实为一个能与原PIDL比较的候选，解释优化方向与局部可达性的责任；
不是再训练固定隐藏特征UV头，也不接管D013/E034/D6/D11。原894884af诊断、d1edbeed数学准备、15项原检查及历史负／未定结果保留。

## 本轮接好了什么

| 组件 | 已实现的本地代码 | 必须留给未来真实环境验证的部分 |
|---|---|---|
| 真实网络接口 | `_Encode`直接调用已有`net.encode`；`torch.func.functional_call`只替换隐藏参数，不构造新架构，不原地改源网络；各隐藏tensor的初始可逆缩放固定 | Linux/Torch对8×400与其激活函数的functional／二阶AD支持、内存与耗时 |
| 原UV边界 | 复现原`fieldCalculation`的算术顺序，启动时与原函数比较≤1e-12；拒绝Williams／ansatz／exact／symmetry／patch路径；非自由DOF受保护 | 真实输入上的逐点一致性和固定边界变化≤1e-12 |
| 实际Phi动态图 | 初始Phi/T直接用旧加载对象；`Phi(theta)=Phi_saved+(D(theta)−D0)T0`；仅D0/Phi_saved/T0为常量，D(theta)继续求导 | 锚定场与安装raw头后的真实NN字段并非天然相同，不能把该图本身的AD自洽当成验证 |
| J/JT/C/CT | 在同一当前raw UV头、局部增量z=0处求J；C由`B(theta)ᵀR.detach()`求导，不重复加入B′z；JVP不支持、图被detach或反传失败即停止，不用零填充代替 | 真实双向伴随、实际full-current重建／闭合后的FD |
| 原生物理切线 | 只对自由位移叶子求固定FEMd的`LocalProblem.parts`弹性能、力和K；固定物理图内复用K反传并显式释放；头H复用旧`HiddenTangent` | 原生H与BᵀKB一致性；Amor存在精确zero-trace即先停，不偷换AD Hessian与广义切线 |
| 有限真实试探 | 复用`build_full_space → persist_space → correct_full_head → persisted_readout`；每候选完整当前SVD、头部再闭合、实际NN读数，再回滚源状态 | 同秩并不足以自动验证动态图导数；真实reprofile检查仍是必需条件 |
| 候选与证据 | 隐藏试探weights、当前Phi/T、实际候选weights和读数字段绑定hash；固定d/history/B0/damage输出行/UV检查后才标fixed_state；回滚后另写证明 | 若旧helper在中途失败，保存已有证据但不把缺失候选当成功 |
| 接受／安装 | 原E数值不增、Ru严格下降、实际Phi头g∞与有限实现误差均≤1e-10；候选对象／weights／Phi／T／q身份一致，再安装并实际字段复读 | 候选政策不等于旧>1e-10科学能量收益，更不等于架构容量或演化闭合 |

代码：`tools/s04_e011_analysis/profiled_hidden_adapter.py`和`profiled_hidden_e011_runtime.py`。
它们无CLI、无模型／数组loader、无producer启动副作用；旧worker、默认设置及核心算法文件没有改动。
旧Newton每候选最多10步，低于上一准备提案12步上限；使用原Cholesky及1e-6相对解残差规则。
不声称已加独立条件数门：正定但病态的H仍须通过实际解、伴随、FD与实现检查，失败即停，无ridge/伪逆/补秩。

## 强制启动前顺序

1. 未来只在批准后的Taobo新目录，以最终源码／环境／六份旧输入hash为绑定；原始B0仍由
   `make_smooth(original_model)`创建，再加载e2dc61d5初态；旧actual Phi/T零状态不重建、不SVD。
   `verify_source_assets`提供六资产字节/hash核对，不加载数据，也不构成执行许可。
2. `startup_checks`对原真实NN做三次同actual-Phi读数，先保存再检查原场≤1e-12、E≤1e-10、头g∞≤1e-10，
   验证源权重、FEMd/history/f、B0和UV未变。此段不是本轮执行内容。
3. `Runtime.form_chart`复用旧头H和native自由力图。`probe_algebra`作两条seed173固定方向的J/C/U/Q/Z伴随与H/BᵀKB检查
   （预定abs1e-10＋rel1e-6），不以这项代替真实NN导数验证。
4. **必须**调用独立实际`Runtime.trial`的完整当前基底重建／头部闭合／实际字段回放。
   两条seed173单位方向，各取±1e-6和±0.5e-6，FD与Qv误差≤1e-10＋1e-4×max(norms)。
   每次Phi持久化；秩改变、头不闭合、实际实现>1e-10、source回滚失败或实际FD不一致即首停。
   不强制旧秩、不拿锚定图自身的差分替代真实full-current检查。
5. 只有上述完成，`one_macrostep`才生成一个物理度量／残差共同方向并试固定4个alpha；
   每个有限候选仍完整真实reprofile，最后按时间顺序接受的闭合态为终点。没有真实source/profile证明不能promote。

reprofile差分不是“零工作”：会在内存中改变隐藏试探并重新求头，但**不接受隐藏更新，不提交历史**，
每次均持久化后回滚。未来最小必要真实验证正是第1–4项，限300秒；本轮没有运行它。
边界上的ReLU/Amor不可微性、截断子空间随参数变化及浮点放大只能在该真实检查中判断，不能靠静审承诺通过。

## 一次未来比较卡

[禁用候选卡](pidl_profiled_hidden_adapter_card_20261020.json)给出17份源码内容绑定、原六份资产路径/字节/hash、
固定c20s4/raw99/FEM outer18状态、比较对象、唯一主读数、资源及首停规则。旧数学准备卡不改写。

- **A强对照**：复用原tight-coupling的head8和17阶段，source137cb031；不再跑固定特征头部臂。
- **B候选**：同一个e2dc61d5共同初态＋a698ec7b实际Phi，最多4个被接受宏步；每步保留隐藏缩放，
  使用ZᵀKZ物理度量、包含C的Q、能量／自由残差共同方向；active不进入训练方向。
- **唯一主读数**：最后有效B终点的`Ru_B/Ru_A`。这是探索性比较，不新增看过数据后的成功阈值。
  至少一个真实闭合隐藏宏步才报告候选比较；共同初态同时作为零更新对照。原初态Ru本已低于A，因此主比值<1本身不证明新增收益，还须并列Ru_B/Ru_initial和E_B/E_A，区分避免原不良校正与实质改善。
  原能量margin>1e-10及原两block基准继续单独报告；E、梯度、UV/H1、active积分／加权relL2／相关性和场图是解释量。
- **有限总量**：300秒准入＋1800秒候选＋600秒局部有界见证＋300秒读数＝3000秒；全阶段共享
  316次能量／force字段、JVP/VJP各768、C/CT各256、native K2048、头组装／factor各50、三角解4096、
  raw前向4096、显式头乘积1000、SVD50。旧helper边界的前向/SVD/读数/组装/解均单独计数；
  任一先到则停，不能保证完成4步，不借余量重试。
- **资源提案上限**：RSS24GiB、GPU allocated24GiB／reserved26GiB、新输出24GiB；未来至少28GiB空闲VRAM且无冲突训练才可考虑准入。
  这不是实测峰值或GPU当前状态。Guard只提供进程内检查；真实producer整包仍须接外部硬watchdog，不能把Guard当硬deadline。
- **首停**：身份/固定项/资源/非有限异常、同actual-Phi读数失败、rank变、Cholesky/原解残差失败、伴随或真实reprofile-FD失败、
  图／二阶AD不支持、头／有限NN实现失败、候选身份/回放/回滚失败、CG未解准／无共同下降／四alpha均未接受。
  无SSH重连、改阈值、加预算或换host的自动重试。

未来outer producer使用本地入口的顺序须为：哈希与环境核对→旧对象创建／原生算子检查→三次actual-Phi读数→
最多4次`one_macrostep`（每次新Runtime，保留初态scales与初始物理半径）→独立局部见证／场读数。
每步需闭合后重新绑定该步Phi与源状态；首个Runtime只接受旧共同初态，不从head8开始。
还须将阶段硬时限、峰值RSS/peak allocated/peak reserved/输出字节遥测、所有helper源码完整bundle与最终commit接到归属明确的producer launcher。
这些宿主层接线与真实环境稳定性尚未验证，因此本卡`execution_enabled=false`、无RunID和launcher，不能据此直接执行。
A/B改变消元、度量、残差选择与工作分配，只能评联合策略，不作等成本或单一开关因果声明。

## 本轮人工检查与结论

人工检查范围：旧15项数学测试、移动基底与二阶AD／detach拒绝、真实接口模拟的固定边界／自由DOF、
C/CT与Q伴随、锚定图内部通过但实际profile不通过、rank/退化/有限误差首停、源状态／试探／回滚／安装与hash绑定、
budget代理及文件记录。所有模型对象均为小型多项式／模拟callable，**不是实际8×400**。
[精确差异复核](pidl_profiled_hidden_adapter_review_20261020.json)记最终文件哈希与检查结果。

结论：从数学组件推进到了现有E011真实API的本地适配代码及可审阅比较卡。
下一项最小必要真实活动是单次300秒、零接受隐藏更新的真实source/Phi/AD/内存/reprofile准入，
须在最终完整producer包另经审批后进行。没有新的PIDL能量、残差、active改善或网络容量结论。
