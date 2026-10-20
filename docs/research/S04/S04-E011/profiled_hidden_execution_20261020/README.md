# c20 PIDL profiled-hidden：关闭的执行封装

目的：在同一冻结c20s4上，区分PIDL能量下降却残差/active场改善不足的方向与度量问题；延续已完成的方向回放，不改变FEM damage、原UV边界、B0/约束Q4路线、实际Phi复用及1e-10。

本轮只补ae01bfed适配器的最后执行层。数学核心、科学比较卡、316字段调用及所有导数/资源上限、旧45项人工检查和既有结果原样保留。没有SSH、GPU查询/预约、真实模型或数组读取、forward/autograd、训练、FEM/历史更新、holdout或跨机上传。

## 一个包，两种明确范围

[关闭执行卡](execution_card.json)的候选RunID为`pf_s04e011_profiled_hidden_c20_r1_20261020`，不表示已启动。唯一原producer为Taobo GPUServer8/drtao/GPU5及卡内UUID；本轮没有实时验证，不允许其他GPU或主机替代。

| 范围 | 可以做什么 | 结束位置 |
|---|---|---|
| `preflight_only` | 原300秒内零接受隐藏更新的重复读数、源/算子/导数/内存首检 | 无论通过与否均退出；不能自行继续候选计算 |
| `conditional_full` | 单次首检通过后，继续1800秒候选、600秒局部见证、300秒读数 | 同一计数/资源/时限链，总上限3000秒；任何失败立即终止 |

包中`authority.closed.json`不能执行。未来启用须绑定精确manifest SHA、RunID、family、上述某一范围及人方批准记录的独立overlay。family尝试名额在资源准入前原子消耗，任何停止均保留；不能换ID重试。仅首检的批准不继承为后续计算批准，也不是科学成功。当前交付停在执行范围决策，本轮不请求或假定新执行许可。

## 控制与复用

复用现有pidfd独立watchdog和ready/start-gate模式，来源及差量见[复用记录](reuse_receipt.json)。单个科学进程保留首检的实际Phi/图/梯度/物理状态与共享计数；首步仅在token完全相同时复用已检查图。后续仍按原适配器重建和验证当前特征。没有新数值方法或新阈值。

内层guardian监督科学进程；外层相同guardian监督controller，包括导入、准入、计算、回滚、收据、清理及全量输出hash。两个guardian收到同样的严格阶段序列。科学工作每阶段留20秒、外层留10秒，均从原300/1800/600/300秒内扣除；保持前一阶段退出截止时点直到下一合法start，失败不能借后续预算。仅停止本链创建且身份绑定的进程；遇到外来GPU任务，停止自身并保留记录。

工作进程累计记录峰值RSS、CUDA allocated/reserved和任务目录字节数，不在阶段间清零；外层另查自身子树RSS/任务存储和selected GPU进程，未知/陈旧/非有限遥测停止。guardian在任何潜在阻塞文件写入之前绑定pidfd，parent-death保护处理父进程丢失。

全量封存必须在外层guardian仍存活时完成。退出后只读四个固定、各不超过1MiB的行政文件（三个尾部log/guard收据和export manifest），不再遍历/哈希原始字段树；若尾读超过总上限或缺失/过大，不能报告完成。离线`retrieve.py`要求producer返回的manifest SHA、尾文件SHA、全部payload bytes/SHA及完整覆盖；传输完整不等于科学成功。没有SSH/scp/重连代码。

## 人工验证与未验证部分

`python3 -B -m unittest discover -s tools/s04_e011_execution -p test_execution.py -v`运行人工文件、mock child/PIDFD/遥测。覆盖范围、阶段截止、先guardian就绪再准入再释放、失败后不释放、早退/缺terminal、第三方进程保护、manifest和包篡改等。真实Linux调度、Torch二阶AD、实际Phi动态图/有限网络重实现及资源可行性仍须未来原300秒首检确认；人工测试不替代它。

资产端点：代码/关闭卡/独立差量审查在本目录；本地单一交付包在`local_archive/experiments/S04-E011/pidl_profiled_hidden_execution_preparation_20261020_v1`，最终manifest SHA见该处build_receipt.json。科学结果仍是[已完成方向审计](../runs/pidl_hidden_direction_result_20261020.md)，并无新增PIDL性能结论。

下一决定：选择是否以及以哪个范围启用精确包。即使将来候选同时降E/Ru，也必须单独阅读active空间误差与共同初态对照；局部切线见证不能当作整个PIDL容量证明。FEM在这里是条件参照，非物理真值。
