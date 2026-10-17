# S04-E021-LATE-BINDING-MOCK-R001：唯一人工mock完成及冻结核对

2026-10-17 Europe/London。执行COMPLETED，五组人工检查及8个比较探针按预期完成，
主对话核对并将唯一新目录设为只读。仅支持本次C0工程行为，不是真实归档、晚期归因或物理有效性结论。
批准的一次已消耗；没有重试、补跑、读取真实JSON／CSV／数组／确认数据或拟合。

## 批准与身份

- 用户明确批准9f00a6e的v2卡、e7bce63代码、唯一S04-E021-LATE-BINDING-MOCK-R001，
  60秒／512MiB／5MiB，失败或触限不重试。卡内准备时状态保留，本记录补充实际执行状态。
- 完整卡`9f00a6e2000a67d804140b6dd24058b0ac0f4c34`，源码
  `e7bce635fcdcbdd70abb06140b50f3bdd1064c16`；独立静态复审认可见5d10aad记录。
- 启动checkout`5d10aad3cf943fce3f702deaddf47a62fbffa1d2`，工作树clean；六源码tracked，
  与e7bce63逐文件diff为空，9984226冻结方案不变；v2卡与9f00a6e无差异。没有源码／配置修改。
- 工作树`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`，
  分支codex/s04-late-regression-plan-20261016。Owner为S04主对话01a1131d-017c-7b03-a95a-ad73ba8fcc9c。
- 主机Wennies-MacBook-Pro-14.local，Python `/Users/wenxiaofang/miniconda3/bin/python3`，本Mac CPU，
  数值线程1，无GPU／SSH／producer作业。启动前固定新目录不存在，相关Python guard／worker为空。
- UTC开始`2026-10-17T15:54:36.753658+00:00`，伦敦16:54:36 BST；guard41075→worker41095。
  外层命令退出0，worker_exit=0，cleanup=ALREADY_EXITED、exit_confirmed=true；无信号／清理错误。

唯一启动命令，从上述工作树执行：

```bash
PYTHONOPTIMIZE=0 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_binding_guard.py --expected-commit e7bce635fcdcbdd70abb06140b50f3bdd1064c16 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-binding-mock-20261017-R001
```

## 资源、终态及冻结

| 项目 | 本次保存记录／文件核对 | 批准上限 |
|---|---:|---:|
| guard计时 | 0.11191695899469778秒 | 60秒，工作58秒 |
| 聚合采样峰值RSS | 54,919,168 bytes＝52.375MiB | 512MiB |
| 写回执前输出 | 9,045 bytes | 计入5MiB |
| 总输出含回执 | 10,575 bytes，3文件 | 5MiB |

primary_reason=null、terminal_caps=[]、errors=[]、receipt_persisted=true、retry=false。
无触限。计时从guard execute开始，不含解释器／import启动；回执序列化另有post检查。
这是采样监督口径，不保证OS硬峰值或采样间资源。未做真实资源触限或OS故障注入。
console的final_output_bytes=10575与三文件stat之和一致；落盘receipt不包含该console追加字段。

唯一新目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-binding-mock-20261017-R001`。

| 冻结文件 | bytes | 权限 |
|---|---:|---|
| checks.json | 4,522 | 0444 |
| engineering.log | 4,523 | 0444 |
| guard_receipt.json | 1,530 | 0444 |

目录0555；只有以上三份常规文件、无符号链接、各nlink=1。先核对保存JSON／日志及PID退出，
再仅移除本目录和三文件写权限；未添加文件、hash或科学副本，未改旧成功／失败现场。
两PID已不存在，同类Python进程为空。engineering.log整体可解析，JSON与checks完全相等，
无额外stderr／Traceback。主对话随后仅用标准库核对已有三文件，不导入项目模块或重新生成mock。

## 人工判据逐条核对

| 冻结清单 | 保存结果与核对 | 允许结论／限制 |
|---|---|---|
| selector／单位3例 | 五selector断言走完；0→1、−25→0.75、25→1.25，身份／counts断言未失败 | 只验证人工doc，不是实际verification值 |
| 类型／缺字段7例 | RUN_TYPE、COMMIT_TYPE、ROWS_BOOL、COUNT_FLOAT、PERCENT_BOOL、PERCENT_STRING、MISSING_ROWS均按精确错误拒绝 | 不等于真实文件schema或内容有效 |
| 非有限3例 | NaN、−Inf、+Inf按声明错误拒绝；只序列化标签 | 未读取真实非有限数据 |
| 比较器8探针 | 5个接受达到指定哨兵，3个拒绝止于ratio；完整调用顺序断言走完，逐条保存预期／实际一致 | 无summary或CSV内容，未完成完整snapshot |
| 1e-12边界 | reference0的下邻点／精确等号接受，上邻点拒绝；Git常量中心两侧inside差9.99866855977416e-13、outside差1.000088900582341e-12 | 相邻数跨界断言走完，不声称center+tau差值精确等于tau |
| 两真实入口关闭 | snapshot在metadata/read前、acquire_real在reader构造前拒绝；开关从未置True | 只是人工关闭路径，不是REAL集成 |
| 非优化启动 | checks中python_optimize=0、python_debug=true | 确认本次非优化运行；-O／-OO拒绝仍只有静态审核，没有额外负例执行 |

checks同时明确real_data_read=false、fitting_invoked=false、real_ready=false、real_acquisition_enabled=false、
csv_contents_read=false、full_snapshot_completed=false、old_suite_run=false。五组与原卡一致，无事后删减。
本C0检查无科学结果图适用；以上决策表说明覆盖，未新增图或计算。

## 判断与唯一下一步建议

执行succeeded；本地取回／完整性verified；主对话工程核对完成，**不是独立结果复审**。
本次已验证人工绑定／单位、类型／非有限拒绝、容差邻界、非优化正常路径和关闭路径；不需重复此mock。
未验证真实输入、完整snapshot／REAL集成、优化负例或实际触限清理；原E021科学结论不变。

当前接入缺口已从字段路径／人工数值边界，转为尚未提供的真实授权reader／受限launcher及其人方许可。
建议唯一下一步仅准备**最小真实只读接入范围与运行卡**供审批：沿用9984226方案、四源白名单和既定预算，
明确授权reader／launcher交接与停止规则；获准后再实现／独立代码审核，真实读取执行仍须单独批准。
本轮没有准备或启动真实launcher、生成真实授权、开启REAL开关、读取四源或执行晚期归因。
不因人工mock完成而调整科学顶层设计、追加拟合、模型或确认数据访问。

方法对话01a12d15-9b60-7280-8248-18386d6ef741只读分工不变，compact状态读取为idle、revision62未变；
没有发送计算或写入消息。主对话唯一写本记录、Experiment索引、Obsidian及Roadmap，避免双写／重复计算。
U0.1175／U0.125继续关闭，E017／NN／多目标训练暂缓。分支和工作树保留，不push或清理其他产物。
