# S01-E022-R001：裂缝类别空间归因未带来前三入选或OOF净收益

2026-10-18。唯一R001执行完成，固定结果已取回Mac并通过接收核验。**冻结主标准为negative：旧684/684保留，新/失/净均0、地点macro变化0。** 这是12个已复用训练地点上的条件selector OOF，不是完整上游独立或新地点泛化结果。

|决定量|结果|
|---|---|
|E003旧命中保留|684/684，100%|
|实际OOF新增/丢失/净GT|0/0/0|
|地点macro召回变化|0|
|主模型及最终追加|三个均abstain；追加0|
|自身FIT已知有益GT留池|3/5/6全部保留|
|最大固定政策/所选政策有益GT入前三|0/0/0|
|14条重叠FIT正记录组内考虑位次|31–1147，均group_cap|

## 实际选择与组件进展

12个active FIT政策均追加6框、新增GT均0；FIT0/1/2净GT分别−1/0/−3，追加预算FP均6。没有符合100%旧保留、正净增及macro提升的active政策，因此三主模型均安全弃权。原43347行/框/概率/score/顺序不变；全部12地点pooled-prefix TP差为0，FP分解仍partial538/duplicate143/no_small_overlap154。

相对E021同fold/parent保存r>0轨迹，14条重叠FIT正记录11条前移、3条后移。最前从E021第40到本次第31；例如fold2/36698从69到31，fold0/36698从83到39。fold0/60376从1128后移到1147。该join只描述保存考虑顺序，14条不是独立GT，不能推出整体排序/泛化改善，更不能冒充前三或检测收益。完整表见E021_E022_saved_rank_comparison.csv及positive_rank_summary.csv。

31156固定类别归因全部完成且有限，30524非零、632零质量、0空context。七个唯一已知有益候选均有非零图，C_sem均正，但parent46437的D_sem=−0.021784（其余六个唯一支持D_sem正）。这些值与非零热图只证明新增类别条件空间信息及提取链路已工作，尚未证明能区分所有负竞争者、定位质量可靠或正例支持充分。39角色头满足残差和同权重常数目标检查；10删除诊断沿主弃权gate保持空选择，不是独立政策成功。

E009/E011/E019/E020/E021旧结果保留。本次新增的是冻结E003池化前7×7空间图与裂缝−背景margin输入导数，未再压缩旧缓存或微调灰度C/D。它仍可能表达接缝/背景，7×7粗空间与共享context分布变化存在局限，不能称分割teacher或像素裂缝真值。已测组件前移未跨过原容量瓶颈，实际问题尚未解决。

## 预算、身份与图表

精确执行源码f8990c148b14298db16490cd6f4460794271a8dc，manifest c0ab6c70a517c3b56f91fee874e1b177879c1a8d45a67ab29ebf9438f82ebc8b；source-only公开d893c5fb7a5d8f9a058d7ea48d919fda163f4949已在指定分支读回。GPU1/CPU1运行402.047秒，聚合RSS2740174848bytes（2.55GiB），GPU allocated48395264/reserved75497472bytes，均在3600秒/各4GiB范围。2368<=2505批，31156backbone/head forward及head输入导数，0backbone backward/参数gradient/update；835源图+6案例解码，source reads/pixel_reads841，39角色solve及其余冻结计数完整。stderr空，无重试/放宽/交集扫描/新地点访问。

固定ZIP f10e4753ba5b946cc80ac64e2a2c0d843cc5ccac4a872706915f3664ac63d32d，66840661bytes/55成员。SHA/CRC、50输出、19输入、835图身份进度、31156保存H及coverage代数、模型/OOF先冻结和43347原行已核验；仅用保存数据核验，不新增特征/前向/拟合/政策/指标。原包保留在local_archive/experiments/S01-E022/runs/S01-E022-R001/。

F00为自身FIT支持/前三与归因退化，F01为实际E003/OOF同预算旧新失净和12地点变化。F02六案例均为冻结规则选出的**未选中FIT机会，无OOF新增**，不是成功案例。原图的右侧imshow重置aspect为equal，使细长context热图成为窄条；几何/归因数据未变。Mac另存derived_display_20261018/F02_cases_readable.png，同6已留存快照、原cases顺序/框/GT/context/保存7×7图，最后统一auto aspect并明确显示拉伸/每案例色阶。原ZIP、源码和原图不改；新增仅6次本地保存快照展示解码，0源图访问或科学计算。renderer及display_receipt.json绑定所有输入/输出。归因非GT、context外GT裁切等限制在README中保留。

## 冻结后的处理

三模型全弃权、前三0，按冻结停止固定最后层margin-Grad-CAM双描述家族；不进行R002，不换层/target/梯度法/平滑/分辨率/归一化/权重/L2/gate/交集/容量救结果。保留E003。下一条有意义的路线须先有可验证的像素定位监督/合格独立空间teacher或新增可信正例支持，并另冻范围与预算；本轮不设计或执行下一Experiment。此次负结果不证明所有语义信息无效。新确认/validation/reserve和旧资格排除地点继续封存。

独立证据与修正版展示验收见docs/reviews/S01-E022_R001_evidence_review_20261018.md；最终收据另记录证据就绪状态，科学negative保持不变。
