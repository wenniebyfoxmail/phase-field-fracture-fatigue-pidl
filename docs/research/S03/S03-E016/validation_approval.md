# E016 stage15 本地验证待审批稿 — 2026-10-15

状态：仅准备，未执行。独立只读代码审查结论另见 code_review.md。
用户当前只批准图器开发、合成测试与审查，不批准读取真实 stage15。

## 本次拟执行的范围

在 Mac 本地新建 S03-E016-R003，只验证已经冻结的 R002 四组预测。
不连接 Taobo，不发送消息或文件，不重新求解、拟合或调参。
q=0、old/proxy/intact/secant 预测、训练侧几何/边界/权重全部不变。
本次若获批准，将首次消费 stage15 响应；此后它不能再用于独立调参验证。

代码快照：b702430e3de98226ccf4a799c613b8df181fc9d4。
数值 runner 与四个依赖保持 R002 原字节；新增图器 SHA-256：
484d6130f2a672fd8bb1a62fc32a38a2ab82830e0066b90da5f17912b72d5a96。
后续只记录审查和审批状态的文档提交不改变这些代码。

## 数据与解释约定

- 训练：cycle292018.5、reference1、stage13/14；留出：stage15。
- 唯一原始输入：原 ZIP 中 global_3d_dic/Nodemaps/global_3d_dic_results_1_15.txt。
  原 ZIP 长度1248078255字节，MD5 e671b804e29401e70043bc1e17f66dd1；
  stage15 原文预存 SHA-256 7148b8544294eff0aea25ff1e903a7acd66c5a68bdc3a2d7139b4e4f75096b16。
- 目标：stage15-stage13 平面位移增量，不是新 cycle 的预测。
- 原有冻结支持：648点。按同一规则筛选有限 XY/U/V；每个冻结 ID 必须存在，
  referenceXY 容差1e-6mm，至少10点且刚体子空间满秩。Z/W 单独缺失不删点。
  四组共用同一 eligible ID、继承训练面积权重；不重建边界/权重，不逐侧对齐。
- 对每组预测减目标后的残差，只去除同一个全局平面平移/转动子空间。
  主指标是面积加权向量范数 MAE（mm），主差值 Δ=MAE(old)-MAE(proxy)。
  正/零/负只描述本次改善/相等/变差，报告全部四组和面积覆盖，不增设噪声阈值。
- 三类图：四组 MAE/Δ、共尺度残差图、原始目标与四组增量 U/V 图。
  图器独立标量公式检查投影、分数和主差值；不改原评分。
- 本次不能证明真实裂尖、材料参数、独立重复性、跨 cycle 疲劳预测或道路迁移。
  单周期/试件、二维静态近似、辅助剖面异常等既有限制继续保留。

## 预算与停止规则

仅一次本地验证调用和一次结果绘图，不包含任何求解。
ZIP 身份核验是流式读盘；解析成员上限16MB。R003 必须全新；任何不一致、
解析/支持/数值/绘图失败都停止并保留现场，不自动重试、不替换响应、不调参。
图器复核误差容差是算术一致性检查，不是物理意义上的接受阈值。
若实际出现此前 Mac BLAS 数值警告，必须保留警告日志并核对独立标量报告；
不在本次权限内静默改代码、重新验证或重新求解。

## 待批准命令（下面仅展示，尚未运行）

命令在一个新 shell 中顺序执行；任一步非零退出立即停止。所有路径本地，
没有账号、收件人或外部提交对象，也没有附件/外发承诺。

```bash
set -euo pipefail
task_repo='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
task_base='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016'
task_py='/Users/wenxiaofang/miniconda3/bin/python3'
cd "$task_repo"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# 先核验已冻结产物、代码和ZIP，再只提取指定stage15成员；此块将读取留出原文。
"$task_py" - <<'PY'
import hashlib, json, subprocess, sys, zipfile
from pathlib import Path
sys.path.insert(0,'scripts')
import aa2024_geometry_prior as m
base=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016')
prep=base/'S03-E016-R001/prepare'; fit=base/'S03-E016-R002/fit'; out=base/'S03-E016-R003'
snapshot='b702430e3de98226ccf4a799c613b8df181fc9d4'
files=['scripts/aa2024_geometry_result_view.py','scripts/aa2024_geometry_prior.py']+['scripts/'+n for n in m.DEPS]
for name in files:
    expected=subprocess.check_output(['git','show',snapshot+':'+name])
    if Path(name).read_bytes()!=expected:raise ValueError('reviewed code changed: '+name)
if out.exists():raise ValueError('R003 already exists; stop, no retry')
expected_fit={
 'fit.json':'cc39afa4d46d172c08d6637dd5496a0be58f73bc08f97646ea735f61bac2609d',
 'frozen_predictions.npz':'c6593309c364e6104c0093c82b812aa5698a5dfe17be1f885ce2bfc8b3a751f9',
 'solved_fields.npz':'b67988bcb85047043cd2331afa601ea9164f64c45bed01a4a2d80417a00bf807',
 'execution_receipt.json':'3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674'}
for name,digest in expected_fit.items():
    if m.sha(fit/name)!=digest:raise ValueError('R002 frozen hash mismatch: '+name)
pr=m.completed(prep,'prepare',m.PREP); fr=m.completed(fit,'fit',m.FIT)
fm=json.loads((fit/'fit.json').read_text()); pb=m.bindings(prep,m.PREP)
if fr.get('input_bindings')!=pb or fm.get('source_prepare')!=pb:raise ValueError('R001 lineage mismatch')
if fm.get('status')!='four_predictions_frozen_before_held_response' or fm.get('cycle')!='292018.5':raise ValueError('fit status/cycle')
m.finite_predictions(m.load(fit/'frozen_predictions.npz'))
target_hash='7148b8544294eff0aea25ff1e903a7acd66c5a68bdc3a2d7139b4e4f75096b16'
if fm.get('held_member_sha256')!=target_hash:raise ValueError('frozen target identity mismatch')
archive=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/aa2024_dic_zenodo_11945905_20261008/raw/multiscale_digital_image_correlation.zip')
if archive.stat().st_size!=1248078255:raise ValueError('ZIP size mismatch')
digest=hashlib.md5()
with archive.open('rb') as stream:
    for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
if digest.hexdigest()!='e671b804e29401e70043bc1e17f66dd1':raise ValueError('ZIP identity mismatch')
member='global_3d_dic/Nodemaps/global_3d_dic_results_1_15.txt'
with zipfile.ZipFile(archive) as z:
    raw=m.read_member(z,member).encode('utf-8')
if hashlib.sha256(raw).hexdigest()!=target_hash:raise ValueError('stage15 member identity mismatch')
out.mkdir()  # exclusive creation, after all preflight checks
(out/'held_input').mkdir()
(out/'held_input/stage15.txt').write_bytes(raw)
record=dict(reviewed_snapshot=snapshot,source_prepare=pb,source_fit=m.bindings(fit,m.FIT),
    frozen_hashes=expected_fit,archive=str(archive),archive_size=archive.stat().st_size,
    archive_md5=digest.hexdigest(),member=member,member_sha256=target_hash)
m.write_json(out/'preflight.json',record)
PY

"$task_py" -u scripts/aa2024_geometry_prior.py validate \
  --input "$task_base/S03-E016-R002/fit" \
  --high-member "$task_base/S03-E016-R003/held_input/stage15.txt" \
  --output "$task_base/S03-E016-R003/validate" \
  --source-commit b702430e3de98226ccf4a799c613b8df181fc9d4 \
  --run-id S03-E016-R003 \
  > "$task_base/S03-E016-R003/validate.log" 2>&1

"$task_py" -u scripts/aa2024_geometry_result_view.py \
  --prepare "$task_base/S03-E016-R001/prepare" \
  --fit "$task_base/S03-E016-R002/fit" \
  --validation "$task_base/S03-E016-R003/validate" \
  --output "$task_base/S03-E016-R003/figures" \
  > "$task_base/S03-E016-R003/render.log" 2>&1

"$task_py" source/validate_figure_sidecars.py "$task_base/S03-E016-R003/figures" \
  > "$task_base/S03-E016-R003/figure_sidecars.json" 2>&1

# 最后核对R002仍逐字节一致；不重写任何来源收据。
"$task_py" - <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0,'scripts')
import aa2024_geometry_prior as m
base=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016')
out=base/'S03-E016-R003'; fit=base/'S03-E016-R002/fit'
before=json.loads((out/'preflight.json').read_text())['frozen_hashes']
after={n:m.sha(fit/n) for n in before}
if after!=before:raise ValueError('R002 mutated; stop interpretation')
m.write_json(out/'frozen_source_after.json',after)
PY
```

完成后只做结果完整性和图形检查，报告四组分数、Δ、共同支持/覆盖、
独立算术复核以及可解释限制。任何新实验、参数变化或对外发送另行审批。
