# D19 R007：可选Newton候选的浮点可行化保护首停，0/600

目的：在同原方程/加载/自身历史和原最终物理精度下，用显式box残差LS信任域子问题替换R006投影Newton射线，检验连续train_A600可行性。本轮唯一尝试已首次失败停止，**0/600**，无重试、无step2、无真实最终QP或历史提交。当前只能确认一次工作目标下降与可行化保护的具体失败机制，不能判断此法能否解决R3后段反弹或完整轨迹成本。

源码`ff2deeb533cba22789170d5f4b8efa8d01c00398`，36文件artifact`c29026a40d521d3435cce85c77e94af9feb457b6fc6eb246d1babc82254d13b3`；card SHA`8de496aebc5d8a7bdc0a2f6f4c39b25006dc8dfb1eb26ceb8d72d2f907f7bb0f`，独立静态审核[execution_review.json](execution_review.json)。原R3–R006失败、舍入资格条款和成本均保留，静态PASS不追认为数值成功。

## 实际执行与完整证据

- 唯一run：`pf_hybrid_solver_v10_20261021_r7`，原GPUServer8 `drtao@172.16.100.2`，4CPU/0GPU；原R3输入只读，98公共OSQP文件同机复制。没有新private input、pilot、旧baseline、其他case或训练。
- 只读preflight4.305491s、dispatch9.075141s，合计13.380632s、两次机械额度已消费。上传仅114109B审核绑定源码控制包；同机OSQP复制980049B。最终runtime/source/input准入通过并实际进入worker。
- phase/case **41.2157510603s**；producer **41.2172501124s**，包含phase，不相加。worker+guardian实测CPU **48.73038s**；GPU0。owned-tree峰RSS **4338204672B≈4.04GiB**，不是整个准备包CPU/AS峰值。
- 第1子步marker→最后闭合trace **37.9505699659s**；失败计数事件elapsed37.9494283283s。未接受的step没有成功step-wall事件，不能伪造accepted elapsed。phase余时为准入/调度/退出等包含项，未细分。
- 错误`cannot represent feasible actual trust step`；guardian的unfinished-step记录是worker异常退出后的次级结果，未到300s。首停时outer2，方向2/8，fresh2/100，inner updates4/16，action upper24/100，不是资源或迭代额度耗尽。
- 全部**162文件112061131B**（runroot150文件1384123B、archive12文件110677008B）按终态清单逐bytes/SHA取回，未只取摘要。4自有PID48885/48886/48903/48904均absent；原state0/latest fingerprint仍`fdedddad…`、version0，只有state0000，无任何CAS/history commit。

本地完整原件与分析：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v10_20261021/`。`full_remote_inventory.json`、`complete_return_verification.json`、`recovered_verified/`是证据；`analysis/analyse_saved.py`仅保存数组代数/图，不重新装配、分解或求解FEM。

## 哪些部分实际起了作用

第1outer构造了通过充分模型下降检查的可行Cauchy点，保存required下界`1.3883111554090189e-8`、保守下降下界`2.7766223095372085e-8`、直接模型pred_lower`5.3347887648539176e-8`。有限改进和合格Newton比较后，最终选中Newton比较候选，模型pred_lower`4.833261032682769e-7`，不劣于Cauchy；实际fresh后rho **0.9663843325**，Phi **4.8332610344e-7→1.6247329602e-8**，约降29.75倍。此处不是Cauchy点直接成为被评估候选。

但原m_work升至**218.1846483**，Ru_L2 **2.1818464831e-6**（原门1e-8）、damage KKT_inf **1.8151024744e-6**（原门1e-7）。working objective下降允许暂时不平衡；没有触发最终QP，没有物理接受或label。两次完整fresh中f均1，不能建立真实f<1覆盖。

两次原块方向都通过既有effective双行/绝对门；第一方向极小机械RHS启用了既有roundoff条款：严格relative **0.007667902>0.001**，但trueL2`1.68444e-17`低于原roundoff界`5.63052e-16`且满足原绝对门。第二方向严格relative约`3.33e-13`。不能写成“两次严格relative均<=.001”，本次没有修改该条款。

![R007工作目标与原物理残差](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v10_20261021/analysis/r7_globalization_trace.png)

看见什么：唯一真实试探的Phi下降，而原归一化残差仍远高于门槛；实际时间也主要不是LS内迭代本身。
说明什么：模型下降与原物理接受必须分开；这次还没完成足以判断长程耦合性能的生产前缀。

## 首停究竟发生在哪里

运行traceback精确落在`solve_box_model`中**可选Newton比较候选**的`feasible_candidate(yn,...)`。当时Cauchy内部证书已经返回、两次PG模型评价已完成；随后Newton候选做状态投影与最多两次向内nextafter，向上TR误差界仍高于radius，按事前首停规则抛错。action upper24=J3+JT3+absJ3+absJT1+norm scans2+原块保守12；这不是24次完整J调用。

**保存数据的边界**：第二outer最新J/r0/w/D/baseu,d/branch和原Newton方向已经保存，但内部Cauchy数值证书及失败Newton候选在函数返回前抛错，未到候选前保存hook；没有该失败候选的fresh物理残差。残留`last_box_trial_before`属于第一outer，不能与第二outer最新J拼成同一点评价。第二outerCauchy通过只能由traceback和控制流确认，不能假称其证书数值已经持久化。

对已保存base/D/原方向作**离线确定性候选代数重放**，无新FEM/J装配/分解，复现向上界未通过分量数 **6→5→1**。最后一项为damage node32062（联合索引204978），base`5.38802338346719e-6`，D`70.32458386204867`；两次修正后重构x`0.001427365865387676`。向上界为`0.10000000000000002`，radius为表示浮点`.1`，但Fraction精确二进制比较得到真正`D*(x-base)`**在radius内**，余量`3.7205071373019344e-17`。其余分量已通过有效上界。因此重放支持：**保守上界在两次修正额度内无法认证一个实际可行的候选**；并不证明实际TR越界、不存在可表示可行步、子问题无解或原物理方程无根。节点/重构x是离线读数，不冒充运行中已保存的失败内部候选，也不是物理瓶颈定位。

## 剩余耗时与数据能力

完成/失败闭合的非嵌套root工作总**36.2885410693s**：原机械预测8.019458s、两次块LU11.396225s、LS子问题1.292558s（其中失败轮约.525537s）、两次model证据写入7.019737s，其他8.560561s。marker到trace差额**1.6620288966s未分摊/UNKNOWN**；嵌套LU/GMRES不重复加到机械父块。诊断开销实际可见，但本次直接停止原因是可行化认证，不能因而删掉必要证据或宣称主要数值成本已消失。

![唯一实际评价的工作场](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v10_20261021/analysis/r7_last_joint_fields.png)

图示同一step1载荷下保存的fresh1→fresh2工作场及实际差；二者均未接受，不是未保存的第二outer失败候选。

![全部可用接受场只有state0](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v10_20261021/analysis/r7_accepted_prefix_fields.png)

![接受演化可用性](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v10_20261021/analysis/r7_available_prefix_evolution.png)

只有原初态u/v/d/driver/A/f，无新接受步、反力演化、卸载、fatigue退化或NN比较。图上明确反力记录缺失，不制造600步曲线。41秒失败与R00657秒接受第1步质量不同，不能作为加速对照。

## 下一步修复建议，仅方案

本次不支持更换网络、加训练、松物理门、增300秒或回到旧Schur方案。应先修**表示可行性判定与可选候选的组合规则**，保留已通过的Cauchy框架：

1. 用有向舍入的状态区间端点构造可表示可行点；对上界与radius重叠的少数分量做事前有界的精确二进制比较（可复用stdlib整数/Fraction，不装新solver）。只有真正越界才继续向内投影；不以“固定再加一两次ULP”当一般保证，不使用atol放宽TR。
2. 事前定义：Cauchy/主LS候选必须通过充分下降和可行性证书；可选Newton比较无法资格时**不替换已有合格best**，不是让一个可选增强使整个合格子问题无返回。实际nonfinite/原方向质量/最终物理资格失败仍首停。此规则必须前瞻审核，不能在本次失败后现场fallback重跑。
3. Cauchy/PG各阶段一旦完成，先持久化其最少数值证书与候选身份，再尝试可选比较；失败前记录具体阶段、最坏区间及触发分量。大J仍只每outer覆盖一次，避免每matvec写盘。

判别签名是：对本次保存数组的区间重叠反例能准确判为可行，同时真实越界仍被拒；原Cauchy下界/JJT/有限资源包络保持；随后才有资格提出一个新的原轨迹生产尝试。本次唯一attempt已消费，**不自动R008、不实现或运行后续修复**。研究处置为repair proposal／当前科学运行closed negative；完整轨迹可行性仍未解决。
