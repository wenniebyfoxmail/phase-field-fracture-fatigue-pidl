# D20 R008 — representable box/TR certification and optional-candidate composition

目的：继续原方程/加载/自身历史train_A600数值可行性。Continue D19，不恢复R007或旧失败；只修已由保存数组证实的保守TR上界误拒与可选候选组合/证书保存顺序。R0070/600、firsttrialPhi29.75倍下降但原m_work218.185、secondouterCauchy数值缺测、162原文件与所有费用永久保留。复用R007完整算法和原所选独审，不新检索、不改Schur/物理/网络、不native pilot。

## Fixed representable-domain proof

给定表示binary64 base x0、正D、正radius R，真实TR为abs(D*(x-x0))<=R；p的精确状态差继续以TwoDiff high+tail表示。所有underflow/subnormal/nonfinite/dtype/shape/原base或box身份错仍真错误首停，不借可选候选跳过。

1. 令q=fl(R/D)，qminus=nextafter(q,-inf)、qplus=nextafter(q,+inf)。在现有normal有限域下，qminus<=实数R/D<=qplus；明确检查不支持范围，不把最近舍入q当严格界。
2. 可表示**内端点**为Linner=succ(fl(x0-qminus))、Uinner=pred(fl(x0+qminus))。若和为零，normal表示数的精确相消保留零；每个端点再保留base：Linner=min(Linner,x0)、Uinner=max(Uinner,x0)，最后与原精确表示box相交。因此不会用向内舍入删去永远合法的零步。上述端点分别位于真实端点内侧；这是一条有证明的端点构造，不是固定多挪几ULP的经验循环。
3. **外端点**用qplus与相反有向舍入，包围真实合法状态区间，同原box相交。主/可选点先按给定scaled proposal生成表示状态，再投影到内区间；恢复原u Dirichlet/precrack，得到严格可行可表示x，不改原d_n下界或物理方程。collapsed interval只保留base；若主Cauchy实际步丢失仍按原非零残差停，不能当根。
4. 验证函数保留旧raw abs(D*high)+abs(D*tail)向上界。位于已证明内区间，或原向上界<=R的分量可直接认证；只有其余重叠项才用stdlib Fraction.from_float对原浮点**精确二进制值**判abs(D*(x-x0))<=representedR，绝不经str/decimal/rounded D*p。真实box外/外包络外/精确TR外不能通过。
5. 单候选合计最多**64项精确比较、CPU0.1s**，整个认证上下文不按分量/内部尝试重置。每次Fraction原子操作前后process_time检查；原子调用的超调只能后采样观察并停止，**不声称严格零CPU超调**。binary64有界位数，不能任意精度全扫描；64/65与CPU耗尽人工检查。原J/JT100、16updates/8outer和step300不变；精确比较单列计费/计数，按Budget跨同outer回溯累计，不混成J动作或重置counter。
6. 记录raw松上界与**certified upper**及来源分开。仅在内区间证明或精确不等式证明后，才可把R作为该分量有效上界，与原raw上界取min；不是无证据clip误差。保存dtype、D/base/x/radius hex、exact margin整数分子/分母、触发索引和内/外/box区间、比较used/CPU/budget。

所有原模型r0=fl(wG)、J/JT、w/D step初冻结、Lbar、Cauchy充分下降、PG与Newton比较的模型区间和actual high+tail完整交叉项保持R007。D尺度与R006几何radius不同。新增box_domain_policy='representable_inner_binary64_v1'进入coupling policy ID，避免把新组合与R007假称完整同策略状态键；原合法state0 fields不拼旧prefix。

## Candidate composition and ordered evidence

- 主Cauchy必须可行且通过原充分下降证书；主PG同类有限资格未完成也停止，不因为已有best吞主错误。原Newton方程方向若计算仍必须通过原各行effective .001 AND绝对/原tinyRHS舍入资格；真实非finite/原方向质量/模型错误/身份/IO/最终CURRENTK失败仍首停。
- **仅可选Newton比较**捕获typed CandidateUncertified：事先枚举的finite box/TR外、有限精确比较额度未完，记录未取得比较资格而不覆盖已认证best。模型未证明更好也保留best。不能广泛catch RuntimeError后继续；underflow、nonfinite和OSError均有传播测试。本包前瞻规定，不回到R007首停后现场fallback。
- Cauchy可行点在模型前存最少p/base，模型评价后存pred区间，再在Cauchy证书完成时持久化证书；两次PG完成各保存候选p及retained-best p、证书/模型/parent/实际可行性。只有这些完成后进入optional。stage evidence IO失败阻止后续optional；异常前记录stage，有限资格失败还保存具体触发区间/候选high+tail。
- 大J/r0/w/D/branch仍每outer只覆盖一次；model前候选用一个覆盖文件，Cauchy/PG/optional完成记录各stage latest，JSONL含outer/parent/modelr0ID/DID/radius，禁止错配不同outer的残留。额外向量为O(n)，不每matvec输出矩阵。所有IO计原step300和存储门。
- 非线性rho规则、原100fresh/8outer/100actions/16updates、original m_work/naturalF触发、真实finalQP→mechanics→CURRENTK pivot>=1e-14→完整m_accept→真实f_solve/f_commit→singleCAS完全沿R007；无eta、正则改方程、松tol或低精度teacher。

## Necessary checks, exact review and sole production attempt

只给定小数组与R007保存base/D/direction/oldlower代数控制delta：严格内/外端点、base零步、精确边界/equality与真正outside nextafter、64/65/CPU耗尽、hard damage/precrack、相消TwoDiff、主失败停止、optional finite不覆盖best、真range/IO传播、Cauchy证据IO故障使optional未执行、R007 node32062反例全向量认证。无native装配/factor/真实step1/2 pilot，原未改切线/历史/final资格审核复用。原独立Codex只聚焦上述逻辑、日志/计数/精确版本绑定；无法证明主资格或有限资源包络就准入前park。

新fresh不可覆盖run pf_hybrid_solver_v11_20261021_r8，从原合法初态原train_A600连续，只有此case。先核R007终态和自有4PID退出、新R008root/claim不存在，未知启动只查自有回执不重发。没有其他5case/3600/NN/旧baseline/新private/holdout/host/install/GPUprobe；R3inputs只读，98已核公共OSQP同机复制，小审核绑定源码包部署。

## Shared clock, limits and closure

HQ-FEM-REPRESENTABLE-BOX-TR-CERTIFICATION-R008-20261021 / human_delegated_hq。本新动作保守receipt **2026-10-21T02:24:52Z**，最多9000s，故本动作结束 **04:54:52Z**，严于原共享截止05:04:27Z。**原共享计费起点仍01:04:27Z**；到R008receipt已用4825s，旧R007dated4551.083195/closure4604.920679/padded4724.920679各保留，其后至receipt100.079321s为idle/UNKNOWN包含项，不把padding称CPU或另叠加原费用。共享允许到04:54:52共13825s；CPU运行可用共享13225s扣已用preparation，始终留>=600s取回收尾及45s终止。此处是两个时钟交集，**不是给R008新4h或续R007科学attempt**。

4CPU/0GPU、owned-tree RSS与AS32GiB、worker30GiB/supervisor1.5GiB/guardian128MiB；新primary1+remote archive7+localreturn8GiB共16GiB含temp。原O(nnzJ+n)内存包络沿用，无新增正常矩阵/Gram/因子/谱；exact最多64个binary64标量有界整数，额外stage latest向量可覆盖且有原步存储headroom及终态扫描。最多2新机械批累计120s含unknown归属，R007两机械不复用为新额度也不从旧账删除。首科学失败/资源IO权限身份错即停，完整保存partial，无autoR009。

旧known1232.4626276369672/R44390/R53056/R0062445及历史缺测reserve600、原136hosth/617.324/12GPUh全部保留。R008终态shared calendar包含R0074825；另列R008自身action elapsed，**不把R007再加到shared elapsed**；producer/case/CPU/GPU/取回/整包CPU UNKNOWN分开。完成或失败均全任务bytes/SHA取回、可用u/v/d/driver/A/r/f/反力演化/失败step elapsed/四类图与sidecars、原渠道保存结果必要复核、原Obsidian报告/mesh/Roadmap同一步收束。只有600原精度连续接受态才能继续teacher判断，未完成的partial不得冒600；当前仍0qualified teacher。
