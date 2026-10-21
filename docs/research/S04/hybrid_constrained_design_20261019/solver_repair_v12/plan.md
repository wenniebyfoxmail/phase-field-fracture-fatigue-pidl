# D21：盒约束内的有限活动面CG改进，准备版

目的：同原FEM方程、精度、加载及真实自身历史下完成连续train_A600，继而才有条件比较神经初猜的额外价值。R008已独立复核首步0/600；本轮按用户“推进下一步”继续实现／测试／原选独审／准备准确预算，**执行卡禁用，未获新科学尝试许可，未SSH或运行FEM**。旧R008的首停、源、费用和时钟不重开。

复用：R008 saved-algebra/result显示7次可行optional Newton的模型pred为负、PG小步的rho近1；末Phi降36.78倍却Ru173.23tol/KKT15.69tol。保留 `Model`/原J及权重/D、表示域证书、Cauchy下界、真实fresh、最终QP／当前K／f_solve/f_commit／CAS。当前D21只改原固定局部模型内的可行方向，不同时更换工作目标或物理容差。源码复用 `hybrid_box_residual_subproblem.py`，新 `hybrid_box_krylov.py`，新策略进入policy ID。

## 机制与精确算法

固定模型 `q(y)=.5||r0+A y||²`，`A=diag(w) J diag(1/D)`；原物理盒与 `||y_actual||inf<=R` 仍通过有向舍入状态区间／high+tail认证。先执行原合格Cauchy，然后至多8次活动面CG改进：

1. 用现有实际候选残差做A转置作用；仅当位于状态内区间端点且梯度指向域外，或区间固定，才阻塞分量。梯度指向内部时释放，不以容差带冻结不可逆活动集。
2. 同一可行面且前一步未截断时使用Fletcher–Reeves二次CG递推；活动面变化、边界截断或方向指向域外时重启为投影负梯度。仅当有界点积的方向导数上界为负才继续；零投影梯度、未认证曲率或有限预算终止只返回已有合格best，不等于物理根或子问题已最优。
3. 计算A*v与其平方范数，取一维二次最优步长和首次边界交点的较小者。**不组装A.T A、Gram／稠密子空间矩阵，不作谱估计或物理正则化。**
4. 将提议转为真实可表示u/d，重新认证原域与TR，再用原Model/high+tail计算保守模型下降区间。仅`candidate.pred_lower>=best.pred_upper`才替换；否则结束该有限增强并保留best。所有真正range/nonfinite/身份／IO异常仍传播，主Cauchy资格仍必须通过。
5. 原optional Newton比较保留为可选增强，有4动作预留时才尝试；它不能替换更好的合格CG/Cauchy。原非线性rho与最终物理接受路径未改。

来源仅作结构参照：PETSc官方TAOGPCG页面描述活动集CG用于盒约束；TAO手册“Gradient Projection Conjugate Gradient Method”限定其凸二次目标。本项目固定LS二次型为半正定，采用有限改进／表示域证书与原Cauchy保护，**不是PETSc实现复刻，也不继承其收敛结论**；无PETSc依赖或安装。[官方接口](https://petsc.org/release/manualpages/Tao/TAOGPCG/)／[官方手册](https://petsc.org/release/manual/tao/#gradient-projection-conjugate-gradient-method-gpcg)／[官方源码](https://petsc.org/main/src/tao/quadratic/impls/gpcg/gpcg.c.html)。agent-reach Exa一次定向查询及官方正文核对；未获得／声称阅读Moré–Toraldo原稿，不是新系统综述。

## 操作、证据与预算

每外层仍<=100 charged actions（原块保守12、J/JT、abs动作与norm scans），<=16 Cauchy/CG/optional/radius总更新。每CG迭代先预留最坏11动作：JT1、J1、候选J/absJ最多4、四扫描及最多一次额外下降重启扫描；另为optional留4动作。状态区间初始化额外计1扫描。预算不足即明确停止增强，不产生超额半次算子调用。真实动作可少于预留，日志记录实际累计；重复半径尝试共用同一Budget，不重置。

复用stage observer与lossless snapshot：Cauchy先存，Krylov候选前／完成存实际u/d/high+tail和当前best；stage名覆盖最新向量文件，JSON每次留iteration、free-mask ID、原outer/parent/load/r0/D/weights、步长、边界截断、模型区间、动作／更新、退出原因。不能把覆盖文件说成所有轮向量均留存。外层新元数据记录Krylov状态／次数，`subproblem_optimality_certified=false`始终明确。

Mac验证仅给定小矩阵／模拟卡控制；独立穷举活跃面 oracle用于n<=4的二次例子，覆盖直接裁剪Newton变坏、耦合子空间改善、半正定、活动释放、边界步、有限预算和异常传播。已有native6项与R007大数组1项排除；无本机native装配、项目保存大J优化、新真实候选、训练或远端版本探针。工程测试不建立FEM收敛或性能。

## 拟审批的一次科学尝试

建议仍为原服务器 `drtao@172.16.100.2`，**全新候选目录**`pf_hybrid_solver_v12_20261021_r9`，原R3 inputs只读、98个公共OSQP文件同机复制；同原state0启动，原train_A120周期×5子步=600，无其他case／NN／旧负基线重跑。

拟总包**4墙钟小时**，4CPU／0GPU、进程树RSS与AS<=32GiB、remote primary1GiB+archive7GiB+localreturn8GiB合计16GiB；至少1800秒留取回／结果复核／图／归档，45秒终止余量。单步300秒／100fresh（99工作+1最终）／8外层及上述100动作16更新不变。最多2次机械动作、合计120秒。首个科学、资源、身份或IO失败立即停，不自动重试／恢复；未知启动结果先核自有回执，不重复worker。

**这4小时是新提案，不是旧R008剩余额度或既有批准。** 提案保守计时自本轮首次核查2026-10-21 10:44:03Z起，含准备、等待审批、准入、未来一次运行及完整收尾，绝对截止14:44:03Z（英国15:44:03）。禁用卡在批准前拒绝启动；过期则park，不自动改起点。1800秒是预留而非完整归档必成的承诺，若未能全量闭合按PARTIAL如实报告。

准确卡 `execution_card.json` 当前 `execution_enabled=false/execution_authority=null`。静态复审绑定规范化template ID和源artifact；未来仅在用户明确批准此次服务器／源码文件及预算后填入原始批准消息与`execution_enabled=true`，重新机械核对实际卡SHA／template ID／源／时钟。任何科学／数据／预算字段变化都不能通过规范化，需修改提案和相应复审。有限CG虽然不显式组装正规矩阵，仍受正规算子的谱性／近相关列影响；本次未测真实条件数，不能由小矩阵收益推断FEM收益。没有实时准入通过的事实；版本与资源在未来获准后的单次只读准入及runtime导入检查中确认，不据R008旧快照声称当前可用。

原研究已知／保守累计19079.39567373949秒保留（含R008最终120秒余量，旧分项不重加），本轮准备日期成本另记；全包CPU及Mac峰值未完整采样仍UNKNOWN。源／审批文件是小包（2MiB压缩／4MiB展开上限），不会上传原私有输入。新调用脚本未执行。

## 决策尺度与下一判别

未来若获准，直接原连续600轨迹，首错即停，沿每case elapsed及实际原物理门报告。成功签名是原接受态连续推进、经真实QP／机械／history认证，且在预算内完成，不是小矩阵oracle、更多Phi下降或更长单步。若子问题内仍只给微小可行步或原Ru/KKT停滞，应据模型最优性缺口／活动面／原残差成本证据转向尺度目标或数值结构；不自动继续堆CG步数、改网络或补训练。尚无真实速度或完整轨迹成功结论。
