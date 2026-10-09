# HQ最小公开数据诊断程序 r1

2026-10-09。已实现并完成有限独立代码审查：PASS_CODE_READY / NOT_RUN_READY。未启动训练、未访问Taobo、未改变原始数据或研究登记。代码位于本任务独立研究目录，尚未作为跨机生产版本同步共享仓库。

## 已实现

| 文件 | 职责 |
|---|---|
| core.py | 合同U-Net、确定性crop、masked BCE/Dice、验证选checkpoint、预算中断、原图评价及结果图 |
| tiling.py | 448窗口/224步长、边界覆盖、重叠概率平均 |
| data_lock.py | canonical角色与文件身份、官方来源对应及逐文件SHA锁 |
| runner.py | 生产入口、授权/主机/环境/代码与数据锁检查、fresh run收据 |
| test_runner.py | CPU合成forward和静态检查；无反向传播/优化器更新 |

数据划分沿用合同r1：METU316训练/62验证/80内部测试；BuildCrack358仅最终来源外诊断。模型选择只能读取验证集；最终推理不创建优化器。主要比较为355张BuildCrack非空发布参考的ΔAURC，各来源单独报告，3空参考单列。标签一致性不能升级为物理真值或现场安全。

## 验收与身份

9项测试通过：模型结构/前向尺寸、padding不计loss、确定性crop与训练角色隔离、拼接、Dice/熵/AURC、canonical身份和泄漏拒绝、checkpoint等分保留最早、最终阶段无优化器、Mac/CPU与预算门。用完整816行源文件重新核对哈希；锁创建先核对BuildCrack官方ZIP及成员CRC、METU916文件恢复CRC。详见LOCAL_VALIDATION_RECEIPT.json、INDEPENDENT_REVIEW.md。

唯一当前数据锁为data_lock_verified_r1.json。data_lock_r1.json是审查前初稿，已废弃，不能使用。当前代码会拒绝缺少来源记录的旧锁。代码snapshot由runner.snapshot()对本目录所有.py名称/内容计算；修改任何.py都会失效，必须重新审查。合同与角色manifest也固定hash，不可静默改分组。

## 仍未执行的内容

未运行任何训练循环、反向传播、参数更新、真实图像模型推理或GPU集成测试。预算/中断仅作静态审查，CUDA数值与生产性能未验证。计划训练+验证6 GPU小时，最终诊断另1小时，总计至多7小时，为合同上限而非已获准资源。

生产入口默认要求Linux CUDA、显式CUDA_VISIBLE_DEVICES和CUBLAS_WORKSPACE_CONFIG=:4096:8、精确hostname/依赖环境/代码snapshot/数据锁匹配，fresh输出限定/mnt/data2/drtao/wennie。没有提供已批准authorization文件，也没有执行命令。检查记录本身不能替代用户授权。

下一步是受控打包/生产前只读核验：正式实验归属与证据域、共享代码版本、Taobo资源可用性、输入部署与环境锁、明确执行授权。这些完成之前NOT_RUN_READY。现有共享仓库的其他任务改动保持不动。

部署包须保留兄弟目录public_source_contract_r1_20261009中的固定合同及两个角色CSV；路径通过roots JSON指定源数据位置。data_lock.create是本机来源冻结辅助工具，生产端用已有verified lock逐文件校验，不重新从任意文件创建信任锁。
