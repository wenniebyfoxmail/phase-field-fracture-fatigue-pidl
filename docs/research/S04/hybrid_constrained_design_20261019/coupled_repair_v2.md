# D11 — 完整耦合求解修复，准备版本 v2

目的：使相同受约束增量物理问题能在原120秒内收敛，进而支持完整 FEM—神经混合方案；不以对称或放宽物理精度代替 FEM 接近度。

本轮：在已冻结的 Linux 控制器/全网格 PASS、物理成本 FAIL 后，按 HQ 的准备任务实现耦合修复并独立复审。本轮不 SSH、不 profile、不计算项目真实状态、不重试成本验证、不训练、不访问新 holdout。旧完整运行授权的实际成本条件没有通过；本文件及配套卡不授权新运行。

## 已知机制与未知量

`linux_validation_result_v1.json` 和独立18项证据审查保留：旧修复首步38.7332486883秒，相对 R1 的56.9524243856秒减少31.990167%；第2步仍触发原120秒。9次QP完成26.220273966秒，8次重平衡完成72.190923061秒，其中LU46.944362322秒已包含在重平衡内，不另加。第9次重平衡及其中LU未结束。

对已保存 work_trace 的嵌套块逐一计数：共同预测器1次assembly/solve/fresh、无新LU；8次完成的重平衡每次2次assembly、2次linear solve、1次LU、1次fresh，单次8.29–9.33秒。结合原机械停止条件（相对更新1e-9且trace符号稳定），这支持“每次机械重平衡很快稳定但反复调用代价高”的推断，不能证明跨耦合迭代active-set剧烈变化。旧日志没有每轮force/KKT/f残差、节点active/trace数组，不能补造收缩率或确定哪一分量阻止接受。

## 三条机制路线与选择

| 路线 | 作用点 | 预期观测 | 代价与决定 |
|---|---|---|---|
| 投影、受保护 type-II Anderson | 减少完整u–d–history map次数 | 更少完整map且原fresh联合检查通过 | 选用；新增完整候选可能更贵，无收敛保证 |
| 旧LU作为GMRES预条件器 | 减少重复LU | 相同map下更低机械耗时 | 暂不采用；跳过当前矩阵LU会改变原pivot1e-14检查合同，需另行设计 |
| 冻结/放宽active-set或trace阈值 | 改变分支切换 | 更少机械/外层迭代 | 暂不采用；现有证据不支持此病因，可能改变物理律或妨碍节点释放 |

## 完整map与加速公式

固定同一个 accepted old、载荷b、网格材料和原历史更新律。一次完整map先求 `u=E(d,b)`，从old重建trial history/f，求原全空间box-QP得到 `g`，再求 `E(g,b)`，从同一old重建history并执行原fresh力残差、KKT、边界和fatigue联合审查。记输出damage为T(d)，r=T(d)-d。机械warm-start和trace分支可能影响解，因此不假定T光滑、单值或已证明收缩。

用最多3个secant的type-II公式：

`gamma = argmin ||r_k - ΔR gamma||_W² + lambda ||gamma||²`

`d_AA = g_k - ΔG gamma`，其中 `ΔG=ΔD+ΔR`。

W是GP积分得到的正节点lumped mass，共同比例归一化；仅用于求解器外推，不是新训练loss。仅对窗口所有输出均非原lower/upper活跃的节点外推，其余保留当前完整QP输出；投影到**原accepted old.damage ≤ d ≤ 1**，硬预裂纹节点始终1。原全空间QP可释放其他活跃点，不能将当前迭代damage滚动当作不可逆下界。

固定工程保护参数：depth3；每物理步最多3个实际候选、1次拒绝后禁用；relative ridge1e-10；正则化条件数≤1e6；仿射系数L1≤5；修正mass RMS≤2倍当前固定点RMS。无稳定free节点、退化/过大系数等在物理求解前跳过。候选先走完整map和fresh审查；若已满足全部原物理接受条件直接接受，否则只有规范化全判据merit≤baseline的0.5才保留。0.5是本次运行前冻结的费用保护选择，不是从项目残差调参；不是新物理容差。

baseline若已物理通过则直接接受。否则保留完整baseline d/u/fresh审查和原生workspace LU对象/精确key。有效但未改善的候选恢复全部baseline和LU，清空窗口；不得混用候选history。真正QP/pivot/非有限值/120秒/证据写入失败原样终止，不当作可回退的候选拒绝。可行投影在eta=0下仍可能造成奇异；保护保证不提交无效状态，不保证一定成功。所有完整map（含拒绝）计入原max_outer100及同一个120秒，不增加时限。

## 网络与FEM责任、标签和诊断

FEM继续负责位移平衡、damage QP、约束、history重建和最终fresh接受；网络只给可行初始damage系数，不能提交状态。reference/classical/neural三臂共享相同耦合policy，label/certificate/fit/model receipt绑定同一policy ID；共同求解器收益不能归为NN收益。网络结构、输入、loss权重、预裂纹/二维初始化、材料与全部物理容差均保持原卡。

旧数据仍只够算子重放及state0初始化；旧R1和验证前缀各仅1个接受状态，不构成完整合格标签集。所需缺口仍为1200训练+600验证转移，测试reference/classical/neural各600，合计3600；1次fit。受保护加速可能改变非凸分支的迭代路径，最终三臂必须满足原场误差/history/f/reaction标准。

新增逐map `iterations.jsonl` 双事件 fsync：先在完整fresh返回后保存最小 `fresh_evaluation`（全部fresh标量/merit/物理通过与否），然后才运行数组诊断、外推提案、缓存操作并追加 `iteration_decision`。缺失decision绝不代表接受；inspector分别报告最近fresh与最近decision。v1独立复审用第二轮提案异常复现最后fresh残差丢失，v2新增该失败测试并修复顺序；原v1 MODIFY保留。每轮增强记录包含：原fresh各残差与merit、观测固定点/merit比、节点bound-active变化、输入/输出damage/u摘要、机械warm-start和trace摘要、history loading mask及f<1数量、提案baseline/下一map关联和拒绝恢复摘要。比值仅是观测，不是收敛证明。日志/哈希/提案计算全部计时；失写终止。旧完整块日志与控制器不变。

## 验证与完整执行安排（未来条件，当前不执行）

复用旧70项人工回归、18项保存证据复审、实际4个Linux控制器和5个保存全网格一致性结果，不再重复实际审计。对本次代码差量运行14项人工代数/单Q4合同测试及旧回归共84项；无项目场、profile或训练。人工map从21降至3次只证明外推实现可运作，不推断真实收敛/速度。

唯一后续执行决策：是否批准**精确复审后的新完整包**在剩余预算内一次执行。若批准，先确定fresh RunID/路径和实时资源身份，以同一完整producer的train_A前5子步为原位可行性检查；任何一个子步未满足原fresh条件或超120秒立即停止，无重启/恢复/重试。若前5步通过，则沿同一accepted链继续完整3600步/1fit，不另跑一遍profile再重启。前5步通过仅证明该前缀可行，不能保证全程。现有阶段顺序保留native replay；不另行重跑已通过Linux控制器/全网格控制案例。新耦合路径的实际收敛、日志成本和RAM仍未验证。

生产时仍需执行卡exact source/card/review绑定、Linux/runtime/输入身份核对、共享GPU实时准入、原守护进程及清理；准备卡schema不同且execution_enabled=false，不能传给producer作为执行许可。配套卡的`execution_template`保存准确原参数；未来需填实际RunID/根目录并获精确复审后才成为执行卡。当前不生成RunID，不连接producer。

## 实际成本、灵敏度与剩余预算

已知旧R1+两次validation累计617.323941530 wall秒、572.315113实际CPU秒、GPU0；按16核保守折算2.743661962 coreh。136 hosth扣除这些后余135.828521127h，12 GPUh未用。`prior_costs`仅按SHA绑定的冻结失败收据扣费，绝不能把失败当准入；validation01已包含在cumulative receipt，不能再次单列。已记录numerical340.000194962秒、其余shared277.323746568秒。早期准备/传输等未完整测量，以上不是项目所有劳动/费用的总额；后续全流程实际费用继续记录，不重置预算。

历史完成块的粗灵敏度（不是预测）：`T≈1.4+13.9*N完整map+9.0*N加速候选+C新诊断`秒。4map/2候选约75秒；6/2约103秒；8/3约140秒，均另加未知新日志及状态变化。加速候选通常额外需要自身输入damage的机械平衡。真实N未知，可能仍超120秒；不能先声明成本通过。内存增加少量O(Nnode*depth)向量及评估期间保留一份baseline LU，实际LU/RAM增量未知，原64GiB不变。

完整预算仍12GPUh（fit6/hybrid6）、136hosth/2176coreh（含以上已知成本）、16核、64GiB RAM、24GiB VRAM、primary/archive各128GiB、0retry。600步hybrid的6小时要求平均在线总费用≤36秒（含setup/IO的阶段账），不是120秒逐步上限即可保证。原quality：mean J≤.001、max J≤.01、history relative≤.05、f RMS≤.01、reaction relative≤.01；classical及NN都通过质量才比较NN至少10%在线加速，且f<1覆盖必须成立。离线标签/训练/先前失败成本单独计入break-even，不能只报NN推理时间。

结论：完整方案保持不变；本次改变耦合迭代初猜及其可观测性，实际效果待有授权的新完整执行证明。旧31.99%仅属于旧版本首步，cost FAIL和零训练/零完整标签仍成立。
