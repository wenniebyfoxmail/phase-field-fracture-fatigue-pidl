# 逐 cycle Delta 图与表：阅读指南

Scientific question：现有三Umax的processed FEM–PINN discrepancy有什么空间/时间结构，
以及哪些state/support字段尚不足以做strict native direct-Delta supervision？

Evidence source：既有E013 input_lock锁定的FEM graph/trajectories与PINN peak exports；最终
Run `S04-direct-delta-D003`，source runner与11个外部hash见archive receipt.json；source-code
base `5b1eec29d2bed37d42baab5850ceb9c57ae16249`，本scope独立branch。

阅读顺序：

1. trajectory_coverage.csv：三轨迹264cycles与C0/H/native-GP缺项，reference明确未teacher-qualified。
2. cycle_discrepancy.png/pdf：原PINN未校正的各通道area-RMSE随physical cycle变化，全部cases，
   相同variable的各case用同axis；zero correction是参照。cycle-summary对peak，无性能门限。
3. delta_maps_u012.png：固定U0.12、c1/c20/c60/c82，FEM-minus-PINN signed maps，native frame，
   无裁窗。每channel共享最大area-p99.5 absolute-limit，每panel标saturated面积；只显示
   systematic stride8网格。数值表始终使用全部86,408cells，未按图的colour limit裁剪。
4. pre_event_summary.csv与cycle_delta_metrics.csv：时间correlation、concentration、邻域jumps
   与mapping-contained/fallback分层，详见diagnostic.md。原始Delta值按source-index按需重建。

Cross-figure interpretation：history/damage discrepancy随cycle累积，空间集中且相邻cycle相关；
raw driver的linear与log尺度表现很不同。描述结果为direct current-field+history模型提供
设计依据，不建立可部署预测增益。mapping fallback不是此描述下raw-linear主差异的原因。

Allowed conclusion：存在可整理的逐cycle、多变量差异，且值得在strict paired data合同上检验
direct-field correction。Blocked：qualified teacher、physical truth、real-road validity、future
forecasting、共享梯度冲突、模型PASS、FEM support deployment feature或回灌稳定性。

Storyline impact：保留E013--E015结果，开启新的直接场输入/表示合同；新NN需和B0/ridge在同
完整Umax切分比较，不要求旧coefficient ridge先PASS。方案与限制见direct_learning_protocol.md。

Visual QA：两张图已实际打开检查；无空白面板（c1 fatigue_f确实全零）、坐标轴和colorbars
可读、全case曲线、signed zero-centered色标、统一per-channel limits。D001原max色轴稀疏
history不可读的问题经D002修复，D003数值分层增强不改变figures。

Output root：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D003/analysis/`。
本scope为描述性准备诊断；Code/Evidence Ready独立review尚未进行，未启动任何training。
