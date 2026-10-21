# 本地实现检查 · 2026-10-21

- 隔离工作树：worktrees/s04-cyclic-alignment-20261021；基础提交 d1edbeedfa88d371724c9659703158f6173764d7。
- 联合针对性检查：82 passed in 7.95s。覆盖 trial controller、fresh acceptance、raw diagnostics、native recovery、现有 Q4/T3 quadrature、Q4 history、FEM overlay builder。
- 收尾保护后 targeted callback/controller 26项复查通过（7.78s）；8个Python入口AST检查及git diff --check通过。
- 检查仅使用人工 FE 小数组、mock callbacks/optimizers、源码与文件保护；无项目 NN 训练、无 FEM 求解、无完整轨迹。
- Q4/T3 的 fresh 节点力与既有独立 NumPy weak-form 装配对照通过。这个结果是本地代数一致性，不替代实际 MATLAB/MEX 的同状态数值 admission。
- 独立复核：history 作者审 FEM；FEM 作者审 raw/recovery 和 acceptance；raw 作者审 controller/训练集成。发现并修复：strict初始SHA缺失、恢复后初模型覆盖风险、失败目录覆盖、异常工作量漏计、LBFGS软max_eval可越界、非零首步误用recovery、缺失phase BC、罚系数差25倍、窄双边界误消残差。复核采用本线程子代理，无对外发送。
- 通用 strict runner 当前只支持全新U0起步；common frozen controls同样不得从旧目录续跑。初始化SHA、paired initial来源、mesh与policy须显式匹配。
- 固定phase mapping不在裸network.state_dict中。读取checkpoint必须同时恢复common_problem；已保存标志。现有legacy-only exporter拒绝native支持，不能拿旧读取器省略mapping重画新结果。
- PIDL accepted JSON记录的是内存已提交、checkpoint写入之前的状态；必须核验相应network与history checkpoint已完整落盘，不能把单独receipt当持久化完成。
- FEM overlay仅在本地对已核实source字节生成；MATLAB/Octave本机不可用。17例 MATLAB mock、checkcode、disabled-mode实际identity和native admission尚未执行，故未报告运行就绪或科学收益。
- `common_problem_q4.json`从已有审计输入生成，251个固定phase节点和mesh digest已核验。该配置不包含/安装FEM前态；D3条件窗口harness仍需配套实现和审查。

联合检查命令：

```sh
python -m pytest -q tests/test_trial_fatigue_coupling.py tests/test_cyclic_acceptance.py tests/test_raw_driver_diagnostics.py tests/test_native_recovery_penalty.py tests/test_native_q4_quadrature.py tests/test_native_tri3_quadrature.py tests/test_native_q4_history.py tools/s04_e036_fem/test_overlay.py
```

原存档、共享dirty主checkout和CITPC12均未改写。无push/部署/新实验。修复收益、优化瓶颈与表达能力结论待experiment.md的成组验证。

## 后续代码准备 · 2026-10-21（与上述已执行检查分开）

用户授权补齐P1/P2共同前态窗口、保存后核验及FEM方案，同时明确暂不运行测试、训练、FEM或部署。本次新增/修改代码仅经文本阅读与独立静态交叉审查；**没有执行pytest、import检查、AST/编译检查、MATLAB checkcode、自测或任何求解**。

新增测试源码覆盖冻结f控制、observer隔离/失败/耗尽、保存失败和篡改、前态物理键/MAT轴与通道、缺失初始历史及禁止覆盖。它们是待执行检查，不计入上方82/26已执行数。原 `source_lock.json` 对应旧修复版本；新代码字节身份见独立 `implementation_lock.json`，不能把新锁文件理解为测试通过。

静态审查中已针对源码修正：P1共同末态检查、显式前态身份与来源绑定、保存读回后才能续接、耗尽诊断失败保留原异常、整数更新预算和墙钟耗尽后不再发起额外数值读出。实际Python/MATLAB可执行性、真实数值一致性、存盘故障行为与配对结果仍需未来授权后的检查。本轮没有生成新的已接受前态、执行许可或科学结果。

后续静态交叉审查覆盖输入/控制器/持久化集成、FEM窗口与读回、事后评分。补充修正了保存核验超时分类、诊断I/O覆盖主错误、CUDA运行错误被当作缺失输入、F1自身历史与checkpoint来源链、原始双精度网格保留和FEM完成记录的文件hash绑定。新FEM只读hash helper及原生history代数核验也未执行。实际系统/MEX加载与绑定、disabled原生对照调用、生产端watchdog/线程/存储包装层仍需执行前准备；未声称运行就绪。

FEM窗口独立静态复核进一步将Newton调用改为本地已查定义所支持的6输出（不再假定未确认的第7个迭代数输出），并要求单位厚度、均质元素材料编号。生产端实际函数定义仍须核验；这些修正不构成运行证据。

## 阶段 A 实际检查与停止 · 2026-10-22（伦敦）

后续用户已批准阶段A。新的110项实现检查通过（7.95s），最新比较器35项完整小数组检查通过（0.60s）；均1线程，运行前后源码hash不变。比较器此前19及targeted5的日志保留，不重复加入35。原82/26历史记录与原source_lock、implementation_lock保持原版本含义。

实际CITPC12函数核对确认Newton声明7输出；新disabled单步入口据此保留原native body的7输出调用，既有6输出调用仍是MATLAB允许的输出前缀。没有执行MATLAB来验证其实际行为。

独立快照命令失败且零启动准备窗口耗尽，原生启动停止。MATLAB checkcode/28 mock、MEX构建、U0 admission、两个disabled控制、四个真实冻结场比较均未运行；全部相关源码仍prepared-only。最终diff格式检查通过，仅证明文本补丁格式。详见[本次结果与精确证据范围](STAGE_A_RESULT_20261022.md)及本次单列源码锁；本次不支持科学改善或进入阶段B。

后续原预算内单次机械续接已修复git快照、核验10输入和36代码文件；首次PowerShell启动包装退出且无attempt/MATLAB/build输出。只读Parser检查watchdog无语法错误，但实际Job/C#执行仍无证据；现场有效策略Restricted，入口策略兼容和进程级错误捕获不足。未重发，未把WMI ReturnValue0算作MATLAB成功。Python110+35结果不变；新增两个driver仅静态复核。[续接记录](STAGE_A_CONTINUATION_20261022.md)。
