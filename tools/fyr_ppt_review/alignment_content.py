"""Revise main slides 7–15; preserve their previous versions as backups."""
from pathlib import Path
import copy,json

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OLD=ROOT/'local_archive/fyr_ppt_15slide_revision_20261017'
OUT=ROOT/'local_archive/fyr_ppt_alignment_update_20261017'
S=json.loads((OLD/'build/content_final.json').read_text())
original=copy.deepcopy(S)
AUDIT=str(ROOT/'local_archive/bc_routes_comparison_20261017/README_analysis.md')

updates={
7:("Damage differs in width, path and front position",
"These maps compare FEM and PIDL at the same peak in cycle eighty-three. The displacement boundary conditions are matched, although the starting damage fields differ. At the selected section, PIDL gives a wider damage band on both meshes. The Q4 front positions are close. On T3, the PIDL band shifts upward, and its front along the centreline is behind FEM. We therefore compare width, path and front position together. This width describes the damage band, not crack opening. Next, we look at fatigue history.",
"这些图比较第83个循环同一峰值时的 FEM 和 PIDL。位移边界已经对齐，但初始损伤场仍有差异。在所选剖面上，两种网格中的 PIDL 损伤带都更宽。Q4 的前沿位置接近；T3 中，PIDL 损伤带向上偏移，沿中线读取的前沿也落后于 FEM。因此，需要一起比较宽度、路径和前沿位置。这里的宽度描述损伤带，不是裂缝张开宽度。接下来再看疲劳历史。"),
8:("Local history and fatigue factor differ",
"The damage maps show a shape difference. Here we compare fatigue history and the factor that lowers fracture resistance. The curves are averages in a narrow strip; the numbers on the right are maxima over all integration points. The PIDL history maximum is lower on Q4 and higher on T3. The local fatigue factor also differs. The direction of the difference therefore depends on the mesh and location. We next follow these differences through the saved cycles.",
"损伤图显示了形状差异。这里进一步比较疲劳历史，以及降低断裂阻力的疲劳因子。曲线是窄带内的平均值，右侧数字则是所有积分点上的最大值。PIDL 的最大历史在 Q4 上更低，在 T3 上更高，局部疲劳因子也不同。因此，差异的方向取决于网格和位置。接下来沿已保存的循环观察这些差异如何发展。"),
9:("Field differences develop before the first event",
"The starting damage already differs, and a damage gap is present at the first saved peak. At cycles twenty, sixty and eighty-three, the Q4 history gap grows. On T3, it first falls and then rises slightly. The fatigue-factor gap grows on both meshes. These saved states show that the differences develop before the event. They do not locate the first inner iteration where a difference appears. The next slide looks at how damage and elastic energy combine locally.",
"初始损伤已经不同，第一个保存峰值也存在损伤差距。比较第20、60和83个循环，Q4 的历史差异增大；T3 先减小，之后略微回升。两种网格的疲劳因子差异都增大。这些保存态说明差异在事件发生前就已发展，但不能定位首次出现差异的内层迭代。下一页看损伤与弹性能如何在局部组合。"),
10:("A close integral can hide a local field gap",
"The active driver is raw elastic energy multiplied by the damage factor. Its value depends on where the two fields overlap. A wider or shifted damage band can change that overlap. For Q4 at cycle eighty-three, the integral differs by about six per cent, while the local relative L2 difference is about forty-eight per cent. This is why we need field maps as well as totals. I will now show what the existing attempts changed.",
"有效驱动力等于原始弹性能乘以损伤因子，其数值取决于两个场在空间上如何重叠。损伤带变宽或偏移，都可能改变这种重叠。第83个循环的 Q4 有效能积分差异约为6%，局部相对 L2 差异却约为48%。因此，除了总体量，还需要查看场图。接下来介绍已有改进尝试改变了什么。"),
11:("What the existing attempts changed",
"Richer local representations changed the fields, but did not give a consistent match. Re-solving displacement with damage fixed reduced the active-field gap only slightly. That check did not repeat the full coupled trajectory. We also found small damage-bound violations. These results do not yet identify the main cause. They give us specific tests: compare the starting state, the fatigue update within each load step, and the field constraints and optimisation. Each test should track local fields and crack growth together.",
"更丰富的局部表示改变了场，但没有得到一致匹配。固定损伤重新求位移，只小幅缩小了有效场差距；这项检查没有重新计算完整耦合轨迹。我们也发现了小幅损伤越界。这些结果尚未确定主要原因，但给出了具体检验：比较初始状态、每个加载子步内的疲劳更新，以及场约束和优化。每项检验都应同时跟踪局部场与裂缝增长。"),
12:("First-year conclusions and the next question",
"The first year established a fatigue PIDL model and a paired FEM comparison on two meshes. Q4 gives close event timing, while local damage and fatigue history still differ. We have described differences in the starting state, band width, path and front position. The next step is to test which parts of the calculation produce these differences, then define which outputs and loading ranges can support future prediction. This gives stage one a clear next task.",
"第一年建立了疲劳 PIDL 模型，并在两种网格上完成配对 FEM 比较。Q4 的事件时间接近，但局部损伤和疲劳历史仍有差异。我们已描述初始状态、带宽、路径和前沿位置的差异。下一步是检验计算中的哪些环节产生了这些差异，再明确哪些输出和加载范围可以支持后续预测。这为第一阶段提供了清楚的下一项任务。"),
13:("Stage 1: test the sources of the field differences",
"I would keep material, mesh and loading fixed, and change one part at a time. First, test a common starting damage field and history. Then compare the fatigue treatment within each load step. I would also check damage bounds, force balance and field optimisation. Path drift is one diagnostic. I am not aiming for perfect symmetry. A useful change should improve local fields while keeping sensible damage localisation, fatigue history and crack growth. These checks will define the model's usable range.",
"下一步固定材料、网格和加载，每次只改变一项。首先检验共同初始损伤场与历史，再比较每个加载子步内的疲劳处理，同时检查损伤界限、力平衡和场优化。路径偏移是一项诊断，不以完全对称为目标。有价值的修改应改善局部场，同时保留合理的损伤局部化、疲劳历史和裂缝增长。这些检查将明确模型的适用范围。"),
14:("Stage 2: prediction with limited observations",
"Within the outputs and loading ranges checked in stage one, I would test what observations add to prediction. One crack mask gives the current shape. An earlier mask adds recent change, and past loading adds part of the driving history. I would compare these inputs under the same future loading and target, using persistence and simple growth extrapolation as baselines. Complete test trajectories would be kept separate. I would report prediction error, interval coverage and interval width near the crack and across future steps.",
"在第一阶段已检查的输出和加载范围内，再检验观测能为预测增加多少信息。一张裂缝掩膜给出当前形状，较早的掩膜增加近期变化，过去加载则补充部分驱动历史。在相同未来加载与目标下比较这些输入，以持续不变和简单增长外推为基线。完整测试轨迹与训练轨迹分开，同时报告裂缝附近及未来各步的预测误差、区间覆盖率和区间宽度。"),
15:("Stage 3: road adaptation and validation",
"The road stage starts with one defined pavement problem. I would choose the material, temperature range, loading and crack-growth target. Relevant fracture and fatigue tests would guide the choice and calibration of the material model. Future crack growth would then be checked against separate measurements. The first-year findings explain this plan: understand the numerical fields, test what observations add, and then evaluate road prediction. Each stage provides information needed for the next.",
"道路阶段从一个明确的路面问题开始，选择材料、温度范围、加载和裂缝增长目标。通过相关断裂与疲劳试验，指导材料模型的选择和标定，再用独立测量检验未来裂缝增长。第一年的发现解释了这项计划：先理解数值场，再检验观测增加的信息，之后评价道路预测。每个阶段都为下一阶段提供必要信息。")}

for n,(title,en,zh) in updates.items():
    S[n-1].update(title=title,en=en,zh=zh)
    if n in [7,11,12,13]:
        S[n-1]['source']+='\n'+AUDIT
    if n>=13:S[n-1]['source']+='\nFuture-work proposal; no new experiment is claimed.'

for j,n in enumerate(range(7,16),47):
    d=copy.deepcopy(original[n-1])
    d.update(kind='preserved_v3_main',backup_original_main=n,backup_label=f'B{j:02d}',hidden=True)
    S.append(d)
for i,d in enumerate(S,1):d['number']=i
assert len(S)==70
(OUT/'build/content_final.json').write_text(json.dumps(S,ensure_ascii=False,indent=2))
(OUT/'review/slide_map.json').write_text(json.dumps({'main':15,'backups':55,'total':70,
 'preserved_existing_backups':46,'new_backups':{f'B{j:02d}':n for j,n in enumerate(range(7,16),47)}},indent=2))
print('Prepared nine revised bilingual narrations; main15 + backup55.')
