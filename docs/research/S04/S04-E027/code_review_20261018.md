# S04-E027 本地准备与独立代码审查交接

2026-10-18；Owner chat `01a14bc7-fd2a-73e1-9d0f-de457ba1dcc0`；HQ chat `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`。用户授权范围是本地接口、三臂代码、必要检查及独立审查；先不启动训练。报告在本对话/本地归档供HQ读取，没有另行发送消息。

**结论：代码准备范围通过独立审查，无剩余已知阻断性代码问题；完整 Code Ready / Run Ready 未签，运行未授权、未执行。**

## 绑定对象

- 最终审查源码快照：`91537ce240d892fc71f714cceedc1cea92c32b1b`，审查时工作区干净；其后仅追加本审查记录与结论，不改算法、runner、config、lock或protocol。
- Worktree：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/fem-synthetic-augmentation-design-20261017`；branch `codex/fem-synthetic-augmentation-design-20261017`。本地commit保存，未push。
- Runner：`SENS_tensile/run_s04_e027.py`；module：`source/s04_e027.py`；tests：`tests/test_s04_e027.py`。
- Protocol：`S04-E027/v1-source-faithful-P-20261018`；`experiment.md`及`data_lock.json`；旧Pro为方案审查，不替代此次代码审查。
- 独立审查者：本任务只读子代理 `/root/e027_independent_review`；主代理实现，审查者未修改源码。审查结果由子代理工具回传保存在本对话。

## 历史复用结论

此前已做过MIT-8 raw驱动warm-up/release、Path C局部damage监督、四字段直接强制和FEM-mesh预训练；不能称本次为首次FEM增强PIDL。Path C旧scorecard有组件收益，不能把所有旧监督归为失败。此次保留数据锚点、原生Q4固定完整前态、同一监督前缀后完整Adam/RNG分叉；定向检索未发现完全相同的三臂。具体出处及旧结果边界见`../fem_supervision_reuse_audit_20261018.md`。

源码核查纠正旧计划P臂转录：真实P是正能量log10加named-weight L2，PIDL gamma16875，而非原始能量或FEM gamma421875；修订写入E027且经独立核对。

## 审查轮次与修复

1. `c0113d565799f08e91be721f8019edb8d6767d9c`：核心接口及算法限定通过；三项P2为缺少分量/梯度与统一指标轨迹、逐段实际资源成本、图说明。独立13 tests及四MAT重放通过。
2. `12d96d14d211078c2efaecb6aba7c6da0b5c7136`：三项修复有效，独立14 tests通过；新增P2为跨臂LP诊断将P专用正能量限制传播到S/C。
3. `91537ce240d892fc71f714cceedc1cea92c32b1b`：保存能量，非正时辅助LP/其梯度NA，P实际目标不改；独立15 tests通过，代码准备范围通过。

已检查：来源一致的P目标、native Q4力/能量、C对damage的梯度、共享前缀完整参数/Adam/RNG复制、质量概率采样不重复加权、四文件身份与前态时序、参考trial history、禁止Mac/未知initializer执行、分量与独立诊断RNG、固定0/1000/1500、四段资源归属、图与评分输出来源、失败/预算保护。静态审查不能替代实际GPU图执行、资源成本验证或结果图视觉检查。

## 已完成的非训练证据

15个轻量测试、py_compile、git diff --check通过。四MAT已有参考重放：force maxabs差`8.605431227630064e-17`，free force norm`3.776120766585009e-15`，raw scaled差`3.020017395882757e-12`，trial-history scaled差`1.7239217865727685e-12`，BC误差0。摘要`nontraining_checks.json`；原收据在项目`local_archive/experiments/S04-E027/preparation_20261018/reference_check_final.json`。

**optimizer.step=0；训练循环进入=0；history commit=0；FEM solve=0；远程访问=0；initializer payload读取=0；新留出读取=0。** 没有新模型性能结果，不生成替代真实结果的图。源码中的未来执行路径未实际调用。额度检查各阶段均剩余81%，未使用reset/credit。

## 交HQ的下一步决定

初始化仅有原producer archive路径，当前无本地文件和精确字节身份，lock明确null；执行入口在数据/GPU/优化器前强制停止，禁止随机/其它checkpoint/旧UV头替代。应先由HQ安排准确权重的身份与可用性核实；任何lock更改须重新绑定审查。

随后由HQ统一决定是否批准指定producer的no-step三图预检和执行；需新Run、exact source、人工授权、完整资源/输出卡。预检P/S/C各100次forward/backward、无optimizer更新；实际成本和CUDA峰值当前未知。拟合总上限仍2 GPU小时/32GiB host/2GiB输出，超限停止，不自动换机/扩容/重试。若运行，完整Code Ready/Run Ready记录、真实图检查和独立证据审查仍须补齐；代码准备通过不授予科学结论或运行许可。
