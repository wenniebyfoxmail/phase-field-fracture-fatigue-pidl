> 2026-10-18更新：本精确版已按核验的总部原始人方授权完成私有部署、唯一R001及接收核验，无公开push；公开分支并非本次执行依赖。下文为原准备历史，当前见execution_status.md与runs/S01-E024-R001/result.md。

# S01-E024-R001 执行准备（尚未传送、推送或执行）

精确CodeReady源码5a931ac0faef7d48e49d096d81d042440f080880，设计c36add67，指定6.1sol-Medium独立双审通过。229绑定/230源码成员，manifestSHAd21b99072c6e363c46ff20e95e43ba9a2f09fa400715ea349bb072acf1d5feda；configSHA9d4060e6afa1938f2529448382fa15e4adb553c11420cdb5dce16aaef37a0cfe，lockSHA292c05a8441c02c40c592f11d4817b60226bf07f85cef1becb980c2bc6e0171b。执行包逐项字节核验一致，任何修改需新绑定和针对性复审。

本地源码包local_archive/experiments/S01-E024/prepared_R001/S01-E024-R001-v1-5a931ac0-source.tar.gz，631472bytes，SHAa71d964a3700a3d8d31380e9fa48e5d3f069b5a34ee2427cb4b422cbb3444c43。私有输入另置prepared_R001/private_input/train_polygons.json，1546138bytes，SHA98542eb41ec03eebf7a1f73ddf372dc36bb4432aefa259a6e4e3e168e202e3e9；850标注/835既有训练图，不传整工作簿/额外地点。未来固定私有路径C:\Users\xw436\pavetrack_inputs\S01-E024\train_polygons.json，不能进入公开Git。

未来指定公开分支codex/s01-e024-qualified-localizer-20261018，source-only提交基于已公开E023fd85517f62b128ef99cb20df5550076d661d5ffa，仅复制230绑定源码/合同/测试，不带私有标注/审查/结果/私有提交历史。尚未生成或推送公开E024提交。

唯一producergpu-server/D-26-09/ad\xw436，物理GPU1/逻辑0，固定GPUUUID与WDDM白名单/空闲检查，CPU1/3600秒/RSS4GiB/GPUallocated-reserved各4GiB，临时空闲盘>=12GiB，原835图/19成员metadata与私有annotation哈希核验。源/Run/log均新目录；使用scripts/pavetrack_qualified_localizer/producer.ps1参数Source/ReviewedCommit/ManifestSha256，脱离SSH包装PID/日志/资源保存。未知状态先查证，无重试/换机/放宽。

RGBcache1531379712payload+FITtarget63807488+资格map100253696+条件完整map382844928，结果包<=3GiB；CNN3×256steps，不调用E003encoder/classifier。先3模型冻结、3资格决定冻结，再按合格集合精确计数拟合原role；0合格净GTnull，>=1合格算完整12OOF而非仅通过子集。最大19既有输入完整绑定，<=841图像读取、6case全Run共用上限；大数组/标注/图片只存私有结果档案。

主标准仍同1FP/image/IoU=.5的旧命中保留>=95%、净GT>=1且macro>0。资格仅为手段；实际前三/预算/保旧净益是最终问题。未合格fold固定E003/弃权，合格后仍无收益则保留定位组件，另冻结效用支持或预算对齐方案；若资格未过停止固定6049CNN，不继续微调损失/描述/阈值/交集/容量或R002。新地点封存。

用户本轮授权范围为冻结→独立审查→实现测试与本地准备；0真实训练/SSH/传送/push/执行。本文件不宣称真实定位资格、预算可行性或OOF收益已成立。
