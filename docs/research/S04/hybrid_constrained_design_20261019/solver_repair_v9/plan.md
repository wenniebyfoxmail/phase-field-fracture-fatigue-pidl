# D18 R006 — joint projected trust-region original-residual Newton

目的：同原方程、加载、自身历史的train_A连续600接受态，仍是未合格数值候选，不是teacher或NN收益。Continue D17：三次原块方向已过线性精度，R5新未接受的全步投影造成近零刚度局部，机械资格在工作评价前失败。复用R3–R5日志、源码和原阅读/独立审核渠道，不重做基线/新文献轮/真实step2 pilot。

本轮唯一干预是联合位移/损伤全局化，明确替换working merit及普通damage-map/每试探机械消元；原AA操作语义与旧路径保留，新mode不声称实际使用AA。原非零Ru、active释放贡献及稀疏块LU/双行真残差复用。所有working points从相同旧d_n/A_n/r_n生成，永不提交历史。

## Prospective deterministic algorithm

1. 原common mechanical predictor at old damage and new BC；初始working point `(u_pred, d_n)`。原fresh assembly给Ru/free、原QP gradient与natural residual `F=d-clip(d-gradient/scale,d_n,1)`。原old-state fingerprint保持。
2. **仅在step初点冻结** `Wu=1/sqrt(diag(K_ff))`，`Wd=damage_gradient_scale/sqrt(diag(H_QP))`；对角必须finite且strictly positive，无可调floor或结果后换权。二者是原机械/断裂算子Jacobi能量尺度。working objective `phi=.5*(||Wu Ru||²+||Wd F||²)`，两行分量均写。此新工作量不替代原tolerance-normalized m_work或m_accept。
3. 原active-set块Newton取 `(du_free,dd)`，保持原非零Ru、active自然map身份行、inactive原gradient行、双行独立.001/原abs精度及一个general sparse LU，无regularisation/备用法。working states不必机械平衡，因此绝不丢Ru。
4. `||s||T=max(||du||inf/L,||dd||inf)`，`L=norm(ptp(mesh.points,axis=0))`，原域对角长度>0。radius初始.1，上限.25，下限1e-8。`alpha=min(1,radius/||s||T)`，u试探在自由DOF沿du；原Dirichlet恢复，d试探按原old lower/1 clip，precrack=1。**模型用实际s_eff**：Ru_model=Ru+A*su+B*sd_eff；inactive F_model=F+(C*su+D*sd_eff)/original_gradient_scale，active F_model=F+sd_eff。因此包含B*(projected_dd-alpha*dd)等交叉项，不能把原du/clipd说成平衡方向。
5. 每个方向最多8个模型trial：保存候选真实u,d/parent/alpha/radius/projection/model，再从同old trial history重装原残差；不机械反解。`pred=phi_base-phi_model`，`ared=phi_base-phi_actual`，`rho=ared/pred`。pred<=0、zero projected step、rho<.1或ared<=0都按已定规则拒绝/rollback，radius*.25；真实nonfinite、坏形状/身份或异常首失败停，不能吞为重试。pred>0且rho>=.1且ared>0才keep；rho<.25接受亦缩*.25；rho>.75且||s_eff||T>=.9radius扩2，上限.25；其余不变。拒绝不重新factor同一方向；keep后重新组装原块，最多8方向。半径小于1e-8或8trial无keep/8direction用尽即首科学失败，无fallback。
6. 原m_work<=.01且naturalF_inf<=原QPprecision(1e-10)才触发**一次**真实最终QP(用此point实际f_solve)→原mechanical re-equilibration→同old fresh trial/finalQP组装/KKT/force→完整原m_accept<=1→CURRENT K/pivot原finite且>=1e-14→StepProposal→原单CAS。最终失败不退回工作循环，不把working phi下降冒充接受。

上述初始半径/阈值事前固定一套，不扫参数。此法是同一Newton射线的radius缩放投影步及ratio接受，不解trust子问题，不保证Cauchy下降或全局收敛；投影后的pred在任意小半径也可能非正而首停。严格触发条件是前瞻保守认证裕量，代价是可能在已合物理精度的近邻先耗预算；H逆放大与历史链意味着它仍不保证最终QP一次通过。最多99个working fresh，预留第100个给最终认证，全部共用原300s。原最终精度不变；若route失败，只说明该有限策略未到达合格轨迹，不证明原方程无根，不继续加预算或训练。

## Bounds, evidence and decisive test

HQ-FEM-JOINT-PROJECTED-TRUST-REGION-R006-20261021/source human_delegated_hq，新包从2026-10-21T00:23:42Z计4h，绝对结束04:23:42Z（强于07:30Z），含实现/测试/审核/2机械批/一次科学运行/取回分析/原Obsidian归档。4CPU/0GPU/owned-tree RSS与AS<=32GiB；worker30GiB/supervisor1.5GiB/guardian128MiB沿旧界；合计新增primary1+archive7+localreturn8GiB=16GiB含temp；每step300s/fresh100/block directions8/trials per direction8。factor/solve各<=8原块/step，原机械/QP有限上限不改。机械2批累计120s，unknown launch先只读核归属不再spawn。保留R4保守4390s、R5保守3056s（前包开始23:32:46Z到本包00:23:42Z；非CPU/producer且不重加），旧known1232.4626276369672s及600s缺测reserve分别保留。

仅原GPUServer8/drtao@172.16.100.2，原R3inputs只读/98已核OSQP同机复制，小公共源码上传；无新private/host/holdout/GPU query/install。新的不可覆盖R006从原state0执行原train_A600，本生产前缀非pilot；一次首真实科学失败停无自动R007。其他5case/3600/NN训练禁止。

先做必要人工小数组：非零Ru、f1/f<1与单侧导数、严重投影后的模型交叉项、近零支撑trial无需机械反解、拒绝与半径耗尽、原lower/BC/旧历史、最终QP/机械/pivot/m_accept无绕过；复用旧块/AA合格检查。原所选独立Codex聚焦改动，准确卡/源hash绑定后同包自动准入一次launch，不新增行政审批。

每trial前固定latest原u/d/parent/半径/预测/投影；完整JSONL记每次rho/actual/model/两行工作残差。资格抛错前记录实际pivot finite/raw ratio或明确nonfinite、matrix key/stage/branch。全部接受u/v/d/driver/A/r/f/反力及旧字段保持，逐case/step elapsed含失败，完整文件/hash取回，CPU/calendar/reserve/UNKNOWN分开。保存证据结果必要复审，四类图沿D17表达，原Roadmap一步闭合。未达到原精度的600连续接受态仍负结果。
