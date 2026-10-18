# W0/W25 原配对：严格诊断修复后固定200步结果

W0逐位复现C；W25没有更接近FEM。综合场误差较C/W0高31.15698%，u/v/d三通道均变差。负damage与高斯点回退减轻，但最大节点回退增加64.58074%，不能把更强惩罚解释为FEM场改善或硬可行性。

## 原因与最小修复

原9个超容差分量来自分项梯度分别经过共享float32网络反向运算，再在参数空间缩放相加，与完整loss先合并上游贡献再统一反传的运算顺序差异。实际GPU控制逐位重现旧direct、postscaled及全部raw components和9点；旧差异没有删除。单一联合反传的独立手算链式系数与完整log直接反传逐位一致；只提前缩放仍分开反传有12点超差。固定hidden3局部GEMM同输入/伴随量的float32/float64控制支持该局部数值路径解释，不能称完整NN双精度参考。

修复仅改`tools/loss_weight_diagnostics.py`中诊断expected的构造，保留独立解析种子(c,c,beta*c,1e-5)，c=1/(ln(10)*S)，通过一次联合VJP传过网络。训练loss、直接backward、RPROP、初始化、历史和物理源文件未改；旧参数空间相加差异继续报告。原atol1e-6/rtol1e-4不变，故意破坏梯度/系数的测试仍会失败。44项轻量检查、精确代码复审及实际零步证据复审通过后才启动本配对。

诊断Run `pf_s04e011_wgradfix_8edc762_20261018T210153Z`，GPU5，3.08903s，0优化/history/FEM。见[算术实测](weight_gradient_arithmetic_controls_20261018.json)、[代码复审](weight_gradient_fix_code_review_20261018.json)、[实测复审](weight_gradient_fix_evidence_review_20261018.json)。

## 执行身份与范围

- Run `pf_s04e011_wpair_fix_8edc762_20261018T210743Z`，source `8edc762a99bacfa6825ed413a148fbcccd09a921`，branch `codex/pidl-weight-gradient-fix-20261018`，Taobo GPUServer8 GPU5，torch2.7.0+cu126，float32，22GiB allocator。
- Wrapper3733082、worker3733119；命令及UTC见本地retrieved/readout/receipt.json与retrieved/launch.json。运行UTC21:09:51起；worker实际elapsed31.82759s，峰值allocated2.65253GiB，exit0。各200、总400更新；history/FEM均0。
- 仅gamma：W0=16875，W25=421875(beta25)；weight decay1e-5及其他loss权重不变；对称0、FEM监督0。新增硬下界/上界关闭；原C的251节点预裂纹线d=1保留。
- 同C初始NN、FEM U0二维d0与hist_alpha，固定锚点/缓冲区、相同c1s1位移U=.02999988、nativeQ4 86756节点/86408单元。初态U0 damage到规定float32 FEM U0逐位相等；该初态不是已加载FEM c1s1解。
- 原完整预检通过，包括bundle重载、初始两beta梯度/首步参数逐位一致、可逆bias扰动触发Eh=9.1818056e-6后完整恢复。每臂k0/1/200、每beta的手算联合/直接梯度Linf均0；0history/新FEM/轨迹。原点Eh=0不影响其后实际gamma分化。
- 诊断外部175+5s，配对3300+5s，合计最坏3485s<3600s；实际两worker elapsed合计34.91662s。旧失败Run及原阴性结果保持原样，未追加其他训练。

## 同一FEM评分

固定update0/200，不挑best点。已有FEM `pf_s04e011_mcs_20261017_v1/retrieved/inputs/c0001_s001_post_commit.mat`只用于输出封存后的离线评分；无目标场进入训练。C来自历史`pf_s04e011_abc_20261018T115520Z`；现W0的0/200全部u/v/d数组与C逐位相同，故没有数值回放漂移。

J=sqrt(sum(m*((du/.12)^2+(dv/.12)^2+dd^2))/(3*sum(m)))；同canonical float64坐标、正nativeQ4 lumped nodal质量；高斯点统计用GP4物理Jacobian权重。J与负damage/回退均不裁剪、不镜像、不平滑。

| 固定200步指标 | C = W0 | W25 | W25相对C/W0 |
|---|---:|---:|---:|
| 综合J | .001404643135 | .001842287484 | 高31.157% |
| u RMS/.12 | .001618555246 | .001815237103 | 高12.152% |
| v RMS/.12 | .001752076084 | .002532330886 | 高44.533% |
| damage RMS | .000479140191 | .000688682844 | 高43.733% |
| 固定前区ROI J | .001585236786 | .003175642028 | 更差 |
| raw驱动relativeL2 | .334936219 | .401055208 | 高19.741% |
| active驱动relativeL2 | .246171792 | .333749578 | 高35.576% |
| 节点最小d | -.000163859615 | -.000055445198 | 负值深度减轻 |
| GP最小d | -.000157593209 | -.000052538693 | 深度减轻66.662% |
| 最大节点回退 max(d0-d,0) | .001865923405 | .003070950508 | 增加64.581% |
| 最大GP回退 | .000554162766 | .000103652613 | 减少81.296% |
| GP负d面积比例(d<−float32 unit epsilon) | 97.70239% | 74.18591% | 均未消失 |
| 正初始damage区GP回退面积/全域面积 | .0340525% | .0293122% | 均未消失 |

优化前共同J=.0151699573655；W0下降90.74063%，W25下降87.85568%。这些是相对于加载FEM同状态的优化改善，与初始二维damage到FEM U0的零误差是不同比较。权重效果由共享初态的W25−W0识别，不把初始化收益计入gamma收益。

W25最大节点回退在(x,y)=(.002487217,.000256832)，d0=.4139423370→.4108713865；W0最大节点回退位于(-.259883103,.001154196)，.8883526921→.8864867687。原不可逆项按高斯点积分，对积分罚项施更大权重不等于保证每个节点d>=d0；本次结果直接显示两种极值可反向变化。机制解释不超出当前固定状态。

第一步基础能量S1共同由.00565921跳至6.72209(约1187.81倍)，随后固定200端点回落；本次不证明单调、收敛或全局最优。W25初始首步与W0相同，后续活动惩罚与共享NN/RPROP轨迹产生总权重效应；不能声称只孤立改变了不可逆误差。

## 取回、场图与结论

本地Run根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_wpair_fix_8edc762_20261018T210743Z`。
完整检查点、梯度向量及raw/active/strain GP原数组留在`/mnt/data2/drtao/pidl_archives/pf_s04e011_wpair_fix_8edc762_20261018T210743Z/readout`。本地取回所有29份compact exports；6份fields仅保留u/v/d，producer逐数组/类型验证精确；其余8份pt和各省略键列入manifest，未声称全量下载。5,257,996字节scoring.tar.xz SHA256 `570b28361da4b27e4a3b36130d45b547d677eb7b65c260989c1a046c88df394f`，全部取回文件大小/哈希验证。

离线源982a2e4f比较代码及82435a24纯sidecar标题修正已复审。`comparison/FEM_C_W0_W25_fields.png`和`C_W0_W25_signed_errors.png`为同前区、同行同色标；`analysis/`还有完整域、初始/终点及剖面。共9图具sidecar并通过验证。

**当前选择：保留C/W0的gamma16875，不选W25作为更接近FEM的设置。** 下一项最小验证先选无训练的离线hard-map影响检查：复用0e8362b5已通过的全网格代数可行性/初始梯度检查，只补现有W0端点上会被截断的节点、空间范围、截断量及饱和/释放梯度比例。不得把投影后的场当成优化结果或FEM收益。主J平方约96.12%来自u/v，硬box首先是可行性候选，未证能修复主要位移误差；只有该检查表明值得继续，才另行提出固定gamma16875及其余权重的同200步hard-box单因素验证。本轮没有启用硬box、追加训练、扩展轨迹或新增FEM。

科学裁定：本单一已见合成状态、固定200步下，gamma25相对gamma1的FEM逼近结果为negative；同时保留其GP惩罚/负值改善。没有泛化、完整轨迹、物理真值或teacher资格结论。原E011资格限制和其它负结果不变。
