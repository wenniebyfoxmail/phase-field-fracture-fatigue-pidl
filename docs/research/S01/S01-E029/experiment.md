# S01-E029 v1候选：冻结空间组件能否转成容量内保旧增益

2026-10-20；继续S01原目标，D8离线设计。**当前只授权本地方案/源码接缝/人工数组测试和必要差异复审；没有真实数据拟合、推理、OOF、SSH、传送、推送或执行权限。** 本文是可审阅候选，不是完整producer Code Ready，也不继承E028运行预算。E028原证据和冻结标准不改。

## 原目标与实测瓶颈

保留E003已有检测，让有益修正进入原前三，再得到实际OOF净收益。复用E012候选及补评分、E017分解标签/无GT上下文、E018低容量角色学习/选择、E022六列11系数和保旧评价，以及E028已验收空间组件；不新造候选、框、GT或压缩器。

D1局部搜索：E018/E019/E020/E021/E022的result/positive_rank_summary、role_probe/learning.py、semantic_selector/{run,learning}.py、protected_selector/{core,run}.py、spatial_selector/spatial.py和target_spatial/{geometry,run}.py。没有另一个E029 worktree/方案owner。选择continue：复用现有选择/评价，仅替换经资格检验的新空间信息，作对齐对照，而非再调整旧描述的层/符号/权重。

- 原43347检测行、31156既有修正、19384 base-eligible不变；有益正例3/5/6在正交集后都留池。
- E018–E022各FIT四active gate均无新增实际GT，均被安全弃权；不是候选不存在或弃权程序故障。
- E019正记录组内考虑位34–829，E020最早20，E021最早40，E022最早31；前三容量已占满。14条重叠FIT记录不是14独立GT。原七个唯一有益候选跨五个既有地点，其中2027已用于E028资格，其余位于514/728/1577/4494；不是新增正例。
- 冻结E028 native/max/>=.5/any在1638和2027相对基线达标，24负向；只证明两个开发地点的部分包络空间对应，不证明候选内排序、单框效用或新地点泛化。

关键机制：原Q*N*A排序必须把准确且真正新增的修正排到源四地点组前三。新定位场可能把框内有效空间支持和原/修框差异送入Q/N；也可能只是宽响应/接缝、稀少正例不支持学习，或A/score-pressure继续压住有益修正。固定空间对齐反事实可区分“空间对应真有用”与“任意附加列/模型容量/阈值巧合”。所有正/负/持平都给出集成决策，不靠更多诊断延后实际效用比较。

## 一次成组比较，主候选不得择优替换

|臂|输入与模型|用途|
|---|---|---|
|B0|原E003全部行、分数、顺序|真实检测基线|
|B1|E018已冻结四列7系数Q/N/A及fold gate；复用原模型/预测，不重拟合|已有几何低容量强对照；集成重放须复现原结果|
|S（唯一主候选）|四旧标量＋冻结E028空间场的两列，E022原11系数Q/N/A|检验新增空间信息能否进入容量并形成净收益|
|M（固定反事实）|与S相同空间场/前景量，32格循环位移(16,16)后计算同两列；同11系数/监督/正则/分组/gate|区分真正对齐信息与质量总量/附加容量；不能事后改位移|

E019–E022已有OOF均全弃权/旧684/684/净0，作为历史对照保留，不能把旧失败改成新验证。B1/S/M同批接入同一候选、原检测、去重/正面积交集/1框每图、3框每原四地点组、score和评价函数。M不是可择优部署臂。禁止新增loss/L2/列数/符号/随机种子/阈值/地点/容量/交集搜索。

### 空间信息定义（无GT运行接口）

完全绑定E028-R002源码a5a8f465、manifest eba54f07…cefff3、原包SHA7bce8845…f2c4ef、CT260权重SHA94523937…ad63及状态digest569c30d9…2830。原始RGB→官方BGR float32/255，固定DeepCrack outputs[0].sigmoid，eval/no_grad、f32、无增广/适配。原生512输入、256中心/步长、128 halo、reflect、batch1，原坐标拼接；不读包络/框GT，不重新训练定位器。

每个候选沿既有original∪corrected外扩25%的整数裁切context（复用E025 pixel_contexts，不重新定义），按E028 geometry.reduce原生连续32×32 bin最大值，H=1[Pmax>=.5]。盒b对每格的覆盖分数为c_b；z(b)=sum(H*c_b)/sum(H)−mean(c_b)，空H时z=0。两列固定为[z(corrected),(z(corrected)−z(original))/2]，不重缩放或按GT选方向。M先循环平移Pmax再作相同计算，保持质量与前景格数。部分包络any仅是上游资格参考，不作为运行特征或这里的新监督。

四旧列/头目标/权重完全复用：corrected_probability、old/new IoU、1/(1+nonparent_overlap)、1/(1+score_pressure)；Q列0/1/4/5拟合corrected_max_IoU，N列2/4/5拟合valid_localisation AND novel_reference，A列3拟合cached admitted且lost=FP=0。ridge=.01，不拟合表示、不估概率校准。S与M各三fold模型/九小矩阵求解，共18solve；B1不拟合。每FIT权重按原target strata→site→image→row等权，正例支持仍3/5/6，不以重叠行扩充独立样本数。不追加十次删除拟合，避免未改变决定的诊断链。

同E018/E022，gate仅[0,.0625,.125,.25,abstain]，strict rank_score>gate且x>=0。在各自FIT8上按原choose：100%旧保留、net>=1且macro>0才active，再按net、少FP/追加、较大gate排序；不合格则abstain。FIT是拟合/校准开发集，非独立验证。推理只接收数值列和GT-free候选/context，不能接收targets、annotations、U、GT identity。

## GT角色与地理边界

固定12旧地点及三held四地点组原样保留：
- held0=[24,514,1577,3662]，FIT为其它8；
- held1=[95,728,1638,4494]，FIT为其它8；
- held2=[151,1400,2027,5508]，FIT为其它8。

E017每FIT自己的监督和cached U仅供该FIT拟合、gate校准/正支持描述；不可合并别fold的U用于本fold训练。**访问隔离按fold/model角色定义，不是“全局从未读取held身份GT”**：三套FIT8的并集覆盖全12地点，同一地点合法地在另fold充当FIT；不得声称所有六模型冻结前其GT从未物理解码。

未来loader/runner必须落实三角色：①每fold FIT worker只能拿本FIT8的监督/框GT用于该模型拟合与gate校准，拒绝本fold held目标或其它fold标签payload；②每fold held推理worker只接该已冻结模型/gate和该held组GT-free数值特征、候选/context对象，不接targets/annotations/U/GT identity，不共享其它fold FIT目标对象；③S/M全部六模型、gate、完整held预测/追加及B1复现统一冻结后，独立evaluation角色才按九/十二地点scope读取评分所需GT，不能反馈主模型/gate/臂/特征。先保存空间场投影/descriptor及hash，再加载任何FIT监督；空间场不能因GT变化。这是逐fold信息集与对象/进程访问合同，完整实现需针对越界payload/共享对象和冻结后篡改作人工拒绝测试，当前纯adapter未声称实现GT loader隔离。

E028资格使用过24/1638/2027的包络GT。因此预先将**另外九地点**[95,151,514,728,1400,1577,3662,4494,5508]设为本次主效用读数范围；这是新E029方案的前瞻边界，不改写E028或删掉24。全部12地点仍生成原政策OOF选择、原group竞争及保旧检查；资格三地点含24单独描述，并给完整12报告，不扫描或替换地点。

主九地点在各held组各占3个，但使用完整四地点原容量竞争，不为九地点补空位/重排。九地点评价时只把已冻结选择投影到该scope；在其自己的pooled9 1FP/image读数计算E003和各臂，避免资格GT进入其预算阈值。另作完整12 pooled12保护和三个原held组sidecar，不能混用operating point的old hit身份。保留逐scope的image数、FP预算/实际FP、阈值/并列规则、old/new/lost identities。

九地点是**相对E028资格未使用的GT**，不是未见过的数据：此前E003/refiner/标签与E019–E022结果已反复复用12地点，不能声称全链OOF、确认性显著性或新地点泛化。资格三个地点也可能进入另外fold的FIT8监督，但从不进入其自己的held模型；这些角色明确记录。353/1459/2028/5982及既有validation/reserve/new-confirmation边界均继续封存；不打开新GT或polygon。

## 单一主要效用读数与结果决定

U_a=主九地点同1FP/image、IoU=.5预算下，相对同scope E003的实际net_GT（new−lost）。唯一主对比 **D=U_S−max(0,U_B1,U_M)**，整GT为单位。原E003原行/概率/score/顺序逐字节不变且S在pooled9与pooled12都lost_old=0，是解释“保旧净增”的必要保护条件；不是靠降原阈值/放宽预算换收益。相较既有>=95%保留标准，这个新候选前瞻使用100%作为明确保旧保护；允许单个净GT改进，不设任意高提升幅度或全fold都active。macro/per-site仅描述，不另设主门槛。B1和M若更好必须报告，不能只和全弃权E003比。

- 有效证据＋S保旧且D>=1：支持此固定对齐信息在九旧开发地点的条件selector OOF保旧增益；保留空间组件/候选集成版本，后续仍需单独决定确认性验证，不能直接部署。
- S保旧且U_S>0但D<=0：有实际增益组件，但没有对齐增益优于强对照的证据；优先保留更简单/更有效对照，不能将S判成独有空间机制成功。
- S保旧且U_S=0，或仅资格三地点有益：主声明negative；若确有前三前移/入选则保留组件进展，停止此固定11系数配方，不扫参数重试。若三个模型全abstain，实际选择策略净0，不能声称S主动保旧成功。
- U_S<0或丢旧：拒绝集成，保留E003；把空间组件通过和选择政策失败分开。
- 身份/数值/运行顺序/预算无效或结果不全：inconclusive/inadmissible，不填0，不重跑。

辅助链只读冻结预测后输出：每FIT有益GT留池→S/M选定与固定active政策的入前三数、实际追加→预算接纳→new/lost/FP/净；逐候选保存group consideration rank和reject原因。机会计数/GT知情上限不能升级成学习效果。所有变化均跟同scope/同operating point比较；不给GT知情oracle单独新预算或新政策搜索。

## 可复用地图、尚缺的信息与未来预算（未获执行许可）

只读现有非GT spatial_extraction_receipt验证：835张均1920×1080；R002覆盖338张/12238context，剩497张/18918context。**不能把R002资格成功误当835张map齐全。** 未来若批准，直接复用R002已冻结native-max投影12238行（按原全局index/parent/image/context和源图SHA join），新497图需相同定位器19880个512tile forward；不对338图重推、不跑cached128、不补新GT。对新图只保留31,156×32×32 float32统一投影（127,614,976 payload bytes）和map哈希/各tile身份，不把全835 native场重复归档；每次最多一个8.3MB原生场，生成投影后释放。M完全从相同投影派生，无额外forward。即使整张图显存允许也不改变E028 tile定义。

拟新一次producer运行3600秒，CPU1/一张已指定且重新核验的GPU0，RSS/CUDA allocated/reserved各4GiB，输出/归档各2GiB，临时空闲>=16GiB，checkpoint1，source decode497、native forward19880、cached forward0、定位fit/update0、selector小矩阵solve18、full12refit0、jackknife0。没有继承或花费E028剩余时间：**这是新预算提案，未批准**。GPU/Windows runtime/隔离Pillow沿E028最终版规则，须完整preflight，不默许共享后台或回退主机。

未来拟合量：S/M共6 model sets、18heads，训练行计77536（按19384 eligible各覆盖两个FIT、两臂；冻结输入校验不符即停），预测行共116304（每臂FIT38768＋held19384），6 GT-free context builds跨臂复用，3 FIT baselines共享、30政策比较。B1复用冻结三模型/gate/预测；其精确收据与未来完整runner/datalock/source-only包须在实施阶段补齐，不伪称当前已具备可执行正式包。

新图forward耗时根据已完成13520native tile的R002估计可在3600秒内尝试，但不是吞吐保证。准入/依赖/hash/非有限值/计数超限/任一资源首触发即保存停止现场，不延时、不换卡/机、不重试、不增RunID。各源图/投影/源档只读；所有最终输出先freeze再评分。预算/原始数据/地图缺失不靠放宽或训练补齐。

## 本地最小实现与审查边界

当前只实现adapter.py：E02832格→两个固定空间列、半格位移、六列拼接及固定地理角色；不导入Torch，不加载私有GT，不调用fit/infer/select，不含producer入口。14项人工数组测试含.5边界、空/满/错位/亚像素coverage/身份分组；不是科学效果。现有learning/select/compare被来源锁定但未真正连接。完整runner、GT隔离loader、模型/输入收据、输出可重建性、producer准入和图表尚待实现及精确复审；本候选**不能标Code Ready或直接运行**。

最小交付需让审查者判断本比较是否值得完整实现，并准确列出后续生产信息缺口。未来正式图表必须给同一组冻结scope的D/U/旧新失/前三链与固定原分数案例；选择规则为实际追加，否则原FIT有益机会，不能事后挑成功图。当前没有新科学图或OOF结果。
