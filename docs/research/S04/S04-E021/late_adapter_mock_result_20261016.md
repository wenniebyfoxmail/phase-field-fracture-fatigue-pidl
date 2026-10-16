# 只读适配器mock：执行与冻结核对

2026-10-16 Europe/London。单次工程执行COMPLETED，5组mock检查走完；未读真实数据、
控制JSON、数组或确认数据，未拟合。真实verification selector仍UNBOUND，真实执行未就绪。

## 身份、调用与预算

用户本轮批准最小适配器／元数据／授权交接及先mock后直接独立代码审核。
源码与运行卡提交 `542995c387d113bc398a9f77ceb38ea1dcf3e0b7`，启动checkout相同，源码干净。
唯一尝试S04-E021-LATE-ADAPTER-MOCK-R001；专用工作树和四源合同见
`late_adapter_contract_mock_card_20261016.md`。无GPU、无SSH、无producer作业。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_adapter_guard.py --expected-commit 542995c387d113bc398a9f77ceb38ea1dcf3e0b7 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-adapter-mock-20261016-R001
```

Mac Wennies-MacBook-Pro-14.local；UTC开始2026-10-16T21:42:11.977159+00:00，
伦敦22:42:11 BST。guard10255→worker10291，退出0，清理ALREADY_EXITED／exit_confirmed=true，
未发信号。primary_reason=null，terminal_caps=[]，errors=[]，receipt_persisted=true。
只调用一次，无轮询重启、重试或扩预算；原LATE-ENG-R002和旧失败现场不动。

| 资源 | 本次 | 上限 |
|---|---:|---:|
| guard计时 | 0.106479791983秒 | 60秒，工作58秒 |
| 聚合采样峰值RSS | 58,556,416 bytes =55.84375MiB | 512MiB |
| 写回执前 | 2,843 bytes | 计入5MiB |
| 全部输出含回执 | 4,373 bytes，3文件 | 5MiB |

计时／RSS／输出为采样监督，不是OS硬峰值保证。回执正文不含console追加的final_output_bytes，
全量4,373 bytes由三文件实际stat之和另核对，不把console字段冒充已落盘字段。

## 冻结核对

目录 `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-adapter-mock-20261016-R001`。
主对话只读核对checks、log和receipt，两个PID均不存在，目录无符号链接，随后移除本次文件及目录写权限。
三文件0444、目录0555；另有空mock_caller目录，无实际授权文件或子输出。
仅冻结本次目录，不修改科学源或旧结果，不新增hash。

| 文件 | bytes |
|---|---:|
| checks.json | 1,421 |
| engineering.log | 1,422 |
| guard_receipt.json | 1,530 |

5组：四个逻辑源／357生成行与三个保存背景副本；11种grant漂移及缺binding先于IO拒绝；
跨cwd绝对路径授权交接、5种env错误／相对路径／父PID错误先于授权callback拒绝；
15种元数据／身份／数值／schema／漂移拒绝和重复／非有限JSON拒绝；fake-fd只读标志／关闭及
非白名单／alias拒绝。checks／log相符，无未捕获Traceback。核心describe、拟合、重放及图均未调用。

fd层测试是mock os.open／fstat／read／close，不是真实源读取、真实OS故障或资源压力测试。
授权callback是内存JSON；完整真实文件reader、真实launcher及独立真实执行批准均不在本轮交付。
grant联锁不能证明人类许可。源码身份通过guard绑定真实提交；mock内授权协议用'a'×40仅测试相等联锁。

## 决策边界

最小只读适配组件与mock交接完成；真实verification字段路径无法仅从Git来源确定，故主动保持UNBOUND。
不猜结构、不以mock宣称真实档案通过，不把保存MSE定位当物理机制／梯度冲突结论。
下一步先独立静态审核精确代码；如无必改项，再申请仅查看verification schema的最小范围，
而非直接执行真实分析。确认U0.1175／U0.125关闭，E017／NN／多目标训练暂缓。
主对话单写记录和Obsidian；方法对话只读，不重复测试、实现或计算。
