# 完整混合路线：一次成套性能修复准备

目的仍是PIDL尽量接近同问题FEM，并检验网络初值相对强数值基线的附加价值。继续D9性能修复，不退回逐权重／硬约束微测试。原R1 time-stop、1接受态、0训练、0GPU秒保持不变。本轮只代码、人工单元／接口与差异复审；无SSH、新profile、真实状态求解、训练、预检或producer重跑，没有另立Run ID。

## 实测瓶颈与整套修复机制

首步56.9524秒：机械46.1803秒(81.09%)、QP5.6860秒、其他solver3.3176秒、保存等1.7685秒。第2步只知120秒触发停止，未保存内部work，不能断言具体根因。旧机械函数会重建当前边界驱动的线性初猜，没有复用上一轮收敛u。

新hybrid-only workspace接收同一路径自己的旧u/上一耦合迭代u；按旧／新边界的最小二乘幅值比缩放并投影当前Dirichlet，再由该实际位移重建trace active set。全零旧态用原边界线性初猜。active set仅是迭代初猜，不限制可变空间。预计算固定几何／材料的vol/dev单元张量和CSR scatter索引；数值LU仅当freeDOFs与完整CSC(data/indices/indptr)字节hash完全相同时复用。d、sign或BC集合变化造成矩阵变化即失效；材料变化拒绝旧workspace，需新身份backend。SciPy SuperLU没有本包可用的独立符号重分解API，本轮不声称符号factor缓存。

reference/classical/hybrid三臂用同一新mechanics策略、同线程/精度/硬件；每条完整轨迹单独backend/cache，只从自己的前态推进。不能把共同机械修复收益算成NN收益。原PIDL/native函数不改。接受态／trial A/r/f、完整节点K、原QP/force/KKT/f容差不改；每次机械返回仍用未缓存旧装配独立审查，最终joint force/KKT/trial仍fresh，一次CAS提交。非凸分支差异由后述能量/trace/front诊断呈现。

## 四风险差异处理（复用43af/独立v4未变发现）

| 项 | 43af剩余缺口 | 本包处理 |
|---|---|---|
| R1 | monitor的walk/fsync仍可能阻塞deadline；成功退出缺少独立终审 | 独立Linux pidfd控制进程，worker先等ready/gate再导入数值库；用datagram IPC发step start/done，不读marker文件执行时限；控制异常fail closed；杀工作进程先于report IO；退出排空IPC并终审。全局/phase/GPU/shared保留45秒reserve，子步仍120秒触发；不是硬实时OS保证 |
| R2 | killed phase丢失已测peak/storage | 共享usage每次测量即更新，异常/清理也带peak、last storage、stop reason、termination及guardian receipt；GPU超限读数先存后报错。文件系统永久失败不能承诺可落盘，但不能继续计算或把缺数写成0 |
| R3 | classical质量未纳联合speed结论 | 两候选使用相同原field/history/reaction阈值；二者均合格才可称matched-quality neural acceleration，失败各自单列，阈值不变 |
| R4 | raw/active、能量/branch、front/可行性/回退、场图及被杀前内部work缺失 | common posthoc独立评分：raw与Carrara driver全域/参考diffuse zone/固定初尖端窗；elastic/fracture/total energy与trace branch；d=.5支撑IoU/front Hausdorff/tip；own-predecessor负damage/healing；初值到最终修正及fallback。固定steps4/304/599/600共色标u/v/d/error和raw/active GP图，PNG/PDF+sidecar+provenance/README。start/end块日志先fsync再操作，外杀保留未闭合start；inspect列unfinished blocks |

所有新诊断只在候选轨迹封存后读取reference；不用于在线初值、选模、阈值或挽救原primary。nodal字段图固定三角拆分仅显示；评分仍native2x2GP。raw/active图为GP加权单元均值与GP误差RMS，色标在同step跨方法共享，跨step不宣称相同范围。参考diffuse zone定义d_GP∈[.05,.95]；固定tip窗x∈[-.02,.12], |y|≤3ell。空zone/front显式null，不填0伪装成功。

## 修订完整比较包与有依据预算（仅提案）

同state0/材料/mesh：train_A(.8)与train_B(1.2)各600接受子步，validation(1.0)600；仅完整1200/600标签后单次网络fit；冻结后test(.9)直接参考/经典secant/NN各600，全部自身历史推进。共3600数值子步。旧已见五态和R1单接受态不拼凑成训练集；原关闭数据仍关闭。网络/损失权重/硬约束不改。

原4h混合阶段要求600步均值≤24秒；首步非机械开销约10.772秒，以首步结构作敏感性反推，机械需降约71.4%，尚无此实测证据。故准备卡在同12GPUh总额内提出训练6h／混合6h（单fit20k上限/原早停规则）；混合均值≤36秒，对应首步机械需降约45.4%。这只是单步结构下的目标条件，不是整轨迹预测或已测收益。若改造不能满足，完整600步仍可能因预算停，不能自动扩时。

五条CPU数值phase各≤20h，NN混合≤6h、训练≤6h，共同replay+分析≤4h，phase上限合计116h；含监督开销独立全局≤136墙钟h／16core≤2176核h。RAM64GiB、VRAM24GiB，primary128GiB+archive128GiB。固定张量／scatter约新增0.4GiB常驻（由86756节点/86408Q4形状推算，不是实测峰值）；其setup、缓存、guardian、逐块fsync、失败和统一评分全部入成本。

preparation_card的execution_enabled=false、run_id/root=null且schema非执行schema；新代码拒绝未明确开启的执行卡。R1不恢复、不换ID绕过。本包当前只能声称实现/非科学检查/精确差异审查准备。新Linux pidfd/IPC实机、实际网格缓存装配一致性与整链性能尚未验证；本轮不做这些预检。未来执行需HQ/用户明确授权精确新包及预算，再冻结可执行Run ID/运行时/准入，不继承R1启动许可。

## 检查与审查范围

沿用原46项未变合同检查，新增人工distorted-Q4张量装配与未缓存legacy一致、warm/cold解一致/数值LU失效、日志先于工作/失败、guardian杀工作先于report IO、ready失败回收、失败peak保留、classical质量失败限制联合claim、诊断与人工字段渲染、unfinished work识别。新Linux系统调用由人工替身检查控制逻辑，绝不冒充实机测试。人工图显式标ARTIFICIAL UNIT ARRAYS，不是FEM/PIDL结果。精确源与准备卡以performance_source_manifest_v1绑定，再做独立差异复审；旧设计/v4与R1结果保留。
