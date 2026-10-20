"""Render the fixed SYNMEM decision figures from saved outputs only.

Purpose: display the exact current match, fixed H20 difference and all three
predeclared horizons. Inputs: result/current_match JSON and saved Boolean masks.
No solver, model, new threshold sweep, adaptive crop or example selection.
All images are PNG; figures, sidecars, README and matplotlib cache stay within
the supplied run directory. Importing this module neither reads data nor plots.
"""
import json
import os
from pathlib import Path

import numpy as np


VARIANTS = ("Base", "Space refinement", "Load-step refinement")
ARMS = ("Low prehistory", "High prehistory")
HORIZONS = (5, 10, 20)


def _read_json(path):
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _read_npz(path, shapes):
    with np.load(path, allow_pickle=False) as archive:
        data = {}
        for key, shape in shapes.items():
            value = np.asarray(archive[key])
            if value.dtype != bool or value.shape != shape:
                raise ValueError(f"{path.name}:{key} needs Boolean shape {shape}")
            data[key] = value.copy()
    return data


def _v1_match(masks):
    return dict(anchor_valid=bool(masks[:, :, 31:33, 8:24].all()),
                identical=bool(np.all(masks == masks[0, 0])),
                differing_pixels=int(np.any(masks != masks[0, 0], axis=(0, 1)).sum()))


def _same_summary(saved, expected):
    return (isinstance(saved, dict)
            and all(type(saved.get(key)) is type(value) and saved[key] == value
                    for key, value in expected.items()))


def _load_outputs(root):
    result = _read_json(root / "result.json")
    match = _read_json(root / "current_match.json")
    origin = _read_npz(root / "origin_observations.npz", {"masks": (3, 2, 64, 64)})["masks"]
    protocol = result.get("protocol", "1.0")
    cross_variant = _v1_match(origin)
    if protocol == "2.0":
        pair_xor = origin[:, 0] != origin[:, 1]
        pair_pixels = np.sum(pair_xor, axis=(1, 2)).tolist()
        pair_identical = [count == 0 for count in pair_pixels]
        expected = dict(matching_scope="within_each_variant",
                        anchor_valid=cross_variant["anchor_valid"],
                        identical=all(pair_identical),
                        differing_pixels=int(np.any(pair_xor, axis=0).sum()))
        pairs_valid = (type(match.get("pair_identical")) is list
                       and all(type(value) is bool for value in match["pair_identical"])
                       and match["pair_identical"] == pair_identical
                       and type(match.get("pair_xor_pixels")) is list
                       and all(type(value) is int for value in match["pair_xor_pixels"])
                       and match["pair_xor_pixels"] == pair_pixels)
        valid = (_same_summary(match, expected) and pairs_valid
                 and _same_summary(match.get("cross_variant_v1"), cross_variant))
    elif protocol == "1.0":
        valid = (_same_summary(match, cross_variant)
                 and match.get("matching_scope") != "within_each_variant")
    else:
        raise ValueError("unsupported saved SYNMEM protocol")
    if not valid:
        raise ValueError("current_match.json does not describe the saved origin masks")
    future = {}
    if result.get("future_executed") is True:
        for horizon in HORIZONS:
            value = _read_npz(root / f"future_h{horizon:02d}.npz",
                              {"masks": (3, 2, 64, 64), "robust": (64, 64),
                               "unstable": (64, 64)})
            masks = value["masks"]
            stable = np.all(masks == masks[0], axis=0)
            expected_robust = stable[0] & stable[1] & (masks[0, 0] != masks[0, 1])
            expected_unstable = ~(stable[0] & stable[1])
            if (not np.array_equal(value["robust"], expected_robust)
                    or not np.array_equal(value["unstable"], expected_unstable)):
                raise ValueError(f"H{horizon} maps disagree with the saved variant masks")
            value["robust_pixels"] = int(value["robust"].sum())
            value["unstable_pixels"] = int(value["unstable"].sum())
            summary = result.get("horizons", {}).get(str(horizon), {})
            if any(summary.get(key) != value[key] for key in ("robust_pixels", "unstable_pixels")):
                raise ValueError(f"H{horizon} result counts disagree with saved maps")
            future[horizon] = value
    elif result.get("future_executed") is not False:
        raise ValueError("result.json must explicitly state future_executed")
    return result, match, origin, future


def _source_links(paths):
    return "\n".join(f"- [{p.name}](<{p.resolve()}>)" for p in paths)


def _write_sidecar(path, *, question, sources, panels, message, limits):
    path.with_suffix(".md").write_text(
        f"# {path.stem}\n\n目的：{question}\n\n"
        f"输出：[{path.name}]({path.name})\n\n"
        f"Data provenance / 数据来源（本次run的准确文件）：\n\n{_source_links(sources)}\n\n"
        f"How to read / 读图：{panels}\n\n{message}\n\nLimitations / 限制：{limits}\n", encoding="utf-8")


def render_synthetic_history(rootdir):
    """Return output paths after rendering a complete or no-match saved result.

    Validation checks only consistency of the already saved images/maps/counts;
    it does not rescore native states or change result.json. No-match results
    always show all six current masks and never manufacture future panels.
    """
    root = Path(rootdir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("rootdir must be an existing run directory")
    result, match, origin, future = _load_outputs(root)
    paired = result.get("protocol") == "2.0"
    cross_variant = match["cross_variant_v1"] if paired else match
    settle_path = root / "zero_settle_observations.npz"
    settle = (_read_npz(settle_path, {"masks": (3, 2, 64, 64)})["masks"]
              if settle_path.exists() else None)
    output = root / "figures"
    output.mkdir(exist_ok=True)
    # Set before importing matplotlib, including in a fresh producer worker.
    runtime = root / ".plot_runtime"
    runtime.mkdir(exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(runtime)
    import matplotlib
    matplotlib.use("Agg", force=True)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.colors import ListedColormap
    from matplotlib.figure import Figure

    cmap = ListedColormap(["#F5F5F2", "#0072B2"])
    common_sources = [root / "result.json", root / "current_match.json",
                      root / "origin_observations.npz"]
    if settle is not None:
        common_sources.append(settle_path)
    limits = ("这是固定d→64×64二值观测（阈值0.5）的合成定义，不是物理裂缝mask、"
              "独立裂长或道路验证。三种离散设置仅检查已测试的敏感性，不构成数值误差上界；"
              "诊断图不能改变H20主判据或弥补当前匹配/完整状态重启条件缺失。"
              "结论仅针对geometry-only观测，不能将未来分歧单独归因于累计A。")

    def figure(rows, cols, size):
        fig = Figure(figsize=size, layout="constrained", facecolor="white")
        FigureCanvasAgg(fig)
        return fig, fig.subplots(rows, cols, squeeze=False)

    def panel(axis, mask, title):
        image = axis.imshow(mask, origin="lower", extent=(-.5, .5, -.5, .5),
                            vmin=0, vmax=1, cmap=cmap, interpolation="nearest")
        axis.set(title=title, xlabel="x (model units)", ylabel="y (model units)",
                 xlim=(-.5, .5), ylim=(-.5, .5))
        axis.set_xticks((-.5, 0., .5)); axis.set_yticks((-.5, 0., .5))
        axis.set_aspect("equal")
        return image

    def save(fig, name):
        path = output / name
        fig.savefig(path, dpi=180, format="png", facecolor="white",
                    metadata={"Software": "SYNMEM saved-output renderer",
                              "Source": str(root)})
        fig.clear()
        return path

    fig, axes = figure(3, 2, (8.6, 10.8))
    for variant, row in enumerate(axes):
        for arm, axis in enumerate(row):
            artist = panel(axis, origin[variant, arm], f"{VARIANTS[variant]} | {ARMS[arm]}")
    fig.colorbar(artist, ax=axes.ravel().tolist(), ticks=[0, 1], shrink=.72,
                 label="Digital mask (0 / 1)")
    if paired:
        fig.suptitle(f"V2 within-configuration current pairs | all matched={match['identical']}\n"
                     f"Pair XOR={match['pair_xor_pixels']} | cross-configuration V1 union="
                     f"{cross_variant['differing_pixels']} pixels (diagnostic)", fontsize=11)
    else:
        fig.suptitle(f"All current-origin masks | identical={match['identical']} | "
                     f"anchor={match['anchor_valid']}", fontsize=13)
    origin_path = save(fig, "origin_masks.png")
    if paired:
        observed = (f"看到：base、空间细化、载荷步细化各自的low/high当前全图匹配为"
                    f"{match['pair_identical']}，各对XOR像素数为{match['pair_xor_pixels']}，"
                    f"配置内XOR并集为{match['differing_pixels']}。"
                    f"跨配置v1六图比较仍保留：相对base/low的不同像素并集为"
                    f"{cross_variant['differing_pixels']}，六图完全一致={cross_variant['identical']}（诊断）。")
        condition = "三配置各自的当前low/high全图匹配和预裂锚点条件"
    else:
        observed = (f"看到：三个离散设置、两条历史的当前图像{'完全一致' if match['identical'] else '不完全一致'}，"
                    f"相对base/low图像的不同像素并集为{match['differing_pixels']}。")
        condition = "当前观测匹配和预裂锚点条件"
    settle_text = ""
    if settle is not None:
        settle_match = _v1_match(settle)
        settle_changes = np.sum(settle != origin, axis=(2, 3)).tolist()
        settle_text = (f"零载settle文件的六图差异并集为{settle_match['differing_pixels']}像素；"
                       f"各图settle→origin的XOR像素数（按三行low/high）为{settle_changes}。"
                       "这是历史前观测的诊断，不改变当前匹配或H20判据。")
    explanation = (f"因此：{condition}均满足，是否存在可分未来需读取固定H20结果。"
                   if match["identical"] and match["anchor_valid"] else
                   "因此：当前匹配或预裂锚点条件未满足，不能据此认定相同当前观测具有不同未来。")
    if paired:
        explanation += "配置内匹配不表示三配置共有一个完全相同的当前观测，也不把v1改写为通过。"
    _write_sidecar(origin_path, question="两条合法历史的允许当前观测是否匹配？",
                   sources=common_sources,
                   panels="按固定base、空间细化、载荷步细化排列三行，low/high两列；"
                          "全域坐标范围均为[-0.5,0.5]²，所有面板共用0/1色域，无裁剪或重配准。",
                   message=observed + "\n\n" + explanation
                           + ("\n\n" + settle_text if settle_text else ""), limits=limits)
    paths = [origin_path]
    primary_met = False
    future_text = "未来未执行；没有H5/H10/H20结果，不将其写成零差异或阴性预测结果。"
    if future:
        last = future[20]
        restart = result.get("full_state_restart") == "exact"
        primary_met = bool(match["identical"] and match["anchor_valid"] and restart
                           and last["robust_pixels"] > 0)
        fig, axes = figure(3, 2, (8.6, 10.8))
        for arm in range(2):
            panel(axes[0, arm], origin[0, arm], f"Base origin | {ARMS[arm]}")
            panel(axes[1, arm], last["masks"][0, arm], f"Base H20 | {ARMS[arm]}")
        panel(axes[2, 0], last["robust"], f"H20 robust differences | {last['robust_pixels']} pixels")
        artist = panel(axes[2, 1], last["unstable"], f"H20 unstable support | {last['unstable_pixels']} pixels")
        fig.colorbar(artist, ax=axes.ravel().tolist(), ticks=[0, 1], shrink=.72,
                     label="Binary indicator (0 / 1)")
        fig.suptitle("Fixed primary horizon H20 | complete field, shared range", fontsize=13)
        h20_path = save(fig, "continuation_h20.png")
        future_text = (f"看到：H20稳健差异为{last['robust_pixels']}像素，不稳定区域为{last['unstable_pixels']}像素；"
                       f"完整状态重启记录为{result.get('full_state_restart', '未提供')}。")
        support_text = ("因此：每种配置内部的当前low/high全图相同、锚点、完整状态重启与H20稳健差像素>0均满足；"
                        "支持配置内观测等价的合法历史在共同载荷下产生跨三配置一致的未来像素差异。"
                        if paired else
                        "因此：当前匹配、锚点、完整状态重启与H20稳健差像素>0均满足，支持本固定数字观测下的Q1。")
        decision_text = (support_text
                         if primary_met else
                         "因此：H20主条件与其所需当前匹配/完整状态重启条件未全部满足，不能用诊断图补成支持。")
        _write_sidecar(h20_path, question="固定H20是否出现跨三设置一致的两臂差异？",
                       sources=common_sources + [root / "future_h20.npz"],
                       panels="第一行是base的low/high当前图，第二行是base的low/high H20图；"
                              "第三行依次为稳健差异与不稳定区域，均显示全部64×64像素。"
                              "稳健指各臂内部在三个设置中一致而两臂不同；不稳定指至少一臂跨设置不同。"
                              "共同全域坐标及0/1色域，数字为像素数，不是物理裂长。",
                       message=future_text + "\n\n" + decision_text, limits=limits)
        paths.append(h20_path)

        fig, axes = figure(1, 1, (7.8, 4.4))
        axis = axes[0, 0]
        counts = [future[h]["robust_pixels"] for h in HORIZONS]
        unstable = [future[h]["unstable_pixels"] for h in HORIZONS]
        axis.plot(HORIZONS, counts, "o-", color="#0072B2", linewidth=1.6,
                  label="Robust differing pixels")
        axis.plot(HORIZONS, unstable, "s--", color="#D55E00", linewidth=1.3,
                  label="Unstable pixels (diagnostic)")
        axis.set(xlabel="Common future cycles", ylabel="Pixel count (of 4096)",
                 xlim=(4, 21), ylim=(-40, 4096 + 80), title="All declared horizons; H20 is primary")
        axis.set_xticks(HORIZONS); axis.set_yticks((0, 1024, 2048, 3072, 4096))
        axis.grid(axis="y", color="#D9D9D9", linewidth=.6)
        for h, value in zip(HORIZONS, counts):
            axis.annotate(str(value), (h, value), xytext=(0, 8), textcoords="offset points",
                          ha="center", color="#0072B2")
        axis.legend(loc="upper left", frameon=False)
        horizon_path = save(fig, "robust_horizon_counts.png")
        _write_sidecar(horizon_path, question="固定H5/H10/H20的稳健差异如何变化？",
                       sources=common_sources + [root / f"future_h{h:02d}.npz" for h in HORIZONS],
                       panels="蓝色实线为稳健差异像素数，橙色虚线为不稳定像素数；横轴为共同未来周期，"
                              "纵轴固定覆盖整个4096像素观测。显示全部预定跨度，不按效果选择H。",
                       message=f"看到：H5/H10/H20稳健差异依次为{counts}像素。\n\n"
                               "因此：只有H20参与主判定；H5/H10及不稳定像素数只描述过程，不能救主指标。",
                       limits=limits)
        paths.append(horizon_path)
        future_text += "\n\n" + decision_text

    current_rule = ("三配置各自的当前low/high全图严格相同（跨配置不要求全等）" if paired else
                    "当前全图跨两臂/三设置完全一致")
    primary_rule = (f"主判据：H20稳健差像素数>0，且{current_rule}、预裂锚点有效、"
                    "完整状态native restart为exact；任一条件缺失均不能作支持。H5/H10、阈值敏感性及"
                    "不稳定区域属于诊断，不替代主判据。native restart检验完整状态续算一致性，"
                    "不是学习模型null效果或真实物理验证。")
    readme = root / "README_analysis.md"
    amendment = ("v2是在查看当前态、未查看future前修订的配置内匹配问题；属于前瞻修订，"
                 "不是完全未见数据的独立复现。v1六图全等比较及其不满足的结果保持原记录，"
                 "不能用v2结果回填或改写。\n\n" if paired else "")
    readme.write_text(
        "# SYNMEM 已保存结果的决策图\n\n"
        f"Run目录：`{root}`；protocol：`{result.get('protocol', '1.0')}`\n\n原结果verdict：`{result.get('verdict', '未提供')}`；"
        f"按保存字段复核的完整主条件：`{primary_met}`。绘图不修改原结果。\n\n"
        f"{primary_rule}\n\n"
        + amendment
        + (settle_text + "\n\n" if settle_text else "")
        + f"![全部当前图](figures/{origin_path.name})\n\n{observed}\n\n{explanation}\n\n"
        + (f"![固定H20](figures/{paths[1].name})\n\n{future_text}\n\n"
           f"![全部跨度](figures/{paths[2].name})\n\n" if future else future_text + "\n\n")
        + "不说明：该d→二值图定义不等于真实可见裂缝；本实验不检验历史表示可恢复性Q2、"
          "模型外迁移Q3或真实道路预测。geometry-only观测下的分歧不能单独归因于累计A。"
          "未执行未来时，主条件未评估；False不应读成方法阴性。\n\n"
        + "准确输入：\n\n" + _source_links(common_sources +
                ([root / f"future_h{h:02d}.npz" for h in HORIZONS] if future else []))
        + "\n", encoding="utf-8")
    return {"readme": str(readme), "figures": [str(p) for p in paths],
            "future_executed": bool(future), "primary_conditions_met": primary_met}


# Short entry expected by the producer worker; import still has no side effects.
render = render_synthetic_history
