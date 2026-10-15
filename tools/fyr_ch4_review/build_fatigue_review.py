"""Write the standalone local bilingual review from the checked numeric tables."""
from pathlib import Path
import csv,json
ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT=ROOT/'local_archive/report_ch4_fatigue_fields_20261015'
def rows(name):return list(csv.DictReader((OUT/'analysis'/name).open()))
S=rows('native_GP_statistics.csv');D=rows('same_state_GP_differences.csv');U=rows('history_update_s3_to_s4.csv')
A=json.loads((OUT/'analysis/source_and_timing_audit.json').read_text())
def stat(so,a,c):return next(r for r in S if r['solver']==so and r['topology']==a and int(r['cycle'])==c)
def gap(a,c,f,domain='full'):return next(r for r in D if r['topology']==a and int(r['cycle'])==c and r['field']==f and r['domain']==domain)
def num(r,k,n=4):return f'{float(r[k]):.{n}f}'
def fig(name,alt):return f'![{alt}]({OUT}/figures/{name}.png)'
def table(headers,body):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in body)
parts=['''# 第4章：疲劳历史与退化因子场图——独立审阅稿

2026-10-15。使用已有 S04-E011 四组 Hard-5 结果；本次仅提取已存状态、计算统计和绘图。没有启动 FEM 求解、网络训练或新的网络场评估，也没有修改 Overleaf 或原第4章英文稿。

## 1. 这轮图说明了什么

同一峰值子步、同一历史更新时间下，FEM 与 PIDL 的平均疲劳历史接近，但局部历史场仍有明显差异。c83 时，Q4 的全域历史相对 L2 差异为 **29.87%**，T3 为 **16.90%**；在预先指定的 `|y_GP| ≤ 0.03` 窄带内，分别为 **64.56%** 和 **41.68%**。因此，平均值接近不能代替空间场比较。

“PIDL 系统性低估疲劳历史”需要改写：c83 的全域平均历史确实略低，但 Q4 的最大历史较低，T3 的最大历史却较高；不同位置的差异也有正有负。只看一个最大值、平均值，或沿用旧八步结果，都不足以描述这四组计算。

三个检查点显示，Q4 的历史场差异逐步增大；T3 从 c20 到 c60 减小，c83 略有回升。两种拓扑的退化因子 MAE 都在三个检查点逐步增大。这里的“演化”指三个已存状态之间的比较，连线仅帮助阅读。

## 2. 先统一状态与历史更新时间

| 项目 | 本次使用的定义 |
| --- | --- |
| 比较系列 | 10 月 S04-E011 FEM-Q4、PIDL-Q4、FEM-T3、PIDL-T3；每循环五个加载子步 |
| 早、中、晚 | c20、c60、c83；均早于该四组轨迹最早的 c84 首次事件 |
| 主图状态 | 第4子步峰值；当前步接受、损伤提交、疲劳历史刷新后 |
| PIDL 全局索引 | `j = 5c − 1`，即 99、299、414；j0 为恢复步 |
| 更新前对照 | 前一接受态 s3，对应 j98、298、413；仅用于检查 s3→s4 的变化 |
| FEM 导出 | `request28_post_commit/cNNNN_s004_post_commit.mat` 中的 `alpha_bar_gp` 与 `f_alpha_gp` |
| PIDL 导出 | 对应 checkpoint 的 `hist_fat`，以及同一 j 的 element diagnostics 中的 `hist_fat_gp`、`f_fatigue_gp` |

**实际加载幅值也已核对一致。** FEM s3/s4 元数据分别记录 0.749999、0.999999；PIDL 原运行 settings 的显式加载序列相同，峰值位移为 0.11999988，名义 Umax 为 0.12。两者不是分别使用 0.999999 和 1。此前发现的小偏移来自共同加载设置，不构成本轮配对幅值不匹配。

| 时点 | FEM | PIDL |
| --- | --- | --- |
| 当前步求解/拟合时 | 已存旧历史固定；装配依据当前试算状态计算 trial fatigue，并可影响当前相场方程 | 从旧疲劳历史得到 f，并在当前步网络拟合期间固定它 |
| 接受当前步后 | 提交损伤与历史；本次快照在两者提交、cyclemax 更新后保存 | 接受损伤，更新疲劳历史，再刷新 f；本次 checkpoint 与 element diagnostics 位于刷新之后 |
| 传至下一步 | 提交后的状态 | 提交后的状态 |

所以，本次图的**保存时点一致**，但两种算法在当前步内部使用疲劳系数的方式仍有区别。单凭这些事后场图，不能把差异全部归因于这一算法区别。

六个 PIDL 峰值状态中，checkpoint 历史与独立保存的 GP 历史逐值完全一致；按生产代码的 float32 运算从历史重算 f，也与保存的 f 逐值完全一致。FEM 快照均标记为 `post-convergence/post-damage-commit/post-history-commit/post-cyclemax-update`。本次没有使用 pre-phase 输入或卸载后的 cycle-end 场代替峰值提交后场。

## 3. 量是什么，空间支持是什么

疲劳历史记为 **ᾱ**，即随加载累积的疲劳量；它不是损伤 d，也不是拉伸能最大历史 H。文件和分析脚本里简写的 `H` 在本次表格中专指 ᾱ。

本组运行使用阈值 αT = 0.5、指数 p = 2 的疲劳退化关系：

- ᾱ ≤ 0.5：`f(ᾱ) = 1`。
- ᾱ > 0.5：`f(ᾱ) = [1 / (ᾱ + 0.5)]²`。

f 越小，疲劳导致的断裂阻力降低越多。这个 f 与损伤刚度退化函数 g(d) 是不同的量，图中没有把它们混用。

| 空间项 | Q4 | T3 |
| --- | --- | --- |
| 单元数 | 86,408 | 172,816 |
| 每单元高斯点数 | 4 | 3 |
| 点序 | (+,+), (−,+), (+,−), (−,−) | (2/3,1/6,1/6), (1/6,2/3,1/6), (1/6,1/6,2/3)，重心坐标 |
| 比较方式 | 同一 Q4 网格内 FEM/PIDL 配对 | 同一 T3 网格内 FEM/PIDL 配对 |

FEM 节点与连接表和本地配对网格完全一致；PIDL 导出的单元中心、面积与该网格在浮点精度内一致。数值比较直接使用原生 GP 值与共同的几何积分权重；两种网格的总积分面积均为 1。相对 L2 定义为 `sqrt[Σw(PIDL−FEM)² / Σw FEM²]`，MAE 为 `Σw|PIDL−FEM| / Σw`；窄带指标只在该区域重新归一化。两种网格的窄带积分面积分别约为 0.059965 与 0.059995，选择规则相同、采样点不同。Q4 与 T3 的 GP 位置不同，没有跨拓扑逐点相减或插值。

**图像与统计的口径分开：** 每个多边形显示单元内 GP 的物理加权均值；f 独立平均，未用 `f(mean(ᾱ))` 代替 `mean(f(ᾱ))`。数值表保留原生 GP 极值与差异，因此图上的单元均值最大值通常小于表中的 GP 最大值。场图仅显示 x∈[−0.5,0.5]、y∈[−0.12,0.12]；全域统计仍覆盖完整计算域。

ᾱ 的所有场图使用同一个对数色标，显示下限为 1e−4；原始值和统计没有裁剪。历史差值采用统一的线性、零中心色标；f 始终用 [0,1]，f 差值用 [−1,1]。差值定义均为 **PIDL − FEM**。`|y_GP| ≤ 0.03` 仅是预先指定的描述性窄带，不是损伤阈值，也不是随当前裂缝轮廓变化的区域。

## 4. c83：疲劳历史的同状态比较
''']
parts+=[fig('c83_history_post_commit','c83 post-commit fatigue history comparison'),'''
**English caption.** Fatigue history at the peak of cycle 83, after the accepted step and history update. The rows show Q4 and T3. The columns show FEM, PIDL and PIDL minus FEM. The field panels use a shared log scale. The difference panels use a shared linear scale. Colours show weighted cell means on each native mesh.

**读图：** 两者的大尺度分布相似，局部差异仍然明显。历史差值色标由全组极值确定，窄带外的小差异会显得很淡；白色不能理解为逐点相同。GP 统计用于补充图中的单元平均显示。
''']
body=[]
for a in ['q4','t3']:
 f,p=stat('FEM',a,83),stat('PIDL',a,83)
 body.append([a.upper(),num(f,'history_mean'),num(p,'history_mean'),num(f,'history_max_GP',3),num(p,'history_max_GP',3),f"{100*float(gap(a,83,'H')['relative_L2']):.2f}%",f"{100*float(gap(a,83,'H','corridor_abs_y_le_0.03')['relative_L2']):.2f}%"])
parts+=[table(['拓扑','FEM 全域均值','PIDL 全域均值','FEM GP 最大值','PIDL GP 最大值','全域相对 L2','窄带相对 L2'],body),'''
**Suggested report text.** At cycle 83, the mean fatigue history is close in FEM and PIDL, but the local fields still differ. The whole-domain relative L2 difference is 29.87% for Q4 and 16.90% for T3. The differences are larger in the central strip. PIDL has a lower maximum history than FEM on Q4, but a higher maximum on T3. The mismatch therefore depends on location and mesh topology.

中文对应：c83 的平均疲劳历史接近，但局部场仍有差异；全域历史相对 L2 差异分别为 Q4 29.87%、T3 16.90%，中央窄带内更大。PIDL 最大历史在 Q4 上较低、T3 上较高，因此差异取决于位置和拓扑。

## 5. c83：疲劳退化因子的同状态比较
''',fig('c83_factor_post_commit','c83 post-commit fatigue factor comparison'),'''
**English caption.** Fatigue degradation factor at the peak of cycle 83, after the history update. The rows show Q4 and T3. The columns show FEM, PIDL and PIDL minus FEM. A lower factor means a greater reduction in fracture resistance. The factor uses a shared range of 0 to 1; differences use −1 to 1.

**读图：** f 的大尺度形态比历史尖峰更接近，但局部差异并未消失。正差值表示 PIDL 的 f 较大，即该处疲劳导致的断裂阻力降低较少；负差值表示相反。色标是单元均值，数值 MAE 是 GP 加权计算。
''']
body=[]
for a in ['q4','t3']:
 f,p=stat('FEM',a,83),stat('PIDL',a,83)
 body.append([a.upper(),num(f,'factor_mean'),num(p,'factor_mean'),num(gap(a,83,'F'),'MAE',5),num(gap(a,83,'F','corridor_abs_y_le_0.03'),'MAE',5),num(f,'factor_min_GP',6),num(p,'factor_min_GP',6)])
parts+=[table(['拓扑','FEM 全域均值','PIDL 全域均值','全域 MAE','窄带 MAE','FEM GP 最小值','PIDL GP 最小值'],body),'''
**Suggested report text.** The mean fatigue factor is also close between the two methods. However, the mean absolute difference is larger in the central strip than over the whole domain. At cycle 83, it is 0.02712 for Q4 and 0.03617 for T3 in the strip. A close domain average can therefore hide local differences in fatigue degradation.

中文对应：两种方法的平均退化因子也较接近，但中央窄带内的 MAE 大于全域值；c83 的窄带 MAE 为 Q4 0.02712、T3 0.03617。全域平均接近会掩盖局部退化差异。

## 6. 早、中、晚：c20 → c60 → c83

这三个时刻分别代表本组比较的早期、中期和事件发生前的晚期。每幅图从上到下为 c20、c60、c83，从左到右为 FEM、PIDL、PIDL−FEM。

### Q4：疲劳历史
''',fig('q4_history_evolution','Q4 fatigue history at c20 c60 c83'),'''
**English caption.** Evolution of fatigue history on Q4 at cycles 20, 60 and 83. Every panel shows the peak state after the history update. The same history and difference scales are used at all three cycles.

### T3：疲劳历史
''',fig('t3_history_evolution','T3 fatigue history at c20 c60 c83'),'''
**English caption.** Evolution of fatigue history on T3 at cycles 20, 60 and 83. The fields are shown on the native T3 mesh. The scales and saved-state timing match the Q4 comparison.

### Q4：疲劳退化因子
''',fig('q4_factor_evolution','Q4 fatigue factor at c20 c60 c83'),'''
**English caption.** Evolution of the fatigue degradation factor on Q4 at cycles 20, 60 and 83. The region with a reduced factor spreads with cycling. Each row compares the same peak and post-update state in FEM and PIDL.

### T3：疲劳退化因子
''',fig('t3_factor_evolution','T3 fatigue factor at c20 c60 c83'),'''
**English caption.** Evolution of the fatigue degradation factor on T3 at cycles 20, 60 and 83. The factor and signed differences use the same scales as the Q4 plots.

### 三时刻的定量比较
''',fig('early_middle_late_metrics','Three-checkpoint means and native GP field differences')]
body=[]
for a in ['q4','t3']:
 for c in [20,60,83]:
  body.append([a.upper(),c,f"{100*float(gap(a,c,'H')['relative_L2']):.2f}%",f"{100*float(gap(a,c,'H','corridor_abs_y_le_0.03')['relative_L2']):.2f}%",num(gap(a,c,'F'),'MAE',5),num(gap(a,c,'F','corridor_abs_y_le_0.03'),'MAE',5)])
parts+=[table(['拓扑','循环','历史全域相对 L2','历史窄带相对 L2','f 全域 MAE','f 窄带 MAE'],body),'''
**English caption.** Domain means and FEM–PIDL field differences at three selected peaks. Solid lines in the lower panels show whole-domain differences; dashed lines show the central strip, |y_GP| ≤ 0.03. History differences use a weighted relative L2 norm with FEM as the reference. Factor differences use a weighted mean absolute difference. Lines connect the three sampled cycles only.

**Suggested report text.** Both methods accumulate fatigue history and reduce the fatigue factor as cycling continues. The field mismatch follows different patterns on the two meshes. On Q4, the history difference increases across the three selected cycles. On T3, it decreases from cycle 20 to cycle 60 and rises slightly at cycle 83. The factor MAE increases on both meshes. These results show why we compare local fields as well as domain averages.

中文对应：两种方法都随循环累积疲劳历史、降低退化因子，但历史场差异的变化取决于拓扑。Q4 在三个时刻逐步增大，T3 先减小再略微回升；两组 f 的 MAE 都逐步增大。因此需同时比较局部场与全域平均。

## 7. 为什么“更新前/后”需要明确标注

下表直接比较 c83 的前一接受态 s3 与峰值接受态 s4。它包含加载子步从 s3 到 s4 的全部已存状态变化，不是同一最终场在提交前/后的一次隔离实验，也不是 FEM Newton 内部 trial f 的测量。
''']
body=[]
for r in U:
 if int(r['cycle'])==83:
  body.append([r['solver']+'-'+r['topology'].upper(),num(r,'history_increment_mean',7),num(r,'history_increment_max',4),num(r,'factor_change_MAE',7),num(r,'factor_change_max',4)])
parts+=[table(['计算','ᾱ 增量全域均值','ᾱ 增量 GP 最大值','f 变化全域 MAE','f 变化绝对 GP 最大值'],body),'''
全域 f 变化均值很小，但最大局部变化可达约 0.20–0.38。混用旧历史系数与刷新后系数，可能明显改变局部图像。这个表说明标注时点的重要性；它没有量化“把更新时机改成相同后，FEM/PIDL 差距能缩小多少”。后者需要独立的控制计算，本次未开展。

## 8. 第4章建议怎么放

建议在介绍疲劳累积量 ᾱ、退化函数 f 和求解/提交顺序之后，先放 c83 的历史与退化因子两图，再放三时刻定量图。正文由“平均量接近、局部历史仍不同、f 的局部差异随循环增大”展开。

四幅演化矩阵可放在同一小节的后部或附录，正文明确引用。若版面有限，保留 f 的演化矩阵，把历史演化矩阵放附录；不要让正文只剩平均量折线而丢失场图。

这组图可以替换旧版本中状态时点、加载步或空间支持不明的疲劳场比较。它们是本组已有结果的描述性比较，不能单独证明误差的因果来源，也没有显示某种新修正方法已缩小差距。

## 9. 文件与复核入口
''']
for name,label in [('native_GP_statistics.csv','四组场统计'),('same_state_GP_differences.csv','同状态全域/窄带差异'),('history_update_s3_to_s4.csv','历史更新时间检查'),('spatial_support_checks.csv','空间支持核对'),('degradation_law_checks.csv','退化关系逐点核对'),('source_and_timing_audit.json','完整来源、时点和显示设置')]:
 parts.append(f'- [{label}]({OUT}/analysis/{name})')
parts+=['',f'- [12 个 FEM 原文件 SHA-256 核对记录]({OUT}/raw/selected_backup_hashes.txt)',f'- [原第4章修改清单]({ROOT}/local_archive/report_ch4_revision_20261015/CHANGES_AND_INTEGRATION.md)',f'''

FEM 来源为已经存在的 Windows OneDrive 备份 `S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_{{Q4,T3}}_C120/request28_post_commit/`。本轮只完整读取所选 12 个文件，其 SHA-256 全部与已有备份清单一致。原运行目录已迁出，未据此更换运行版本。

PIDL 来源为 `/mnt/data2/drtao/pidl_archives/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/` 下的两组 production，生产代码提交为 `ad749c8bbba8120b3961add989b11427fab86254`。具体检查点路径、大小、mtime、GP 顺序和导出交叉检查值见 JSON。新提取的两个数据容器也有本地 SHA-256。

复核完成：24 个 solver/topology/cycle/substep 场状态均有限；疲劳历史非负，f 在 [0,1]；退化关系逐点一致至浮点精度；s3→s4 以及三个已存峰值之间的历史均不下降、f 均不增加；空间支持与加载因子已核对。七张 PNG 已逐张查看标题、色标、裁剪和标签。

显示用历史上限为 {A['history_display_max']:.6g}，共同差值范围为 ±{A['history_difference_limits'][1]:.6g}。完整数值以 CSV 为准。
''']
(OUT/'REVIEW.md').write_text('\n\n'.join(parts)+'\n')
print(OUT/'REVIEW.md')
