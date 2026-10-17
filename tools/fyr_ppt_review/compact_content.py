"""Fifteen connected main slides, with every previous page retained as backup."""
from pathlib import Path
import json,copy
R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OLD=R/'local_archive/fyr_ppt_evidence_revision_20261017';W=R/'local_archive/fyr_ppt_15slide_revision_20261017'
src=json.loads((OLD/'build/content_final.json').read_text());S=[]
def add(kind,title,en,zh,refs,**kw):
 S.append(dict(kind=kind,title=title,en=en,zh=zh,source='\n'.join(src[n-1]['source'] for n in refs),original_pages=refs,**kw))
add('cover','Road-crack Prediction',
 'Good morning. My name is Wennie Wan, and my supervisor is Brian Sheil. My long-term PhD goal is to predict how road cracks develop and grow. In my first year, I built and tested a neural solver for a controlled fracture problem. I will explain how it works, where its fields differ from FEM, and how those findings guide the next steps.',
 '大家好，我叫 Wennie Wan，导师是 Brian Sheil。我的博士长期目标是预测道路裂缝如何发展和增长。第一年，我建立并检验了一个用于受控断裂问题的神经求解器。接下来介绍它如何计算、它的场与 FEM 哪里不同，以及这些发现如何决定下一步工作。',[1])
add('question','Research question and PhD plan',
 'Inspection tells us where a crack is visible. Predicting its growth also needs a model of damage and loading history. My PhD has three stages: test the numerical model, study what limited observations add, then adapt the method to roads. This first-year study addresses the first stage. The question is whether a neural solver reproduces the local fields and history of the FEM calculation.',
 '检测告诉我们裂缝在哪里可见，预测其增长还需要损伤与加载历史模型。博士研究分三个阶段：检验数值模型、研究有限观测能增加多少信息，再将方法适配到道路。第一年聚焦第一阶段，问题是：神经求解器能否复现 FEM 计算中的局部场与历史？',[2,3])
add('model','The specimen and phase-field fatigue model',
 'We use a unit square with a starter crack on the left. The top edge follows a displacement cycle, while the bottom is fixed. The intact material is linear elastic. Damage d reduces stiffness, and fatigue history reduces fracture resistance through f. We solve for displacement and damage together. The elastic law is linear, but damage and stored history make the full response nonlinear and dependent on the loading path.',
 '采用左侧带初始裂纹的单位正方形试件。顶边施加循环位移，底边固定。完整材料为线弹性，损伤 d 降低刚度，疲劳历史通过 f 降低断裂阻力。需要耦合求解位移和损伤。弹性关系是线性的，但损伤和已存储历史使完整响应具有非线性与加载路径依赖。',[4,5,6,7,8,45])
add('fem','FEM calculation at one load substep',
 'At a fixed load, FEM first solves displacement with damage fixed. It then solves damage using the displacement field and trial fatigue values. These solves repeat until the stopping test is met. The stored old history stays fixed during iteration. After accepting the fields, the code updates accumulated fatigue, the previous driver and f once, then moves to the next substep. Five substeps make one physical cycle.',
 '在固定载荷下，FEM 先固定损伤求位移，再利用位移场与试算疲劳量求损伤，交替进行直到满足停止条件。迭代中，存储的旧历史保持固定。接受场以后，一次性更新累积疲劳、前一驱动力和 f，再进入下一个子步。五个子步组成一个物理循环。',[9,12,13])
add('pidl','PIDL calculation and neural field',
 'PIDL takes spatial coordinates and represents displacement and damage with a network with eight hidden layers and four hundred neurons per layer. The current load enters through boundary constraints. RPROP updates the network parameters to reduce energy and damage penalties. During this fit, the old fatigue factor stays fixed. After fitting, the code accepts damage, updates fatigue history and the previous driver, then refreshes f. It carries the fitted network and updated history into the next substep.',
 'PIDL 输入空间坐标，用八个隐藏层、每层四百个神经元的网络表示位移和损伤。当前载荷通过边界约束进入。RPROP 更新网络参数，降低能量和损伤罚项。拟合时旧疲劳因子保持固定。拟合后，接受损伤、更新疲劳历史与前一驱动力，再刷新 f；拟合后的网络和更新历史一起进入下一子步。',[10,11,12,13])
add('comparison','Common loading, initial state and event rule',
 'The four calculations use the same nodes and five-step loading path, with Q4 or T3 connectivity. We compare fields at the same peak and on matching spatial support. The recovered damage already differs before cycling, although fatigue history starts at zero. Under one event rule, Q4 PIDL reaches the threshold one cycle after FEM. T3 reaches it five cycles later. We then ask whether this timing agreement also means local-field agreement.',
 '四组计算使用相同节点和五步加载路径，分别采用 Q4 或 T3 连通方式。在同一峰值、匹配空间支持上比较场。循环前恢复的损伤已经不同，而疲劳历史从零开始。使用统一事件判据后，PIDL-Q4 比 FEM 晚一个循环达到阈值，T3 晚五个。接下来检查：时间接近是否也意味着局部场接近？',[13,14,15,16,24])
add('damage','Damage differs in width and front position',
 'These maps compare both meshes at cycle eighty-three, before the first event. PIDL has a wider damage band in the selected wake section on both meshes. The Q4 front positions are close. On T3, the PIDL front falls behind FEM and the transverse profile is also shifted. This is a local shape difference rather than a uniform offset. The reported width describes the diffuse damage band, not the physical crack opening.',
 '这些图比较第 83 个循环，两种网格都尚未达到首次事件。所选尾迹剖面上，PIDL 的损伤带都更宽。Q4 的前沿位置接近；T3 中，PIDL 前沿落后于 FEM，横向剖面也有偏移。因此这是局部形状差异，而非整体偏移。这里的宽度描述弥散损伤带，不是实际裂缝张开宽度。',[17,18,19,35],image=str(W/'figures/damage_front_pair.png'))
add('history','Fatigue history changes fracture resistance',
 'These curves show where history and the fatigue factor differ after the same accepted peak. They are spatial averages in a narrow strip, not peak-value curves. The largest history value is lower in PIDL on Q4, but higher on T3. The factor also differs locally. We therefore need location as well as amplitude. All values use the original scale. The full maps and exact peak locations are in the backup slides.',
 '这些曲线展示同一接受峰值之后，历史与疲劳因子在哪里不同。曲线是窄带内的空间平均，不是峰值曲线。PIDL 的最大历史在 Q4 上更低，在 T3 上却更高，因子也存在局部差异。因此需要同时看位置和幅值。数值使用原始尺度，完整场图和精确峰值位置保留在备份页。',[20,21,22,40],image=src[20]['image'])
add('evolution','Field differences before the first event',
 'The mismatch is already present in recovered damage before cycling and at the first saved peak. Across cycles twenty, sixty and eighty-three, the Q4 history difference grows. T3 first falls and then rises slightly. The fatigue-factor difference grows on both meshes. These three saved states show the trend, but they do not identify the exact inner iteration where each difference starts.',
 '循环前恢复的损伤和第一个保存峰值中已经存在差异。比较 c20、c60、c83，Q4 的历史差异增大，T3 先减小后略微回升；两种网格的疲劳因子差异都增大。这三个保存态显示阶段变化，但不能定位每项差异从哪一次内层迭代开始。',[23,24,36,37,38,39,46],image=str(W/'figures/history_evolution_gaps.png'))
add('energy','Why a close integral can hide a local gap',
 'The active driver multiplies raw elastic energy by the damage factor. Its value depends on where those fields overlap. For Q4 at cycle eighty-three, the active-energy integral differs by about six per cent, while the local relative L2 difference is about forty-eight per cent. The maps help explain that contrast. They do not yet separate the effects of the starting state, fatigue timing, damage bounds and optimisation.',
 '有效驱动力等于原始弹性能乘以损伤因子，其数值取决于两个场在空间上如何重叠。c83 的 Q4 有效能积分差异约为 6%，局部相对 L2 差异却约为 48%。这些图有助于解释这个现象，但尚未分离初始状态、疲劳时序、损伤界限和优化各自的影响。',[25,27],image=str(W/'figures/q4_energy_overlap.png'))
add('attempts','Attempts to narrow the field gap',
 'I tested richer local representations and examined the numerical fields. The representation changes altered the fields, but did not give a consistent match. Re-solving displacement while holding damage fixed reduced the active-field gap only slightly. Most of it remained. The raw PIDL fields also contain small damage-bound violations. These checks point to the coupled damage and history updates, rather than displacement alone, as the next focus.',
 '我们尝试了更丰富的局部表示，并检查了数值场。表示方式改变了场，但没有得到一致匹配。固定损伤重新求位移，只小幅缩小有效场差距，大部分仍然存在。原始 PIDL 场也有小幅损伤越界。这些检查使下一步聚焦损伤与历史的耦合更新，而不只处理位移。',[19,26,27])
add('conclusion','First-year conclusions and the next question',
 'The first year produced a working fatigue PIDL implementation and a paired FEM comparison. Q4 gives close event timing, while local damage and fatigue fields still differ. The initial state is already different, and displacement re-solves do not remove most of the gap. The next question is how much comes from the starting damage, current-step fatigue treatment and damage constraints. That gives us a specific next part of stage one.',
 '第一年建立了可运行的疲劳 PIDL 实现，并完成配对 FEM 比较。Q4 的事件时间接近，但局部损伤和疲劳场仍有差异。初始状态已经不同，位移重求解也未消除大部分差距。下一问题是：初始损伤、当前子步疲劳处理和损伤约束各贡献多少？这为第一阶段的下一步提供了具体方向。',[15,16,26,27,28,29])
add('controls','Stage 1: controlled tests of the field gap',
 'I would keep the material, mesh and loading fixed and vary one part at a time. First, compare a common recovered damage state and history. Next, match the current-step fatigue treatment. Then check damage constraints and the residual of the final accepted fields. For each change, follow the full trajectory and local fields as well as the event cycle. This tests the explanations raised by the first-year results.',
 '下一步固定材料、网格和加载，每次只改变一项。先比较共同恢复损伤态与历史，再匹配当前子步的疲劳处理，之后检查损伤约束及最终接受场残差。每项修改都同时跟踪完整轨迹、局部场和事件循环。这些检验直接回应第一年结果提出的解释。',[29,33])
add('observations','Stage 2: prediction with limited observations',
 'After those checks, I would test what observations add to future prediction. I would compare one crack mask, two masks, and past loading information under the same future loading and target. Persistence and simple growth extrapolation provide baselines. Complete trajectories should stay together in the evaluation split. I would assess mean error, interval coverage and interval width near the crack and across future steps. These are planned tests.',
 '完成上述检查后，再研究观测能为未来预测增加多少信息。在相同未来加载与目标下，比较一张裂缝掩膜、两张掩膜以及过去加载信息，以持续不变和简单增长外推为基线。评价划分中完整轨迹应保持在一起，同时评价裂缝附近及未来各步的均值误差、区间覆盖率和宽度。这些都是计划中的检验。',[30,31,33])
add('roads','Stage 3: road adaptation and validation',
 'The road stage begins with one clear pavement problem. I would choose the material, temperature range, loading and crack-growth target, then select and calibrate suitable mechanics. Predictions would be checked against separate measurements. The first-year results explain the order: resolve the numerical field differences, test what observations add, then assess road prediction. Each stage answers a question needed by the next.',
 '道路阶段从一个清楚的路面问题开始：选择材料、温度范围、加载和裂缝增长目标，再选择并标定合适的力学模型，用独立测量检验预测。第一年结果决定了这个顺序：先处理数值场差异，再检验观测增加的信息，之后评价道路预测。每个阶段回答下一阶段所需要的问题。',[32,33])

order=[4,5,6,7,8,45,9,10,11,12,13,14,15,16,24,17,18,19,35,20,21,22,23,36,37,38,39,40,46,25,26,27,28,29,30,31,32,33,2,3,41,42,43,44,1,34]
assert len(S)==15 and sorted(order)==list(range(1,47))
for b,n in enumerate(order,1):
 d=copy.deepcopy(src[n-1]);d.update(kind='preserved_backup',backup_original_slide=n,backup_label=f'B{b:02d}',hidden=True);S.append(d)
for i,d in enumerate(S,1):d['number']=i
(W/'build/content.json').write_text(json.dumps(S,ensure_ascii=False,indent=2))
(W/'review/slide_map.json').write_text(json.dumps(dict(main=15,backup=46,total=61,slides=[dict(number=i+1,title=d['title'],source_pages=d.get('original_pages',[d.get('backup_original_slide')]),backup_label=d.get('backup_label'),hidden=d.get('hidden',False)) for i,d in enumerate(S)]),ensure_ascii=False,indent=2))
print('15 main slides; all 46 previous pages retained as hidden backups.')
