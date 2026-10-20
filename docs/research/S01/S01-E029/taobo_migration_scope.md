# S01-E029：GPU选择复查与Taobo迁移边界（未执行）

2026-10-20。承接用户恢复授权：重新检查GPU0及其他卡，不只等待GPU0；一次R001总3600秒，含结果取回验收；E003、容量/弃权、固定交集和封存不变。此记录不是Linux Code Ready，也不是实际模型/OOF结果。原v3源码和原准入记录均保持。

## 已核实的选择

14:15:19Z，D-26-09 GPU0利用率83%，GPU1为32%，分别有真实compute PID16340/39912；四个既有Python训练进程、CPU79%，原CPU<50/无共享Python/选中GPU零利用率规则不满足。检查覆盖该机全部两卡，没有只等GPU0。

Taobo GPUServer8全部八卡均已查。GPU5 UUID GPU-5622bd47-1050-3003-246d-3cabe2b4791b，0%/4MiB已用/24077MiB空闲，无compute PID，是唯一无resident compute的候选。GPU0/1/2/3/4/7虽有0%快照，但均有resident compute；GPU6为55%。不能把0%单次快照当作其它任务已释放。大盘/mnt/data2可用638906994688bytes，/mnt/data3可用1008188522496bytes。只读核查，没有预占GPU。

Taobo现有/usr/bin/python3为3.10.12、Torch2.7.0、vision0.22.0、numpy1.24.4、psutil7.0.0、matplotlib3.10.3、Pillow11.1.0；已审v3锁定Windows、Python3.12.14、Torch2.11.0+cu128、vision0.26.0+cu128、numpy2.5.2、psutil7.2.2、matplotlib3.11.2、Pillow12.3.0。当前未满足原runtime，不能简单改CUDA_VISIBLE_DEVICES=5或借用旧环境执行。

## 最小迁移范围（独立静态核查结论，不是实现通过）

1. 在/mnt/data2/drtao/wennie/任务专属目录提供隔离Linux运行库，锁解释器/依赖的Linux构建版本、文件hash/origin及兼容驱动。不得用Windows wheel，不改共享环境，不默许Torch2.7替代2.11；不放宽旧B1数值重放1e-12。
2. 原11私有输入逐字节/SHA不变；ZIP、scope里Windows路径保留为原逻辑身份，验证用PureWindowsPath。另冻结497图image_id→Linux物理路径/SHA，仅open与caps使用resolver；不重写旧输入、source_image_root或R002 scope来救join。
3. 迁移对象仅精确源码、11个原输入、497张缺投影原图和独立runtime/字体清单；338张图只复用12238投影，不额外迁移/重解码。私有输入不进入公开分支，跨主机传送在最终精确版本/对象清单批准之后；当前没有传送。
4. Linux worker的psutil需只观察自身；controller在精确权限外聚合本任务PID/birth。只给必要自身/proc元数据及固定字体/runtime读能力，不放开整个/proc、/mnt或数据根。字体发现不得在cap后偷偷spawn。
5. 用本任务专属session/process group与PID/birth/UID/cwd/cmdline代替taskkill，只清理本任务；保留写盘失败仍清理、有限等待、绝对墙时内清理预留、停止包/CRC/双清单和不重试。
6. 将gpu-server绑定迁至GPUServer8/GPU5精确UUID（运行前重新核验）；他卡任务不等于选中卡任务。Windows全机无Python规则不能自动放宽成Linux共用规则，需作为显式平台准入差异审查，保留CPU/RAM和选中GPU独占/内存/功耗约束。
7. 科学接缝全部原样：四臂/同11系数/固定错位/阈值/18solve/497图19880forward、FIT逐折隔离、六模型及全部held冻结后评分、B1可信重放、前三容量/弃权、主九D与9/12零失旧保护。新确认地点与原封存仍不访问。不得插入真实微测、减少样本或追加forward来救预算。

没有发现静态必然超过4GiB或3600秒的矛盾；RTX4090实际吞吐/峰值尚未证明，不能写成已可行。全部实际预检和执行仍须在同一次首停链，保留实际停止而非扩预算。Linux启动代码、隔离runtime来源锁、精确迁移清单和权限/进程测试尚未完成，因此当前不能提交Linux执行批准或声称Linux Code Ready。

下一可执行的开发工作是按上述范围完成Linux适配、测试及精确代码复审，再形成一次具体迁移/运行决定；不再以等GPU0作为唯一出路。原Windows版本仍Code Ready，但本次没有满足其冻结准入的机器。源码/私有传送、公开推送、授权文件/producer启动全0，预算用时0秒，前三/保留率/净GT为null。

证据：local_archive/experiments/S01-E029/execution_R001/resume_admission_01/里的全部GPU快照、runtime metadata及admission_receipt.json。独立静态可迁移性核查使用原6.1 sol / High审查者；其结论仅必要实现清单，不作Code Ready PASS。
