# D17：原残差稀疏耦合主动集块Newton与明确的AA操作历史

目的：延续D12–D16，先获得原精度、真实自身历史下train_A完整600接受态，决定连续数值teacher是否可达及值得；不是网络收益或物理验证。复用原唯一worktree、R3/R4全部失败/已存证据、A/B/C/D与最终接受合同；不重跑旧基线，不增加网络/其他5case/材料载荷族。

新前瞻授权`HQ-FEM-COUPLED-BLOCK-NEWTON-20261020`，human_delegated_hq；已核先前HQ直接人方托管/计算决定消息01a15b4c-2e3a-7772-b74b-46f4ab752766，后续HQ明确限定此单一新方法包。R4已消费许可/首停不改变。实际接收的首次clock23:32:46Z作为新4h保守起点，最晚2026-10-21T03:32:46Z，强于HQ07:30Z绝对限；含实现/必要原渠道差量复核、部署/准入、一次生产、取回图证/Obsidian。只原GPUServer8 drtao@172.16.100.2，4CPU/0GPU/RSS与AS各<=32GiB，worker30GiB、supervisor1.5GiB、guardian128MiB，完整归属树仍监控。新primary1GiB/archive7GiB/localreturn8GiB共16GiB，含临时写入，不复制旧私有输入。新run`pf_hybrid_solver_v8_20261021_r5`，所有路径全新，不覆盖R3/R4，不resume或第二次worker。

## 核心机制与原方程

R4全程工作残差保护/有限回溯有效，但H-only预条件的有界Schur第二点相对真残差.155253>.001而首停；并查明AA用全步减加后的逐位相等识别操作，误清历史。两者合并修复同一个耦合候选，不能把修复后收敛当已测。

- 新mode `guarded_block_newton`；普通map/AA/Newton均同一m_work严格下降/完整factor-key-domain快照回滚，原AA L1<=5、trust/bounds保护保留。alpha1直接复制target（必要原box投影，无base减加）；以显式full_original_QP_map/alpha及history operation识别真正全QP，只它能加入AA历史。半步/拒绝/方向后的清理原因、长度均落盘。有限改进不是标签。
- 位移约束消元后，原自然残差F=d-clip(d-Rd/scale,d_n,1)，按原z上下界判inactive及释放。活动delta_a=-F_a，固定d_n=1不动。原残差切线A=Ru,u，B=Ru,d，C=Rd,u，D=Rd,d（含f1/f<1/loading/拉压单侧trial链）复用R4，禁止代入f后改能量、加正则改方程或稠密显式Schur。
- 一般稀疏块 `[A B_I; C_I D_II] [delta_u;delta_I] = [-Ru-B_a delta_a; -Rd_I-D_Ia delta_a]`。Ru保留当前真实非零自由残差；Rd直接用原gradient，不以浮点scale*F重构。唯一线性实现：SciPy SuperLU、COLAMD、默认threshold pivot；一次factor/solve，无迭代增加、refinement、ordering扫描、预条件或备用solver。矩阵稀疏标识/dim/nnz、L/U填充、pivot诊断、真残差先保存；当前A不另做方向LU，最终当前K/pivot资格照旧。

## 事前固定的双行线性质量

每行独立取b_u、b_d及原尺度真残差r_u、r_d，relative目标仍.001||b_i||。数值为binary64，零或极小右端不能要求逐位真零：用该行非零运算数m=nnz(Arow)+nnz(Brow)+3（损伤行用C/D）及gamma_m=m*eps/(1-m*eps)，计算 `q_i=||gamma_m*(|A_i||delta_u|+|B_i||delta_I|+|b_i|)||_2`。阈值仅 `max(.001||b_i||,q_i)`，没有可调atol/固定分母floor/跨行尺度。所有项零时q=0；该条处理相消舍入的可达性，不宣称实测谱/误差收敛。

仍同时要求原绝对标准：机械L2<=force_tolerance*force_scale=1e-8；损伤inf<=damage_tolerance*damage_gradient_scale=1e-7且L2<=原joint_sum=4e-6。两行的原relative目标、舍入界、有效目标、实际L2/inf、是否通过均单列，不能靠大机械RHS掩盖损伤误差。矩阵非有限、一般LU失败/真实警告、任一独立真行失败首停。所有运行warning设error，数值因子/solve捕获warning落盘再停。

这只是方向质量，不是物理接受。Newton/AA点m_accept/actual-QP操作疲劳项NA；真实最终QP→机械重平衡→fresh完整m_accept/当前K-pivot→真实f_solve与f_commit→一次CAS不可省。同一子步所有trial从原旧接受A_n/r_n/d_n生成，不提交拒绝态，不改历史，不用loss变化替物理。

## 有限工作、资源及事前准备

原step300秒、最多100fresh（包括initial/普通/AA/Newton/每次回溯），每方向alpha1,1/2,1/4,1/8，最多8次块方向/step；第9次前停止，不必用尽8次。原mechanics50/QP200000及原有有限机械回收GMRES界不变；块方向无Krylov或fallback。首个新科学数值/真实warning/身份权限资源失败整包停，不自动换法/host/card/上限重试。

复用原R3 input只读与98批准公共OSQP文件在同服务器复制到新隔离deps，不读旧cache、不上传新私有数据、不安装/系统变更/探GPU。零启动机械最多2动作、累计120墙钟秒，含一次只读身份/版本来源/容量/输入哈希与一次小源码控制部署/提交；未知launch先查原归属reservation/receipt，不重发worker。

本地只用网格connectivity做稀疏结构计数，不做实尺寸operator/数值因子/孤立第2步pilot：86756节点/86408Q4，自由机械172916，最坏全inactive块维259672，潜在结构nnz上界7008426，基础CSC data/index约85.14MB。它不含LU fill/峰值工作空间，不能证明实际32GiB/300秒可行；R4峰值RSS4.09GiB也仅是已测前缀。没有结构上已明确超限的基础矩阵，但真实LU资源/时间未知，靠原硬界在唯一生产尝试中判断，不另跑尺寸探针或承诺成功。

新4h从接收起不重新给部署满4h，生产扣实现/审核/机械以及600秒取回分析和45秒终止reserve。旧已知研究1232.462627637秒保留；R4从22:19:36Z到本新接收23:32:46Z保守扣4390秒（覆盖旧3689.498快照及后续收尾/空档，非实测CPU/producer，不能重复再加R4的150.709）。旧600秒缺测reserve单列、未知旧CPU不作0。原136hosth/12GPUh账保留，当前无训练/GPU许可。

## 必要差量检查和结果

复用原R4物理/导数/合同/资源检查；本次仅人工小数组检查：非逐位可逆fullQP/半步/拒绝AA操作语义；非零Ru和两个active贡献、释放、f<1链、原Rd而非scaleF；与小系统Schur代数等价；零rhs相消/全零无任意floor/大机械rhs不能掩damage、原abs门；原NA/finalQP/缓存守恒回滚、8direction和100fresh、warning首停；新CPU卡/时间/存储/一次归属控制。使用原独立Codex reviewer，只新差量复核，不新reviewowner或全量重复旧材料。

保存全部iteration/work trace、双行真残差/Ru/KKT/active/branch与耗时/失败；新固定tag best_before_newton/candidate_after_newton/last_rejected_candidate保存最新完整u/d/A/r/f/psi/真实f_solve及明确UNACCEPTED parent/load/outer；last_block_direction保存最近方向/两行rhs/原Ru/Rd/F/自由DOF和inactive/两行真线性残差向量。固定tag可来自不同方向，不伪称同一次前后对，全部标量轨迹仍完整。每个接受态原D13成员无损压缩、全部600步保存，archive headroom及归属树资源/最终扫描照旧。

仅复核无承重缺陷才准确哈希冻结/自动准入/一次原train_A120cycle×原5loads（amplitude.8）完整连续600步；首5步属于同一生产前缀。成功仅称此受限家族合格连续数值轨迹，f<1和加载/卸载覆盖据实报告；仍非全teacher家族、NN额外收益或物理真解。失败保存未接受证据/费用并选一条机制改路线，不训练掩盖。完成声明范围的取回哈希核验、原负基线比较、每case/step含失败elapsed、u/d/driver/fatigue/反力/演化图及费用/必要结果差量复核，在原Obsidian报告/Roadmap记录。
