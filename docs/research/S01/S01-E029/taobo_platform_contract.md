# E029 Taobo GPU5 Linux 最小适配合同（源码审查对象，未执行）

2026-10-20，用户明确要求Linux最小适配/测试、6.1 sol-High独立代码复审后准备一次迁移/执行审批版，并取消3600秒预算限制。本修订只改变producer/runtime/路径/准入/清理和墙时；原experiment.md、data_lock.json、E003及定位/选择数学不改。旧Windows v3及其准入负记录仍留在原commit/档案，不能用本修订倒签。

## 科学接缝不变

`taobo_run_config.json`的locations/held/封存、四臂、两个固定空间列、11系数/三head、固定.5/半格错位、原GT角色、ridge/gates/权重、全次数、容量1/image与3/原组、弃权、严格正面积交集、九主地点D与9/12零失旧保护，逐字段与原配置一致；B1旧模型/政策/1e-12重放容差不改。所有地点仍是旧开发地点，不声称全pipeline独立OOF/新地点泛化。主目标仍是有益修正入前三并形成保旧实际净收益。

实际source/spatial/fit/held/evaluate代码复用原十phase controller；profile=taobo显式选择新config/manifest/环境，非自动fallback。原11输入SHA、R002338图12238投影和497图19880forward、六模型18solve等全部保留。bank以PureWindowsPath验证旧路径；所有原记录保持旧字节和逻辑路径，只有读取/权限映射到Linux `private/images/<image_id>`。角色读能力及冻结屏障不变。取消墙时通过budget.total_task_wall_seconds/wall_seconds=null与精确外部approval.wall_seconds=null表达，不能误用3600或无限循环新样本；工作量仍有精确次数上限。

## 运行环境与私有迁移

指定GPUServer8/drtao/GPU5 UUID GPU-5622bd47-1050-3003-246d-3cabe2b4791b，逻辑cuda:0；新任务根 `/mnt/data2/drtao/wennie/S01-E029-R001`，所有source/private/runtime/tmp/cache/run/logs/archive均在该大盘任务根。原3600硬墙时和末尾预留逻辑取消；记录所有阶段elapsed，无替代总时限。CPU单线程、聚合RSS/CUDA allocated/reserved各4GiB，研究输出/结果包各2GiB、私有包4GiB、runtime下载8GiB，free disk准入提高为32GiB；不借取消墙时增加模型/数据/阈值搜索或自动重试。

Taobo准入与Windows全机无Python规则的显式平台差异：允许别卡继续计算，只要求选中GPU5没有compute进程、采样利用率0%、空闲>=8192MiB；主机CPU<50%、可用RAM>=8GiB、磁盘>=32GiB。不触碰他卡任务。运行前/空间前向前重新核验；空闲快照不是预留承诺。不会默认转其它卡或主机。

`taobo_runtime_spec.json`冻结CPython3.12.14官方source SHA和42个已解析Linux wheel的URL/SHA（包括Linux条件依赖和CUDA12.8，不使用Mac marker的残缺解析）。版本沿用Torch2.11+cu128/vision.26/numpy2.5.2/Pillow12.3等。仅在受批生命周期内，从冻结artifact构建专属Python（make -j1）并离线无依赖解析安装这42轮；不改系统/共享venv、不sudo、不在Mac安装/导入Torch。内部file symlink实体化，拒绝外部/目录链接；构建输出全文件SHA、source recipe SHA和artifact身份记录到runtime_lock，实际执行前严格验证库存/版本/origin。编译器/驱动及native可用性保留为同一执行链准入，未声称本机已验证。安装/准入不额外跑真实模型、图像或GT微测。

迁移清单由已冻结E017 candidate_identity成员（GT-free）推导，仅11原输入+497张缺投影图，共508payload文件和1个private_catalogue成员。目录/图像ID、原Windows来源、每项SHA均在私有catalogue；公开仅其整体SHA `5dc25418f62a6493ad0412d24d6d253b6f23e8b42471308d701bb0f7783adb66`、数量及源成员SHA，private_catalogue及所有内容不进公开分支。metadata/images个别bytes未知不填造，固定SHA和单文件256MiB上限仍强制。源服务器导出只校验/复制bytes，不解码metadata GT、图像或模型；取回Mac中转后Taobo按实际export receipt SHA/bytes、完整gzip CRC、目录/每项SHA安全接收。首次打包/传输未知或失败只保留现场，不盲目覆盖重发。

## Linux权限、资源与首停

worker只量自身RSS，不在audit hook后扫描全/proc；仅允许自身 `/proc/<pid>/statm`，其controller在cap外聚合受管树。worker发现controller父PID消失即首停自退。runtime/字体仅已库存的精确文件；字体发现在安装cap之前完成，渲染只用runtime自带DejaVu，held仍不能打开metadata/ZIP/FIT政策或跨fold模型。

producer_taobo.sh清除继承环境并以固定绝对工具路径重新进入干净bash，在首个Python前先核精确manifest SHA，再核全部源码绑定。最终启动命令还须从env -i进入bash，避免首个shell载入BASH_ENV/LD_PRELOAD。编译/安装/执行使用显式环境白名单及空pip/config-site配置，不继承用户构建/加载设置。wrapper保留构建后runtime_lock可信SHA，系统stdlib在启动runtime Python之前核库存和全部字节；同一摘要传到controller/worker并在每阶段复核，拒绝文件与lock一起自重签。独立watcher在wrapper死亡时终止自己的整个阶段进程组，包括编译器和worker；日志写入失败仍清理。每阶段资源收据记录elapsed_seconds。外层仅系统Python stdlib及任务源码内的/proc读取器做生命周期监督；外部六字段精确approval、全新launch_claim且execution_enabled=false缺一不可。bootstrap必须经同一已批wrapper的独立父存活监督进程启动，核验wrapper和watcher出生身份。每个阶段独占新session，controller及其worker留在该session、受管PID/出生时间/UID/cmd/cwd核验，不按UID或进程名杀人；其他GPU任务不是本任务许可。日志/原因写盘失败仍finally清理；所有清理/日志等待有限，资源失败明确cleanup_uncertain，保留首因，不重试/换机。成功与停止同路径固定tar，partial不覆盖、不把null补净0。打包/接收复用原pack/receive；null deadline仅Linux profile显式使用，旧finite deadline测试仍通过。

## 本地测试与结论边界

74项人工数组/mock/字节归档/权限与所有权测试通过，包含原49项；未调用真实或synthetic fit，未加载/前向真实模型、未读真实GT或源RGB/地图；Linux runtime仅完成artifact解析与source hash，不在Mac构建/安装。原已有显示QA仍有效，renderer科学内容未修改；字体接缝与原图layout分开验证。Code Ready只由精确独立代码复审签出；不能用静态通过证明native/Linux吞吐、内存或净收益。

最终审批版必须展示精确source-only commit/包、指定分支、源Windows账号与Taobo账号、508payload与catalogue、runtime recipe、唯一R001命令和结果取回。当前仅本地准备，无SSH部署、私有输入导出/迁移、推送、占卡或producer运行。
