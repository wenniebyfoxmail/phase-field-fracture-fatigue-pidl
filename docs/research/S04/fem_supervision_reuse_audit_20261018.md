# 既有 FEM 监督方向核查（2026-10-18）

**结论：做过这个大方向，不能称本次是首次 FEM 增强 PIDL。** 但本轮定向检查未找到与拟议三臂完全相同的原生Q4、固定完整前态、u/v/d联合拟合、同一监督检查点分叉的试验。仅说明所查记录，不声称穷尽历史。

|已有工作|实现/已有结果|本次处理|
|---|---|---|
|MIT-8，2026-04-25起|`run_mit8_warmup_umax.py`、`source/fem_supervision.py`、`source/fit.py`：前K周期物理+FEM raw ψ监督，之后撤除；owner方法总结记录release后易回baseline。runner内“学不成即容量不足”的解释过强，不继承|已有warm-up/release思想，不再当新点；本次只做一个状态且保留监督锚点，不作撤除后稳定性结论|
|Path C局部damage监督，5月初快照|`docs/advisor_method_evolution.md` §7.5、`docs/fem_likeness_scorecard.md`：局部alpha标签。旧非统一scorecard给Path C λ1的a(N) RMS .026、baseline .087；不是当前Hard5受控比较|保留曾有组件收益，不能把旧监督全说成失败；不转移该精度或阈值到当前试验|
|四字段直接监督，2026-06-01|`local_archive/taobo_remote_gap_census_20260627/raw_remote/pidl-field-supervision-90dd3ad/analysis/decision.md`及归档runner：alpha/alpha_bar/raw/active，λ1、K20。默认pretrain因缺mesh失败；off后的active c1检测/c4停止、raw c13/c16；alpha拟合不等于history/driver闭合|复用目标/时序教训；不把setup错误算物理失败。不重跑强制隐藏驱动，不启动长周期|
|FEM-mesh pretraining，2026-06-15|`.../A_hist_alpha_max_pair_analysis_20260615/analysis/decision.md`：换预训练网格，并非直接监督FEM状态。两臂均c80首次触边/c83停；tip MAE .037686→.040275，未改善|“FEM预训练”名称不能混为FEM数据蒸馏；不重跑该网格消融|
|近期UV监督/头修正、S09状态算子|既有方案所引E013/E023/E024、S09 E007–E009|复用Q4/质量权重、网络、能量和评价接口；不接管其训练/资产或重复其arm|

**源码核查还纠正了上一版方案P臂的两项转录错误：** E011 NCP归档`read_pidl_plateau.py::objective`实际为`log10(E_el+E_d+E_hist)+1e-5*sum(named weight²)`；owner `run_pidl_block_diagnosis.py::Problem`明确PIDL `tol_ir=.005/gamma=16875`，FEM才是`.001/421875`。上一版把原始能量与FEM罚系数写成当前PINN目标，不能照抄实现。本轮以日期修订写入新E027，保持C/S主问题、预算与输入不变，交独立代码审查核对源一致性；此前Pro设计通过不覆盖该新修订。

复用：本worktree的`network.py`、`field_computation.py`、`q4_quadrature.py`、`compute_energy.py`等纯构造/算子，不导入会解析CLI或训练的config/main；旧FEMSupervision的自动发现、时间/最近邻插值不用于本次固定原生接口。旧runner不执行。没有新数组拟合、训练或FEM求解。
