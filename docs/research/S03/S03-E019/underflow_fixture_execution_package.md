# U01-F01 v1 — 修正后tiny确切命令/资源卡（未执行）

2026-10-17；仅供总部核清下一次tiny执行资格，不构成本轮运行许可。
候选Run标识`S03-E019-D03-U01-A002`。A001记录原样保留，不重试/续跑。
源码仅三个人工fixture函数差异，理由见underflow_fixture_revision.md。
原Pro/代码审查未变部分复用；当前待原只读渠道焦点静态复核。

更新：焦点复核`PASS_STATIC_FIXTURE_DIFF`，绑定clean `2b4253761c756e893d46bebbeb36ae753be51955`。
回执见underflow_fixture_revision.md。本包准备完成，仍未执行，未取得新运行许可。

## 固定版本

源码基线`ab6f123a0174c7009b5427c0db0b98901ca1e2d3`，后续只允许docs记录提交。

| 源文件 | SHA256 |
|---|---|
| aa2024_dyadic_reference.py（未改） | a492c822d7e06d82ff0c43306b7fdb004e2cb5b987b28bb5fd1646bcb8fd1c36 |
| aa2024_q_recheck.py（未改） | 0a7ebbd60d778b8e0cf2171891b68ab928ff73e0092c244f7958174ac9d49acd |
| aa2024_q_verify.py（未改） | 90755956092e16cb84c0ebedd9907c21a79ea523d1819dc8fb657ec10ae7d873 |
| test_aa2024_q_recheck.py（原24项未改） | a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf |
| test_aa2024_underflow.py（仅三fixture函数） | faec84e6e98c2063f9010e97028eebee52a8c782684640ed0c7e0b1bc124b87f |

## 确切命令（只展示，不执行）

工作目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_underflow.py --source-commit ab6f123a0174c7009b5427c0db0b98901ca1e2d3
```

## 资源/信息/停止卡

| 项目 | 冻结范围 |
|---|---|
| 对象 | 41新增人工边界+24原有stub回归，共65设计项；运行计数须由实际输出确认 |
| 设备 | 本地CPU单线程，CUDA_VISIBLE_DEVICES空；六类线程环境均1；不装软件 |
| 预算 | 每包仍为原60秒软完成预算，含导入/身份/模型/测试及最终打印后检查；不硬杀运行中的核；不把A001已用耗时当新授权余量 |
| 分解/求解 | 实际QR0、SVD0、eig/solve/lstsq/pinv0；同尺寸artificial生成禁止 |
| 读取 | 仅源码位型、小数组/Fraction、源码字节/Git身份；不读report/NPZ/真实/留出/local_archive |
| 写入 | 该命令仅终端stdout/stderr；-B及PYTHONDONTWRITEBYTECODE=1；无图/数值目录；另行保存只新增运行记录，不改A001 |
| 守卫 | 原np.load/分解/同尺寸生成/真实读取守卫、首个非预期错误/警告failfast、不自动重试；量纲容差和五site不动 |
| 身份 | 起止五源码SHA、HEAD/clean；后继仅docs；来源/预算失败不得产生成功结论 |
| 夜间额度 | 阶段前后及连续工作约5分钟检查正常Codex窗口，任一剩余<80%或未知则不启动；本轮开始为used9%/remaining91% |
| 限制 | 不启动B002/C/D，不读取或修改冻结产物；不以静态通过当65项或硬件/反演通过 |

独立静态复核通过后仍只停在交付；总部另行核清是否可使用原tiny授权余量
或需新授权。本任务不自行判定余量、不执行新命令，不因普通静态修复把
A001的首停/不自动重试解释成失效。

## 2026-10-18 A002已执行一次：65/65通过

用户在本对话另作明确批准后，按上方确切命令执行一次，未重用A001许可。
chunk97939d exit0，65项通过，无异常/重试；原容差/单线程60秒和零实际
分解保持，未读真实/留出或启动B002/C/D。完整输出、计时口径与限制见
[underflow_a002_results.md](underflow_a002_results.md)。本次许可已使用完毕，
不自动再次执行或进入下一规模；开头“未执行/待核清”为历史准备状态。
