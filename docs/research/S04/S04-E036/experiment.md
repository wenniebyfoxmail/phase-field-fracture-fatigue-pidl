# S04-E036 · 循环 PIDL/FEM 离散设置修复与差距归因

## 实际进展（2026-10-25 20:25 UTC）

**当前控制状态：用户已直接答复新的续传审批“请继续 移除所有limit”。原剩余四项评分及原条件下的一次C0释放恢复授权，累计、传输、回收及每作业墙钟上限取消。原科学阈值、预定迭代/数值停止、共享机器串行和新失败不自动重试保留。pidl_history_audit已接回唯一GPU5执行权；正在准备独立无墙钟控制版，随后核查并续传。原D3 c1评分已完成，不重跑；旧partial、失败收据和封存payload原字节保留。尚未把恢复授权或准备完成说成远端已启动。**

阶段 A 已复用 timing owner 的真实 disabled 双解与四态 116/116 核验；未重跑。原始 P0 已在 Taobo 完成 12 态原 checkpoint/映射零更新重读并完整取回；这不是历史训练时 GPU 场的逐位重现声明。P0–F0 十二态平均 J=0.01389757549。

主 FEM c1 的 s1/s2/s3 接受并读回；s4 跑满 1500 外迭代仍失败，s5 未执行。s4 最终 Ru=3.6220152042e-5，是限值 36.22 倍；末 100 次呈稳定奇偶两值，失败未提交历史。不重试该主窗口。主 c83 已完整接受五步并取回55个原始文件；c20s4/c60s4 的存档前态分别以机械残差21.84倍/7.81倍限值被拒绝，原生求解未开始，不补建历史。strict c1s4 已于05:04:47 UTC自然终结，1500 outer后严格验收仍失败、无历史提交；后续四态严格参考与nodal oracle现已全部结束，结果见下方终态节；不能替代失败的主参考。

参考变化单独报告：固定 P0，c1 已接受三态平均 J 从0.00558470变为0.01502807；c83五态从0.01882949变为0.02489191，主要变化在c83s4（0.02367830→0.05145631）。这些数不是 PIDL 修复收益。证据为 `analysis/p0_f1_f0_c1_accepted_prefix_20261023.json` 与 `analysis/p0_f1_f0_c83_20261023.json`。

D3 c1 两臂均在s1的2000次更新后拒绝，零历史提交；2000个loss与10个块指标完全相同，f差为0。Ru=.00270184，且存在愈合与负损伤，因此该态无可辨识的步内疲劳修复收益，也没有已接受轨迹。D3 c83于22:28:27结束，两臂均在s1的2000次更新后拒绝，零提交。步内更新使f最大差从.0333918降到.0101502（约69.6%），但Ru从.00433903变为.00441736，愈合幅从.0533845变为.0547355；不能计作已接受复现收益。真实metadata已取回，详见 `analysis/d3_c83_failure_diagnosis_20261023.json`。

四份D3拒绝末态保存字段也已取回：原terminal_failure没有context，已逐张量确认最后outer@2000与terminal的权重、旧态、固定f、状态键和工作量完全相同后，才提取既有u/v/d；没有新forward或物理装配。c1s1两臂场逐字相等，J=.0009264810995；c83s1 P1/P2的J分别=.0083610595671/.0093011103179，步内更新的诊断场差反增11.2432%。这不产生接受轨迹收益，十二态总体改善仍不可计算。证据 `raw_archive/d3_saved_terminal_fields_20261024_transport02/transfer_receipt.json`、`analysis/d3_saved_array_contrast_20261024.json` 与 `figures/d3_saved_field_contrast_20261024.png`；原Obsidian mesh笔记已写回同一结论。

c83保存场的通道/空间分解进一步定位到damage：P2的u/v平方误差均稍降，damage平方项从6.12619e-5增至7.84251e-5，抵消了位移改善；damage占P2总J²的90.65%。约3.99%集中面积的`|y|<=.02`带承载94.36%的damage平方误差。该分解是已保存场的描述性统计，不是网络表达下界或机制因果贡献率。证据 `analysis/d3_c83_damage_localisation_20261024.json`，图 `figures/d3_c83_damage_localisation_20261024.png`；未进行新网络计算或物理装配。

D4 c1s2四臂各2000次更新已完成并全量取回端点，均未通过物理检查。L+/L0/C+/C0的机械残差分别为.00572262/.00634259/.00156178/.000990620；纯保存数组J分别为.00906525/.00900829/.03797762/.03795155。加入clamp消除了约束违反但场差扩大；两clamp臂全部86756节点d逐字等于旧damage，raw全部处于下界或以下；已保存force诊断确认4646个可行增损伤下降方向被挡，覆盖100%的该末态phase KKT平方，暴露出投影饱和的优化障碍。不能以残差降低宣称场差改善，也不能以此证明原网络表达不足。详见 `analysis/c1s2_matrix_saved_array_diagnostic_20261023.json` 和 `analysis/c1s2_matrix_clamp_activity_20261023.json`。

c1s2 原结构全参数 float64 seen-target 拟合已于00:32:06 UTC正常结束，6863.3217 GPU秒；3448个L-BFGS accepted steps/7552 closures，无RPROP。停止原因是`fit_stagnation_no_capacity_lower_bound`，最终Q=.00931208230、J=.00267592032708、G=.00891932325、maxd=.12479720；Ru=.04426245、phase KKT=12.2390、愈合幅=.01685788，physical=false、零历史提交。同一原函数族实现了更近的场，但拟合数值停滞不证明容量下界，且该监督结果不能计入physics-only改进。最终字段已完整回收；其combined receipt通过已有fit归档引用复用大文件，不能假定所有字节都在combined目录内。

c1s2 C0 continuation随后于00:36:58 UTC正常结束，新增285.3484 GPU秒。累计5200 RPROP、26 L-BFGS步/89 closures、25次系数刷新，停止为`fixed_f_numerical_stagnation_not_stationarity_proof`；全float64末态Ru=.00075754433（757.54倍限值），phase KKT=6.1117222e-5，feasible=true、physical=false、零提交。保存数组J=.03794910145，相比首段.03795154582几乎不变；全部86756节点d仍逐字等于旧下界，86505个raw输出低于旧下界，最大埋入深度从.761506增至.899415。保存参数物理梯度L2=.0208405并非零，因此数值停滞不能改称参数驻点。

终态保存force诊断仍有4646个被clamp挡住的可行增损伤方向，承载全部phase KKT平方；f_solve=f_commit=1、全部历史/f差为0。该机制证据支持解除平坦区后再检验同网络的物理下降，不等于解释全部机械残差。综合来源为 `raw_archive/d4_c1s2_combined_terminal_20261024_transport01/retrieval_receipt.json`（SHA e08056c0c431861da5f5570c5a426d9ac80f2c2d63958e4f5512824e4030b0c6）、`analysis/c1s2_continuation_final_saved_diagnostics_20261024.json` 和 `analysis/c1s2_completed_endpoint_comparison_20261024.json`。图 `figures/c1s2_completed_endpoints_20261024.png/.pdf` 已检查排版；只读取保存数组/既有检查，没有Mac网络或native重算。

resident已继续运行：c1s4/c83s2四臂matrix分别于00:45:43/00:54:11 UTC正常终结，各507.1768/501.8752 GPU秒；八臂均physical=false，C臂feasible、L臂infeasible。metadata及八个终态字段已回收；c1s4仍无合格标准F1目标，不给J。c83s4 matrix也已于01:02:43.519 UTC正常终结，新增500.2447 GPU秒；01:19:58实际队列回执确认已进入c83s2 fit、无halt，后续c83s4 fit和既定评分仍由原GPU owner负责。该处01:17:14/outer639为历史运行快照；strict的真实终态与F2后续见下文。

c83s2已完成纯保存数组同F1比较：L+/L0/C+/C0的J分别为.00965253/.01136726/.00191553/.00196692，四臂仍全部拒绝。与c1s2不同，此态clamp的诊断场差更小，但两C臂全部86756节点d=old、86505个自由raw低于old，最大埋入深度分别1.001206/1.005470。F1本步仅4860个节点增损伤、最大增量.0151966，故不增长damage也可给出较小平均场差；C+/C0剩余J²的92.45%/88.94%来自v。不能由小J宣称已正确推进损伤，也不能把该态clamp场差收益算成已接受改善。尚未用该纯数组分析推断blocked下降方向或KKT占比。证据 `analysis/c83s2_matrix_saved_array_diagnostic_20261024.json`（SHA 87d7d5cf6bdb9528f8bc72b03e416aa4d777fd89d0263d9551769a20b07d4692）。

c83s4四臂2000更新首段的J为L+ .01378121、L0 .01839499、C+ .05106521、C0 .13748788；均物理拒绝、零历史提交。C0的86756节点d仍全部等于old，C+也仅2节点增损伤（最大.00017915）；F1目标本步有6318节点增长、最大增量.9984823、面积RMS增量.01936208。两C臂的raw下界最大埋入深度约1.00。与c83s2不同，这次遗漏了更大的目标损伤变化，位移偏差也更显著：C0 max(v)=1.114756（F1 .146234），v最大绝对误差.994812、承载94.81%的J²。C+ max|u|=.037695（F1 .005483）。这些是实际字段统计，不把F1最大增量当作网络表达下界。

c83s4 C0的fresh Ru=1.37633324、phaseKKT=.44913411、f_solve到fresh_commit差=.98603812；C+对应.00521242/.00059803/.18541394，L+/L0的f差也达.131926/.251356。C0末200更新后Ru从.00841720升到1.37633，未形成力平衡或疲劳系数固定点；不同块使用不同f，不能把跨块能量读数当作同一目标的下降轨迹。任务exit0、2000步完整结束，属于已声明首段的科学未收敛，非技术故障。不能将本态失败仅概括为clamp饱和，也不能将c1s2对L2的小效应推广为所有态均无影响。证据 `analysis/c83s4_saved_block_checks_20261024.json` 与 `analysis/c83s4_matrix_saved_array_diagnostic_20261024.json`（SHA c2ccb564810ef099935e764406966fbf1950dd8b0ae93e45f40eb4615d531bde）。

四个预定独立状态×四臂的首段现已全部完成，物理接受0/16。因此原“C0四态通过后再运行其自身c1/c83窗口及中期端点”的条件未触发，该依赖分支不启动。c1s2条件释放仍只检验它已确认的真实终态机制，不能替其它状态生成成功记录；继续原resident两fit、五个既定评分及独立FEM分工，不原样加步数重试。

已回收非终态step1200的真实字段和completion：J=.0033163080，最大v误差.04211884、最大d误差.12395025，都定位在预裂纹内部x约−.277、y近0。该保存读出仍有Ru=.0349792、phase KKT=14.5883、愈合幅.0247315，历史罚能占总能量98.82%；近似更好不等于物理合格。纯数组套用既定C0投影后的J=.0031764397，仅为同保存输出的代数反事实，未装配残差，也不作为物理延续初值。`analysis/fit_c1s2_step1200_saved_analysis_20261024.json`保存该边界。

F1预裂纹y=0的251个固定d=1节点，其相邻v最大变化.05645564发生在dx=.002，是本步U=.05999988的94.09%。拟合已解析其中部分变化，但窄局部转折仍有误差。该现象提出参考精度/支路敏感性问题，不能直接称FEM错误、非唯一性或网络容量不足；既定strict c1s2与NN-start oracle将用于区分。纯节点邻接检查也确认没有四节点d全为1的单元，不能仅凭裂纹节点d=1就断言存在完全零刚度模态。证据 `analysis/c1s2_precrack_line_profile_20261024.json/.csv` 和 `figures/c1s2_precrack_line_profile_20261024.png`。

预裂纹线变化已逐字对回原MATLAB checkpoint的blocked DOF顺序（前N为ux、后N为uy），u/v/d全部一致，排除该变化由本次F1导出产生。证据 `analysis/c1s2_f1_export_array_identity_20261024.json`。这只核验导出，仍不证明参考唯一或已达严格容差。

对该线又给出源码条件下的构造性表达结论：实际BC为`v(x,0)=U*vhat/4+U/2`，U非零且固定预裂纹只约束damage。251个互异x上的任意有限v值可用250个ReLU hinge插值，其余七隐层恒等传递，因此原8×400结构在实数算术/无硬范数界下能精确表达这条线的节点值。窄转折本身不能证明该局部的架构障碍；构造的大斜率可能造成优化困难。它不证明完整二维三场/GP梯度可表达，不是实际拟合或物理成绩；没有实例化或评估网络。完整推导 `analysis/precrack_line_expressivity_note_20261024.md`。

全网格逐点原像也已用保存数组核对：86458个位移自由节点BC系数全正，目标damage对legacy/C0均有原像。已核实的通用ReLU充分定理在该宽深与三输出下只保证52272点，未覆盖86756点；充分界不足不能反推表达不可能。实际浮点BC有约1e-9或更小的固定误差底，远小于5e-8容差，不能解释宏观差距。完整二维三场的表达存在性仍未决，未继续扩建理论检索或数值试验。来源与定理代入见 `analysis/full_discrete_expressivity_scope_20261024.md`。

进一步读取三个已接受F1态的原生保存节点力，确认原软罚与FEM硬box的驻点条件不同：在精确下/上界仍有正常约束反力的自由节点，c1s2/c83s2/c83s4分别为81985/80945/80079个。raw phase L2约.0074–.0077，而对应box KKT仅1.87e-5/2.16e-5/2.84e-5；精确边界反力占raw力平方的99.9994%/99.9907%/99.9817%。有限二次软罚在可行边界的导数为零，不能代替这些硬约束反力；只有节点力向网络切空间的完整投影才决定实际参数梯度，该投影此处未测。这个结果证明需要对齐约束问题，不能把上述反力占比当作场差解释率，也不证明网络容量不足。全部由保存数组得到，无新装配/forward。证据 `analysis/fem_bound_reactions_exact_verified_20261024.json`，图 `figures/fem_bound_reactions_20261024.png`。

固定六作业resident队列于22:54:51真实启动（PID1724403），22:58回读确认独占attempt且无halt；一次SSH回显丢失后仅查询，没有重发启动。计划SHA为51ebeb7bdd13fae8e8c0bbf7a9fc962ea82c0dad248949f1d145b6d712270049，脚本SHA为fe72208fbc3d3a6f467aae6e33f5949fc26d118ae02ba6ecbb29cfb055f076f2。先等待现有c1s2 fit有效结束与进程清理，再依次执行c1s2 C0 continuation、c1s4/c83s2/c83s4四臂矩阵、c83s2/c83s4原结构拟合；每个任务沿用原声明算法和86400秒防挂，无累计上限、无自动重试。root在队列持有GPU调度时不再手工并行启动。部署/启动/回读原始证据位于 `run_workspace/resident_queue_20261023/`。

后处理调度明确由`pidl_history_audit`承接：队列全部正常结束、身份/finished/SHA及进程清理核实后，GPU5串行运行已准备D3 scorer 1000d3c6与D4 scorer 75044464。D4 c1s2用唯一真实matrix+fit+continuation合并inventory，c83两态同样绑定实际完整发布快照；c1s4没有合格F1目标就保持unavailable。队列运行、halt、未知身份或技术失败时不手工越过或重试；root不并行调度GPU。C0条件release的真实失败f64终态及机制条件现已满足，另见下方独立一次决定；必须排在resident和上述五个评分正常终结/清理后，不插入或修改resident。该分工完成已有比较与预声明条件分支。

本对话15分钟app持久化自动接续的首次创建曾被自动审批拒绝，理由为缺少明确人方许可，并存在已暂停HQ托管；该次未创建。随后用户对本对话、15分钟、静默无变化、报告交付后停止及不恢复跨对话HQ的完整问题，明确回答“允许本对话自动接续”。2026-10-24 00:19 UTC工具已成功创建`pidl-fem` heartbeat，并回读确认ACTIVE、15分钟、目标为本对话`01a15fd3-ed7b-7122-9ef4-eb5846c4a6c8`。现有resident和两机执行者的独占分工不变；自动接续先查原执行者，避免重复调度。此许可不授权失败重试或额外试验，也不恢复HQ托管。该控制层状态不构成任何科学结果。

## D3 c83 输入部署超时后的停止（2026-10-25 16:58 UTC）

已获批的控制字段修复成功启动并完成D3 c1评分；随后D3 c83使用原 `deploy_prepared_stream.py`（SHA79081d365d8d5fbe096df5dad86e15679520da5eab7be7020e5ae74c1d56b0d7）部署冻结输入包时，原subprocess 1200秒防挂触发，local exit1、stdout/stderr为空。原执行者只追加一次紧凑只读核查，未重传或派发。16:58:46 UTC实际确认远端partial为12,320,768 B、SHAe7961db28ebcce95ab1aff1bf21c03b14835aedd4064169a8bde5d5af61df95f；预期完整包94,059,994 B、SHAb9803f12a047a747814bfd9832a1268b98a017579c430f2ad0d2151011de09f5。远端transfer receipt、jobdir、intent、launch均不存在，匹配进程为空，GPU5为4 MiB/0%。这是部署I/O超时，零新增评分计算，不是科学拒绝。

新停止记录 `run_workspace/postprocessing_dispatch_20261024/halted_transfer_20261025.json` SHA59b46f1d465e39b1103a9f6fc485a6a92a669b62c3f9ce6e9b2d592692ea84f8，实际核查SHA55c0bb88d0b4785df150a1f654c25cbe655f642dd42eeb2acd849cd2cc6fdc25；root保存控制对账见 `analysis/c83_scoring_transfer_timeout_control_20261025.json`。已完成D3 c1结果保留；D3 c83与三个D4评分、C0 release均未执行。原partial不覆盖、不删除，原首次故障和10月25日继续授权也保持原字节。此次新的技术失败不由旧继续许可自动豁免，heartbeat不得重传、补派或越过顺序。

只可先核对本地完整包与保存partial身份，准备同一输入的具体恢复方案供用户决定；无新SSH、运行、阈值修改或科学计算。阶段A、原训练和全部FEM结果继续复用，整体改善率仍缺失。

## 修复后第一项正式评分（2026-10-25 16:36 UTC）

D3 c1 正式评分在 16:36:47 UTC 正常 exit0，评分用时9.96893 GPU秒；原执行者已确认所属进程清理。14份回收文件由root按收据逐项复核SHA/bytes，收据 `raw_archive/d3_c1_score_20261025_transport01/retrieval_receipt.json` SHA `ef8a4475369f16339ce90b1180dff1cfc940a7fa055b39ac75b8e5ff5808310b`，完整结果 SHA `6024e0cf5628bd2e1adee23420dab7406fabbaa940c523d996db7ff1b7ba8490`。

首步10个等更新端点中，P1/P2的场差及全部原生GP、能量、反力诊断对象逐项相同，两臂 `unverified_snapshots=[]`。2000更新时J均为 .0009264810995313352，fresh Ru=.002701840872、phase box KKT=.066491995001，仍不可行且物理拒绝。零合格端点配对、总体aggregate=null；评分成功不改变原训练的拒绝状态。c1s2严格参考的同前态敏感性由正式评分再次读取为verified、J=.0004090859383863217，仍是参考变化。汇总 `analysis/d3_c1_formal_scoring_20261025.json` SHA `79f603763b369839719c35aa05a038a3043315ef4c0330eadd1424ba5fc72723`；Mac只校验保存JSON与原文件字节。

## 控制修复后的明确继续授权（2026-10-25 16:35 UTC）

用户对原审批问题直接回答“允许按原范围继续（推荐）”。本次许可精确覆盖：应用已通过本地固定检查的控制字段修复、原五份 prepared 评分按原顺序串行执行，以及原前置条件满足后的已绑定一次 C0 release。原 `halted.json` 及失败请求不改写；其中等待用户授权的控制状态由此次人方批准取代，历史故障事实不变。

独立授权收据 `run_workspace/postprocessing_dispatch_20261024/user_continuation_authorization_20261025.json` SHA `f208a2d69263bbd52130e5ac1ec2df14ebb64dcd13821a508344f9d9248c96bf` 保存完整问题、回答、六项控制来源和五份评分准备包身份。控制器仍绑定候选 SHA `5478fe2d48d51efafd8a910718e7ad8e3ce6536f956f6a442df7676d84ba49b2`，验证收据 SHA `f69770a749b01dabfb22f88da4663a8ab94fc9139ad3816f9ca9c1feb75e6d06`；C0 决定仍绑定 SHA `86b21c306479089d2e2575bd86dd41d9ea6f15071f84e36948e5d5e3094ddc4e`。本次只复核这些保存字节，没有重复本地回归、网络推理或 FEM 装配。

`pidl_history_audit` 继续独占 GPU5 的实时核查、派发和回收；root 只整合记录。新的可归因 attempt 目录保留原失败材料，未知启动先核验，不凭昨日空闲快照判断当前可用。新的技术失败、超时、身份不明或资源冲突仍停止依赖动作，不自动重试；科学代码、目标、阈值和真实 float64 来源不变，fit 权重不进入 physics-only。阶段 A 及已结束 FEM 均不重跑。本节授权与执行准备不构成完成结果。

原 GPU owner 本次先只读确认 122 项已上传引用的 SHA 一致，六个待处理作业均无启动/结果或进程，GPU5 为 4 MiB/0%。修复控制器在 16:36:36.971987 UTC 唯一启动 `d3_c1_scoring_01`，supervisor PID2717414；七个原训练任务的终态、源码和所属进程清理全部通过。实况收据 `run_workspace/postprocessing_dispatch_20261024/dispatch_d3_c1_user_continuation_20261025_01/stdout.json`，root 保存字节核对见 `analysis/scoring_resumption_control_20261025.json`；没有 root 并行 SSH。下一项仍须等待本项终态及清理。

## c83s4 拟合终态与后处理启动前失败（2026-10-24 19:57–20:10 UTC）

最后c83s4原结构全参数float64 seen-target拟合于19:57:18.842 UTC正常exit0，25463.100028 GPU秒；12602 L-BFGS步、28334 closures、65发布快照、零历史提交。真实停止为`fit_stagnation_no_capacity_lower_bound`，非超时或技术故障。Q=.0252961367082、J=.00554544189594、G=.0246808145437，最大u/v/d误差.00589986212/.10145885574/.33212419240；既定Q≤.001和maxd≤.01均未达到。原函数族、teacher初始化和无L2目标仍仅属于seen-target路径，没有流入physics-only。

fresh机械残差=.09718388920、phase box KKT=17.05011639，physical=false、feasible=false；不可逆违反=.33212419240、上界违反=.00267655736、负损伤=.00744885064，BC通过、fresh历史和f差为0。86756节点中81666低于old，77218为负damage，585超过1。保存标量中G²占Q²95.1942%，v项占G²88.2175%；仅作原报告代数分解，没有在Mac重算GP梯度。较小目标误差不构成物理成功，有限拟合停滞也不构成容量下界。

同前态保存字段比较J：L+ .01378120592、L0 .01839499403、C+ .05106520835、C0 .13748788294、fit .00554544190；五个网络末态均被拒绝，目标/精度/工作量不同，不能据此算软件修复收益或优化效率。fit与matrix的physics manifest字节相同，所有old damage/history/driver逐数组等于同一F1 c83s3，尺度/网格/原F1目标核验一致。C0全部d=old；C+仅两节点改变；F1本步6318节点增损伤。完整对照 `analysis/c83s4_completed_endpoint_comparison_20261024.json/.md`，JSON SHAaec09d731df4bca079e504c951a3730f79d4e7697c4a58f06fa17fa4f93abef4。

combined receipt SHAff75baa96f197afee6999018c4a36c89eb924c0c0f87376ea0c65129dbaf3879，192文件、archive1203025920 B；final completion SHA2de9e1aed902005f62ec1e880344623ca55434077ee6dd28e375b14830bb0726，fields SHA54bc93abef6d72eaa5fac9c08eb258e57e454bed1f095b8c4a57966938893580。root复核关键metadata/fields字节及completion/work/watchdog/queue一致性；控制记录 `analysis/c83s4_fit_terminal_control_20261024.json` SHA06d62c248fd308eb915b6355e9a9cf1129466d4ff32ad0bfa99076a6d218bcf4。

resident于19:57:31.091 UTC记录fixed_queue_completed、count6、no_retries=true，全部所属进程清理；19:58:33实际只读观察active_jobs为空、scheduler不存在、GPU5 4MiB/0%，其它共享GPU作业未触碰。原执行者已生成唯一c83s4全量评分准备包，109 replay=44 matrix+65 fit，未据准备状态宣称评分完成。

20:09:32 D3 c1评分输入实际上传成功；首次派发在检查原训练前置作业时因`remote_dispatch.py:120`读取`prior['name']`而KeyError。冻结plan的predecessor.job只有job/job_root，无name；异常在任何评分launch intent创建之前。20:10:17只读检查确认launch_intent/launch_receipt/supervisor/output/collection_result全部不存在，无匹配评分进程、GPU5空闲。因此这是启动前控制兼容性故障，零评分计算，不是科学求解失败。五项评分及C0 release均未执行；没有自动修复重试，原失败脚本和请求字节保留。

持久停止记录 `run_workspace/postprocessing_dispatch_20261024/halted.json` SHAd850c3fe95eb0f85dc86183830139a121b583207fe2e64a693bd4a2f1812d4a4，实际无启动收据SHA055ed4710372093e712715bf50c2670a885ac80ddbe6ca93fb39d20d7db5bb44；root控制记录 `analysis/scoring_prelaunch_failure_control_20261024.json`。仅准备独立本地控制字段修复，不修改科学代码、输入目标或阈值，不上传、不派发；依用户技术失败后不自动重试的规则，修复后需用户明确继续原评分/C0条件链。

独立本地派发修复候选现已就绪：`run_workspace/postprocessing_dispatch_20261024/schema_compatibility_candidate_20261024/remote_dispatch.py` SHA5478fe2d48d51efafd8a910718e7ad8e3ce6536f956f6a442df7676d84ba49b2。只从已绑定job_root解析训练作业名，并校验name/job/顶层predecessor标签一致，替换两处直接name索引；既有科学算子、计划、目标、阈值和原失败材料保持不变。本地回归复现原KeyError，真实7个训练条目与5份评分准备包均通过，5类路径/标识矛盾均拒绝；21份原材料SHA保持，零网络/子进程/execute/科学计算。validation receipt SHA f69770a749b01dabfb22f88da4663a8ab94fc9139ad3816f9ca9c1feb75e6d06；候选及diff可审阅，但未部署/派发，不代表远端运行通过。用户继续许可仍待确认。

## c1s2 节点 oracle 的真实终态与归因修正（2026-10-24 17:27 UTC）

原定oracle_c1s2_01于17:27:17.010 UTC正常结束、exit0，30 outer后通过原普通判据U1e-6/joint4e-4；fresh Ru=9.75133722378e-7、phase box KKT=1.59940250408e-5，criterion=.975133722378。只提交一次，version1→2；它是节点FEM接受，不是严格验收或网络端点接受。watchdog491.80366秒、supervisor492.7428659秒、driver482.523967秒，三种时钟保留各自含义。37份原始文件共64265848 B已完整回收，root再次逐文件核对SHA/bytes；transfer SHA35000cc425e0af9febb5e57cf7f9f5ecc7bb37a6ecb01dcd925207773b597cde。17:30:01清理收据确认cmd44668/supervisor11560/watchdog23144/MATLAB13424全部退出、compute为空，CIT现无待派发请求，不新增严格oracle试验。

初猜是原L+ / 2000 RPROP保存末场，不是seen-target权重；source fields SHA7075f1f7ae40ad65a6b28e823ac91d2cd7a67b296f3be3142e7e70319e003ede。初猜投影仅满足既定BC/box：77778个damage项变化、最大.00431697558，54个位移项变化、最大2.62268e-9；投影不提交历史、不做恢复求解。immutable前态仍是原main/strict共同的F1 c1s1（SHA275096dafc587d94383744104272b07d97ca49e47781a1846a417e01bfa32da4）。原L+旧态、oracle输入/前态/proposal旧态、各参考的全部history/driver逐数组一致；proposal/checkpoint/export/window终态和readback链一致。fresh历史与f各项误差为0，f_solve=f_commit=1，BC/box/finite均通过。原转换matmul警告及四项显式加权零误差检查原样保留，没有新native或网络计算。

但这个接受结果没有靠近主F1：原L+对主F1的J=.009065253915，投影初猜=.009065088839，oracle对主F1=.009139576211、对已接受strict=.009195829529，而oracle对原L+仅.001405932839。oracle-main最大u/v/d差为.0036667453/.0628505432/.2194027387。相同251节点预裂纹线上，main和strict最大相邻v变化分别.05645564/.05646472，均在x=-.350→-.348；oracle只有.009108865，位置x=-.036→-.034。它保留了不同的场结构，而不只是残差数值变化。

因此，同一离散输入、同一旧态及普通验收政策下，两种已声明初猜得到不同的合格数值端点。不能把原L+距主F1的全部场差简单归为“还没收敛到任何合格节点平衡”，也不能据此归因网络表达不足。现有结果提示初猜相关的数值解选择及容差/条件性敏感性；oracle尚未按严格阈值接受，现有证据不区分近似解的病态敏感性与严格不同解支，不证明非唯一性或全局稳定性。原网络仍拒绝，节点松弛结果是否能由原网络完整实现仍未决。软罚/硬box差异、clamp梯度阻挡和F2方法对照继续支持约束/求解障碍，但不能独占解释全场距离。

控制记录 `analysis/fem_oracle_c1s2_terminal_control_20261024.json` SHA2f675ce53b3026b10fc4b0cee8bf6ea021afec28d995aab80a192b24d7826428；同前态纯数组比较 `analysis/c1s2_nodal_oracle_comparison_20261024.json` SHAdc824f71ff16a7f2cf4e8e2cf1ee490d5b37adf11795ae391c1ad3cc07416484及同名md。CIT完成收据为 `run_workspace/fem_strict_oracle_b34e97d_20261023/serial_dispatch_completed_20261024.json`。不替换main F1，不新增oracle评分接口或重算五项既定评分，不计入三项修复收益。GPU owner 17:35:25实际回执确认原最后c83s4 fit仍在运行，后续五项评分和绑定C0条件释放顺序不变。

## 严格 c83s4 的真实终态（2026-10-24 17:17 UTC）

strict_c83s4_01按原U1e-8/joint4e-6条件运行1500 outer后，于17:17:07.448 UTC以`E036:OuterExhausted`自然科学拒绝；watchdog耗时26366.4211968秒、exit1、stop_reason=exited、wrapper_error=null，Job Object已关闭。32份原文件共120681882 B已回收并逐项复核SHA/bytes；transfer receipt SHA1fb7d069df99e16aa7b749c6021f182ecf863856f41eb3237addadc930aaefe6，failure.mat SHAed8e5a71b4cbfe8ac53603e384d22efd6a83dc0290dbd364209957d3cd7fa822。17:18:21清理收据确认原cmd43800/supervisor7624/watchdog8064/MATLAB16604全部退出、compute为空；控制记录 `analysis/fem_strict_c83s4_terminal_control_20261024.json`。

保存同状态fresh Ru=2.65991940792e-15，phase box KKT=2.58272674875e-5，联合判据超限6.45681687255倍。1500次fresh联合检查全失败；机械从outer34通过，native自身曾报告1468次accepted，末内层res_sum=1.956e-6不能代替fresh检查。末100次phase KKT区间宽2.82841e-17，仅证明标量平台；保存场/力/系数有限且满足box及BC。旧态、pre/accepted、输入和主F1 proposal中的前态逐数组等于已发布c83s3（checkpoint SHAb6fc426e160394a4e246a57c6fdfe93163a36a30548101b482582458645fd685）；version413不变、proposal为空、零历史提交。

本态6334节点damage高于old、最大增量.99846917，因此该FEM失败不是PIDL clamp全部damage冻结的同一个现象。fresh历史/f代数回读误差约2.22e-16，但内层f到fresh f仍相差.00787674432；不能仅凭此差异分配损伤残差的因果份额。拒绝末态距同前态主F1的诊断J=.000350674427，最大u/v/d差约4.22533e-5/6.46632e-6/.06150913。phase KKT较主F1下降约9.10%仍未过严格标准；这些不是PIDL改善或合格参考敏感性。

四个预定strict参考现在只有c1s2通过，c1s4/c83s2/c83s4均自然拒绝。两个c83 tightening槽保留缺失，不导出失败目标，不改主F1。完整诊断 `analysis/fem_strict_c83s4_terminal_diagnosis_20261024.json`（SHAa53e5b065f68d5d4e97d31d38179e0f8f968a9e60f5d2847d4c33a69f1e08208），只读保存数组、没有NN/native重算。原FEM owner完成清理后于17:19:03.973 UTC一次派发原定oracle_c1s2_01，MATLAB13424实际创建17:19:05.876 UTC；初猜仍为原L+保存场，immutable old仍为F1 c1s1、源码b34e97d不变，派发不代表通过。该作业之后无其它已准备待运行FEM请求。GPU最后c83s4拟合及其后五项评分/条件释放继续原顺序，未追加或重试。

D3 c83的两个严格参考缺失已由原GPU owner绑定到唯一正式评分准备包 `run_workspace/gpu_c83_scoring_strict_unavailable_1000d3c6_20261024/prepared.json`（SHA00c6c1cad64eec4568c40a8412d957de3a811910f14eebd9dbcd5d77a3586370）。两槽均null/unavailable，仅附真实failure/config/terminal/transfer字节；main F1和1000d3c6评分算子不变。该包仍是prepared_not_transferred_or_scored，未据准备状态宣称完成。

## c83s2 原结构拟合真实终态（2026-10-24 12:52 UTC）

原resident的c83s2 seen-target fit于12:52:45.048 UTC正常退出，42588.581773 GPU秒；20847个L-BFGS accepted steps/47879 closures，0 RPROP、0 coefficient refresh、0 history commit，106份发布快照。停止原因`fit_stagnation_no_capacity_lower_bound`，未超时、未技术失败。真实最终Q=.0130896343915、J=.00301511829466、G=.0127376446085；max u/v/d误差约.00287277/.05106767/.24500048。保持原函数族、float64、weight_l2=0，已有teacher初始化只属于seen-target路径，没有用于physics-only。

同末态fresh诊断仍physical=false/feasible=false：Ru=.05795436917，phase box KKT=17.23620508，下界违反.24500048197、上界违反.00288886738、negative damage .00415886374，BC通过，历史及f的fresh一致性差为0。字段可更接近目标与物理合格是不同问题；有限拟合停滞不是网络容量下界。此次目标包含J与GP梯度项G，不能只按J对不同目标的优化路线排名。

combined回收receipt SHA725f2984b352fafad47771e891487e7bc57e429badc12bbff83a742f282bff4f，231文件、archive1209948160 B；大文件位置以`local_files[].local_path`为准。final completion SHA6e982c3940ea0af55060b4af531cb9f8c3621fd5ecab875fde452af072729905，fields SHAa330d5c3191da2eea68e451a8c47a8cf380417ec98f085f06fa30a9148247cab。原执行者完成全部回收核验，root重查关键metadata绑定，控制记录 `analysis/c83s2_fit_terminal_control_20261024.json`；同设置纯数组比较已完成：同一请求key、physics manifest及c83s1旧damage/history/driver与原main F1全部核对一致，fit J的数组重算与原报告相符。L+/L0/C+/C0/fit五个端点的J依次为.00965253/.01136726/.00191553/.00196692/.00301512，五者全部物理拒绝。fit虽比两legacy物理臂的J更小，却比两clamp臂更大；目标、精度与工作量不同，只作端点描述。fit中81438节点低于old，77234节点d<0，583节点d>1；C臂则d全部冻结在old，两类失败机制不可混为一谈。

保存fit目标的G²占Q²94.6942%，其中v梯度项占G²77.1906%；这是已有scalar report的代数分解，不是新GP梯度评分。原停止要求Q≤.001且max damage error≤.01均未达到；有限L-BFGS停滞仍不能给出容量下界，完整二维三场/梯度表达能力未决。原权重来源和主F1未改，未用fit初始化physics-only。完整保存数组对照 `analysis/c83s2_completed_endpoint_comparison_20261024.json`（SHA f8812d31ff45d6f6e04b0f83f7bf6545dfc6bf8e4d2117d52a0a2eb6f4e8ff6a），无新forward、原生装配、梯度重算或图。

原resident已验证前项进程清理并进入最后c83s4 fit；13:16:17回读723步/1515 closures，无halt。c83s2唯一完整matrix+fit评分包已纯I/O准备，150快照=44 matrix+106 fit，prepared SHA c3e75fc935b846497bced6a3ec48f2c75f6b0c2d2e5d4c4d0a879d93d0d2d554；未部署或启动。依然等原resident全部正常结束与清理后，由原GPU owner串行完成五项正式评分和已绑定一次C0条件释放。

## 严格 c83s2 的真实终态（2026-10-24 09:51 UTC）

strict_c83s2_01按原U1e-8/joint4e-6判据运行1500 outer后，于09:51:53.573 UTC以`E036:OuterExhausted`自然科学拒绝；没有历史提交或下一步。watchdog elapsed14760.9835849秒、exit1、stop_reason=exited、wrapper_error=null且Job Object已关闭，supervisor仅转报同一次非零退出。32份原始文件共115523370 B已逐项核SHA/bytes，transfer receipt SHA0406fc4d3c895a97671e282746baf23e1bb078a50e01e0aa8825fc63a18a2a0b；09:56:54的清理收据确认原cmd30936/supervisor49620/watchdog8456/MATLAB9548均不在，compute为空。控制层记录 `analysis/fem_strict_c83s2_terminal_control_20261024.json`，完整failure.mat保留于原归档。

该状态没有合格的tightening target，D3 c83/s2的`reference_tightening`保持null，以 `run_workspace/d3_c83s2_tightening_unavailable_20261024.json`绑定真实失败来源。主F1不改变，不把native日志中的res_sum当作fresh接受，也不将拒绝末态计入参考敏感性成功或总体改善率。保存数组诊断已完成：fresh Ru=1.37893330510e-15，phase box KKT=2.23149887472e-5，严格联合判据超限5.578747倍；全部1500次joint均未过，机械从outer3起通过。末100次phase KKT区间宽仅1.20075e-17，证明标量平台，不证明全部场逐位静止。native自身报告1499次accepted，最后res_sum=1.4449e-6，仍不能替代fresh残差。

全部accepted/pre/input/predecessor及主F1 proposal的旧态逐数组等于同一已发布c83s1（checkpoint SHA b6171a0fb0fd707517832c8dde753686f26825d6f89208351d7dd46819118b95），version411保持不变；proposal/f_commit为空。与c1s4不同，本态疲劳已激活：保存内层f与fresh f最大差.000830922246，fresh历史及f代数回读误差约2.22e-16，不能把该差异称为已提交历史污染，或仅凭它分配phase残差的因果份额。

主F1 c83s2原第3次outer按自身标准通过，phase KKT=2.16190971736e-5；strict拒绝末态反高约3.2189%。strict与main的诊断场距离J=5.33005746e-5，最大u/v/d差约4.94425e-6/7.71251e-6/.0131288。小场差没有带来严格残差接受；该比较不构成合格参考敏感性、不改判主F1、不计PIDL收益。详细来源、约束与历史核验见 `analysis/fem_strict_c83s2_terminal_diagnosis_20261024.json`（SHA cbe681dd4a81ac39cbb342c8f8d8eb4ef5aed751ce411e935a554ae055dc70f8）；全程只读保存数组，未运行native或网络。

原FEM owner完成回收与清理后，于09:57:39一次派发原定strict_c83s4_01，MATLAB16604实际创建于09:57:40.965 UTC；源码b34e97d和严格阈值不变。10:03:34实读确认该进程正在执行，后续只剩原定oracle_c1s2_01。root未另开SSH或启动producer，未重试c83s2。GPU resident仍运行原c83s2拟合，评分与C0条件释放顺序不变。

## 严格 c1s2 已接受：预裂纹变化对本次容差收紧稳定（2026-10-24）

strict_c1s2_01从原已发布F1 c1s1前态独立求解，于05:39:55.939 UTC正常结束，71 outer后通过；fresh Ru=9.13318132354e-9，phase box KKT=1.65707767477e-6，criterion=.913318132354，仍按U1e-8/joint4e-6接受，只提交一次历史。36份原文件61771710 B已逐项核SHA/bytes，transfer receipt SHA f1bb72ca0860c41c76529e3c1e096346de57f536ad186a14ed9d0f6e0bfb78bf；原所属进程已清理。既有export_window仅转换保存数组得到tightening target SHA f93b54e7fe597fbfab76070bb7bb9f5a5f02b34492e945adf29e9ecf97258766，不覆盖主F1。

strict与main c1s2的面积归一三通道J=.0004090859384，最大u/v/d差分别约3.75817e-5/.0003310862/.04213316。在y=0的251个预裂纹节点，最大相邻v变化仍发生在x=-.350→-.348：main为-.0564556393，strict为-.0564647208，幅度仅变化约0.0161%。这次严格求解没有消除窄尖变；结论限于同网格同前态的本次容差收紧，不构成参考唯一性或网格收敛证明。

固定已有C0最终字段只换参考后，J由.03794910145变为.03798223638；固定原结构seen-target拟合终态由.00267592033变为.00269513578，均没有网络更新。这是参考敏感性，不能当作PIDL收益或容量下界。reference J²的99.7876%来自damage；固定legacy首段仅换参考也从.00906525391变为.00910775531。两份proposal/checkpoint/readback/completion来源及逐元素一致性已核，均为version1→2一次提交。完整来源链、保存读回及数组对照在 `analysis/c1s2_strict_reference_sensitivity_20261024.json`（SHA99814a39bfbf2d5468f029069280aa93093a767adfc64637b89984ef9cdd1658）；原FEM owner已按原队列一次派发strict_c83s2_01，后续预定状态不变。

转换曾出现NumPy matmul的divide/overflow/invalid RuntimeWarning，原stderr完整保留。只针对该真实保存数组的四节点逐项乘加核对，driver/history/f_commit最大差全0、十个snapshot字段全finite；未查明运行时warning原因，没有修改算子、安装依赖或扩展环境测试。记录 `analysis/fem_strict_c1s2_completed_20261024/conversion_warning_array_check.json`。

正式评分尚未运行：D3原1000d3c6 scorer已有逐slot reference_tightening入口，GPU owner已纯I/O派生真实c1/s2资料的新包 `run_workspace/gpu_c1_scoring_with_sensitivity_1000d3c6_20261024/prepared.json`（SHA637324bdcfce4d62eadcf2fd54aed02ad8c4fc5b8fde055020020577bd95f086），保留旧准备版本并只执行正式一次评分。main targets、代码与authority字节不变；D4的75044464 scorer没有第二目标入口，继续使用原主F1，参考敏感性通过D3结果与纯数组解释复用，不改拟合目标或新增评分作业。

## 严格 c1s4 的真实终态（2026-10-24 05:04 UTC）

原strict按既定joint4e-6/U1e-8条件完成1500 outer后以`E036:OuterExhausted`自然科学拒绝；watchdog历时23898.9789653秒、exit1、stop_reason=exited、wrapper_error=null。supervisor的failure字段是转报非零科学退出，不能单据该措辞判成另一个技术故障。32份原始文件共73513420 B已逐项核SHA/bytes，原cmd484/supervisor47700/watchdog7728/MATLAB14540均已退出。完整来源 `raw_archive/strict_c1s4_01_terminal_20261024/transfer_receipt.json`（SHA77e1569941432ac793ee605b4c1a9a6854b41e0ebb9e1fceeabe2ebe6d5f3c40），failure.mat SHA d67c305f733cb186916fb58531e8e5d61d61349bebf449962f993f003ef59413。

同状态fresh机械残差已降到2.9866602073e-15，phase box KKT=8.53660910434e-6，联合和8.53660910733e-6，strict criterion=2.13415227683；feasible=true但joint_pass=false，零历史提交。accepted/pre的u/d/lower及全部四通道history精确等于原已发布c1s3 checkpoint；保存候选/力/系数均有限。末100次phase KKT仅在8.53660910433612e-6至8.536609104348381e-6之间变化，1500次fresh接受0次，虽然native自身报告1484次accepted。日志末内层res_sum=3.0976e-6不能替代投影后的fresh KKT。

因此收紧内求解已消除主F1失败的机械残差，但严格目标仍停在损伤约束残差平台；这支持参考求解算法影响结果，而不支持“所有差距都是网络表达不足”。把这个保存末态代入主F1的较松数值阈值可通过，仅是阈值敏感性诊断，不能事后改判、发布为strict成功或填补原c1s4的F1目标，也不能用于总体改善百分比。原FEM owner继续已批准的一次F2方法验证，不原样重跑strict；root仅作保存数组分析。控制层证据 `analysis/fem_strict_c1s4_terminal_control_20261024.json`，完整数值诊断 `analysis/fem_strict_c1s4_terminal_diagnosis_20261024.json`。

## 前瞻方法：F2 节点约束求解（2026-10-24，代表验证已完成）

strict c1s4现已自然拒绝，原失败及源码保持不变；以下为先前F2设计依据。源码核查发现 native Newton 在更新场后仍以更新前 residual 判停，PF 返回后再投影；最终同状态检查正确阻止假收敛。strict日志中下一轮首机械装配可推断上一末态Ru已低于严格阈值，继续循环现更指向fresh phase KKT；这些日志推断不是完整终态验收。

用户“从第一性原理突破、无累计资源上限”的当前授权覆盖同离散问题的机制性求解修复。准备一个独立 F2 solver：保持同原生算子、旧态、固定f的内层、节点[old,1]和全部最终阈值，复用现有MATLAB活动集/投影线搜索；约束phase后解当前damage的位移平衡，再从immutable旧态重算f和全部KKT。不得直接替用旧Python GP约束QP，不重复阶段A，不扩大网络。

代表性验证固定为c1s4真实F1s3前态；在同一个producer作业内先核对native固定f二次子问题K/b的实际两点残差/能量关系，再执行活动集耦合求解，以现有独立fresh残差、feasibility、f一致性及保存读回验收。非有限、线搜索或身份失败即停，不原样重试。该新solver必须另名F2，不能覆盖旧main/strict结果，不能填入原P1/P2对F1的改善率。

F2完整源码已固定于4482f97a939470e3be32fa42d55f4f7cfab83a32，独立目录 `tools/s04_e036_fem/f2/`。root已按用户当前授权批准这一次c1s4代表验证：CIT独占dispatcher可生成实际批准包、只部署新隔离文件，并在当前strict自然终结及所有所属进程清理可证后启动一次F2，无需再次行政确认。未知终态或机器冲突不启动，失败不自动重试。Damage内解4e-8、外层joint4e-6/U1e-8、f固定点1e-10；每轮记录完整精度fresh残差。未进行本地native/NN计算或额外测试梯队，实际两点算子检查在该代表作业内完成。初始未批准准备包及一致性记录保留于 `run_workspace/fem_f2_c1s4_4482f97a_prepared_v1/`，不能将其当作实际launch证据。

实际approved_v1已于23:10:45 UTC部署47个新文件、核对728个SHA绑定，未覆盖原strict源码。ZIP SHA1666ddd30868f23d12c8404f9172852f6154a3cb48cbe0b0946106ebc1ce7faf；源锁仍为3f4c771681ce13d8f93a083458f8ce1916dde1bc96bbe4a40ce2a0146e8c9a1f。23:10:45时F2 label尚未消费；strict自然终结、完整回收及旧进程清理核验后，原FEM owner已于05:09:58.885 UTC一次派发f2_c1s4_01，05:10:00.774实际创建MATLAB13772（watchdog11744/supervisor2368/cmd49308）。05:10:13状态回读确认entry/authority与批准包一致、CPU已运行；这证明已执行，不代表方法通过。启动传输 `run_workspace/fem_f2_c1s4_4482f97a_approved_v1/actual_launch_transport.json` SHA1bff791e13151cf2b53fa295f9d70aa2e63ba6bb6c17ae67452489542fdb960b；实际进程收据 `run_workspace/fem_strict_oracle_b34e97d_20261023/f2_c1s4_01_status_20261024T051013Z.json` SHA d5100e6dc8b9f0a7c8d3db12c8e0ef91a0174cd590ff6ba4abae6fc4499e1a1a。仍由原FEM owner独占CIT串行调度，root没有另开SSH或producer。

## F2 c1s4 代表验证已通过原严格判据（2026-10-24 05:11 UTC终态）

同一个已发布F1 c1s3前态、同原生离散算子与硬box下，F2活动集约束求解在第5个outer通过joint4e-6/U1e-8/fdelta1e-10验收：fresh Ru=2.8304737420193594e-15，phase KKT=2.8513637412581075e-6，criterion=.7128409360，fdelta=0、feasible=true。outer4的KKT=4.2307884540488205e-6未通过，outer5才通过；没有放宽容差。该命名方法于05:11:04 UTC自然完成、exit0，driver52.8062744秒，只有一次history commit、version3→4；不要把运行时钟或外迭代数差异换算成通用效率结论。

38个原始文件共67114378 B已逐项SHA/bytes核对，transfer receipt SHA2a8b00f45a1890404695fd3ab3a513257948d73ba79441036e33f635acd2725b；`f2_result.mat` SHA ed727af8e647b720d3ab351249fece65c07b03cdbd70bc8b425e041da0de4bde。旧前态u/d/lower/全部history精确等于F1s3；候选audit不提交，completion/result只提交一次，solve/commit历史与f差均0。原生固定f子问题校验保留：首outer两点能量差误差1.08691268e-17，五次anchor检查均在原atol1e-10+rtol1e-8内，native_f_overridden/old_history_modified均false。完整保存链及字段对比见 `analysis/fem_f2_c1s4_saved_result_20261024.json`；原始数据 `raw_archive/f2_c1s4_01_terminal_20261024/retrieved/`。

完整序列化链复核已完成：proposal/checkpoint/result的实际数组精确一致，completion按SHA绑定proposal/checkpoint/readback/predictor；候选与提交的history/f映射差均为0，保存f_solve全为1。F2与strict拒绝候选的u/v/d最大场差分别为.000379578/.002211838/.027537045，与main拒绝候选为.000354438/.001898416/.029039720；这些是不同方法端点间的诊断差，不能当作PIDL修复比例。保存结果分析JSON SHA e887e9e76915788f4db8b632a6bb7887ddc0a1f2dea2e130c098226ace3fb72a。F2属于独立前瞻方法，不把它的成功归入步内疲劳、残差检查或raw导出的单项修复收益。

这是此离散状态的约束求解方法成功：原strict在1500 outer后仍phase残差平台，F2在保持同前态与严格终态阈值时得到了可接受解，因此该FEM困难存在具体的算法来源。F2并未使用网络，不能据此宣称PIDL已有可接受轨迹或完整网络表达已足够；F2保留独立方法标签与`primary_F1_replacement=false`，不填回原c1s4 F1目标、不与旧结果相加为总体改善率、不延伸s5。原FEM owner清理后已按原四态计划派发strict_c1s2_01；GPU原resident与五项评分/C0一次条件释放的顺序不变。

## 条件分支：解除 C0 下界饱和（真实终态已绑定，一次执行已批准、未运行）

同结构修复准备在 `tools/s04_e036/constraint_release_preparation/`：固定实际saved f_solve和immutable旧态，先用节点损伤力作一个真正可行且降能的投影步，再让原完整网络拟合其raw预像与实际场。保留C0 clamp、原参数数目及边界；raw代理项的梯度明确不是物理能量梯度，也没有straight-through替换。只有实际clamped场严格可行、同f能量下降及被挡方向实际实现均达到预声明份额，且保存读回完成，才保留新权重；否则全量回滚。独立fresh KKT/f验收仍沿用原规则，释放成功不等于复现成功。

此准备不读取FEM未来目标、不接入或改变resident队列。producer adapter现已准备：用原61文件底座加5个命名overlay文件，纯I/O late binder只接受真实失败的float64 C0终态，保留原时钟、权重、old、f_solve和work；释放成功后最多调用一次原物理L-BFGS，失败完整回滚并留档。原authority模板保留未批准历史。真实continuation现已失败且阻挡仍在，root依据用户现有任务授权批准这一个预声明条件分支；不是原样重试。实际候选tar SHA `e91bc93a4088f86a5c624cb28d2d69fb412860e6b0baf82ce3bd619ae71599cb`，原61文件及becc4166五overlay字节不变。`run_workspace/c0_release_c1s2_preparation_20261024/root_one_attempt_decision.json`（SHA 86b21c306479089d2e2575bd86dd41d9ea6f15071f84e36948e5d5e3094ddc4e）绑定源completion cfcc2c9d、候选包及原GPU owner唯一调度权。仅在resident、其后五个既定评分均正常完成且所属进程清理/GPU5空闲可证后，使用全新`jobs/d4_c1s2_release_01`；producer binder须逐项匹配实际来源链并绑定真实UUID/新时钟，随后最多一次release和一次原physics-only L-BFGS。技术失败、未知、资源冲突或源不匹配停依赖动作，不重试、不接fit权重。包已准备但尚未部署/启动；Mac没有NN/native或新科学测试。

## 当前范围（2026-10-22 人方分工更新）

本对话继续负责cyclic PIDL/FEM完整同设置对照与差距归因。timing对话 `01a1603e-8e80-7153-a753-d895b9edb7f5` 独占阶段A，本对话只核验并复用其真实产物，不重复阶段A，不修改其工作树。阶段B FEM、P1/P2主对照、机制/表达鉴别由本对话完成。新隔离工作树 `worktrees/s04-gap-attribution-20261022`；既有混合工作树及失败记录保留。

用户本次明确“不设置资源上限”，取消先前48 GPUh＋8 FEMh累计上限；每个独立进程仍有显式防挂时间、实际耗时与进程记录，未知状态先核查，科学失败不静默覆盖或原样重试。原P1/P2前2000更新/步继续作为等工作量观测设计；后续有机制依据的候选另列前瞻方法，不把新结果填回旧预算点。原物理状态、允许的历史、native KKT阈值及不补跑历史/新U0 recovery边界不变。当前scope以 `local_archive/experiments/S04-E036/gap_attribution_20261022/authority_scope.json` 为准，后文旧授权是历史。

第一性原理决策：物理节点残差R、网络pullback J_theta^T R、包含weight-L2的参数梯度、原始NN可行场函数族是四个不同对象。已审代码显示TrainableReLU系数未被weight-L2惩罚，存在场不变而正则变化的参数缩放；同时原legacy映射加GP软罚不等价于节点硬box约束。下一机制设计直接比较这些差别，不再重复已做过的冻结head微调。

前瞻机制矩阵在c1s2/c1s4/c83s2/c83s4固定F1旧前态，分别绑定canonical ad749c8前一physical step网络1/3/411/413，全部臂同初值，不依赖主P2是否已到达这些状态。四臂为 legacy/direct-box-projection × lambda=1e-5/0，均使用同一个原生物理算子与trial-f语义；投影明确改变复合输出函数族，不是“仅换优化器”。原映射的全网络target-fit只测seen-target近似能力；拟合失败不能证明容量不足。完整第一性原理方案已归档于 `local_archive/experiments/S04-E036/gap_attribution_20261022/analysis/first_principles_design.md`；已有实现检查结果直接复用，不为首次执行或commit变化另加独立复审。

本次明确采用该方案的以下前瞻比较：

- 四臂首段同为2000次RPROP、每200次重建优化器/重算系数并保存；预定候选C0为direct clamp且lambda=0。后续求稳与float64/L-BFGS变化独立计量，不混入首段等工作量收益；更换冻结f时清空旧目标的L-BFGS曲率历史。
- 原映射全参数拟合使用节点面积误差与原生Q4梯度误差。Q≤1e-3且maxd≤.01只是程序停止点；报告实际达到的近似上界，不能把该数值当作FEM精度、物理合格或容量充分的阈值。拟合权重不进入physics-only窗口。
- 四个预定D4状态各允许一次joint4e-6/u1e-8严格FEM复算，始终使用与主参考相同前态；已存在同条件严格解直接复用。此项替代旧单态tightening范围，仅用作逐态数值敏感性，失败不加第三次求解，不叫误差界。
- 节点oracle明确从每态L+最后完整场起步，先投影共同BC及[d_old,1]，保存投影前后场与幅度；不可用则标unavailable，不能换较容易初猜。始终绑定F1旧d/A/r，其结果不是NN成绩。
- C0若在四态通过fresh验收，再执行它自己的c1/c83五步窗口与c20s4/c60s4端点，按自身已合格历史推进；不借用target-fit权重或其他臂的历史。

精度约定在执行前明确：所有F1输入旧d/A/r保留原始float64，fresh末态验收始终使用该原始前态，不把round到float32的下界冒充共同下界。D3保留float32网络、loss和active采样；用于loss的旧d/f显式转换并记录转换最大差值。D4四物理臂首段统一采用float32网络参数及网络输入求值，输出节点u/v/d提升到float64后，以native float64几何和原始old64组装能量/driver；clamp也在这一共同double节点场上执行。D4四臂物理组装精度一致，与D3之间不称逐字继续。后续full-float64网络求稳单独标记精度与优化器改变。

本节为 2026-10-22 执行前范围；最新实际执行与结果见顶部日期记录。已有本地检查、输入转换和参数文件读取本身不能代表误差缩小。阶段A状态以其owner真实原生证据为准。

### 当前实现检查：固定基准通过即推进（2026-10-22）

按已安装 research-decision-core 的同名规则，移除本卡由agent自加的首次执行前独立复核、每次commit复审及后续评分/元数据复审要求。已完成的审查、测试与失败记录保留；不因此重复执行。没有本轮人方明确要求额外代码审核的指令。资源、进程归属和输入身份仍在实际使用时直接核验。

当前实现固定基准命令为 `python3 -m pytest -q tests/test_e036_mechanism_runner.py tests/test_e036_fem_export.py`。代表性输入是既有微型Q4与已保存字段/初猜的序列化fixture；检查四臂共同前态与更新计数、目标隔离、保存读回、原生导出字段/来源对应。预期全部通过，且不执行项目网络或原生求解。两文件已有24项和23项通过结果，当前对应字节未变，直接复用；不是要求把它们再跑一遍。旧历史测试、T3回归与已有实验不并入本基准。

尚在完成的输入生成/评分收尾各使用一个代表性微型端到端I/O用例覆盖其新增接口，不追加多轮smoke或独立审核；通过即进入实际既定对照。失败只修复并重跑受影响项。文档、路径和元数据小改只核直接一致性。真实阶段A核验、B参考、P1/P2、预定四态机制/拟合比较是回答本科研问题所需的观测，保留原状态和判据，不当作每次代码修改都重跑的回归测试。

以下为原任务的历史设计和阶段记录；涉及旧预算、旧待批状态或旧审核安排时，以本节当前范围与上述实现检查规则为准，不重写历史结果。


目的：解释原生 GP PIDL 在循环加载下与 FEM 的差距。2026-10-21 用户明确要求先修复步内疲劳、最终残差与 raw 导出，再进行同设置对照，最后区分优化与网络表达。此记录继续 mesh 对齐目标；旧 E011/E035 结果和权限不变。

本轮：修复代码、人工单元检查、独立交叉复核、拟定有预算上限的成组验证。尚无新项目 NN 优化或 FEM 求解，也未修改 CITPC12。**现状是 D2 代码与验证设计完成；不是已缩小场误差。**

## 复用与决策路径

复用上一轮 `local_archive/pidl_cyclic_audit_20261021/` 的源码核验与 19 态保存应变审计；原生 GP 代码来自 d1edbeed（ad749c8 的同源分支），独立分支 codex/s04-cyclic-alignment-20261021。复用 E011 fresh assembly、commit_once、phase tangent、已有 precrack 对齐输入及 frozen-state 诊断，避免重做旧 head-fit/优化试验。查阅 E011 precrack preparation 后确认：固定裂纹边界与罚系数差异不能遗漏。

| 阶段 | 要解决的问题 | 证据与转向条件 |
|---|---|---|
| D1 已完成 | 存在什么离散差异 | 源码与存档审计；不把诊断 bug 当训练机制 |
| D2 本轮 | 修复是否实现了声明的方程与接受语义 | 人工 Q4/T3 弱式、历史、边界、预算测试和跨作者复核；MATLAB 运行检查仍需 producer |
| D3 待预算授权 | 共同设置后差距能减少多少 | 成组共同前态和短连续窗口；不合格末态只作诊断，不能填补或续接成轨迹 |
| D4 D3 的条件分支 | 剩余是优化、表达还是未匹配的目标 | 同结构继续优化与同结构场拟合；不能由一次拟合失败证明容量不足 |

## 本轮实现

1. `source/trial_fatigue_coupling.py` 与 `model_train.py`：每个 physical substep 固定旧 A/r/d；冻结 f 求解，然后从同一旧状态重建 `A_trial=A_old+relu(g(d)psi_raw-r_old)`，更新 f，检查固定点和当前末态残差。f 从计算图 detach。只有全部通过才提交一次；失败保存原因与实际工作量。禁止 strict 自动预训练、续跑和失败目录覆盖，初始网络需 SHA 校验。
2. `source/cyclic_acceptance.py`：同一个最终 u/v/d、旧 lower/history 上重新装配 float64 原生节点力；检查自由位移、损伤约束残差、规定边界及历史重算一致性。不靠 loss plateau 或参数梯度认定平衡。
3. `tools/s04_e036_fem/`：在已核实 live FEM 字节上构建隔离 overlay。当前 eq→pf 新装配，接受后从原始旧 history 生成单次提交；原默认路径不变。MATLAB selftest、checkcode 和原生同状态 admission 尚未执行。
4. raw 从应变直接计算；原生 GP 全保存，再显式给出算术/面积加权均值。旧 `from_g` 名称保留为标明语义的兼容别名。**raw 修复没有进入训练损失或 current_active 历史驱动，单独能改变的物理训练轨迹为零。**
5. 可选共同设置包还包括：固定 251 个预裂纹节点 d=1；tol_ir=.001，对应 gamma=421875（原 PIDL .005→16875，差25倍）；负损伤恢复罚13781.25（原 PIDL无此项）。这些是另外的目标/边界修正，不能把它们产生的收益全部叫作疲劳更新收益。默认不启用，free 节点原映射不变。

## 共同离散问题与接受规则

采用原生 Q4 四 GP、同一个 ordered mesh（86756 nodes /86408 elements）、同一节点和 GP 顺序、同一积分权重。T3 仅作为本轮实现检查，不额外开启 T3 科学试验。

E=1, nu=.3, Gc=.01, ell=.01, eta=0, AT1/Amor/plane strain, alpha_T=.5, asymptotic p=2。top/bottom ux=0、bottom uy=0、top uy=U；显式 crack DOFs d=1。`common_problem_q4.json` 绑定 mesh digest、原始 boundary mask 来源与 251 节点，未安装任何加载后的 FEM 目标到训练中。

每圈 U=[.02999988,.05999988,.08999988,.11999988,0]，名义 Umax=.12。状态键包括 trajectory/Umax、cycle、substep、U、pre/post commit、旧前态来源；不得按文件 step 号直接配对。

主验收明确为 **nodal_box_kkt**：在 d_old 下界上保留 min(Rd,0)，在1上界保留max(Rd,0)，内部保留Rd；仅确实重合的上下界无可行方向。BC反力排除但规定值仍检查。要求物理 0<=d<=1 严格，d>=old 的误差容差1e-8；不隐藏 clipping。`max((||Ru||+||Rkkt||)/4e-4,||Ru||/1e-6)<=1`。所有 raw residual 同时保存。

这是把 FEM 已有投影输出域明确为共同约束问题的**接受规则变更**，不是声称旧 penalty+projection 已解决该问题。fresh机械1e-6的最终联合要求也比旧外层仅sum stop更严格。`soft_penalty_equations` 只作明确的另一个诊断规则，不能见结果后切换。AT1 完好下界的正反力不应误判为失衡。

PIDL GP历史 float32→float64 重算容差 abs/rel各2e-6；FEM double commit identity1e-10，分别记录，不混作残差精度。PIDL `f_solve`指最后optimizer实际冻结系数，FEM `f_solve`指fresh装配系数；FEM另存`f_last_inner_return`。比较时使用明确对应字段。

## 成组验证设计（尚未执行）

### 固定内容与比较结构

保持同一 8×400 coordinate MLP、seed1、相同初始参数、float32求解、同一网格/载荷/能量项及原 weight_decay=1e-5。FEM场只用于指定的前态传入、最终评分及后述明确标记的表达探针；不能用待评分终态选 checkpoint、调整停止阈值或学习率。

保留三个层次，**不输出一个无法辨识的“疲劳修复贡献百分比”**：

- P0/F0：既有原设置存档，raw重算为独立 sidecar，不覆盖原文件。
- P1/F1：共同 material/BC/predecessor；PIDL仍使用旧 f 作为冻结系数；FEM用fresh最终接受。这个差分同时包含设置与参考末态变化，分开报告 P0–F0、P0–F1、P1–F1。
- P2/F1：与P1相同，但PIDL使用本轮trial-f/末态接受。P1与P2的比较才用于评价耦合修复包。

在同一末态诊断中保存：首次旧loss plateau快照、首次f固定点快照、最终fresh验收/耗尽快照，以及每200次更新快照。以相同累计更新次数比较P1/P2；残差验收造成的额外计算另报。冻结-f控制使用相同200步分块和优化器重建安排，避免把重启优化器本身混入f更新效应。首次固定点快照只是诊断，不自动commit，也不虚构一条第三轨迹。P1也必须通过共同trial-f末态残差才能commit；冻结f解可能因此拒绝。拒绝末态的等预算J仍报告为diagnostic，不能纳入accepted改善率或按旧loss stop续接。

### 状态覆盖与初始化

采用两个各完整5个substep的短窗口 c1、c83，覆盖加载、峰值、卸载；另做 c20s4、c60s4 两个冻结前态端点。早期、稳定累积、晚期都有覆盖。c83窗口及独立端点均是**给定存档前态的局部条件试验**，不是从c1连续预测到c83。

每个窗口两臂从同一已保存FEM前态的lower/A/r开始，使用同一已有PIDL参数作优化初值；这些是前态输入，不是该窗口未来终态监督。窗口内各自提交自己的接受历史；从第二步起两臂不再拥有共同前态，窗口差分明确为耦合与历史传播包的综合效应；一臂未通过时立即停止该臂窗口，保留失败，不把另一臂前态接进去。端点试验无后续历史传播。取出前态时核验哈希、物理键、节点/GP顺序及原生装配；缺失或不合格则标 unavailable，不能换一个容易状态。

当前通用strict runner只支持全新U0起步；**不能用它伪装late-window resume**。D3须复用E011 frozen-state harness，将本轮controller接入显式前态调用，并独立检查；该配套harness与producer admission属于下面同一条件授权链，尚未完成/执行。现有json仅锁mesh/BC/材料，不等于完整初始化。

### 测量与归因

主量采用固定尺度 primitive field gap：`J=sqrt(sum_i m_i*((du/.12)^2+(dv/.12)^2+dd^2)/(3*sum_i m_i))`；m_i为原生Q4积分得到的节点集中面积；分别列u/v/d贡献。次量包括nativeGP active-driver加权L2、raw、A、f、相场耗散、反力、自由残差、bounds、实际工作量与时间。卸载零reference范数时报告绝对误差，不偷偷加epsilon。

改善量报告`1-J(P2,F1)/J(P1,F1)`，分状态及固定等权聚合；若分母0则undefined，未通过验收的点不得加入“已解释比例”。同时给同设置FEM tightening/replay变化作为参考数值误差；若改善同该变化相当，则不声称可辨识收益。没有预设任意“必须提高x%”阈值，不把单轨迹多个状态当独立样本或泛化证据。两窗口不足以评价疲劳寿命。

### 优化与表达的条件鉴别

仅在共同BC/材料/历史/接受规则已匹配、FEM端点合格后进入。预定 c1s2,c1s4,c83s2,c83s4，不按误差挑点。D4每一对诊断都重新绑定同一个明确的F1旧前态，不沿用P1/P2各自演化历史却称为同问题：

1. 同网络、同前态，继续物理优化（RPROP/LBFGS的明确有界比较）并记录自由残差随工作量变化。若同结构可同时降低残差和场误差，支持优化受限。
2. 同结构拟合该FEM的u/v/d与nativeGP梯度，单独标记为seen-target表达探针，不并入physics-only成绩。达到FEM数值误差尺度说明这些离散场可表达；若physics-only仍差，不能再归咎于该状态的容量。
3. 拟合失败只能说明当前拟合程序未找到表达，不能证明网络表达上限。必要时用已有E011/E035结果区分L2正则、激活饱和、约束不可行和优化条件数；扩大网络或修改损失应另列待决分支，不能用本轮有限失败直接下结论。

raw单独修复贡献0物理轨迹；共同设置包、耦合/停止包的效应只按上述嵌套差分报告，不当互相独立、可相加的因果百分比。

## 建议的一次性执行上限（未获本轮预算批准）

目标生产端：gpu-taobo（PIDL），citpc12-ssh（FEM）。不启用CSD3或其它新机器。先检查资源和已有进程；零启动连接/环境检查合计最多30分钟，不能重启共享服务。

- 总上限：**48 GPU-hours + 8 CITPC12 CPU wall-hours**；不是完成保证。达到任何上限即停止，保留未解决结果。
- 主比较24个PIDL physical substeps：2臂×(2窗口×5步+2独立峰值)，每步最多2000次RPROP，至多10个200-step外层，总48000次。两臂相同总预算；较早合格可停，额外预算不得转移给某一失败状态。
- 条件优化/表达探针：4预定态×2种诊断×最多2000次更新，总16000次；合计最大64000次RPROP更新。LBFGS仅用于4个继续物理优化探针，每态最多200迭代/400closure，合计最多800迭代/1600closure，独立计数且计入同一总墙钟；表达探针不额外调用LBFGS。不能无限line search。
- 该条件前态设计不运行新的U0 recovery；只加载已有零载荷/窗口前态。通用strict runner的U0起步不属于这24步预算，不得为了绕开harness限制额外启动。
- f固定点abs/rel各2e-6，relaxation=1，数值阈值不按结果放宽。原生FEM每步max_outer=1500、同MAT_CHAR，墙钟上限优先；失败不自动扩大上限、换seed或重新开始。
- 同一冻结末态最多一次紧容差FEM check（joint4e-6/u1e-8）用于参考误差估计，计入8h；不得用它掩盖主参考未验收。
- 明确停止：非有限、能量log域错误、BC/状态identity失败、资源冲突、任一总/步预算耗尽。出现科学失败后不重跑该臂；可以完成预先列出的其它独立状态。结果未知先核查进程/receipt，不重复spawn。

本预算决定是新的计算资源授权，不是为已授权的修复、单元检查重复请示。依据已安装 research-decision-core 的 Bounded Task Authority，一次批准覆盖配套harness实现→必要复核→隔离部署→admission→这一组运行→归档，不逐步再问。

## 本轮结论与限制

代码层已处理步内f滞后、最终同状态残差与raw除法bug，并将新发现的硬裂纹BC和25倍罚系数差异显式纳入共同设置。全部科学收益目前仍未知；不能报告“已解释x%差距”，也不能判断剩余为网络表达不足。实际MATLAB、producer端原生残差一致性与完整对照执行尚未完成。

## 2026-10-21 后续：共同前态对照与保存核验的代码准备

用户本次授权仅为补齐 P1/P2、共同前态窗口和保存后核验代码，并给出具体 FEM 验证方案和预算；明确禁止测试执行、训练、FEM、部署。此授权覆盖准备，不继承上文建议预算或其他任务运行权限。前面的实现/检查记录保留为 b84a0c0a 历史，本节不改写既有结果。

- 新独立入口 `tools/s04_e036/run_paired_windows.py` 直接绑定 c1/c83 的五步窗口与 c20s4/c60s4 端点；显式加载共同 FEM 前态和相同已有 PIDL 网络，两臂分别延续自己的已接受历史，不经过通用 runner 的 U0 recovery 或自动续跑。
- P1 使用 `coefficient_mode=frozen_old`，每个物理步内一直冻结旧 f；P2 使用 `trial`。两臂共享每块200、每步最多2000更新及 fresh trial-history 末态检查；P2另需f固定点。P1的f差值保留为诊断，不额外要求旧系数等于新系数。旧 loss plateau、首次f固定点和每块场均保存；这些快照不能自行提交。
- 输入转换器只转换已完整保存的 checkpoint；admission须绑定真实原生残差和读回证据。缺 c82s5/c20s3/c60s3 或完整初态则 unavailable，不虚构前态、不替换状态、不补跑整条历史。共同配置本身仍不是前态。
- 新 bundle 同时保存旧前态、末态、权重、共同场映射、f_solve/f_commit和状态键；保存后读回重建网络场并重新检查，成功才发布 completion，后一步只消费读回值。FEM另有只读 proposal/native step checkpoint 核验工具。详细接口见 `tools/s04_e036/README.md`。
- 当前只是代码补充及人工静态交叉审查，测试源码已新增但本轮全部未运行。新的实现身份单列 `implementation_lock.json`；原 `source_lock.json` 和82项/26项历史结果不扩展为对本次改动的验证。
- 独立评分入口只读取事后F1目标，核对共同起点及各自后续来源链；按Q4集中面积输出u/v/d误差和等更新数诊断。缺失任一预定对时不发布12态整体改善率。FEM另新增显式前态窗口入口，保存后使用已核验读回值推进；实际系统/MEX输入绑定、disabled原生对照调用与资源控制仍待执行前准备和复核。

新的待批建议单列于 `FEM_VALIDATION_PLAN.md`：FEM先3小时实际检查，再最多7小时成组求解/一次紧容差检查；PIDL主比较另列最多24 GPU-hours，不含D4。上述均为停止上限而非耗时预测，均未获本轮执行批准。代码的时间检查不能替代未来生产端的外部watchdog。静态实现完成不改变“真实同状态一致性及场误差收益尚未知”的结论。

## 2026-10-22（伦敦）阶段 A 授权与本次停止

用户随后明确授权“先按阶段 A 推进，按照你说的上限来，允许必要测试和 FEM 核验”。本条替代上一节仅准备的执行边界，原历史文字和结果保留。批准范围仅 Stage A：总墙钟3小时、最多4 CPU线程、单个原生求解串行；两次c1s1 disabled控制各1800秒/outer1500，四组冻结场各600秒。包含必要代码修复、轻量测试、独立复核与隔离准备；不包括阶段B、NN训练、新recovery、全历史重建、科学重试或换producer。

本次case为 `local_archive/experiments/S04-E036/stage_a_20261021_2142`；启动记录21:42:35Z，总截止00:42:35Z，启动前设置零启动准备1200秒上限。现有共同前态及四组s3/s4文件已盘点，实际CITPC12源/MEX/编译器/CHOLMOD路径已只读核对。独立快照命令因PowerShell的git archive参数解析错误退出；后续23:28:07Z读时已越过该零启动上限，因此本次原生启动停止，未延长或重开。23:31:38Z只读复核：新任务目录无文件，MATLAB/Python/ifx进程列表为空。旧source及历史数据未改写。

本地轻量实现检查已运行，具体批次、字节身份与结果见 [阶段A记录](STAGE_A_RESULT_20261022.md)。新MATLAB harness、显式MEX构建与外部超时控制仅完成源码准备/静态复核。实际编译、MATLAB checkcode/mock、U0原生入场、disabled双臂及四组真实冻结场比较均未执行。该结果是启动准备失败/停止，不是FEM数值负结果，也不允许进入阶段B；当前D2仍是实际同状态一致性待核验。

### 同范围机械续接结果

HQ以原直接人方3小时授权为基础，前瞻允许一次≤300秒快照修复，原截止00:42:35Z不变。正确git参数的隔离快照一次成功（producer8.493秒），10输入SHA与36文件代码包逐项匹配。第一次prepare启动只留下WMI创建收据，wrapper已退出，没有watchdog attempt、MATLAB或build输出。后续只读诊断确认PowerShell Restricted、脚本解析无错误；证据支持脚本入口策略阻断，具体进程异常未捕获。按本次首次控制故障停止条件未重发/改策略，无MATLAB/MEX/FEM/训练。D2仍缺真实同状态证据；[续接范围、完整失败链与下一缺项](STAGE_A_CONTINUATION_20261022.md)。

## D3 c83 续传方案已备妥，待本次明确批准（2026-10-25 17:17 UTC）

[完整恢复方案](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/run_workspace/postprocessing_dispatch_20261024/c83_resume_candidate_20261025_01/README.md)仅准备同一冻结输入的传输恢复，尚未执行。保留原12,320,768 B部分包，只传剩余81,739,226 B，以10段顺序写入独立attempt；每段1200秒，预检查、传输、重组与原部署核验共用12000秒总上限。完整归档SHA、安全解包及101个新文件/35个原复用证据路径全部通过后，才由原GPU owner串行继续D3 c83、D4 c1s2、D4 c83s2、D4 c83s4评分；D3 c1不重跑。全部原评分完成且清理确认后，才允许此前绑定的一次C0条件释放。新失败即停，原86400秒科学作业防挂不变。

方案SHA `bf99d03819dd749f8a2f6ba87f8ca76b31f94866779d06a0fc70c2dc2d02aafb`；控制器SHA `9dadb6ecb02ccd171fef92e91409aa71b946055b402f052853cc2053478db044`；原部署校验接入SHA `a11238aa3d3cb8fcd745de440387352f852b9ee79896b04aabaea31c8721a8d7`；本地准备检查收据SHA `687bc429935260c3415be52ad0964120e1045f091de9bc7a16598b8910db031a`。检查仅覆盖保存字节、metadata、语法及一次隔离JSON写读；远端行为未执行验证。raw-string换行曾有展示歧义，AST检查确认原候选已是换行，未将其误写为已复现故障；当前以chr(10)显式表达。

当前仍受新的超时停止收据约束；本方案的12000秒恢复窗口须单独得到人方明确批准，准备完成不等于执行获准。root未新增SSH、传输、评分或物理计算。

## 本次直接继续授权：移除资源时限（2026-10-25 20:25 UTC）

用户对已展示的D3 c83分段续传、原剩余四评分及一次有条件C0方案直接回复“请继续 移除所有limit”。原始答复、问题ID及精确范围保存于 `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/run_workspace/postprocessing_dispatch_20261024/user_continuation_no_resource_limits_20261025.json`，SHA `06726bfbe75f29749d8af21a2027aaa690df9fd32e882355e344d2a00c8ff44e`。该批准取代超时收据的等待许可状态；不改写旧失败。累计、传输分段/整体、回收和GPU作业墙钟上限均改为null；连接失败检测仍保留，科学验收阈值、原迭代/数值停止条件和新失败首停不重试不变。无新增FEM或实验，不重新运行D3 c1。

执行由原pidl_history_audit独占。原partial与原archive/manifest不改；独立传输和评分/C0控制覆盖层须明确记录其SHA及实际命令，确保外层监督进程和内层Deadline都不再因elapsed time停止，而非只改文字或将24小时换成大数。constraint_release_design仅完成本地传输控制版；本记录时尚未新增远端动作。授权内的控制修订无需再次请求用户确认。
