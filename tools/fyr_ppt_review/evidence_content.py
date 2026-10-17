"""Presentation argument and bilingual narration, based on existing evidence."""
from pathlib import Path
import json,csv,copy
R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');W=R/'local_archive/fyr_ppt_evidence_revision_20261017'
old=json.loads((R/'local_archive/fyr_ppt_process_revision_20261017/build/content.json').read_text())
S=[];base=str(R/'local_archive/report_ch4_rewrite_integrated_20261015/draft/Chapter4_Integrated_Rewrite.md')
analysis=str(W/'analysis');uq=str(W/'uq/UQ_AUDIT_AND_SLIDE_PLAN.md')
def use(n,**kw):
 d=copy.deepcopy(old[n-1]);d.update(kw);S.append(d);return d
def add(kind,title,en,zh,source=base,**kw):
 d=dict(kind=kind,title=title,en=en,zh=zh,source=source,**kw);S.append(d);return d
def prose(title,rows,en,zh,**kw):return add('prose',title,en,zh,rows=rows,**kw)
def tab(title,values,widths,en,zh,**kw):return add('native_table',title,en,zh,values=values,widths=widths,**kw)
def fig(title,file,message,small,en,zh,source=analysis,**kw):return add('figure',title,en,zh,source,image=str(file),message=message,small=small,**kw)

use(1,kicker='INTRODUCTION');use(2,kicker='INTRODUCTION')
tab('What existing approaches provide',
 [['Approach','Useful output','Question for this PhD'],['Inspection and segmentation','Visible crack geometry','What hidden state is missing?'],['Mechanics models','Damage and fatigue fields','Can the neural solver reproduce them?'],['Supervised field prediction','A learned future-field map','What observations support prediction?']],
 [300,410,440],
 'The literature gives us several useful pieces. Inspection describes visible cracks. Mechanics models describe hidden damage and fatigue. Supervised models learn changes from examples. My first-year question sits in the mechanics part: can a neural solver reproduce the fields and history of a controlled fracture calculation?',
 '现有文献提供了几类有用方法：检测描述可见裂缝，力学模型描述隐含损伤和疲劳，监督模型从样本中学习变化。第一年的问题位于力学部分：神经求解器能否复现受控断裂计算中的场和历史？',
 source=str(R/'overleaf_paper_68334c/Chapter2/chapter2.tex'),kicker='LITERATURE REVIEW',foot='First-year question: field and history agreement in a controlled problem')
use(3,kicker='METHODS');use(4,kicker='METHODS')
prose('Elasticity, damage and fatigue',
 [['Intact elastic material','ε = sym ∇u     σ₀ = C : ε'],['Damage changes the stress response','ψel = g(d) ψ⁺(ε) + ψ⁻(ε)\nσ = g(d) ∂ψ⁺/∂ε + ∂ψ⁻/∂ε'],['Fatigue changes fracture resistance','ψfracture = f(ᾱ) Gc [d/ℓ + ℓ|∇d|²] / cw']],
 'We first calculate strain from displacement. The intact material follows a linear elastic law. Damage then reduces the active part of the elastic energy. Fatigue reduces the energy needed for further fracture. The bulk elastic law is linear, while damage and accumulated history make the full problem nonlinear and dependent on the loading path.',
 '先由位移计算应变。完整材料遵循线弹性关系，损伤再降低有效弹性能部分，疲劳则降低进一步断裂所需的能量。基体弹性关系是线性的，但损伤和累积历史使完整问题具有非线性和加载路径依赖。',
 source=base+' §4.1; '+str(R/'overleaf_paper_68334c/Chapter3/chapter3.tex'),kicker='METHODS',foot='AT1: w(d) = d, cw = 8/3   ·   Amor split   ·   Plane strain   ·   Residual stiffness = 0')
use(5,kicker='METHODS',en='The active fatigue driver is g of d times the raw tensile energy. At each accepted substep, the positive change from the previous driver adds to accumulated history. We store the current driver for the next substep. Above the threshold, the fatigue factor decreases. This factor reduces fracture resistance.',zh='有效疲劳驱动力为 g(d) 乘以原始拉伸能。在每个接受的子步，与前一步驱动力相比的正增量加入累积历史；当前驱动力保存给下一子步。超过阈值后，疲劳因子下降，降低断裂阻力。')
prose('The physical calculation chain',
 [['Known inputs','Geometry, initial crack, material parameters and prescribed load U'],['Fields at the current load','Displacement u → strain ε → elastic energy → damage d'],['History carried forward','Active driver a → ᾱnew = ᾱold + max(a − aprev, 0) → fnew']],
 'This is the chain behind both calculations. The geometry, material parameters and load are known inputs. We solve for displacement and damage. Displacement gives strain and elastic energy. Damage changes the energy, so the fields are coupled. The accepted active driver updates fatigue history and the factor for the next loading state.',
 '这是两种计算共同的物理链条。几何、材料参数和载荷是已知输入，需要求解位移和损伤。位移决定应变和弹性能，损伤又改变能量，因此这些场相互耦合。接受态的有效驱动力更新疲劳历史和下一加载态的因子。',
 kicker='METHODS',foot='a = (1 − d)² ψraw   ·   aprev is the previous accepted active driver')
use(6,kicker='METHODS');use(7,kicker='METHODS')
add('network','The neural field and its training objective',
 'The network takes spatial coordinates and returns displacement and damage fields. The current load enters through the boundary constraints. Eight hidden layers use four hundred neurons each and trainable ReLU activations. RPROP changes the network parameters to reduce the energy objective and damage penalties. Material parameters stay fixed. A larger network alone does not explain a better field.',
 '网络输入空间坐标，输出位移和损伤场。当前载荷通过边界约束进入。网络有八个隐藏层，每层四百个神经元，采用可训练 ReLU 激活。RPROP 更新网络参数，降低能量目标和损伤罚项；材料参数保持固定。仅凭网络更大，不能解释场为何改善。',
 source=base+' §4.1 and §4.6; production source commit ad749c8bbba8120b3961add989b11427fab86254',kicker='METHODS')
tab('State passed to the next substep',
 [['State','FEM','PIDL'],['Fields and numerical state','Accepted u, v and d','Network θ and accepted d'],['Fatigue memory','ᾱ and previous active driver','ᾱ and previous active driver'],['Fracture coefficient','Updated f(ᾱ)','Updated f(ᾱ)'],['Additional history','Stored maximum raw-energy history','Previous accepted damage for penalty']],
 [320,415,415],
 'Both solvers carry more than two fatigue variables. They store accumulated history and the previous active driver, then refresh f. FEM also stores its maximum raw-energy history and accepted fields. PIDL carries its network parameters and previous accepted damage. Saving a step records the state selected by the stopping rule. We still need to check the residual and bounds of those final fields.',
 '两种求解器传递的状态不止两个疲劳变量：都保存累积历史和前一有效驱动力，并刷新 f。FEM 还保存原始能量最大历史和接受态场；PIDL 传递网络参数及前一接受损伤。保存一步表示记录停止规则选出的状态，最终场的残差和界限仍需检查。',
 source=base+' §4.1.2; solve_fatigue_fracture.m; at1_history_fatigue.f90 history slots 1–4; model_train.py commit ad749c8',kicker='METHODS',foot='Accepted state: output of the stopping rule. Check its final residual and bounds')
use(8,kicker='METHODS');use(9,kicker='METHODS')
use(10,kicker='RESULTS AND DISCUSSION');use(11,kicker='RESULTS AND DISCUSSION')
fig('Q4 damage near the advancing front',W/'figures/q4_damage_zoom_profiles.png',
 'The PIDL wake is wider; the forward extent is close',
 'c83 peak   ·   Map: x = 0.35–0.50, y = ±0.035   ·   Raw profiles at fixed x',
 'The zoom and transverse profiles show where the Q4 fields differ. At x equals zero point two five, the thresholded PIDL damage band is wider. Near the front, their forward extents are close. This supports a local shape difference rather than a uniform damage offset. The band width here describes the phase field, not the physical crack opening.',
 '放大图和横向剖面显示 Q4 场在哪里不同。在 x=0.25 处，PIDL 的阈值损伤带更宽；在前沿附近，两者的前向范围接近。这支持局部形状差异的解释，而非整体损伤偏移。这里的带宽描述相场，不是实际裂缝张开宽度。',kicker='RESULTS AND DISCUSSION')
fig('T3 damage near the advancing front',W/'figures/t3_damage_zoom_profiles.png',
 'The PIDL band is wider and the front falls behind FEM',
 'Same c83 peak and crop as Q4   ·   Profiles show shape and position differences',
 'The T3 difference is larger. PIDL has a wider band in the wake and a shifted transverse profile at x equals zero point four. At x equals zero point four six, FEM still has high damage, while PIDL is close to zero. These observations separate band width, lateral position and forward growth.',
 'T3 的差异更明显：PIDL 的尾迹损伤带更宽，在 x=0.4 处横向剖面也有偏移。在 x=0.46 处，FEM 仍有高损伤，PIDL 已接近零。这些观察把带宽、横向位置和前向增长区分开。',kicker='RESULTS AND DISCUSSION')
tab('Damage differences in numbers',
 [['c83 diagnostic','FEM-Q4','PIDL-Q4','FEM-T3','PIDL-T3'],['Band width at x = 0.25','0.01316','0.01548','0.01180','0.01772'],['Centreline extent at d ≥ 0.5','0.4745','0.4708','0.4636','0.4322'],['Minimum raw nodal d','0','−0.01018','0','−0.00991']],
 [390,190,190,190,190],
 'These fixed diagnostics put numbers on the maps. PIDL has the wider band at the chosen wake section on both meshes. The front difference is much larger on T3. Outside the central strip, PIDL does not show widespread positive damage above zero point one, but it has small negative values. That makes the damage bounds part of the numerical question.',
 '这些固定位置的指标为图像观察提供数值。两种网格上，PIDL 在所选尾迹剖面的损伤带都更宽，T3 的前沿差异更大。中央窄带外，PIDL 没有大面积高于 0.1 的正损伤，但存在小幅负值，因此损伤界限也是需要处理的数值问题。',
 source=analysis+'/damage_sections_c83.csv; '+analysis+'/damage_descriptive_metrics.csv',kicker='RESULTS AND DISCUSSION',foot='Dimensionless coordinates   ·   Band width: d ≥ 0.5 within y = ±0.04   ·   Not crack opening')
use(13,kicker='RESULTS AND DISCUSSION',small='Raw ᾱ, shared log scale; display floor 10⁻⁴   ·   Cell means   ·   Metrics use native GP values')
fig('Where fatigue history accumulates',W/'figures/c83_history_factor_profiles.png',
 'The history peak changes in amplitude and location',
 'c83 after history update   ·   GP-weighted x bins, width 0.01   ·   |yGP| ≤ 0.01',
 'The profiles show the spatial pattern without normalising history to one. At cycle eighty-three, Q4 peak history is twenty-one point four four in FEM and seventeen point zero three in PIDL. On T3, it is twenty-two point two eight and twenty-six point seven seven. The largest values occur around the starter-crack region, so a peak alone does not describe the advancing front.',
 '剖面展示未经归一化的历史分布。c83 的 Q4 峰值为 FEM 21.44、PIDL 17.03；T3 则为 FEM 22.28、PIDL 26.77。最大值位于初始裂纹附近，因此单个峰值并不能描述推进前沿。',kicker='RESULTS AND DISCUSSION')
use(14,kicker='RESULTS AND DISCUSSION');use(15,kicker='RESULTS AND DISCUSSION')
prose('When the differences appear',
 [['Starting state','Recovered damage already differs at zero load: 8.04% Q4, 7.47% T3'],['First saved peak','Damage relative L2: 10.22% Q4, 10.43% T3 at c1'],['Later fatigue checkpoints','Q4 history gap grows from c20 to c83; T3 follows a different trend']],
 'The differences do not first appear near failure. The recovered damage already differs before cyclic loading, and the first saved peak also shows a field gap. The later history maps show how the mismatch develops. The stored checkpoints locate these differences in time, but they do not identify the exact inner iteration where each difference begins.',
 '差异并不是临近破坏才出现。循环加载前恢复的损伤已不同，第一个保存的峰值也有场差异。后面的历史图显示差异如何演化。这些检查点可以定位阶段，但不能确定每项差异从哪一次内层迭代开始。',
 source=analysis+'/damage_descriptive_metrics.csv; initial field and fatigue tables in '+base,kicker='RESULTS AND DISCUSSION',foot='Relative L2 uses FEM as denominator; nodal damage and native-GP history are separate metrics')
use(16,kicker='RESULTS AND DISCUSSION',small='Native GP product before averaging   ·   Energy diagnostic before PIDL history refresh')
use(17,kicker='RESULTS AND DISCUSSION',title='Attempts to narrow the field gap')
prose('What the evidence explains',
 [['Observed','Local damage shape, energy and fatigue history differ even when event times are close'],['Supported interpretation','The active driver depends on the spatial overlap of energy and damage'],['Still to separate','Initial damage, current-step fatigue, damage bounds and optimisation can all contribute']],
 'The product of raw energy and damage degradation helps explain why a close integral can hide a large local gap. The displacement re-solves also show that displacement alone does not remove the mismatch. We have not yet separated the effects of initial damage, fatigue timing, bounds and optimisation. The next controls test these contributions one at a time.',
 '原始能量与损伤退化的乘积，有助于解释为什么积分接近时仍可能存在较大局部差异。位移重求解也表明，仅处理位移并不能消除差距。目前尚未分离初始损伤、疲劳时序、界限和优化各自的影响；下一步将逐项控制检验。',
 kicker='RESULTS AND DISCUSSION',foot='Architecture changes are observations; a mechanism explanation needs a controlled comparison')
use(18,kicker='RESULTS AND DISCUSSION')
use(19,kicker='FUTURE WORK',title='Stage 1: resolve the numerical differences')
use(20,kicker='FUTURE WORK',title='Stage 2: prediction with limited observations')
prose('Uncertainty in future field predictions',
 [['Mean error','How close is the predicted mean to the reference field?'],['Interval coverage and width','How often does the interval contain the reference, and how wide is it?'],['Location and prediction horizon','Evaluate the crack region separately and follow error across future steps']],
 'Uncertainty is useful only when we test it against errors. I would assess mean error, interval coverage and interval width together. I would also check the crack region and future steps separately. The separate supervised study has archived summary scores, but the raw predictions and file identities need to be recovered before we can recompute calibration.',
 '不确定性需要与误差对照检验才有意义。我会一起评价平均预测误差、区间覆盖率和区间宽度，并分别检查裂缝区域与未来各步。独立监督研究保留了汇总分数，但重新计算校准前，还需要找回原始预测与文件身份。',
 source=uq,kicker='FUTURE WORK',foot='Planned evaluation for the supervised model   ·   Lower ensemble spread alone does not establish reliability')
use(21,kicker='FUTURE WORK',title='Stage 3: a measured pavement problem')
tab('Future work linked to the first-year findings',
 [['Order','Reason from current results','Next evidence'],['First: numerical controls','Local fields differ under close event timing','Common starts and matched updates'],['Then: limited observations','Visible shape does not give full history','Held-out complete trajectories'],['Finally: pavement adaptation','Current material is a controlled benchmark','Material tests and separate observations']],
 [335,420,395],
 'The order follows the first-year findings. I would first resolve the numerical controls and final-state checks. I would then test what observations add to future prediction on held-out trajectories. Pavement adaptation follows with a chosen material and measured loading. We can schedule the later stages once the first controlled tests show what evidence we need.',
 '未来工作的顺序由第一年结论决定：先完成数值控制与最终状态检查，再在独立轨迹上检验观测对未来预测增加了多少信息，之后结合选定材料和实测载荷开展道路适配。前面的控制检验明确所需证据后，再细化后续时间安排。',
 kicker='FUTURE WORK',foot='Proposed order, not completed results   ·   Stage 2 and Stage 3 remain future plans')
use(22,kicker='DISCUSSION')
MAIN=len(S)
# Supporting figures retain the full evidence while keeping the main sequence readable.
use(12,kicker='BACKUP: DAMAGE FIELD')
F=R/'local_archive/report_ch4_fatigue_fields_20261015/figures'
for a,word in [('q4','Q4'),('t3','T3')]:
 for field,label in [('history','history'),('factor','factor')]:
  fig(word+' fatigue '+label+' evolution',F/f'{a}_{field}_evolution.png',
   'The same peaks: c20, c60 and c83',
   ('Raw history, shared log scale, floor 10⁻⁴' if field=='history' else 'f in [0,1]')+'   ·   Cell means after update',
   'This supporting figure shows the full spatial comparison at the three saved peaks. FEM, PIDL and their signed difference use the same coordinates and colour scales. The history and factor maps use accepted states after history update. These maps support the evolution metrics shown earlier.',
   '这张补充图展示三个已保存峰值的完整空间对比。FEM、PIDL 和带符号差值使用相同坐标与色标。历史和因子图都使用历史更新后的接受态，与前面的演化指标对应。',source=str(F.parent/'analysis/source_and_timing_audit.json'),kicker='BACKUP: EVOLUTION')
tab('Fatigue history maxima at the saved peaks',
 [['Cycle','FEM-Q4','PIDL-Q4','FEM-T3','PIDL-T3'],['20','5.08','6.41','6.03','13.16'],['60','15.29','13.91','16.57','23.51'],['83','21.44','17.03','22.28','26.77']],
 [230,230,230,230,230],
 'The maxima make the topology dependence clear. PIDL is higher on Q4 at cycle twenty, but lower at cycles sixty and eighty-three. On T3, PIDL has the higher maximum at all three saved peaks. This is why I describe the location and stage of the difference instead of calling history uniformly underestimated.',
 '最大值清楚地显示拓扑依赖。Q4 上 PIDL 在 c20 更高，c60 和 c83 更低；T3 上 PIDL 在三个保存峰值都更高。因此需要说明差异的位置与阶段，不能概括为历史一致偏低。',
 source=analysis+'/history_peaks_and_means.csv',kicker='BACKUP: HISTORY',foot='Raw native-GP maxima   ·   c83 maximum x: FEM-Q4 −0.274, PIDL-Q4 −0.251; FEM-T3 −0.259, PIDL-T3 −0.251')
fig('Reported supervised interval coverage',W/'uq/reported_region_coverage.png',
 'Coverage varies by method and by spatial region',
 'Separate supervised study   ·   Archived summaries; raw predictions and file/time identities not rechecked',
 'These are archived summary scores from the separate supervised study. At nominal ninety-five per cent, the reported crack-region coverage ranges widely across models. Coverage alone cannot rank the methods because interval widths are missing. We need the original predictions to check calibration and identify the evaluation files.',
 '这是独立监督研究归档的汇总分数。在名义 95% 水平下，各模型报告的裂缝区域覆盖率差别很大。缺少区间宽度时，不能只按覆盖率排名。需要原始预测来复核校准并确认评价文件。',source=uq,kicker='BACKUP: SUPERVISED UQ')
fig('Reported rollout coverage and error',W/'uq/reported_rollout_coverage_and_error.png',
 'Closer coverage can accompany larger mean prediction error',
 'Archived summaries   ·   Correlated starts within 150 files   ·   No fresh calibration',
 'At horizon twenty, CA-FNO reports coverage closer to ninety-five per cent, but its mean prediction error is larger than FNO. That trade-off is visible only when we show error beside coverage. The starts within each file are correlated, so they do not count as independent trajectories.',
 '在第 20 步，CA-FNO 报告的覆盖率更接近 95%，但平均预测误差也比 FNO 更大。只有把误差和覆盖率一起展示，才能看到这一取舍。每个文件内的起点相关，不能当作独立轨迹。',source=uq,kicker='BACKUP: SUPERVISED UQ')
use(23,kicker='BACKUP: MAINTENANCE',
 en='This backup comes from a separate maintenance study. Grades run from one, best, to three, worst. Different repair models can match the same historical post-repair grades. The question is whether they also give the same chance of reaching grade three after three years. Some starting conditions give one value, while others allow a range. These ranges describe what the available information permits.',
 zh='这一备份页来自独立的维修研究。等级从一到三，分别表示最好到最差。不同维修模型可以符合相同的历史维修后等级。问题是：它们对三年后达到三级的概率，是否也给出相同预测？有些初始条件对应一个数值，有些则允许一定范围。这些范围描述现有信息允许的结果。')
use(24,kicker='BACKUP: MAINTENANCE',
 en='Here I compare four ways to collect information, with four hundred grade scores each. A uses one source. B repeats visits. C varies exposure. D adds a worst-grade source. The added source gives the narrowest average confidence interval for the target probability in this example. Dots represent datasets and diamonds show means. Stars mark runs that reached a resource limit. The value of observations depends on the prediction target.',
 zh='这里比较四种信息收集方式，每种都使用四百个等级分数。A 使用一个来源，B 重复访问，C 改变暴露时间，D 增加最差等级来源。在这个算例中，增加来源后，目标概率置信区间的平均宽度最小。圆点表示数据集，菱形表示均值，星号表示达到资源上限的计算。观测的价值取决于具体预测目标。')
prose('The Amor elastic-energy split',
 [['Elastic constants','K = E / [3(1 − 2ν)]     μ = E / [2(1 + ν)]'],['Active elastic energy','ψ⁺ = ½K ⟨tr ε⟩₊² + μ εdev : εdev'],['Compressive volumetric energy','ψ⁻ = ½K ⟨tr ε⟩₋²']],
 'This is the Amor split used in the benchmark. The positive volumetric part and the deviatoric part enter the active energy. The compressive volumetric part remains separate. K and mu come from Young’s modulus and Poisson’s ratio. In plane strain, the out-of-plane strain is zero, while the constitutive split uses the three-dimensional strain decomposition.',
 '这是基准模型采用的 Amor 分裂。正体积项和偏应变项进入有效能量，压缩体积项单独保留。K 和 μ 由杨氏模量与泊松比确定。平面应变下，面外应变为零，本构分解仍采用三维应变分解。',
 source=base+' §4.1; production source energy implementation',kicker='BACKUP: CONSTITUTIVE LAW',foot='⟨z⟩₊ = max(z,0), ⟨z⟩₋ = min(z,0)   ·   εdev = ε − tr(ε)I/3')
rows=list(csv.DictReader((W/'analysis/history_peaks_and_means.csv').open()))
rates=[]
for a,b in [(20,60),(60,83)]:
 vals=[]
 for arm,solver in [('q4','FEM'),('q4','PIDL'),('t3','FEM'),('t3','PIDL')]:
  lo=next(r for r in rows if r['topology']==arm and r['solver']==solver and int(r['cycle'])==a)
  hi=next(r for r in rows if r['topology']==arm and r['solver']==solver and int(r['cycle'])==b)
  rate=(float(hi['mean'])-float(lo['mean']))/(b-a);vals.append(f'{rate:.6f}')
  rates.append(dict(topology=arm,solver=solver,start_cycle=a,end_cycle=b,mean_history_gain_per_cycle=rate))
 if a==20:rate_table=[['Cycle interval','FEM-Q4','PIDL-Q4','FEM-T3','PIDL-T3']]
 rate_table.append([f'{a}–{b}',*vals])
tab('Average history gain between saved peaks',rate_table,[270,220,220,220,220],
 'These are changes in domain-mean history divided by the number of physical cycles between two saved peaks. Q4 PIDL gains less mean history than FEM in both intervals. T3 PIDL gains less in the first interval and slightly more in the second. This describes average accumulation over each interval. It does not resolve the cycle-by-cycle local rate.',
 '这里用两个保存峰值之间的全域平均历史增量，除以相隔的物理循环数。Q4 的 PIDL 在两个区间都比 FEM 累积得慢；T3 在前一区间较慢，后一区间略快。这描述区间平均累积，不能解析逐循环的局部速率。',
 source=analysis+'/history_peaks_and_means.csv',kicker='BACKUP: HISTORY',foot='(Mean ᾱ at end − mean ᾱ at start) / cycle interval   ·   Same post-update peak phase')
(W/'analysis/history_interval_rates.json').write_text(json.dumps(rates,indent=2))

for i,d in enumerate(S,1):d['number']=i
(W/'build/content.json').write_text(json.dumps(S,ensure_ascii=False,indent=2))
(W/'review/slide_map.json').write_text(json.dumps({'main_slides':MAIN,'total':len(S),'slides':[{'number':i+1,'title':d['title'],'section':d['kicker']} for i,d in enumerate(S)]},ensure_ascii=False,indent=2))
print('Main',MAIN,'Total',len(S))
