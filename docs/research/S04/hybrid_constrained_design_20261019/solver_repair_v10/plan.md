# D19 R007 — feasible box residual least-squares trust subproblem

目的：继续原方程、自身历史、原train_A600接受态的数值可行性问题；不是六case比较、teacher合格或NN收益。Continue D18，复用R3–R006已核日志/代码/负结果/文献及原独审渠道，不重跑旧基线、不新检索、不真实step2 pilot。R006的Phi下降约908倍仍Ru超原门约1639倍，8方向用尽；旧radius-scaled Newton ray没有约束模型充分下降保证。本包只干预这一个承重机制，不修改原F=0。

## Fixed numerical model and finite algorithm

1. 原common机械预测器从合法原初态、原加载推进。每个step旧d_n/A_n/r_n不可变；working candidate只由同一旧态计算trial history/ftrial。全残差G=(Ru_free,F_natural)，F=d-project_[d_n,1](d-original_gradient/scale)。原自然VI活动行用identity，错误符号bound可释放，precrack保持固定。working状态不要求机械平衡，不删除Ru。
2. 行乘子w在step初点冻结：Wu=1/sqrt(diag(initial K_ff))，Wd=original_gradient_scale/sqrt(diag(initial H_QP))。对角必须正finite，无floor。变量尺度D在step第一原广义J处冻结为computed weighted-J column2norm，正finite且无zero column；此后不随accepted working point改变。TR为||D p_exact||inf<=radius（与R006几何norm不同，不能按同radius做因果归因）。初始化radius.1/max.25/min1e-8，一套参数不扫。
3. 每outer重新组原自然残差广义稀疏J=[[A,B],[Iinactive*C/scale,Iinactive*Ddamage/scale+Iactive]]，含原ftrial历史链和全部交叉项。实际使用的二次模型精确定义为q(p)=.5||r0+diag(w)J p||²，其中**r0=fl(w*G)**是冻结computed基向量；J,w,D也是冻结表示数据，在理论证书中按实数解释。该定义不把r0冒充无舍入的wG。原实际objective仍按相同w计算；无改变物理方程/原接受门。
4. M=diag(w)J diag(D^-1)，由稀疏绝对行列和及标准gamma/outward界取Lbar>=||M||1||M||inf>=||M||2²。不测谱、不形成JTWJ/稠密Gram，不新增真实因子pilot。g=D^-1 J^T(w*r0)。scaled box与infinityTR交集含0，理想Cauchy yc=project_box(-g/Lbar)。投影最优性给-g·yc>=Lbar||yc||²，因此q(0)-q(pc)>=.5Lbar||yc||²。
5. 返回状态先恢复原u边界、原d_n<=d<=1与precrack。**实际状态之精确差以Knuth TwoDiff high+tail保存**，不能把fl(x-xbase)视为精确差。Jhigh及Jtail均实际作用并计账；模型/方向交叉项/梯度证书包含tail。TR按逐分量向上乘积与和界核对，最多2次nextafter向base修正，否则停止；无可调atol。p=high+tail。所有保存候选包含实际u/d、high/tail/Cauchy high/tail。
6. 对实际Cauchy p，利用h=J^T(w*r0)及稀疏JT误差界、dot误差界、D*p范数上界，认证 -h·p-.5Lbar||Dp||² >= .25Lbar||Dp||²>0；另独立前向J模型pred_lower也须>=同一充分下降下界。所有误差用binary64 EPS及操作数gamma/outward界，不靠经验atol；subnormal、潜在product underflow/overflow、零投影梯度但G非零、状态加法吞步或无法认证均明确停。此证书仅当前分支线性模型，不能证明实际非线性下降、根或全局收敛。
7. 在同box/TR下最多2次投影LS梯度改进，再与原合格稀疏块Newton的可行候选比较；只有candidate.pred_lower>=best.pred_upper才替换，区间重叠则保留best。最终model至少不劣于原Cauchy。原块Newton每outer最多一个原general LU/solve，仍执行原独立双行.001/effective roundoff+绝对门；失败首停，不切换到Cauchy救已失败的Newton。Cauchy/LS不是解Jp=-G，不强套Newton两行资格。
8. 每outer最多100合计动作：J、JT、absJ、absJT、metric/norm scans全部保守计入；原块操作另预扣12 upper（Bdelta/Ddelta2、true rows4、abs rows4、原gradient与mechanical residual2），不是宣称12次完整J调用。实际tail多一次J/absJ亦计。每outer最多16合计Cauchy/PG/Newton比较/半径更新；拒绝不重置计数或重做因子。先检查再动作，不越上限。每step最多8outer，共享原300s与100fresh（99working+1final）。
9. fresh后ared=phi_base-phi_actual，rho=ared/pred。pred须已有正下界；仅ared>0且rho>=.1保留，rho<.25缩radius*.25，rho>.75且实际TR上界>=.9radius扩2至max.25，其余不变。拒绝完整回滚base。重复实际u/d hash跳过fresh且计半径更新；不能同点重复消耗fresh。资源/模型/原方向质量失败、有限更新用尽或半径塌缩即停，无fallback/autoR008。
10. 原m_work<=.01且naturalF_inf<=1e-10触发一次真实最终原QP→机械再平衡→CURRENT K与pivot>=1e-14→完整原m_accept<=1→实际f_solve/f_commit→单CAS。最终资格失败不回working循环。所有原容差、不可逆下界、历史更新时刻及真实操作系数保持。working Phi/LS小不作为accepted label。

## Implementation checks and resource envelope

Mac仅人工数组/单元/原控制检查；无项目mesh求解。覆盖Cauchy解析下界与精确Fraction模型区间、D=1.1/1.2/1.3真实乘积越界、TwoDiff非零tail完整J作用、非零Ru与f1/f<1原切线、活动释放、zero projected gradient nonroot、underflow、100动作/16更新、拒绝共享budget/一outer、原final QP/pivot/physical失败不得提交。原独立Codex聚焦此delta及准确card/artifact。

内存空间是稀疏O(nnz(J)+n)，无O(n²)矩阵；保留原block LU及少数J/absJ/scaledM副本。Q4每element12联合局部DOF给完整J原始条目上界144*86408=12,442,752（未合并上界），CSC每副本数据/index约0.20GiB级；即保守10份约2GiB另加向量与原R006观测4.18GiB峰值，在32GiB包络内有余量。这是结构估算，非新实测峰值或因子fill保证；原owned-tree RSS/AS硬门继续约束实际运行。每outer只覆盖一次latest fullJ模型文件，不每matvec输出矩阵；原每step latest diagnostics和接受态按原归档。R006已接受压缩state1约9.27MB，600份约5.56GB仅作为7GiB归档可行估算，压缩率不保证；所有temp+primary1/remote archive7/localreturn8GiB共16GiB硬门及原step headroom检查保留。拒绝/证据IO也计300s。

## Exact authority, costs and one production decision

HQ-FEM-BOX-LINEARIZED-RESIDUAL-TRUST-SUBPROBLEM-R007-20261021，source human_delegated_hq。实际收到2026-10-21T01:04:27Z，4hostwallh绝对结束05:04:27Z（强于07:30Z），包括此前准备、来源核清、审核、控制、运行、完整取回图证与原Obsidian归档；取回预留>=600s，不重新起钟。后续HQ澄清旧R3方案请求不泛化撤回R007；真实更晚人方具体限制仍优先。科学最多一个fresh新run原train_A连续600，原始state0生产前缀，不拼R006前缀/孤立step2/其他5case/NN/GPU/新数据host。

原GPUServer8 drtao@172.16.100.2，4CPU/0GPU/owned-tree RSS及AS32GiB，worker30GiB/supervisor1.5GiB/guardian128MiB；最多2机械批累计120s含unknown归属，第一只读preflight先核本次root/receipt/guard鲜明归属，若已有根不另spawn。只原R3 inputs只读及98已核公共OSQP同机复制，小已审源码上传；无新私有上传/安装/GPUprobe。未知启动只读核收据不重发，首科学失败停。

旧known1232.4626276369672s、R4保守4390s、R5保守3056s、R006保守2445s保留。R0062445按00:23:42Z至新收01:04:27Z日历计，包含dated1580.783519与closure1896.254731及后来idle/UNKNOWN padding，不是实际CPU，不再重加producer160.74943。历史缺测reserve600另列，旧136hosth/617.324不抹除。新hostcalendar/producer/每case-step含失败elapsed/worker+guardianCPU/GPU0/reserve/UNKNOWN分别记，不重复加包含项。

每候选fresh前保存原G/branch/w/D/baseu,d/parent/Cauchy与actual high+tail/model bounds/rho预算；最后modelJ只覆盖一次每outer latest，坏pivot在抛错前保存实际ratio和matrixkey。一次运行或真正准入前park后，全部自有任务文件清单/bytes/SHA完整取回，保存所有可用u/v/d/driver/fatigue/reaction/evolution与四类图及sidecars；原渠道结果复核后更新原报告、mesh对齐与Roadmap一步。不满600仍是未通过数值候选，不自动改网络、tol、历史或重试。
