# G01 v0.2 — 人工子进程执行包 v1.1（待焦点复审及用户批准）

2026-10-18。已获准实现/设计/只读代码审查，未获测试或运行许可。
计划 SHA946c71850116b0c092052a3109a30a239f2d36062121668e9434c282f95c8098 不变；
设计见 thread_stop_test_design.md。仅本包人工测试，不含资源检查或数值验收。

## 代码身份

基线 `8e1bab3155439b30b605e7447ef84e314f9a9fba`，后继仅允许 docs、clean；
启动前及结束后核对实际 HEAD 和下列7个SHA，不以旧A002/B002源码代替。

| scripts/ 文件 | SHA256 |
|---|---|
| aa2024_runtime_guard.py | e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c |
| test_aa2024_runtime_guard.py | 05d000359b32d5570f3701d0231737f58d1b9d7ea039a435cf1bcf5fa4c59563 |
| aa2024_q_recheck.py | fc35d2c2a85780228468417613eb194ac95e6ca8b77d37f76f4ac1eba3bb8fcf |
| aa2024_q_verify.py | db48c03ccd5b4972663e10b31f54cbbc3562b9d78d994852f10b69190c85af09 |
| test_aa2024_q_recheck.py | a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf |
| aa2024_dyadic_reference.py | a492c822d7e06d82ff0c43306b7fdb004e2cb5b987b28bb5fd1646bcb8fd1c36 |
| test_aa2024_underflow.py | faec84e6e98c2063f9010e97028eebee52a8c782684640ed0c7e0b1bc124b87f |

## 唯一拟执行命令 A-G01（当前不执行）

工作目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_runtime_guard.py --source-commit 8e1bab3155439b30b605e7447ef84e314f9a9fba
```

若审查修改源码，必须更新代码基线/哈希/确切命令并复审，不能执行本旧版。
本命令不启动 producer、verifier、原65项单元、B002/B003或C/D；不发文件。
不把展示该命令视为执行批准，需用户另批一次，不自动重试。

## 资源和信息集

- 26个隔离人工子进程顺序执行，加2类源码静态断言；依次验证正常路径与
  预登记的进程fatal负控。非预期异常首次即停，不因某些负控预期exit70而
  忽略父包或其他子例的异常。字体日志没有任何真实运行豁免。
  v1.1另核对故障类别/原生异常类名、触发/写入哨兵；并发准备失败退出71，
  不把意外设置错误造成的exit70冒充预期故障。26子例数量/总预算未变。
- 仅标准库+guard，实际SVD0/QR0、求解0；不导入NumPy/SciPy/Matplotlib/
  torch/producer/verifier/原参考算术/原65项测试，不做全尺寸人工生成或出图。
- 只读本仓库源码和Git、本次自建临时目录小型哨兵/事件文件；不读任何
  local_archive/旧report/真实数组或留出，不改冻结预测/产物。
- 临时目录由 TemporaryDirectory 创建并由其清理，仅新人工文件。父stdout
  保存26项exit、事件/终端文本、代码身份与计时的JSON，作为本次轻量原始记录；
  失败保存完整异常/工具输出，不通过额外命令继续跑剩余例。
- 整包60秒软完成计时从首个time导入后开始，涵盖依赖导入、Git/代码身份、
  源码静态断言、所有子例、临时清理、末次身份和stdout后检查；单子例最多
  min(3秒,剩余预算)，Git最多min(5秒,剩余预算)，不另增预算。无硬实时保证。
- 六类数值线程环境1、CUDA空。人工Python工作线程只用于故障注入，非多线程
  数值计算。首个超时/不符/非预期警告或异常/身份变化即停，不续时或重试。

## 运行后可以与不能说明什么

父命令exit0、全部预登记子例符合、源码/预算/读写保护检查通过，才支持
人工条件下该守卫的实现行为；不能证明任意原生线程硬停、完整CLI真实运行、
原尺寸资源预算、实际DIC/物理反演或B002重新有效。独立静态代码审查不是
测试通过或新运行许可。本轮不会运行该命令、语法检查、导入或数值程序。

启动前重查普通Codex额度与源码身份；任一正常窗口剩余<80%或不可核实，
不启新阶段，只安全保存。当前准备阶段额度remaining82%，并非剩余18%。
