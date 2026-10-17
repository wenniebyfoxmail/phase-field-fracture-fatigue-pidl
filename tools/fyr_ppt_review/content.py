import json
from pathlib import Path
R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');W=R/'local_archive/fyr_ppt_process_revision_20261017';C=R/'local_archive/report_ch4_rewrite_integrated_20261015';F=R/'local_archive/report_ch4_fatigue_fields_20261015'
slides=[]
def add(kind,title,en,zh,source,**kw):slides.append(dict(kind=kind,title=title,en=en,zh=zh,source=source,**kw))
old='Original assessment deck: /Users/wenxiaofang/Downloads/Winnie_First_Year_Assessment.pptx.'
base=str(C/'draft/Chapter4_Integrated_Rewrite.md')
sourcecode='PIDL production commit ad749c8bbba8120b3961add989b11427fab86254, source/model_train.py; FEM solve_fatigue_fracture.m archived with S04-E011.'
add('cover','Road-crack Prediction',
'Good morning. My name is Wennie Wan, and my supervisor is Brian Sheil. My long-term PhD objective is to predict how road cracks develop and grow. Today I focus on the first stage: building and testing a physics-informed model in a controlled fracture problem.',
'大家好，我叫 Wennie Wan，我的导师是 Brian Sheil。我的博士长期目标是预测道路裂缝如何发展和增长。今天我主要介绍第一阶段：在受控断裂问题中建立并检验物理信息模型。',old)
add('stages','The three-stage PhD plan',
'I see the PhD in three stages. First, build and test the numerical model. Second, study what limited observations tell us about future crack growth. Third, adapt the approach to roads and test it against measurements. My first-year report focuses on stage one. The later stages are future plans.',
'博士研究分为三个阶段。第一，建立并检验数值模型。第二，研究有限观测能为未来裂缝增长提供多少信息。第三，将方法适配到道路，并用测量数据检验。第一年报告聚焦第一阶段，后两个阶段是未来计划。',
'Wennie_Wan_Bilingual_Learning_Notes_three_stage.pdf, pages 1–2; existing first-year presentation framing.',kicker='RESEARCH PLAN')
add('benchmark','The controlled fracture problem',
'This is a two-dimensional specimen with a starter crack on the left. The bottom is fixed and the top follows a displacement cycle. The bulk material is linear elastic. A phase field represents fracture, and a fatigue law reduces fracture resistance. These are normalised benchmark parameters. FEM and PIDL solve this same model.',
'这是一个左侧带初始裂纹的二维试件。底边固定，顶边施加循环位移。基体使用线弹性材料，相场表示断裂，疲劳定律降低断裂阻力。这里使用归一化基准参数。FEM 和 PIDL 求解的是同一个模型。',base+' Section 4.1.',kicker='MODEL')
add('phase','Phase field: damage and fracture resistance',
'The phase field d describes damage across the specimen. Zero means intact material and one means fully damaged material. The length scale controls the width of the diffuse crack. The model balances elastic energy and the energy needed to form a crack. Fatigue reduces the fracture-energy term through the factor f.',
'相场变量 d 描述试件内的损伤。零表示完好，一表示完全损伤。长度尺度控制弥散裂纹的宽度。模型在弹性能与形成裂纹所需的能量之间取得平衡。疲劳通过因子 f 降低断裂能项。',base+' Section 4.1; phase-field formulation in the report Chapter 3.',kicker='MODEL')
add('fatigue','Fatigue history and degradation',
'Damage reduces tensile stiffness through g of d. The active driver is the raw tensile energy multiplied by this factor. We accumulate fatigue history from the active driver along the loading path. Below the history threshold, f is one. Above it, f decreases, so further fracture costs less energy. History and damage are different variables.',
'损伤通过 g(d) 降低拉伸刚度。有效驱动力等于原始拉伸能乘以这个因子。疲劳历史沿加载路径从有效驱动力累积。历史低于阈值时，f 为一；超过阈值后，f 下降，使进一步断裂所需的能量降低。疲劳历史和损伤是不同变量。',base+' Section 4.1; fatigue-law figure from original slide 8.',kicker='MODEL')
add('fem','FEM: one loading substep',
'FEM starts from the previous accepted fields and history. At the current load, it first solves displacement with damage fixed. It then solves damage using the displacement field. During the damage solve, the code calculates trial fatigue values from the current trial state. The displacement and damage solves repeat until the staggered stopping test is met. The code then accepts the fields, commits the history and moves to the next loading substep.',
'FEM 从前一接受态的场和历史开始。在当前载荷下，先固定损伤求位移，再利用位移场求损伤。在损伤求解中，代码根据当前试算状态计算试算疲劳量。位移和损伤交替求解，直到满足交错迭代的停止条件。随后接受当前场、提交历史，再进入下一个加载子步。',sourcecode,kicker='COMPUTATION')
add('pidl','PIDL: one loading substep',
'PIDL uses a neural network to represent displacement and damage. At the current load, it evaluates the fields and computes the energy objective and damage penalties. RPROP updates the network weights, and this loop repeats. The fatigue factor from the previous accepted history stays fixed during fitting. After fitting, the code accepts damage, updates fatigue history and refreshes f. It carries the fitted weights and updated history into the next loading substep.',
'PIDL 用神经网络表示位移和损伤。在当前载荷下，先评估场，再计算能量目标和损伤罚项。RPROP 更新网络权重，并重复这个循环。拟合期间，由前一接受态历史得到的疲劳因子保持固定。拟合结束后，接受损伤、更新疲劳历史并刷新 f。拟合后的权重和更新后的历史一起传到下一个加载子步。',sourcecode,kicker='COMPUTATION')
add('cycle','Iterations, loading substeps and cycles',
'These are three different levels. Inner iterations solve or fit the fields at one fixed displacement. After that loading substep is accepted, its fields and history are carried forward. Five loading substeps make one physical cycle. The fourth is the peak and the fifth unloads to zero. Network weights and numerical fields change during computation; the prescribed material parameters stay fixed.',
'这里有三个不同层次。内层迭代在一个固定的位移下求解或拟合场。接受这个加载子步后，场和历史传到下一步。五个加载子步组成一个物理循环；第四步是峰值，第五步卸载到零。计算过程中网络权重和数值场会变化，规定的材料参数保持固定。',base+' Sections 4.1.1–4.1.2; production settings with explicit_cycle_displacements.',kicker='COMPUTATION')
add('compare','What the paired comparison checks',
'The paired study contains four calculations: FEM and PIDL on Q4 and T3 meshes. They use the same ordered nodes and the same five-step loading sequence. I first compare the recovered starting damage, then event timing, then local fields. The history and fatigue-factor maps use peak states after history update. Within each topology, the fields use matching native Gauss-point support.',
'配对研究包括四组计算：Q4 和 T3 网格上的 FEM 与 PIDL。它们使用同一组有序节点和相同的五步加载序列。我先比较恢复后的初始损伤，再比较事件时间，最后比较局部场。历史和疲劳因子图统一使用历史更新后的峰值状态。同一拓扑内使用匹配的原生高斯点支持。',base+' Sections 4.1–4.3; '+str(F/'analysis/source_and_timing_audit.json'),kicker='COMPARISON')
add('figure','Recovered initial damage',
'The four calculations start with a similar crack shape, but their recovered damage fields differ. The weighted relative damage difference is about eight per cent on Q4 and seven and a half per cent on T3. Fatigue history starts at zero and f starts at one. This gives us the actual starting conditions for interpreting later differences.',
'四组计算的初始裂纹形态相似，但恢复后的损伤场不同。加权损伤相对差异在 Q4 上约为百分之八，在 T3 上约为百分之七点五。疲劳历史从零开始，f 从一开始。这些是解释后续差异时应使用的实际起点。',base+' Section 4.2; initial-state tables.',image=str(C/'figures/initial_damage_four_arms.png'),message='Recovered damage differs; fatigue history starts at zero',small='Weighted damage relative L2: Q4 8.04% · T3 7.47%',kicker='RESULTS')
add('events','Event timing under one rule',
'I apply the same boundary-damage rule to all one hundred and twenty saved peaks in each calculation. First detection occurs at cycle eighty-four for both FEM runs, eighty-five for PIDL-Q4 and eighty-nine for PIDL-T3. Confirmation is labelled three physical cycles later for every calculation. Q4 gives closer event timing here. The next question is whether the local fields also agree.',
'我对每组计算保存的 120 个峰值使用同一个边界损伤判据。两组 FEM 都在第 84 个循环首次检测到事件；PIDL-Q4 为第 85 个，PIDL-T3 为第 89 个。四组的确认标签都取首次检测后三个物理循环。这里 Q4 的事件时间更接近。接下来要问的是：局部场是否也一致？',base+' Section 4.3; '+str(R/'local_archive/report_ch4_revision_20261015/analysis/unified_events.csv'),kicker='RESULTS')
add('figure','Damage at the common c83 peak',
'Cycle eighty-three is before the earliest event in every calculation. The difference maps show a broader PIDL damage band in parts of the crack wake, with less damage near parts of the advancing front. The mismatch changes with position. A single average would lose this information.',
'第 83 个循环早于四组中最早的事件。差值图显示，PIDL 在部分裂纹尾迹区域的损伤带更宽，而在部分推进前沿的损伤更低。差异随位置变化，单个平均值无法保留这些信息。',base+' Section 4.4.1.',image=str(C/'figures/hard5_c83_damage_comparison.png'),message='Local differences change along the crack path',small='Same physical cycle and peak phase in all four calculations',kicker='RESULTS')
add('figure','Fatigue history at the common c83 peak',
'These maps use accumulated fatigue history after the accepted peak step. The domain means are close, but the spatial relative differences are about thirty per cent for Q4 and seventeen per cent for T3. PIDL has a lower local maximum on Q4 and a higher maximum on T3. The direction of the difference therefore depends on the location and topology.',
'这些图使用峰值子步接受并更新后的累积疲劳历史。全域均值接近，但空间相对差异在 Q4 上约为百分之三十，在 T3 上约为百分之十七。PIDL 在 Q4 上的局部最大值较低，在 T3 上却较高。因此差异方向取决于位置和拓扑。',base+' Section 4.4.3; '+str(F/'analysis/native_GP_statistics.csv'),image=str(C/'figures/c83_history_post_commit.png'),message='History relative L2: Q4 29.87% · T3 16.90%',small='Post-update GP histories; native-cell means shown',kicker='RESULTS')
add('figure','Fatigue factor at the common c83 peak',
'The factor maps show where accumulated fatigue has reduced fracture resistance. The full-domain mean absolute differences are small. In the central strip near the crack line, they rise to about zero point zero two seven for Q4 and zero point zero three six for T3. Positive differences mean a larger factor in PIDL; negative differences mean more fatigue degradation in PIDL.',
'疲劳因子图显示累积疲劳在哪些位置降低了断裂阻力。全域平均绝对差异较小；在裂纹线附近的中央窄带内，Q4 约为 0.027，T3 约为 0.036。正差值表示 PIDL 的因子更大，负差值表示 PIDL 的疲劳退化更多。',base+' Section 4.4.4; '+str(F/'analysis/same_state_GP_differences.csv'),image=str(C/'figures/c83_factor_post_commit.png'),message='Central-strip factor MAE: Q4 0.02712 · T3 0.03617',small='Central strip: |yGP| ≤ 0.03 · Signed difference: PIDL − FEM',kicker='RESULTS')
add('evolution','Early, middle and late evolution',
'I compare three saved peaks: cycles twenty, sixty and eighty-three. On Q4, the history-field difference increases across these checkpoints. On T3, it first decreases and then rises slightly. The factor difference increases on both meshes. These are three sampled states, with lines joining them to help us read the changes.',
'我比较三个已保存的峰值：第 20、60、83 个循环。Q4 的历史场差异在这三个时刻逐步增大；T3 先减小，之后略微回升。两种网格的因子差异都在增大。这里展示的是三个采样状态，连线只是帮助阅读变化。',base+' Section 4.4.2; fatigue metric tables.',image=str(C/'figures/early_middle_late_metrics.png'),kicker='RESULTS')
add('figure','How energy and damage combine locally',
'The active driver is the product of raw tensile energy and damage degradation. Its value depends on where the energy concentration sits relative to the damaged region. For Q4, the active-energy integral differs by about six per cent, but the spatial relative difference is about forty-eight per cent. Existing field-exchange checks show how sensitive this product is to the local arrangement.',
'有效驱动力是原始拉伸能和损伤退化因子的乘积，其数值取决于能量集中区相对于损伤区的位置。在 Q4 上，有效能积分差异约为百分之六，但空间相对差异约为百分之四十八。已有的场交换检查说明，这个乘积对局部空间关系很敏感。',base+' Section 4.5.1; native-GP c83 energy decomposition.',image=str(C/'figures/hard5_c83_active_q4.png'),message='Q4 active energy: integral +5.81% · relative L2 0.476',small='ψactive = g(d) ψraw, evaluated before spatial averaging',kicker='INTERPRETATION')
add('attempts','What the existing checks clarified',
'I also examined ways to reduce the gap. Richer local representations changed the fields, but did not give a consistent match. The paired meshes exposed different responses to discretisation. Re-solving displacement with damage fixed left most of the active-field difference. At cycle eighty-three, Q4 changed from zero point four seven six to zero point four six three. These checks motivate closer tests of the damage state and coupled updates.',
'我也检查了缩小差距的办法。更丰富的局部表示改变了场，但没有得到稳定的一致结果。配对网格暴露了两种方法对离散方式的不同响应。固定损伤重新求解位移后，大部分有效场差异仍然保留。第 83 个循环的 Q4 差异从 0.476 变为 0.463。这些检查推动我们进一步研究损伤状态和耦合更新。',base+' Section 4.6. Existing fixed-damage re-solves use bounded damage and η=10⁻⁶ sensitivity for the common comparison.',kicker='DIAGNOSTICS')
add('summary','What the first-year study established',
'The first-year work produced a fatigue PIDL implementation and a more consistent comparison with FEM. The paired study gives close event timing on Q4, while local damage and fatigue fields still differ. The comparison also identifies specific numerical questions: the recovered starting state, current-step fatigue treatment and damage constraints. These findings define the next part of stage one.',
'第一年工作建立了疲劳 PIDL 实现，并形成了更一致的 FEM 对比。Q4 的配对事件时间接近，但局部损伤和疲劳场仍有差异。比较还明确了具体数值问题：恢复后的初始状态、当前步疲劳处理和损伤约束。这些认识决定了第一阶段接下来的工作。',base+' Section 4.7.',kicker='FIRST-YEAR FINDINGS')
add('controls','Next: explain and reduce the numerical gap',
'The next controlled comparisons will change one factor at a time. First, start from a common damage and history state. Then compare current-step fatigue treatments. Finally, test damage constraints and check residuals on the final accepted fields. I will compare the full trajectories as well as event timing and local-field differences. This should show which changes improve numerical agreement and where differences remain.',
'下一步控制比较将一次改变一个因素。先使用共同的损伤与历史初始状态，再比较当前步疲劳处理，最后检查损伤约束及最终接受场的残差。我会同时比较完整轨迹、事件时间和局部场差异，从而判断哪些改变改善了数值一致性，哪些差异仍然存在。',base+' Sections 4.6–4.7; future-work discussion in this chat. Proposed work.',kicker='FUTURE WORK · STAGE 1')
add('observations','Stage 2: prediction from limited observations',
'Once the numerical basis is clear, I will study limited observations. The proposed comparison starts with one synthetic crack mask, then two masks with a known time interval, and then adds a past-loading summary. The future loading and growth target stay fixed. I will compare prediction errors against simple persistence and growth extrapolation, and ask which extra information improves the forecast.',
'数值基础明确后，我将研究有限观测。拟议比较从一张合成裂纹掩膜开始，再加入带已知时间间隔的第二张掩膜，最后加入过去的加载摘要。未来加载和增长目标保持固定。我会用保持当前状态和增长外推等简单方法作对照，判断哪些额外信息能改善预测。',old+' Original slides 11, 15–16; three-stage bilingual notes. Proposed study.',kicker='FUTURE WORK · STAGE 2')
add('roads','Stage 3: a defined pavement problem',
'The road stage needs a specific material, loading problem and measurement target. I will select the mechanical model for that problem, calibrate it with relevant data, and test future crack evolution on measurements kept separate from calibration. The choice of an elastic, viscoelastic or cohesive model will follow the target pavement problem. This is the later road-validation stage of the PhD.',
'道路阶段需要明确材料、加载问题和测量目标。我将针对该问题选择力学模型，用相关数据标定，再用与标定分开的测量数据检验未来裂缝演化。弹性、黏弹性或黏聚模型的选择将由目标道路问题决定。这属于博士后续的道路验证阶段。',
'Three-stage bilingual notes; future-work discussion in this chat. Model choices are planned options, not claims about the present linear-elastic benchmark.',kicker='FUTURE WORK · STAGE 3')
add('thanks','Thank you',
'Thank you. I welcome your questions about the calculation process, the local-field differences and the next research steps.',
'谢谢大家，欢迎就计算流程、局部场差异和下一步研究提出问题。',old,kicker='DISCUSSION')
for orig,title,zh in [(9,'Target-specific Information','这一备份页来自独立的维修信息研究，用于讨论观测信息与具体预测目标的关系。它与本次循环疲劳配对比较属于不同研究。'),(10,'Source Comparison','这一备份页比较不同信息来源设计对目标概率区间宽度的影响。它来自独立的维修信息研究，不是道路裂缝预测结果。'),(12,'Supervised Field Prediction','这一备份页保留独立监督学习示例，展示参考损伤、FNO 平均预测和绝对误差。它与本次逐加载步拟合的 PIDL 是不同任务；这里不据此判断时序疲劳预测能力。')]:
 add('backup',title,'',zh,old+f' Original slide {orig}; original notes retained.',original=orig,kicker='BACKUP')
(W/'build/content.json').write_text(json.dumps(slides,ensure_ascii=False,indent=2)+'\n')
print('Wrote',len(slides),'slide specifications')
