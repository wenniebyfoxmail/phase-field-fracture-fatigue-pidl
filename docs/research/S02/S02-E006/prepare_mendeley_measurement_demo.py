"""One AI teaching example, deliberately excluded from the human review packet.

Plots published current-frame CSV nodes only. Does not estimate an automatic
tip, read author labels, fit a model, or fill a formal measurement row.
"""
from pathlib import Path
import argparse
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from scipy.spatial import cKDTree


GROUP = "E_0Deg_20%_#1"
STAGE = 1600
COLUMNS = ["item_id", "left_endpoint_x_mm", "left_endpoint_y_mm",
           "right_endpoint_x_mm", "right_endpoint_y_mm",
           "unmeasurable_reason", "confidence_note"]


def main(base):
    formal = base / "measurement_review_packet"
    protected = {p: p.read_bytes() for p in
                 [formal / "blank_measurements.csv", formal / "INTERNAL_source_key.json"]}
    key = json.loads(protected[formal / "INTERNAL_source_key.json"])
    assert not any(k["group"] == GROUP and k["stage"] == STAGE for k in key)
    with (formal / "blank_measurements.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 30
    assert all(not row[c] for row in rows for c in COLUMNS[1:])

    source, = (base / "csv_extracted").rglob(f"{GROUP}_{STAGE}.csv")
    a = np.loadtxt(source, skiprows=4)
    assert np.isfinite(a[:, [1, 2, 5]]).all()
    out = base / "measurement_demo"
    out.mkdir(exist_ok=True)

    # Selected visually from this frame, not an algorithmic or human measurement.
    # Midpoint of two nearby boundary nodes illustrates rounding, not accuracy.
    upper = a[a[:, 0] == 9512][0]
    lower = a[a[:, 0] == 9635][0]
    left = np.round((upper[1:3] + lower[1:3]) / 2, 1)
    assert np.allclose(left, [-0.2, 48.9])
    spacing = float(np.median(cKDTree(a[:, 1:3]).query(a[:, 1:3], k=2)[0][:, 1]))
    lo, hi = np.percentile(a[:, 5], [1, 99])
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7.2),
                             gridspec_kw={"width_ratios": [1, 1.25]})
    fig.subplots_adjust(left=.065, right=.91, top=.85, bottom=.20, wspace=.27)
    for ax in axes:
        im = ax.scatter(a[:, 1], a[:, 2], c=a[:, 5], s=7,
                        cmap="viridis", vmin=lo, vmax=hi, rasterized=True)
        ax.set(xlabel="Published CSV x / mm", ylabel="Published CSV y / mm", aspect="equal")
    axes[0].set(xlim=(-3, 103), ylim=(-5, 108), title="A. Current raw displacement field")
    axes[0].add_patch(Rectangle((-2, 40), 50, 19, fill=False, ec="black", ls="--", lw=1))
    axes[0].annotate("Smooth colour variation\nis not a crack endpoint", xy=(23, 71),
                     xytext=(8, 88), fontsize=10,
                     arrowprops={"arrowstyle": "->", "color": "black"})
    axes[1].set(xlim=(-2, 48), ylim=(40, 59), title="B. Raw-node zoom; same colour scale")
    axes[1].plot(*left, "o", ms=8, mfc="white", mec="black", zorder=5)
    axes[1].annotate("A: approximate boundary intersection\n(-0.2, 48.9) mm", xy=left,
                     xytext=(2, 56), fontsize=10,
                     bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9, "pad": 3},
                     arrowprops={"arrowstyle": "->", "color": "black"})
    axes[1].add_patch(Rectangle((20, 47.4), 20, 3.2, fill=False, ec="black", ls=":", lw=1.3))
    axes[1].annotate("B: contrast fades; no unique right tip\nLeave right coordinates blank", xy=(30, 49),
                     xytext=(10, 42), fontsize=10,
                     bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9, "pad": 3},
                     arrowprops={"arrowstyle": "->", "color": "black"})
    cb = fig.colorbar(im, ax=axes, fraction=.025, pad=.025, shrink=.8, extend="both")
    cb.set_label("Published displacement_y / mm")
    fig.suptitle("DEMO ONLY | One current frame, not a formal human replicate\n"
                 f"{GROUP} | file / internal Stage {STAGE}; not certified fatigue-cycle time", fontsize=13)
    fig.text(.065, .11,
             "CSV row: DEMO_ONLY | left=(-0.2, 48.9) mm | right=blank | projected span=not computed\n"
             f"Nearest-node spacing median: {spacing:.2f} mm (not a measurement-error estimate). No interpolated field.\n"
             "Dotted box is a discussion crop, not a tip interval. Colour saturation: 1st/99th percentiles. No future frames or labels used.",
             fontsize=10, va="top")
    fig.savefig(out / "manual_measurement_demo.png", dpi=180)
    plt.close(fig)

    row = dict(item_id="DEMO_ONLY", left_endpoint_x_mm=left[0], left_endpoint_y_mm=left[1],
               right_endpoint_x_mm="", right_endpoint_y_mm="",
               unmeasurable_reason="Right endpoint cannot be uniquely located from this current raw uy field.",
               confidence_note="AI teaching example, not human annotation. Left coordinates approximate; no calibrated uncertainty; no length computed.")
    with (out / "demo_measurements.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerow(row)
    manifest = dict(status="AI_DEMO_ONLY_EXCLUDED_FROM_FORMAL_REVIEW", source=str(source),
                    group=GROUP, stage=STAGE, outside_formal_unique_frames=True,
                    left_example_mm=left.tolist(), right_endpoint_mm=None,
                    projected_length_mm=None, median_nearest_node_spacing_mm=spacing,
                    left_bracketing_node_ids=[9512, 9635],
                    formal_template_and_source_key_unchanged=True,
                    training=False, fit=False, future_frames_used=False,
                    author_lengths_used=False, automatic_tip_used=False)
    for p, before in protected.items():
        assert p.read_bytes() == before
    (out / "demo_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "manual_measurement_demo.md").write_text(f"""# 人工复测教学示范：允许记为无法测量

## 问题与范围
如何识别当前发布DIC位移场的不连续端点，并在终点不清楚时填写复测表。
这是Codex制作的教学示范，不是人类独立测量、不计入正式25个唯一帧及5次重复。

## 来源 / Data provenance
原始文件：`{source}`；文件号及内部Stage均为1600，未将其认证为疲劳循环时间。
直接绘制CSV列x、y、displacement_y，单位按源文件为mm；没有插值、自动裂尖、作者标签或未来帧。
帧不在正式包中；正式空白测量表和来源键已逐字节核对未变。

## 读图 / How to read
A为原始全场；虚线框给出B的空间裁剪范围。B仍显示原始散点，颜色是displacement_y，
两面板共用全场1/99百分位色限，色条两端表示饱和。平滑颜色渐变不能独立用作裂尖。
白圆是左侧不连续与可见数据边界交点的粗略示范；右侧点线框只圈出需讨论的区域，
不是裂尖误差区间，不把颜色过渡带的末端指定为物理裂尖。

## 填写与数值
左端示范取边界附近节点9512与9635的坐标中点，按图示精度舍入为(-0.2,48.9)mm。
这只是演示读坐标的方法，不是已验证的端点定义或精度。右端无法唯一定位，两个坐标留空，
在unmeasurable_reason写明原因。因此不计算投影长度，不能用0代替空值。
邻点最近距离中位数约{spacing:.2f}mm，仅说明采样尺度，不是测量误差或置信区间。

## 限制与用途 / Limitations
本图支持如何记录不确定性，不支持物理裂长准确度、试件独立性、时间同步或历史预测价值。
右端需原始光学图像或明确且独立验证的定位规则才能可靠补填；不能靠后续帧、自动曲线或
单调增长假定补猜。示范CSV单独保存；无拟合、训练或正式复测结果。
""")
    (out / "README.md").write_text("""# 单帧测量示范（不计正式复测）

先看manual_measurement_demo.png及同名说明，再看demo_measurements.csv。
DEMO_ONLY是Codex教学行，不是人工测量；右端留空，长度不计算。
原measurement_review_packet/blank_measurements.csv仍为30条空白测量项。
正式复测应逐张独立判断，不查看自动结果、作者长度或未来帧；无法定位时填原因。
坐标读CSV毫米轴，PT像素不能直接换算毫米。两端均可辨时才计算右x减左x；
该值是可见不连续范围的水平投影，不默认等于作者裂长或物理裂纹弧长。
""")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    main(parser.parse_args().base)
