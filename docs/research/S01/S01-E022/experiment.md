---
storyline_id: S01
experiment_id: S01-E022
protocol_revision: v1
created_at: 2026-10-17
status: frozen_pending_independent_design_review
branch: codex/s01-e022-semantic-localization-20261017
base_commit: 17e14b49
---

# 冻结E003裂缝类别空间归因，尝试把有益修正送入原前三容量

## 问题、信息轴及先例

C2 real-road当前图像检测，有限候选银行、目标身份计数、固定地点组条件OOF。唯一问题：E003冻结分类器对“裂缝相对背景”的空间证据，能否使有益修正进入每原源组前三，并在同1FP/image、IoU=.5下取得保旧实际OOF净收益？比较器为原E003，不是新的检测器或未来预测。

|先例|已用信息及已知结果|E022区别|
|---|---|---|
|E009|576池化内容+12标量的589参数二值定位衰减，净0|读取池化前7×7空间图及冻结类别头的margin导数；不拟合高维质量头、不衰减检测分数|
|E011|12标量的低容量U，净0|新增类别条件空间位置，非几何/置信度重组|
|E019|同池化缓存PCA2，净0|不读576npy、不压缩缓存；池化已丢失的空间分布重新通过冻结网络读取|
|E020|缓存草图8及Q/N监督方向，净0|不换投影/方向，不学习表示，仅原11系数角色头|
|E021|无类别语义的灰度暗细线C/D，前三0、OOF旧684/684净0|完全移除灰度响应；使用E003曾学过裂缝/背景标签的权重与类别margin梯度。不是调核、灰度阈值或C/D缩放|

“更有语义”仅指输出由既有裂缝类别权重条件化，不是已证明定位准确。E003是二值分类器，可能学到背景/接缝；7×7很粗、共享context相对训练crop存在分布变化、ReLU可全零、分类正确不保证框准确。此风险不靠展示漂亮热图解决，必须经过容量及实际检出测试。现有资产未提供已合格的像素裂缝teacher；不下载新权重/外部数据、不用GT制作预测掩码，不把归因图当分割GT。FIT仅3/5/6有益GT、10条重叠支持删除诊断，均不能当独立样本扩增。

## 仅一个固定测量，不搜索表示

输入仍原E017固定19成员ZIP、原metadata、835严格锁定训练图与31156候选身份；另读取指定E003 best_ranker.pt，SHA bc304c5f5275975b1b5ec99fa6c398dba99835892c39e40a914896f8c3e22e65。旧43347原框、19384基础eligible、分组/监督不变。只允许此train根；旧四资格地点353/1459/2028/5982与新确认/validation/reserve封存。不目录枚举、不补图、不按GT筛图。逐图hash后同字节buffer解码，最多同时一张原图、16个context。

共享context继续原框与修正框union，各方向加宽高25%，floor左上/ceil右下并clip；固定RGB、torchvision0.26.0 Resize((224,224))默认bilinear/antialias、ToTensor、ImageNet mean/std，float32、eval、无增强/自适应统计。每候选恰一次backbone。取冻结MobileNetV3-small最后features张量F(576,7,7)，z=mean_ij F。冻结classifier输出两个logit，m=logit_crack−logit_background，a_k=dm/dz_k。只在detach的z上enable_grad，所有模型参数requires_grad=False；backbone no_grad，禁止backbone backward、参数梯度、优化器或训练。H_ij=ReLU(sum_k a_k F_kij)，存7×7 H和两logit、导数/参数冻结检查及空间尺寸，不存庞大F。该H为margin Grad-CAM的统一49倍（标准权重对F梯度平均为a/49），比例对下述质量比例抵消；非概率/分割。

以7×7等分context单元的**精确面积覆盖比例**w_ij(B)计算z(B)=sum(H*w)/sum(H)−mean(w)。这样短框不会因无cell中心落入而直接空掉，但不能恢复7×7内细节；不插值伪造分辨率。输入两列C_sem=z(B1)，D_sem=(z(B1)−z(B0))/2，范围[-1,1]。M<=1e−12则两值0并记录，不能删除候选/改资格。合格输入的修正框严格位于图内且正面积，因此共享context必非空；如仍为空属于身份/几何失败并停止，不改资格补救；有限数值、尺寸、标签顺序、head导数检查失败直接停止。预测提取函数只接图像/两框/冻结模型，绝不接GT/地点监督。真实run前不提取这些新特征，不按旧正例选择层/尺度/类别target。

依据：[Grad-CAM原论文](https://openaccess.thecvf.com/content_ICCV_2017/html/Selvaraju_Grad-CAM_Visual_Explanations_ICCV_2017_paper.html)支持类别梯度生成粗定位归因这一机制，并不证明裂缝定位质量；[torchvision官方实现](https://github.com/pytorch/vision/blob/v0.26.0/torchvision/models/mobilenetv3.py)规定features/avgpool/classifier，实际运行仍需本地结构和固定checkpoint核验。上述margin/coverage是本实验明确假设，不将文献结论移植成结果。

## 学习、隔离及保护机制

除末两列信息源外，沿E021六列接口、Q5/N4/A2共11监督系数。Q目标corrected_max_IoU，N有效定位且novel_reference，A已有admitted且lost0/FP0；权重与L2=.01、截距不惩罚、float64正规方程、残差/目标不劣常数容差1e−9完全不变。clip角色值，r=Q*N*A仅排追加、不是检测概率。全部9主头先合格才角色预测。

每自身FIT8用固定r>0、1/16、1/8、1/4、abstain五政策联合比较；active须旧100%保留且净GT>=1和macro>0，决胜顺序沿净GT/较少追加FP/较少追加量/较大gate。无合格则弃权。E003原行/框/概率/score/顺序全部固定；同原重复IoU<=.7、正面积交集、x>=0、修正间冲突>.5、accepted-only状态、每图1/每固定四地点源组3，检测score仍旧s0，不扫描交集阈值或放大容量。

当前held像素固定前向与归因不拟合参数；自身held不能拟合头/归一化/gate。上游E003已见这些训练地点、研究者也见过历次结果，所以仅selector条件OOF，不称完整管线独立、新地点泛化或统计确认。三model/全OOF先冻结，再held/pooled评价与10个删除正支持地点行的诊断。诊断只重拟合角色头，固定语义描述/context/原FIT8监督/银行/main gate，不重选政策/新U/GT几何，不反馈主结果。

## 预算及可行性

未来最多一次S01-E022-R001，尚未授权执行。gpu-server/D-26-09/ad\xw436固定物理GPU1、逻辑0、原RTX PRO6000 UUID，原Python3.12.14/torch2.11.0+cu128/vision0.26.0+cu128；CUDA_VISIBLE_DEVICES=1、CPU线程1，3600s、聚合RSS4GiB、GPU allocated/reserved各4GiB、0.5s守护，无重试/换机/资源放宽；上限1GPU小时，冲突或资源不足就停止。原E012已有31156crop同模型前向的执行先例，但新context与head输入导数可能增加成本，不假定必然在预算内。

835源图解码+最多6案例，源读取/pixel_reads<=841；31156context测量/backbone rows/head forward rows/head input-gradient rows，各候选恰一次，批量<=16、最多2505批（835×ceil(40/16)，逐图候选数上限40）。0backbone backward、0参数gradient/optimizer steps，0新U/GT几何/full12refit/新地点。只做头输入导数属于真实autograd工作，不能记成无梯度计算。39角色拟合/solve、13组、38768主监督行、6context、188214角色预测行、3FIT基线/15政策/1pooled+3held。计数与内存覆盖模型加载/归因/保存图像/校验，不把GPU省略。

FIT正GT3/5/6、E017同容量GT知情机会+3/+4/+5重叠不可相加，只给可达到的机会，不给可学习功效保证。稠密Q/N标签不是稀少净增正例替代。最小决定性测试是固定语义图→同容量选择→真实OOF，而不是又试一批缓存压缩器或扩大模型。

## 冻结标准、组件及停止

唯一主标准：同1FP/image、IoU=.5、一次pooled12条件OOF，先核E003684旧命中，再要求旧保留>=95%、净GT>=1、地点macro召回变化>0。净1为最小可数工程收益，不要求全oracle/全FIT active。身份、数值、隔离、先冻结、预算为可解释性前提，原行100%保留不同于预算旧命中保留。

组件：L0源/权重身份、图有限性/零质量/覆盖，L1正例留池与保护弃权，L2已知正GT最大/所选入前三及预算、全部考虑位次，L3实际旧/新/失/净/macro及12地点变化。保存所有FIT正候选与竞争者的两值、H、角色/排序轨迹，不把非零热图/类别可视化/拟合损失下降/个别前移当主收益。

主通过→有限银行条件OOF收益；主未过→negative且保留组件进展。若仍前三0/全弃权，完成固定OOF后停止本**固定最后层margin-Grad-CAM双描述**家族，不换层/target/梯度法/平滑/分辨率/重加权/归一化/灰度/阈值/L2/gate/交集/容量救结果，也不R002。此时研究转向有合格像素定位监督/独立空间teacher或新增可信正例的证据建设，须另冻方案，不能宣称所有语义信息无用。若前三有而预算净无，下一方案只针对保存预算/冲突/旧损伤；仅FIT进展不声称OOF成功。

## 最小证据、图表与本次范围

保存19原样输入、模型hash与runtime/冻结/输入梯度审计、835图进度、31156对7×7H/logits/coverage/mass/两值及身份、39头数值、全部FIT/held排序与容量/预算、先冻结OOF/模型、十删除诊断、资源和严格清单。最多6来源图片hash快照。F00支持→前三/零图比例，F01E003同预算实际旧新失净及所有地点，F02实际图GT/原框/修正框与同候选保存7×7语义热图并排，显示粗网格边界/“归因非GT”。选择只在OOF冻结/评价之后：优先实际OOF追加按原score降序/image/box/key取6，若无追加则同序唯一FIT正机会，明确未选中/无OOF新增。不能挑最好热图；分析不新增匹配/政策/指标/前向，案例<=6额外解码。

本次仅冻结→指定6.1 sol-Medium独立设计审查→通过后实现与纯合成测试→精确版本独立代码及实际合成图表审查。Mac不真实图片解码/特征/拟合，不SSH/传送/push/R001。源码范围scripts/pavetrack_semantic_selector与对应tests/E022合同/审查/简短S01记录；仅引用E021及祖先，旧源码/结果不改。新worktree从已闭合17e14b49建立；设计审查和代码审查分别记录，任何失败修订须聚焦复审。
