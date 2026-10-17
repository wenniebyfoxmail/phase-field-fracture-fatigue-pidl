# E019-D03-B001 — 同尺寸人工资源检查首停记录

2026-10-17。用户批准执行包确切B命令一次；单线程CPU、60秒软预算、目标
1次SVD/2次薄QR，首个非预期异常停止，不重试，不启动C/D。

## 结果：未完成，不是资源/数值证书通过

一次启动chunk55927e，运行session40100；只轮询同一进程，终止输出chunk
5f16c3，退出码1。没有重新启动、恢复、追补检查、修改源码或异常豁免。
启动前UTC观测21:06:29；失败后记录21:06:46（非进程精确起止计时）。
失败收据没有输出总耗时，不能补造完成时间或宣称完整60秒可行性成立。

首个异常：

```text
aa2024_q_recheck.py:233, analyze
close(mm(A.T, Lr), Vr*sr, 'AT Lr=Vr sr', 'matrix')
FloatingPointError: underflow encountered in multiply
```

它发生在保留奇异对右侧作用关系检查的`Vr*sr`浮点乘法求值，尚未得到
该比较的通过/失败结果，不是已测得的奇异关系容差超标。未判断其实际
量级、根因或是否影响原容差，没有将其擅自当作可忽略的舍入现象。

原失败收据：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B001/failure_receipt.json`

- execution_status=failed；mode=synthetic；hostname=Wennies-MacBook-Pro-14.local；
  PID5698；Python3.12.2，NumPy2.2.6。
- 受控API计数：SVD1、QR1。第一次QR建立H，第二次修复QR尚未到达；
  因首停，不为凑足原计划次数而继续。计数不是独立整进程历史审计。
- inputs={}、artifacts_sha256={}。只生成failure_receipt.json（1106bytes）；
  没有certificate.npz、report.json、图片、图说明、成功收据或完成标志。
- 只核对失败收据和文件列表，没有读/计算合成数组、补算、独立验收或读图。
  无图可验；不运行图说明校验器，不把缺图判作科学负结果。
- 未读取真实数组、stage15响应或新留出；未调用opaque输入哈希；没有对外发送。
  原预测、冻结产物和源码不变。B001失败目录原样保留，不覆盖或重用。

## 确切命令及身份

工作目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py synthetic --source-commit a3352a6954543f965d559a1f1a6452cf9e58b2fb --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B001
```

受审代码a3352a6954543f965d559a1f1a6452cf9e58b2fb；实际HEAD
ce1eb27818a19d7582896cb46dd5ad070327edcd，启动前后均clean，仅docs后继。
三文件启动前后SHA与失败收据一致：

| 源码 | SHA256 |
|---|---|
| aa2024_q_recheck.py | 06fd574663eb7d7b740b26f77f9dd50d479f992bc707808cb30ccb52fa4765b0 |
| aa2024_q_verify.py | d378b5cbc8d446c624d14917fd3b3bfa75ca6f29be67726590d794b4c01d26a0 |
| test_aa2024_q_recheck.py | a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf |

## 决策边界

A的24项人工单元通过仍保留；B暴露了实际全尺寸求值的执行阻断，但没有
完成Q修复或三场账本，不能据此否定修复算法、真实DIC或反演路线。
下一项建议仅准备源码/纯合成层面的下溢处理方案，说明如何保持原容差与
异常语义，另审另批；本轮不实施、不忽略下溢、不改阈值，也不重跑B。
B验收、真实C/D继续未授权/未执行。
