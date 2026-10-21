# D18 R006结果：联合试探避开机械消元失败，但有限Newton射线仍停滞

目的仍是原train_A、自身历史、原物理精度的连续600接受态。本轮由HQ-FEM-JOINT-PROJECTED-TRUST-REGION-R006-20261021前瞻授权一项联合投影/有限信任半径原残差路线，非复用R5许可。完成实现、人工检查、原所选独立准确复审、准入、一次运行、完整取回与保存证据分析。**科学主目标失败：仅1/600，teacher与NN收益均未取得。** 原QP/机械/currentK-pivot/最终m_accept/真实f_solve-f_commit/单CAS历史规则未改。

## 1. 一次实际执行与耗时

冻结源`e01a69b5a0cad6ac4ce7670c76f159a9212bd232`，35源artifact`d1dc3da4db490e72ec5c49ef80227b5369bd3cf6a234446447e59d662134685f`，cardSHA`07126f393e8f1632d4ece83f211436cbf7a9d20c1de4e5dee15e008196b5ccb0`。必要人工数组/API/资源检查与独立复核通过不等于科学收敛。审核发现的费用说明、嵌套predictor父项归属、all-inf诊断先持久化均在准入前修正并重绑，无真实pilot。

原GPUServer8，fresh `pf_hybrid_solver_v9_20261021_r6`。两机械批总10.331942333秒；105440bytes公共源码控制包，98个公共OSQP文件980049bytes同机复制，原R3输入只读/新私有输入上传0。实际NumPy1.24.4/SciPy1.15.3/OSQP1.0.4/psutil7.0.0通过；4CPU/0GPU。UTC00:37:07.705单次spawn，00:39:48.788终态failed，4归属PID4058425/4058426/4058433/4058434均退出，无重试/续算/其他case或训练。

| 计量 | 结果 |
|---|---:|
| 接受/计划 | 1/600 |
| 第1步含IO | 57.129551881秒 |
| 第1步solver | 56.337471532秒 |
| 第2步marker至最后trace | 100.326613766秒，失败范围 |
| 第2步budget事件solver elapsed | 100.325315525秒 |
| case phase | 160.747991161秒 |
| producer | 160.749429795秒，包含phase |
| worker+guardian实测CPU | 194.573449秒 |
| GPU / NNfit | 0 / 0 |
| owned-tree RSS观测峰值 | 4484874240bytes，约4.18GiB |

逐case/子步全精度见case_elapsed_times.csv、step_elapsed_times.csv。失败步没有成功step事件，不能把trace范围标作完成耗时；producer/phase/step互有包含，不重复相加。guardian的unfinished-step是Python预算失败退出后的记录，不是300秒先到。新包4h自00:23:42Z起至04:23:42Z，旧known1232.4626276369672秒、R4保守4390秒、R5保守3056秒和旧缺测600秒reserve分别保留；没有归零或重复加producer。整包CPU未知，actual CPU与含准备/审核/取回/分析的日历扣额见completion_cost.json；后续收尾另作快照。

## 2. 这次实际改善与没有改善的部分

新的working objective是步初原正算子对角冻结权重的Phi，明确替换旧工作准则；绝不替换原m_accept。第1步用了3个块方向/3次试探、1次最终真实QP/机械认证，m_accept0.0035913、currentK pivot ratio0.00163910，原接受合同通过。第2步从自身首态继续，不拼接R3/R4/R5。

第2步15次fresh=初点1+联合试探14；8keep/6reject；8个块方向全部返回。**工作试探机械反解0次，step2最终QP/机械认证0次**，因此这次没有重现R5的候选先机械消元/pivot资格失败。相同old历史与原bounds/BC每次重建、拒绝不更新base或接受历史，实际向量与权重ID独立重构通过。

跨两步11个块方向均过原effective双行真残差及原绝对门。两步首块Ru右端约2.20e-15/4.39e-15，机械真L2约1.68e-17/1.52e-16，相对值0.0076679/0.0347129大于0.001，依**既有逐行运算舍入界**通过；其余点不依赖该放行。不能写“全部严格relative<=.001”，也不是本次临时放宽阈值。块方向精度与工作点物理平衡仍是两种资格。

## 3. 为什么先快降后停滞

Phi从3.401929939e-6下降至3.746504084e-9（约908倍），保留点严格下降。前两方向fullstep的rho约0.975/0.916；第3方向fullstep预测下降却实际上升（rho=-0.504），收缩后保留。后续较大试探反复失配：方向4的rho0.00806、方向6为-1.44573、方向7为-3.03803；较小射线步可以下降，却只带来很小进展。

最后两方向未缩放damage方向inf由1.2464增到2.4449；最后radius9.765625e-5、alpha3.99434e-5，实际d步inf9.765625e-5、自由u步inf1.00921e-5。最后预测下降2.99302e-13、实际1.52101e-13、rho0.50819。向量验证投影改变量仅5.54e-17，base14与kept15均0个全nodal-d1单元；最大非precrack损伤约0.94872→0.94876。**后期瓶颈已不是R5那种大幅box截断，而是当前有限Newton射线只能走小步。** 不据此断言切线奇异、条件数、谱或整个原方程无根；本次没有重装K或测谱。

最后Phi约92.84%来自机械分量，原forceL2=1.63887633e-5，仍为1e-8绝对门的1638.876倍；damage KKTinf1.13199533e-7也略高于原1e-7。工作目标小/下降不构成平衡，更不能只把失败归于更严格的内部认证触发。8方向后按前瞻规则首停，未到半径最小值1e-8，亦未耗尽300秒/100fresh/每方向8trial或资源界。增加方向会否成功未知，本次不继续检验。

另有一项效率缺口：方向3两次radius0.1/0.025都大于其方向norm0.0232145，alpha均1，outer4/5的实际u/d哈希完全相同；多做了一次相同fresh审查。该重复没有消耗额外块方向，不能当作8方向终止根因；唯一尝试已消费，本次只记录，不改后继续跑。

## 4. 成本瓶颈与可用物理证据

第2步不重叠trace root合计92.048708321秒：8个块LU46.470801949秒、solve1.038144289秒、fresh force8.930917752秒、damage assembly6.355056258秒、切线3.906722073秒；工作点/方向/候选持久化合计22.240720429秒。其余约8.277905446秒在已测step范围内但没有逐项trace归属（Python/矩阵乘/投影等不可据日志再分摊），不记0。不能把nested机械/IO子项再叠加。精细证据写入是实测成本，但没有取消本次已批准的诊断，优化它也不证明剩余物理残差会收敛。

完整162files/81832683bytes（整个新runroot+archive）逐size/SHA验证；原输入未复制。状态0→1/D13父链/latest version1与真实f_solve均核验；保存psi与原旧态重建A/r误差1.25e-16、f误差0，opaque不变，此为后验表示误差而非放宽接受。全部完成fresh仍f=1，没有真实疲劳退化/卸载覆盖。原命名output_equilibrated_u_id在joint trial只代表给定u的哈希，mechanically_eliminated=false；不能按字段旧名字称其平衡。

首接受态与R5有相同mesh/material/initial/load/cycle/substep等加载身份，但coupling_policy_id不同，不能称完整physical合同对象相同，数值亦不逐位相同：位移inf差3.81343e-6、damage1.66282e-4、driver/A3.32472e-5、f差0。仅作保存场描述，均是各自原规则下的有限精度结果；不能把case耗时差当同端点加速或孤立归因。完整可用u/v/d/driver场和load/反力/A/r/f演化都只展示0→1，联合working场单列，绝不凑成600轨迹/训练标签。

## 5. 收束与最小缺项

本有限radius-scaled projected Newton-ray策略在批准预算内没有到达第2步合格根，原600轨迹仍失败。实现/线性方向/直接联合试探/诊断得到可复用资产；当前数据不支持继续靠增加方向、时间或训练推进。R5故障路径已避开，但整个数值可达性缺口没有闭合，不能称数值teacher合格。

若将来重新开放同方程路线，承重缺项是能在约束下提供足够下降的**实际全局化/子问题设计**与原精度连续轨迹的可负担性；当前做法不解信任域子问题、无Cauchy下降保证，不能仅改一个半径或删除pivot救结果。是否需要受约束子问题、其他求解表示或资格合同复核，现有保存记录不能替代前瞻设计/独立审查。此处只列缺项，没有实施或授权R007，不扩loading/property、不给NN训练标签。

四幅PNG/PDF与同stem来源说明、完整trial/force/block/trace CSV、原始清单在本地case的analysis/与recovered_verified/。analysis_manifest.json绑定最终脚本/派生数据/图证；evidence_review.json为原渠道保存结果独立复核，静态通过与科学失败分列。原R3/R4/R5负结果及费用全部保留；原Obsidian报告、mesh笔记与Roadmap登记D18终态。

## 6. 图证入口

![R006联合工作目标与原物理残差](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v9_20261021/analysis/r6_globalization_trace.png)

左上Phi保留点持续下降，右上全部15fresh的原m_work始终未在第2步合格，底排是所有14次试探的半径/alpha和rho。支持有限射线后期进展不足，不支持工作下降等于物理接受。

[同载荷未接受u/v/d工作场](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v9_20261021/analysis/r6_last_joint_fields.png)／[完整可用0→1接受字段](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v9_20261021/analysis/r6_accepted_prefix_fields.png)／[可用反力/A/r/f演化](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v9_20261021/analysis/r6_available_prefix_evolution.png)。各图同stem说明与PDF在同目录。
