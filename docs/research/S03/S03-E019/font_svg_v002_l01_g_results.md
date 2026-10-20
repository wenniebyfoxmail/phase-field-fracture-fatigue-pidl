# F01 V002-L01：G 一次生成完成，尚未打开或验收

2026-10-20（Europe/London）。本轮仅执行获批命令 G 一次，状态
`LAYOUT_GENERATED_NOT_ACCEPTED`。只支持布局派生路径完成，不是图形可读性、
数值或真实 DIC 反演通过。原 S01／结构已通过范围和旧首停记录不改写。

## 本次权限、预检与执行身份

- 人方明确批准执行包的确切 G：唯一新 V002-L01 目录、单线程 CPU、60 秒
  软预算、零 SVD/QR、科学值及柱高不变；首个非预期异常／警告即停，不重试。
  明确暂不打开图或启动 V1–V3；不把机械执行批准扩为后续验收批准。
- 获批文件：[execution_package.md](preparation/f01_v002_layout/execution_package.md)，
  SHA256 `8b74abfd0f047a02801a84b81f4c9966e9c037e1d9d55ae867bd2203f6c52d55`，原字节保留。
- 启动前 clean HEAD `114e9bc45f855d4895f4568f97bf34542c99b57c`；代码快照
  `a8b10844c173f6d7f7479251685e78137fdc5f80` 为祖先，后继仅三件 docs。
- 预检 chunk `f969ae`：CLI、测试、manifest、旧草案、原图器、G01、执行包
  七个指定 SHA 全部 OK；唯一 NEW 既不存在，也不是悬空符号链接，父目录存在。
  G 内部在来源读取前、mkdir 前再次检查新鲜性及非链接路径。
- 实际主机 `Wennies-MacBook-Pro-14.local`，PID `61510`。同步工具 chunk
  `ad6526`，exit0，无运行中 session、无警告或异常；未自动重试。
- 打印前计时 `0.28557858301792294 s`，收据前 `0.24611062498297542 s`；
  G 打印后末次源码／清单／guard／60 秒软检查亦通过。两者是过程取样，
  不是精确全程耗时。工具 wall 采用不同口径，不混同或相加。

工作目录：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013
```

实际命令（仅一次）：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_release.py --mode generate --manifest-sha 2b19ff62464aa7759e982cd084ed54cc7809aff2026fa144ca2b6c17d80f5b75 --self-sha fda7a06e4ced32db18b592ff9b0a9c6249c9e6091f1f77d690a0c34e1944141c --snapshot a8b10844c173f6d7f7479251685e78137fdc5f80
```

完整 stdout：

```json
{"status": "LAYOUT_GENERATED_NOT_ACCEPTED", "elapsed_before_print": 0.28557858301792294}
```

## 已生成范围与运行内检查

唯一 NEW：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01
```

G 内部核对来源目录精确十件与 manifest 相同、写入前后来源字节／stat 不变，
独占创建 NEW 七件并读回；新图／说明等于固定布局变换的内存结果，完成文件
绑定收据，源码／清单／clean HEAD 起止一致。这里只引用 G 实际完成的检查，
没有额外运行 verify／finish／validator，也不称独立结构或语义验收。

四件派生与事件文件 SHA 来自实际运行收据：

| 文件 | SHA256 |
|---|---|
| `residuals.svg` | `f4051470027642281a5e6f9f5f9bd41afefae6f9eb8ff1d8d970bf6d095fec0c` |
| `residuals.md` | `54ffcaba86a88db114f5e548988a217f49b79d0bf290398482ed3be63aba6641` |
| `square_ledger.svg` | `018d607c9ccb19af36ae343fc8a4df2249d727682f7c4b322779957ded3222c6` |
| `square_ledger.md` | `a830f23bbe5b388193736032038dd1cc0afdec4c62fc984922889ba643b48edd` |
| `runtime_guard_events.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空） |

另两件为 `layout_receipt.json`、`layout_completion.json`；后者保存的收据 SHA
为 `748c1f636b31828fb7e080f5205279d5964f62f2bcc8ec0fa722a1d711480376`。
运行收据保留十件来源和五件代码 SHA、两图／S01 companion→新图／同名说明
映射、runtime HEAD／PID／主机／命令、六线程变量均 1、G01 healthy=true／
fatal_seen=false、actual_svd=actual_qr=0、scientific_recomputation=false、
visual_acceptance=false、source_status=incomplete_unaccepted_synthetic。
这些是本进程的受控记录，不是历史 B003 或全机计算审计。

布局按冻结代码派生：V 行屏幕组下移70、画布／底注扩展、账本补三条原
data-value 字符串标签；点保存属性／色标／柱高／科学值没有修改路径，不
重算或重新舍入。是否真正解决遮挡及可读性尚未目视，不能用代码预期代替。

执行后只为报告读取新收据／completion 并列目录，看到精确七件、事件文件
0字节，工作区仍 clean（归档文档前）。未读取新 SVG／说明正文去补做验收。
原 V001／S01、renderer、G01、草案、manifest 和获批执行包均未修改。

## 限制与当前停点

未打开／渲染／转换／截图／导出图，未启动独立代理或 V1–V3，未运行侧注
validator（人方明确本轮仅 G）。没有 NumPy／SciPy／Matplotlib、字体预热、
字体警告豁免、SVD/QR、科学重算或求解；未读 B003 数值、真实数组、stage15
或新留出，不启动 C/D，不外发。原权重／预测／容差不变。

现在停在生成完成：**新说明语义、实际完整画面／右侧色标和最终跨目视身份
检查均未完成**。B003 仍 incomplete／unaccepted，真实 DIC 反演／预测没有
新增有效性结论。若人方后续批准，沿执行包 V1→实际目视→V3 完成一次独立
只读验收；本次批准不继承到它们，也不自动继续。
