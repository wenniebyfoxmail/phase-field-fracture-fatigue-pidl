---
storyline_id: S01
experiment_id: S01-E023
protocol_revision: v1
created_at: 2026-10-18
status: frozen_pending_independent_design_review
branch: codex/s01-e023-pixel-supervision-20261018
base_commit: 45e07302
---

# 用可核验裂缝区域像素监督训练低容量空间读出，检验保旧实际收益

## 资格与解决目标

当前图像real-road C2检测，原835图/12训练地点/原候选银行，selector条件OOF。唯一决定性问题：新增的**人工多边形区域监督**能否使有益修正进入原前三容量并取得E003保旧净收益？比较器仍E003，同1FP/image/IoU=.5；不是新地点/完整上游独立或精确裂缝宽度证明。

核验范围及数值见asset_audit.json。原SHA72e3cfe6工作簿含835图850实例，其中819裂缝(249Alligator/570Transverse)、31Patch/Pothole；原835均覆盖，所有多边形有限/正面积/图内，裂缝bbox与原E003metadata全部匹配。六个此前固定已留存E022训练快照的overlay已实际打开，显示多边形沿裂缝区域但可能包入背景，非精确裂缝宽度；其中一例包络较宽。Crack polygon/bbox面积比例中位.4145，范围.0457–.9042。只可作为**人工裂缝区域包络**监督，不宣称物理宽度或像素参考完全准确。新源图读取0，仅6次原保存快照展示解码；封存地点字段不用于核验统计/训练，未开新像素。

现有模型资格：E003只有类别/框监督，其7×7归因不是mask。旧197图YOLO分割试验含353训练和1374/4073模型选择，非当前12地点合格独立teacher；其二类既有像素结果Dice0，多类Dice约.133，不能据模型名当合格空间来源。SAM2旧pilot需GT提示才部分有效，自动oracle仍差、类别无关，不用作新像素真值。旧结果只读，不新开其validation/test像素或前向。无需外部下载/新标注者或权重。

|先例|新增差异|
|---|---|
|E009|曾用576池化+标量高维二值质量；本次41系数像素头直接受区域标签约束，检测分数不动|
|E011|曾用12标量U；本次增加局部空间特征与人工区域像素标签|
|E019/E020|曾用PCA/监督缓存方向；本次不读576npy或再换其压缩器，空间单元上逐点监督|
|E021|灰度暗细线C/D无语义标签；本次使用人工多边形监督，不调整灰度配方|
|E022|冻结类别归因，前三0/旧684/净0；本次像素头目标是人工区域内外标签，且使用中间40×14×14特征；不是归因重缩放|

多边形监督、空间层/分辨率和容量均变，不能单因果归因于某一处。原有净增正GT3/5/6不增加；百万采样单元不是百万独立裂缝或新增净增正例。目标是一个可执行的最小像素监督修复，而非给旧负结果换标签。

## 唯一固定模型与允许信息

835图/31156两框共享union+25%context，floor/ceil/clip，RGB224及E022固定预处理；E003精确权重SHA bc304c5f5275975b1b5ec99fa6c398dba99835892c39e40a914896f8c3e22e65。只取MobileNetV3-small features[:6]，原生40×14×14，eval/no_grad/float32，0CNN参数更新/梯度，0分类头前向或导数。中间层选择为原生较细空间/小通道成本假设，不选层/分辨率/权重扫描。输出float32磁盘memmap(31156,40,14,14)，payload977052160bytes；单图/<=16context，逐图释放。原pixel identity/hash/root校验全部沿用，不读旧pooled缓存、不做PCA/草图或表示拟合。

每当前主fold只在其FIT8训练像素头。原835图的annotation snapshot与bank image/地点/尺寸/bbox逐一对齐；只对当前FIT图调用区域mask栅格化，先在原图尺寸用Pillow ImageDraw填充两裂缝类别polygon并union，其他类别不填。区域外0包含未标注裂缝的不确定性，不能称完整场景真值；保留该偏差。每context在14格固定行列索引[1,5,8,12]的16中心，映回原图floor后读二值区域标签；边界取clip到图内像素。预测无polygon/GT/地点参数。每context固定16点，不按标签/排名选点、无膨胀腐蚀/GT提示/增强。

每fold41系数加截距的像素ridge，y∈{0,1}，L2=.01/不罚截距/float64正常方程。正负层等总权重；层内地点→图→context→cell等质量，只有出现的层参与，单层常数允许但不能宣称学习了区域区别。保存各层/地点/图/上下文/单元支持；主pixel三次fit采样996992行，0优化器/SGD。数值残差<=1e−9、目标不劣同权重常数；单层pixel supervision视不可拟合区域区别，停止拟合后续selector并记录inconclusive，不造正例。

pixel map=clip(b0+sum b_k F_kij,0,1)，并非校准概率。每fold在其全部31156context预测固定14×14图，93468maps总计；像素头只见FIT8标签，held图固定无监督特征可以预提取。原框/修正框在14格均匀单元的精确面积覆盖，C=z(new)、D=(z(new)−z(old))/2，z=sum(P*coverage)/sum(P)−mean(coverage)。零质量给0并记账，不改eligibility；有效修正框在图内保证非空context，否则身份失败停止。

随后本fold同六列/11系数Q/N/A/L2/权重/目标/clip/r=Q*N*A，五固定gate与FIT联合择策保持E022，0检测score改动。pixel头和角色头同FIT标签阶段适配，FIT校准可能乐观；三个主foldheld保留隔离，不能称完整管线独立。所有3pixel头及9role头合格后才role prediction；模型/OOF先冻结再held/pooled评价。原10个role-only删除诊断在主gate一直弃权时无信息，本版不做删除refit，不增加监督独立性的声明；新增pixel held组件替代它们，条件OOF不变。

## 不变检测、标准与组件

原E00343347行/框/概率/分数/顺序保留；19384基础eligible、正面积交集、x>=0、原重复IoU<=.7、修正冲突>.5、accepted-only、每图1/每固定四地点组3、稳定并列、四activegate0/1⁄16/1⁄8/1⁄4加abstain均不变。FIT active仍100%保旧且净GT>=1/macro>0，否则弃权。主标准一次pooled12条件OOF先核684旧命中，再旧保留>=95%、净GT>=1、地点macro变化>0。净1是最小可数工程收益，无全部oracle/全部FITactive要求。

可行性：E017已有同容量GT知情机会+3/+4/+5重叠，不相加，不保证可学；新819区域实例提供不同空间监督，不增加3/5/6效用正GT。先检查采样正负支持/对齐，再一次冻结实际检验。训练损失、非零图、百万像素、局部排名均不救主标准。

组件L0标签身份/有限性/图内/正负采样支持/模型数值；L1保留正例与原检测；L2最大/所选正GT入前三、预算、保存考虑位；L3实际新/失/净/macro/地点差。OOF及三模型冻结后才为每个held候选生成14格中心polygon参考(只此时读当前held标签)，报告固定.5的区域Dice、Brier对自身FIT前景率常数、全前景/全背景基线及每图差；每图先等context平均再地点平均，像素不是独立样本。仅监督语义组件，不选择层/gate/模型或再拟合；0额外政策/检测指标。不能用该组件阈值过高抹掉已发生实际保旧收益，也不能用它救无检测收益。来源标签不是像素宽度teacher。

主过→有限银行保旧工程收益；主未过→negative，另记可用像素组件。若仍前三0/全弃权则完成固定OOF后停止此固定中间层+41系数像素ridge家族，不换层/容量/目标/采样/阈值/L2/归一化/交集搜索/R002。若像素组件改善但容量无，则下一路线需要新增可信效用支持或直接预算对齐目标；若像素组件也不改善，则先补合格标注/模型容量与域证据，不再仅换描述。下一方案必须另冻结，本版不自动启动。新确认/validation/reserve及353/1459/2028/5982继续封存。

## 预算、证据与本轮权限

未来最多一次S01-E023-R001，gpu-server/D-26-09/GPU1/CPU1，原精确runtime/UUID，3600s、聚合RSS4GiB、GPUallocated/reserved各4GiB/0.5秒守护，无重试/换机/放宽。源835图+<=6case读/解码上限841，31156冻结backbone rows、<=2505batch，0class head forward/gradient/新U/GT几何/full12refit/新地点。cache977052160bytes+header，磁盘临时空间预检至少8GiB，固定包上限2GiB。3pixel fits+9role fits共12linear solves，主像素采样996992、pixelmap93468、pixelheldreference31156，3rolesets/38768roletargetrows/58152rolepredictionrows/6context/3FITbaselines/15政策/1pooled+3held。

最小证据：19输入、标签snapshot850行及workbook原SHA/范围证明，完整featurecache或其严格绑定单独文件，3pixelhead/9rolehead/支持与数值、三fold14格预测map、FIT/held排序和容量/预算、模型OOF先冻结、pixelheld参考组件、原行摘要、资源收据/严格清单。所有raw/local大数组不入Git。F00支持→前三/区域像素组件，F01实际OOF/原检测/12地点差，F02最多6实际图/GTpolygon/原修正框/保存学得map，若无追加仍按原E022固定score顺序取6唯一FIT机会并明确未选中，无额外前向；图与热图相同context和显示aspect，声明region envelope/非宽度真值。

本次仅资产只读核验→冻结→6.1 sol-Medium设计审查→通过后实现/纯合成测试→精确版本独立代码/合成图验收和执行准备。0真实训练/特征提取/SSH/源码发送/公开push/producerRun。本轮已用原6快照做审计显示，不打开新源像素。代码范围scripts/pavetrack_pixel_selector/tests同名/E023合同审查/简短S01记录，旧源码/结果不改。未来producer执行需本轮之外具体指令，审查通过不是实际收益或运行。
