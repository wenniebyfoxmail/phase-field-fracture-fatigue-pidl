# E029最终生产实现合同（待精确差异复审／未执行）

2026-10-20，继续同一owner D8；科学方案沿用已审2da7e4df，不重开设计、不改变四臂、11系数、固定(16,16)错位、前三容量、弃权或九地点主读数D。experiment.md / candidate_config.json / review_manifest.json是最初离线候选的不可变历史；本文件与run_config/data_lock/source_manifest补全当时尚缺的实现/运行细节。execution_enabled=false，新的精确人方批准文件才允许一次E029-R001；E028余额不是本Run授权。

## 入口与强制信息边界

复用E028冻结原生tile/Engine、隔离Pillow/版本与GPU UUID准入、retained Process handle＋受管树taskkill、psutil计数监督和固定归档思路。复用E012/Cursor原行前缀/分地点读取、E017监督校验、E018角色/选择与B1冻结政策、E022原11系数数学、同一检测compare。没有另造通用运行平台；E029 controller只串接十个顺序任务进程。

`bank → spatial → FIT0/1/2 → held0/1/2 → evaluate → render → 固定成功/停止包`。模型/GPU构造只在spatial实际执行函数内；Mac import/tests无Torch。每角色独立进程和精确文件能力：

- bank仅从E017 ZIP读三固定成员；qualification只解码原43347行前缀，忽略GT/oracle尾。候选/score来源及全局index/parent/image/location/context/源图SHA强绑定。B1仅解码原保存模型的数值head与gate，跳过FIT表/GT字段，并锁定原OOF。
- spatial不持有GT/标签ZIP/metadata访问能力。R002338图12238行native-max按旧全局index与原context/原图SHA复用；其余497图/18918行只沿原1920×1080图像运行19880个512tile，0 cached128前向。全31156×32×32 float32场（127614976 payload bytes）、两臂两列、六个GT-free固定案例先冻结，再允许FIT。源权重和状态digest必须仍与R002一致。
- 每FIT worker仅允许本折ZIP三成员与本FIT8目标的Cursor解码；监督错fold/row/cache被旧校验拒绝。分别拟合S/M同三head、按原FIT gate规则校准；全三折六模型合格后才开始任何held推理。导出只含数值head、gate、fold/arm/held/source-digest，不带FIT政策、标签或目标。
- held文件能力拒绝metadata、E017ZIP、FIT表、其它折inference文件；不共享FIT Python对象。推理只能使用GT-free bank/context/六列及本折已冻数值模型。B1重放的候选/特征/选择与冻结E018一致，连续预测数值容差1e-12（不改变政策或GT读数）。这是既有浮点实现重放容差，不是扫描。
- bank/spatial/models/OOF冻结记录由controller内存中的可信对象固定，再检查落盘记录和原文件；不能修改文件并自重哈希来救判定。request携带这些冻结文件的可信摘要，跨折/arm/source key强制匹配。全部held和B1重放冻结后独立evaluate角色才解码12个旧地点的评分GT，按各自operating point比较pooled9/pooled12、资格三地点与三个原held组，任何评价结果不回流。

三FIT8并集本来覆盖全12；不声称所有held身份GT在所有模型冻结前全局未解码。隔离以本fold/model角色为单位。九主地点仍是反复消耗的开发地点，资格三地点包括24仍在原四地点组capacity竞争；无fresh/full-pipeline OOF或地理泛化主张。

## 次数、预算与首停

run_config固定：source reads/decodes497、native forward19880、reuse12238/new18918、descriptor31156、case捕获6；S/M六模型/18head/18solve、训练77536行、预测116304行、6 context、3 FIT baseline、30校准政策；B1另有19384行冻结模型数值重放，不拟合；6评价scope基线和24同scope臂比较。B1重放计数是原设计未列清的复现成本，不是新政策搜索。0空间训练/梯度、0cached前向、0jackknife/full12 refit/交集或权重扫描。

总外部墙时3600秒：预检＋输入校验＋完整生产最多3480秒，余120秒预留固定成功/停止包，打包不能延长总3600。CPU1，一张GPU0指定UUID；聚合RSS与CUDA allocated/reserved各4GiB，output/archive各2GiB，起始空闲>=16GiB。单图8.3MB native场流式释放，不归档835整图场；只存统一投影、单图场hash、冻结链/数值模型/预测/评价及六个原解码时捕获RGB，不追加源图读取。六案例按各原组非资格新图lexicographic首/末图、各图首context，在GT之前固定，不能改成成功图。

父子Guard和外部PowerShell墙时/RSS监管保持有界。首触发先持久化原因，再按Popen所有权、PID/出生时间及命令身份清理本任务树；不按进程名杀其它用户。无法确认清理则明确cleanup_uncertain，不自动retry/fallback/增预算。软件/数据/地图/身份或资源不符同样首停。实际Windows PowerShell、DLL/驱动、共享GPU/磁盘状态不能由Mac人工测试证明，全部置于同一正式执行准入/首停链，不另偷跑native probe。

## 最终证据与接收

每phase严格输出清单、资源/身份收据；完整成功必须所有计数准确、所有冻结仍有效、E003原行摘要未变且原pooled12基线684可复现。结果主对比与9/12零失旧标准原样保留；主/分项结果都由保存比较重建，停止或不全写null而非净0。

原F00=四臂主九U/D与全12旧新失；F01=原FIT3/5/6支持到选定capacity；F02=六个预定实际源图/原修框/GT框/保存空间场，明确拉伸与0..1色阶、是否OOF入选；框GT不是像素真值，案例不覆盖或推翻聚合结果。README和所有raw预测/模型/评价/来源SHA一并归档。

pack.py只读本任务run/wrapper与source manifest，成功/停止同一路径，安全普通tar成员与每文件hash，raw及压缩包均2GiB内；部分包不覆盖、不重试。receive.py不联网、不调用模型/评分，只接已批准取回的固定对象，先SHA/bytes和完整gzip CRC，再安全抽取/双清单绑定；接收验证不代替后续独立数字复算、原图验收和科学解释。

精确源码包/本地source-only commit、指定分支、私有复用清单11项、未来一次命令、固定包路径与Mac验收命令在execution_approval.md（生成后）中。该审批版仅提出完整执行决定；当前没有SSH、部署、占卡、推送、真实fit/forward/OOF或GT/留出访问。

## 生产差异修复v2（科学标准不变）

v1独立审查的五项执行阻断已逐项修订：每角色只增加已绑定121个Pillow文件的精确读能力；首个Python之前PowerShell核验252源码绑定、121运行库库存/哈希和六字段严格授权；Guard用RLock、单次内存快照并容忍自有原子文件rename消失；原因持久化失败仍进入finally清理；CIM/taskkill/日志等待有界且每项失败不跳过后续清理。原触发原因保留，清理不明另记cleanup_uncertain。每FIT/held还从GT-free bank推导本角色准确次数，角色结束和每阶段总计均立即检查，不能到全流程结束才发现超量。

本地49项人工数组/mock/权限子进程测试不拟合、不导入Torch、不解码真实GT/地图/图像、不计算真实政策读数。人工图仅验证显示，零值增加标注，独立红色SYNTHETIC标记不作为研究结果。没有本机PowerShell，Windows原生解析/运行仍在未来同一受批执行链，未声称Mac测试已经验证。
