# D16：全程保护与约化VI耦合，一次连续train_A

沿D12–D15同一owner、工作树和目标：先取得完整自身历史下的合格连续FEM轨迹，再决定完整teacher/NN比较是否值得。R3第2步首停、三次有效AA及内层降本保留，绝不重跑R3作负基线。新authority是**human_delegated_hq**：已用read_thread核到原HQ直接用户消息01a15b4c-2e3a-7772-b74b-46f4ab752766（托管至明早9点、可授权科研计算）；HQ随后前瞻批准本包，非复用已消费R3许可。完整边界见authority.json。

## 连贯干预与机制签名

- 新`guarded_vi_newton`共同数值路径；原力学/损伤/疲劳残差、tol、d_n不可逆下界、活动释放、同一旧态历史及单CAS不变。
- 当前工作点含d/u/freshQP/trial历史/审查/完整factor/key/domain快照。所有ordinary/AA/Newton候选用同一`m_work`严格下降保护；回滚不更新accepted历史。无QP的操作分量为NA，`m_work<=1`不是接受。
- 每次真实QP映射先存冻结QP的原KKT，再机械平衡并fresh审查。只有该真实QP的f_solve与最终trial f_commit满足原完整`m_accept`，且当前K LU/pivot通过，才产生proposal和一次提交。Newton点不得直接成为标签。
- 改善快（ordinary m_work比<.9）时持续有界depth3 AA；成功3次不永久关闭。ordinary停滞/增长（比>=.9或全回溯拒绝）切原残差约化VI Newton。投影节点通过梯度符号可释放。
- 原残差块`[A B; C D]`；C/D含原trial fatigue链，包含loading max和A>alpha分支；不替换为对代入f的能量求导。`S=D-C A^-1 B`用每Newton点固定的当前A精确LU作用，非SPD假定；damage原Hessian inactive块作预条件。活动行delta=-F，inactive RHS扣除S(delta_active)。
- 有限工作：整个子步同一起点300秒、最多100次fresh（含initial、普通、AA、Newton、每个回溯与最终认证）；每方向4个alpha=1,1/2,1/4,1/8。Schur GMRES restart16×最多3cycle，最多64次Schur作用，真线性残差<=1e-3×rhs范数；原mechanics50轮、GMRES20×4、QP200000及真实remaining time不变。无合格方向/内层失败/预算/资源失败即停止，无自动科学重试。

预期签名是第2步穿过原门并继续完整加载/卸载/疲劳600步；不能以降能、小步长、较小m_work、静态拟合或测试数代替。如果严格保护仍无方向或费用超限，保留它作为新耦合候选的阴性结果。

## 准确范围与成本

只做原train_A，base五点载荷、amplitude .8、120cycle/600接受步、原state0/材料/网格。正常首5步属于同一次生产前缀，不另开profile或重启；不启动其余5case、3600整包或fit。GPU0；不查询/占用GPU5。输入只读复用原GPUServer8 R3路径，不发送私有数据、不复制输入或安装/修改共享环境。仅将原stage核验的98个OSQP文件980049bytes在同机复制到新任务隔离deps，原缓存不复制/不读取/不更改；新隔离deps拒绝任何.pyc或__pycache__。

总包4墙钟小时从保守22:19:36Z起扣，含所有本轮准备/审查/部署/尝试/取回/图证，最晚02:19:36Z结束；其中600秒预留取回/分析，生产还须扣45秒终止余量。新包不清零既有已知1232.462627637秒研究成本，也不将历史600秒缺测预留冒作actual或未知CPU冒作0。保守时钟扣额与producer/worker实测分别记录。

最多4CPU共享亲和池、完整归属树RSS/VMS<=32GiB（含outer timeout、supervisor、worker和guardian），并将worker AS限制30GiB、supervisor软限制1.5GiB、guardian128MiB；所有单进程硬限制不超过32GiB。原输入不复制，remote新primary<=1GiB、archive<=7GiB、本地取回<=8GiB，合计<=16GiB；逐步开始保留128MiB archive临时写余量，逐步结束及worker退出后复核大小，辅以运行中扫描，触限停止，不把瞬时/未采到峰值假作已实测保证。每个接受态的全部NPY成员（包含D13证据与metadata）逐成员哈希核对后无损ZIP压缩保存，不能删步或精度转换。当前只验证连续轨迹，故train_A `role=reference`，暂不导出NN训练特征；这不改物理键/接受态，却意味着成功也不等于训练包已准备完整。

机械零启动准入最多2个动作、累计120秒：一次只读CPU/内存/原数据/归属核对和一次已审小代码包部署/提交，各远程timeout20秒、连接10秒、本地上限45秒；余量含清理，不循环探资源。科学worker只允许启动一次。未知执行先查原reservation/receipt/归属，不换RunID再投。所有本轮费用计同包。

## 复用与新增检查

复用R3物理内核、MechanicsWorkspace/旧LU预条件、damage QP、trial_history、bind_proposal/StateStore、PersistentWorkTrace及Linux pidfd gate/guardian/run_owned_worker。CPU专用入口只冻结单轨迹、4CPU/0GPU/新预算，避免修改旧九phase完整pipeline语义。全部新卡/源码/输入/运行路径/authority/artifact由准确独立复核绑定。

必要人工检查覆盖原B/C/D方向导数（f1/f<1、拉压、加载/卸载及相等处单侧）、投影活动释放、Schur与dense微系统、所有候选统一m_work、无QP NA与实际最终QP、实际改动factor/key/domain后回滚、100fresh/有限动作、坏pivot首停。另核对CPU入口拒绝越界/重复未知启动、初始准入错误仍存终态、无损完整NPZ/原子写失败。不是新增toy科研阶梯或对实际R3重算。

## 证据与结果规则

每case保留完整elapsed、接受步数、错误/guardian、每fresh/回滚/AA/Schur记录；新增每GMRES调用返回码、累计inner计数、真残差与target及矩阵身份，最坏KKT节点/符号/lower gap，冻结QP与平衡后KKT分列。仅保留**最新一对**Newton前best与之后候选全场快照（两个固定tag覆盖），明确`UNACCEPTED_SOLVER_WORK_POINT_NOT_LABEL`及parent/load/outer，绝不声称保存所有候选、不混入states/标签。全部候选标量/work trace仍保留。复用OSQP逐文件SHA来自原R3 stage收据，准入对98个文件与闭合文件集合核验，不能仅以版本字符串替代。

成功仅称该600步连续自身历史轨迹在原合同下完成，报告f<1及加载/卸载实际覆盖；不能称唯一/物理真解、完整teacher或NN收益。失败保留所有已接受状态与未接受候选，不拼接成合格轨迹。复用R3已有标量/worktrace和已接受前缀作删失比较；不同CPU数及方法一揽子变更不是纯因子速度A/B。图证展示残差/成本、全场/反力/历史与失败签名，并回原Obsidian living report及Roadmap；下一决定是是否值得完整teacher，不自动扩展。
