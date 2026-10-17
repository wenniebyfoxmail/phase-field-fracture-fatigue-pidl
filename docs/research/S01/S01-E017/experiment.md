---
storyline_id: S01
experiment_id: S01-E017
protocol_revision: v1
created_at: 2026-10-17
status: frozen_pending_independent_design_review
branch: codex/s01-e017-supervision-feasibility-20261017
base_commit: e075e1b76cee840c176f3d35b9e23d5534331987
---

# 定位质量与预算接纳监督的可行性检查

## 先对照终止路线，再定义唯一新轴

E009在旧四个已消耗资格地点上用576pooled+12标量的589参数logistic头学二值“修正框与任意GT最大IoU>=.5”，再把质量概率乘到修正检测分数。有效重复框仍为正监督；定位有效不等于预算新增。实际112框追加、10框进入检测预算，旧282/282保留但新增/净GT均0，partial FP110→112。

E011保留12标量/13参数ridge，学单值U=new−lost−FP，按predU>0过滤后仍按不变s0排序。各FIT仅4/1/4/3正支持；4个已知有益候选全被预测负，追加1729框、11框进入预算且均为FP；旧282/282保留、净0，partial FP110→114。禁止原样重跑质量头、旧ridge或换L2/阈值。

上述保存结果已只读核对，压缩对照在historical_failure_comparison.json；不重算旧四地点标签/特征/指标或拟合旧模型。E012随后把证据扩充为其他12既有训练地点7正GT/5地点、FIT3/5/6，但E013–E016仍没让已知正例入cap。E01670个正候选×政策记录全在源组3名额已满之后出现，故下一步首先检查可分解监督和预算竞争上下文是否存在，暂不承诺一个新头能学会。

**本实验唯一新轴：把“质量—目标新颖性—预算角色”拆开，配GT无关的原检测库相对竞争特征。** 目标不是更换回归器，而是辨别旧有效定位标签和单值U混在一起的不同机制，明确下一低容量学习需要的信息。新增监督维度/候选对不等于新增独立正GT，不能把密集几何标签当3/5/6问题已解决。

## 问题、范围与信息集

C1真实道路当前图像、训练监督/固定oracle修复空间可行性。能否在不变原框/检测分数/准入/cap下，利用明确分解的训练监督，在至少一个自身FIT8识别出实际保旧净增的固定oracle选择，并把“有几何改善却无预算收益”与有益机会分开记录？比较是同一FIT E003、一个固定validity-only诊断和一个固定decomposed诊断，均GT知情且不是模型或上界。

只读锁定E012-R004已有源包、候选身份/评分、三个既有FIT8单例记录，及E002元数据内这12既有train地点。旧四资格地点、validation/confirmation/reserve不作为运行输入；新确认地点继续封存。E009/E011只保留已归档标量对照，不带旧原图/GT/权重进运行。无原图、pooled/cache特征值、checkpoint、重新评分、新修正或新U。

三次审计各自使用明确FIT8 scope；当前held4的GT、其他fold单例标签、R004全12 oracle选择/标签不能进入该scope。运行可依次查看3个FIT各自的训练结果，但不进行held/full12检测评价、不挑主模型、不把跨fold复用GT当独立测试。作用域parser沿用E012；originals只读取qualification原43347行，跳过GT知情修正尾部。candidate_identity内潜在U/reason字段也不得进入新特征或监督，只信当前own-FIT8的既有标签。设计基于已看过的训练结果，没有确认性泛化主张。

## 固定分解监督

先在每个自身FIT按不变E003和同1FP/image、IoU=.5计算一次baseline及原预算命中身份集合H0，并与该FIT缓存baseline逐项核对。核验所有eligible候选/标签的索引、parent/image/location、s0、U=new−lost−FP、new/lost身份范围、admitted/cutoff。三个基线共3次，不重新逐候选评估U。

对每个自身FIT base-eligible候选（含之后被正交集/x拒绝者，报告流失）记录：

1. corrected_max_IoU：修正框对本图GT的最大IoU。最高值>0时以最小annotation index打破并列作为corrected_reference；最高值为0或无GT则reference=null，不虚构目标身份。
2. parent_max_IoU作为旧质量参照；parent_IoU_on_corrected_reference与修正框针对**同一reference**的IoU差gain_same_reference。无reference时gain=null。不能把原框对GT-A和修正对GT-B的两个最大IoU差当同目标改善。
3. valid_localisation=(corrected_max_IoU>=.5)，novel_reference=(reference非空且不在自身FIT的H0)。这是修正匹配参照，不声称被证明是原物理目标身份；同时保存parent-best-reference一致/切换/无参照状态。
4. 原封不动关联own-FIT缓存admitted、new/lost/FP/U及身份/单例cutoff，分开保存，不生成新U。admitted不等于TP，valid不等于新GT，gain>0不等于joint收益。

报告各label计数、distinct reference GT、位置分布和positive location支持，valid但FP、valid但未admitted、valid但reference已在H0、gain>0但U<=0等交叉表。正例、GT、图像、地点分别去重；未知计数不事前假定，FIT原U正GT3/5/6只核对来源身份，不当新监督充分性结论。支持少或某类为空应记录并限制后续模型，不把表能生成就叫可学。

## 三个新增GT无关上下文（不拟合）

原E011特征为绝对几何、原/修正概率与非parent最大IoU/最大分数，没有以下原库相对压力计数：

- original_higher_score_rows_per_image：当前scope所有原框中score>s0的行数 / scope图像数。
- original_equal_score_rows_per_image：当前scope所有原框中score==s0的行数 / scope图像数，保留原子分数并列信息，不加epsilon。
- higher_or_equal_score_nonparent_overlap_count：同图非parent原框中score>=s0且与修正框IoU>=.5的数量；这是匹配/冗余上下文，不是新的正交集阈值。

这些只从可获得的原框、分数、候选/图像scope计算，函数不接收GT/H0/labels。observed cutoff、GT overlap/reference、admitted/new/lost/U均为监督/审计，**不可作部署特征**。特征变化范围、常量、唯一值数量仅描述信息供给，不做标签相关性筛选、特征选择或声称预测力；FIT8与未来held4库大小不同，即便按图归一化仍可能有迁移差异。旧scalar12中的nonparent overlap score与此计数不能混为新增独立样本。

## 两个固定GT知情诊断，保持原检测和容量

共同固定准入：E012 base eligible、E015严格坐标正面积交集、x>=0。原检测/分数/顺序保持，s0不替换；修正间IoU>.5冲突、accepted-only状态、每图1/每四地点源组3保留。非入选者不占cap，不扫描交集/IoU/alpha/模型阈值。IoU=.5仅复用原检测匹配/重叠规则。

A validity_only：只保留上述共同准入且valid_localisation的候选，按不变s0降序、image/box/key稳定排序。它借用E009二值标签含义，但不是重跑E009的学习头或分数衰减政策；只是同当前cap下解释绝对定位有效为何未必有益。

B decomposed_novel_budget：A候选再要求novel_reference、own缓存admitted=true、lost=0、FP=0，按gain_same_reference降序，再按不变s0/image/box/key排序。故它把本图定位/目标新颖性和该FIT单例预算角色显式结合，目标是先验证新监督能否把有益候选排在有限容量内。不得仅按U>0代替这些字段，不枚举候选子集或用joint结果换顺序。每FIT固定A/B各计算一次实际联合预算比较，不能把缓存单例U相加当joint。

每个诊断均报告选中身份、原/修正框、保旧/新/失/净GT、macro变化、实际FP、correction前缀数量/身份，和已知U正GT入cap情况；即使某诊断为空也比较一次，保持完整预算记录。单例admission可随联合追加改变，故B也可能失败或非上界。

两诊断只是GT知情训练能力探针，不产生GT-free预测、可部署模型或学得收益；原检测作为当前使用方案不变，无保护下净增则建议弃权。共同准入/固定cap可能压低机会，但不为救结果修改。

## 结果标准、可达性和下一动作

必要有效性只包括来源/原框/分数、scope和既有label语义一致、特征GT-free及预算。新监督可用性表要如实给出，不以“多一个字段”当成功。

唯一主可行性判据：**三个自身FIT中至少一个B诊断在同1FP/image、IoU=.5达到原预算命中100%保留、净GT>=1、macro delta>0。** 这只支持当前固定监督政策下存在可控修复机会，绝不代表3/5/6足够训练，或任何实际OOF/学得净收益。只要求一折有最小countable机会，不要求全部FIT通过或追回7GT；+7是已有GT知情空间，不是B上界。A结果不投票、不选模型；B失败也不能用A成功救主判据。

组件层次：L0完整可靠监督表/GT-free上下文；L1可辨的定位/新颖性/预算角色及地点支持；L2自身FIT已知正例进原cap；L3至少一FIT固定B真实保旧净增，仍然是oracle可行性，不是最终检测效果。若B未达主判据，停止这一分解oracle家族，按共同准入流失、reference切换、单例/联合预算差异定位一个可控新信息需求，不加臂/改过滤条件/扩cap；可保留A或部分label组件进展。

若B有机会且监督分布可用，下一应另冻**低容量的分解监督学习探针**（学习定位/新颖性或预算接纳，GT-free上下文为输入），再以原检测/cap/弃权下真实OOF保旧>=95%、净GT>=1和macro提升验证。密集几何正例不提升独立新增GT数；需正/负支持与地点分布决定模型可用容量，禁止直接恢复高维头或把GT标签喂预测。若密集监督仍只支持相同3/5/6新增GT且无可观测区分，转监督/候选证据来源，不能循环换线性惩罚或权重。

## 预算、证据与本轮范围

拟议未来一次S01-E017-R001，gpu-server/D-26-09/ad\xw436，CPU1/禁GPU/OMP/MKL1，总900秒、主进程及后代聚合RSS4GiB，0.5秒资源守护。3FIT baselines、3上下文构建、最多且预期38768条监督记录（11588+13422+13758；有数不符停止）、6固定oracle联合比较。0model fits/新U/原图/头或backbone前向/梯度/线性求解/held比较/full12比较；无自动retry、预算加码/换机器或新地点。原库排序/二分计数避免按每候选扫描全库；几何只按本图GT及本图原框，图级复用。真实Windows时延未测，合成可行性不当生产时延保证。

最小输出：原框/分数/来源摘要，3自身FIT既有标签等价和baseline核验，分解监督表与独立GT-free上下文表，GT/地点支持/交叉表、两oracle各3scope选择轨迹和joint/prefix/FP分解、主可行性结论与不可推广边界，资源与语义输出收据。F00监督流转与地点支持、F01两固定oracle保旧/净增分折结果、F02按原分数稳定选最多6个B追加案例（无追加明确空）；README声明oracle/非新学习/非上界。只读保存结果绘图，不加政策/指标/新U。

当前用户只授权范围/预算/标准冻结、6.1 sol-Medium独立设计审查后实现和纯合成测试；之后同模型独立代码审查。**本轮不在Mac计算真实新监督、特征、GT匹配、joint或新oracle结果，不SSH/传送/推送/执行R001。** 历史保存数值只读可用于对照。新文件限scripts/pavetrack_supervision_feasibility、对应tests、E017协议/配置/锁/manifest/审查和S01记录；复用私有E015/E013读入/匹配/资源及原坐标门槛，不改冻结E003–E016。safe during running trainings。
