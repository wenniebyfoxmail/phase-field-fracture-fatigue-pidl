#!/usr/bin/env python3
"""Single-owner 17-line annotation UI with mechanical 66-point derivation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
STATUS = "EXPLORATORY_SINGLE_OWNER_LINE_ANNOTATION__NOT_INDEPENDENT"
LINE_STATUSES = {"unreviewed", "usable", "missing_print", "occluded", "ambiguous"}
SPOT_STATUSES = {"unreviewed", "locally_visible", "locally_occluded", "locally_ambiguous", "missing_print"}
LINE_IDS = tuple([f"V{i}" for i in range(11)] + [f"H{j}" for j in range(6)])
SPOT_IDS = ("G[0,0]", "G[10,0]", "G[0,5]", "G[10,5]", "G[2,2]", "G[8,2]", "G[2,3]", "G[8,3]")
DENOM_EPS = 1e-9
BOUNDS_TOL_PX = 3.0
MIN_SPAN_FRACTION = 0.5


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PACKETS = load_module(
    "cross_state_registration_packets_for_lines",
    ROOT / "scripts" / "ltpp_prepare_cross_state_registration_review_packets.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def automatic_rectangle_source(row: dict) -> dict[str, float]:
    return {
        "left": float(row["x0"]),
        "top": float(row["y0"]),
        "right": float(row["x1"]),
        "bottom": float(row["y1"]),
    }


def suggested_line(line_id: str, rect: dict[str, float]) -> list[list[float]]:
    if line_id.startswith("V"):
        x = rect["left"] + (rect["right"] - rect["left"]) * int(line_id[1:]) / 10.0
        return [[x, rect["top"]], [x, rect["bottom"]]]
    y = rect["bottom"] - (rect["bottom"] - rect["top"]) * int(line_id[1:]) / 5.0
    return [[rect["left"], y], [rect["right"], y]]


def normalised_line(points: list[list[float]]) -> np.ndarray:
    if len(points) != 2:
        raise ValueError("usable line requires exactly two points")
    first = np.asarray([*points[0], 1.0], dtype=float)
    second = np.asarray([*points[1], 1.0], dtype=float)
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("line points must be finite")
    line = np.cross(first, second)
    norm = float(np.hypot(line[0], line[1]))
    if norm < DENOM_EPS:
        raise ValueError("line points are duplicate")
    return line / norm


def line_position(line: np.ndarray, family: str, anchor: tuple[float, float]) -> float:
    if family == "V":
        y = anchor[1]
        if abs(line[0]) < DENOM_EPS:
            raise ValueError("vertical line cannot be evaluated at centre y")
        return float(-(line[1] * y + line[2]) / line[0])
    x = anchor[0]
    if abs(line[1]) < DENOM_EPS:
        raise ValueError("horizontal line cannot be evaluated at centre x")
    return float(-(line[0] * x + line[2]) / line[1])


def intersect(first: np.ndarray, second: np.ndarray) -> tuple[float, float] | None:
    point = np.cross(first, second)
    if not np.isfinite(point).all() or abs(point[2]) < DENOM_EPS:
        return None
    return float(point[0] / point[2]), float(point[1] / point[2])


def inside_rect(point: tuple[float, float], rect: dict[str, float], tolerance: float = BOUNDS_TOL_PX) -> bool:
    x, y = point
    return (
        rect["left"] - tolerance <= x <= rect["right"] + tolerance
        and rect["top"] - tolerance <= y <= rect["bottom"] + tolerance
    )


def owner_frame(lines: dict[str, np.ndarray]) -> dict | None:
    """Return the owner-observed convex outer frame, never an automatic fallback."""
    outer = ("V0", "V10", "H0", "H5")
    if any(line_id not in lines for line_id in outer):
        return None
    corners = [
        intersect(lines["V0"], lines["H0"]),
        intersect(lines["V10"], lines["H0"]),
        intersect(lines["V10"], lines["H5"]),
        intersect(lines["V0"], lines["H5"]),
    ]
    if any(point is None or not np.isfinite(point).all() for point in corners):
        return None
    points = np.asarray(corners, dtype=float)
    cross_products = []
    for index in range(4):
        first = points[(index + 1) % 4] - points[index]
        second = points[(index + 2) % 4] - points[(index + 1) % 4]
        cross_products.append(float(first[0] * second[1] - first[1] * second[0]))
    if any(abs(value) < DENOM_EPS for value in cross_products):
        return None
    if not (all(value > 0 for value in cross_products) or all(value < 0 for value in cross_products)):
        return None
    centroid = tuple(map(float, points.mean(axis=0)))
    try:
        if not line_position(lines["V0"], "V", centroid) < line_position(lines["V10"], "V", centroid):
            return None
        if not line_position(lines["H0"], "H", centroid) > line_position(lines["H5"], "H", centroid):
            return None
    except ValueError:
        return None
    return {"corners": [list(map(float, point)) for point in points], "centroid": centroid}


def inside_owner_frame(
    point: tuple[float, float], lines: dict[str, np.ndarray], frame: dict, tolerance: float = BOUNDS_TOL_PX
) -> bool:
    sample = np.asarray([point[0], point[1], 1.0], dtype=float)
    centre = np.asarray([*frame["centroid"], 1.0], dtype=float)
    for line_id in ("V0", "V10", "H0", "H5"):
        boundary = lines[line_id]
        centre_side = float(boundary @ centre)
        if abs(centre_side) < DENOM_EPS:
            return False
        signed_inward_distance = float(boundary @ sample) * (1.0 if centre_side > 0 else -1.0)
        if signed_inward_distance < -tolerance:
            return False
    return True


def validate_usable_line(line_id: str, task: dict, rect: dict[str, float], image_shape: tuple[int, int]) -> np.ndarray:
    points = task.get("points_source_px")
    line = normalised_line(points)
    height, width = image_shape
    for point in points:
        x, y = map(float, point)
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"{line_id} point outside image")
    dx = abs(float(points[1][0]) - float(points[0][0]))
    dy = abs(float(points[1][1]) - float(points[0][1]))
    if line_id.startswith("V"):
        if not (dy > dx and dy >= MIN_SPAN_FRACTION * (rect["bottom"] - rect["top"])):
            raise ValueError(f"{line_id} fails vertical orientation/span")
    elif not (dx > dy and dx >= MIN_SPAN_FRACTION * (rect["right"] - rect["left"])):
        raise ValueError(f"{line_id} fails horizontal orientation/span")
    return line


def derive_and_validate(record: dict, image_shape: tuple[int, int]) -> dict:
    rect = record["automatic_rectangle_source_px"]
    tasks = record["lines"]
    if tuple(tasks) != LINE_IDS:
        raise ValueError("line inventory/order mismatch")
    lines: dict[str, np.ndarray] = {}
    for line_id, task in tasks.items():
        status = task.get("status")
        if status not in LINE_STATUSES or status == "unreviewed":
            raise ValueError(f"{line_id} is unreviewed or invalid")
        points = task.get("points_source_px", [])
        if status == "usable":
            lines[line_id] = validate_usable_line(line_id, task, rect, image_shape)
        elif points:
            raise ValueError(f"{line_id} non-usable line retains points")

    frame = owner_frame(lines)
    automatic_anchor = ((rect["left"] + rect["right"]) / 2.0, (rect["top"] + rect["bottom"]) / 2.0)
    order_anchor = frame["centroid"] if frame is not None else automatic_anchor
    full_image = {"left": 0.0, "top": 0.0, "right": float(image_shape[1] - 1), "bottom": float(image_shape[0] - 1)}
    for family, ids in (("V", LINE_IDS[:11]), ("H", LINE_IDS[11:])):
        available = [line_id for line_id in ids if line_id in lines]
        positions = [line_position(lines[line_id], family, order_anchor) for line_id in available]
        if family == "V" and any(a >= b for a, b in zip(positions, positions[1:])):
            raise ValueError("vertical family order/crossing failure")
        if family == "H" and any(a <= b for a, b in zip(positions, positions[1:])):
            raise ValueError("horizontal family order/crossing failure")
        for index, first_id in enumerate(available):
            for second_id in available[index + 1:]:
                crossing = intersect(lines[first_id], lines[second_id])
                if crossing is not None and inside_rect(crossing, full_image, 0.0):
                    raise ValueError(f"same-family crossing inside source image: {first_id}/{second_id}")

    spots = record["spot_checks"]
    if tuple(spots) != SPOT_IDS:
        raise ValueError("spot-check inventory/order mismatch")
    if any(task.get("status") not in SPOT_STATUSES or task.get("status") == "unreviewed" for task in spots.values()):
        raise ValueError("all spot checks require review")

    derived = {}
    for j in range(6):
        for i in range(11):
            candidate = f"G[{i},{j}]"
            v_id, h_id = f"V{i}", f"H{j}"
            if v_id not in lines or h_id not in lines:
                derived[candidate] = {"status": "invalid_derived", "reason": "source_line_unusable"}
                continue
            point = intersect(lines[v_id], lines[h_id])
            if point is None:
                derived[candidate] = {"status": "invalid_derived", "reason": "near_parallel_or_nonfinite"}
                continue
            if frame is None:
                derived[candidate] = {"status": "invalid_derived", "reason": "owner_frame_unavailable"}
                continue
            if not inside_owner_frame(point, lines, frame):
                derived[candidate] = {"status": "invalid_derived", "reason": "outside_owner_frame"}
                continue
            local_status = spots[candidate]["status"] if candidate in spots else "not_spot_checked"
            evidence = (
                "derived_geometry__local_print_visible"
                if local_status == "locally_visible"
                else "derived_geometry__local_print_not_verified"
            )
            derived[candidate] = {
                "status": "derived_from_single_owner_lines",
                "point_source_px": [round(point[0], 6), round(point[1], 6)],
                "local_status": local_status,
                "evidence": evidence,
            }
    return derived


def initialize(point_packet: Path, gate_specs: list[tuple[Path, str, int]], preregistration: Path, output: Path, project_root: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite line packet: {output}")
    point_receipt = point_packet / "input_receipt.json"
    point_rows = {row["survey_date"]: row for row in json.loads(point_receipt.read_text())["inputs"]}
    gate_rows, gate_receipts = PACKETS.load_rows(project_root, gate_specs)
    if len(gate_rows) != 14 or set(point_rows) != {row["survey_date"] for row in gate_rows}:
        raise ValueError("exact 14-map point packet and gate inventory required")
    images = output / "images"
    records = output / "records"
    images.mkdir(parents=True)
    records.mkdir()
    inputs = []
    for row in gate_rows:
        date = row["survey_date"]
        point_record_path = point_packet / "records" / f"{date}.json"
        point_record = json.loads(point_record_path.read_text())
        if point_record.get("locked") or any(task["status"] != "unreviewed" for task in point_record["tasks"].values()):
            raise ValueError(f"point packet already used: {date}")
        source_image = Path(row["source_path"])
        target_image = images / f"{date}.png"
        shutil.copy2(source_image, target_image)
        image = cv2.imread(str(target_image), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"cannot read full source image: {date}")
        height, width = image.shape[:2]
        rect = automatic_rectangle_source(row)
        lines = {
            line_id: {"status": "unreviewed", "points_source_px": [], "suggested_source_px": suggested_line(line_id, rect), "note": ""}
            for line_id in LINE_IDS
        }
        spots = {spot: {"status": "unreviewed", "note": ""} for spot in SPOT_IDS}
        record = {
            "schema_version": "ltpp_cross_state_single_owner_line_annotation_full_source_v2",
            "classification": STATUS,
            "section": row["section"],
            "survey_date": date,
            "locked": False,
            "source_origin_px": [0, 0],
            "source_image_size_px": [width, height],
            "automatic_rectangle_source_px": rect,
            "lines": lines,
            "spot_checks": spots,
            "derived_intersections": {},
        }
        atomic_json(records / f"{date}.json", record)
        inputs.append({
            "section": row["section"],
            "survey_date": date,
            "source_path": str(source_image.resolve()),
            "source_width_px": width,
            "source_height_px": height,
            "image_sha256": sha256(target_image),
            "gate_source_sha256": row["source_sha256"],
        })
    receipt = {
        "status": STATUS,
        "created_at_utc": utc_now(),
        "maps": 14,
        "line_tasks_per_map": 17,
        "line_clicks_per_map": 34,
        "spot_classifications_per_map": 8,
        "derived_intersections_per_map": 66,
        "source_point_packet": str(point_packet.resolve()),
        "source_point_packet_receipt_sha256": sha256(point_receipt),
        "full_source_amendment_sha256": sha256(preregistration),
        "base_preregistration_sha256": "71cfe00b2eb46f0c797ffe57b639ef0cd539cf18ab007556346910568236ba95",
        "display_policy": "complete_original_source__no_crop__origin_0_0",
        "automatic_rectangle_role": "grey_suggestion_and_fixed_span_scale_only",
        "admissible_frame": "owner_lines_V0_V10_H0_H5__no_automatic_fallback",
        "gate_receipts": gate_receipts,
        "formal_tier_b_controls_created": False,
        "transform_fit_authorized": False,
        "final_gate_run": False,
        "inputs": inputs,
    }
    atomic_json(output / "input_receipt.json", receipt)
    manifest_files = list(images.glob("*.png")) + [output / "input_receipt.json"]
    (output / "frozen_inputs.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(output)}\n" for path in sorted(manifest_files)), encoding="ascii"
    )
    return receipt


HTML = r'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>LTPP 单人直线标注</title>
<style>*{box-sizing:border-box}body{margin:0;font:14px system-ui;background:#f3efe5;color:#17211b}header{padding:11px 16px;background:white;border-bottom:2px solid #17211b}.warn{color:#a3172a;font-weight:800}main{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:10px;padding:10px}.viewport{height:74vh;overflow:auto;background:#999;border:1px solid #222}.stage{position:relative;width:max-content;background:white}.stage img{display:block}.stage svg{position:absolute;inset:0}.side{background:#fff;padding:10px;border:1px solid #333}.tasks{display:grid;grid-template-columns:repeat(6,1fr);gap:3px;max-height:190px;overflow:auto}.task{padding:5px 2px;border:1px solid #aaa;background:#eee}.task.active{background:#ffd85a;border:2px solid #9b1c31}.task.done{background:#e3f5e9;color:#087443}.current{font-size:17px;font-weight:800;padding:8px;background:#fff0b8;margin:5px 0}.help{background:#e8f7f8;border-left:5px solid #00a7b5;padding:8px;line-height:1.45}button,select,textarea{width:100%;padding:7px;margin:4px 0}textarea{height:42px}.autoRect{fill:none;stroke:#555;stroke-width:3;stroke-dasharray:13 9}.line{stroke:#00a7b5;stroke-width:4}.suggest{stroke:#777;stroke-width:2;stroke-dasharray:9 7}.activeLine{stroke:#ff2d75;stroke-width:6}.click{fill:#ff2d75;stroke:white;stroke-width:2}.derived{fill:#19a45b;stroke:white;stroke-width:1}.spot{fill:none;stroke:#f2a900;stroke-width:5}.bad{color:#a3172a}@media(max-width:900px){main{grid-template-columns:1fr}.viewport{height:55vh}}</style></head><body>
<header><b>17 条格线 → 自动派生 66 点</b>　<span class="warn">单人 development-only，不是独立 Tier B / final controls</span></header><main><section class="viewport" id="viewport"><div class="stage"><img id="image"><svg id="overlay"></svg></div></section><aside class="side">
<div class="help"><b>当前显示完整原始 0–50 ft 页面，没有裁切。</b> 灰色虚线框/线只是自动建议，不是有效边界。先完成 V0–V10（左→右）和 H0–H5（下→上）；你标出的 V0/V10/H0/H5 决定真实外框。每条 usable 线点两个相距较远的打印中心位置，随后给 8 个橙色圆圈做局部可见性分类。</div>
<label>地图<select id="date"></select></label><div class="current" id="current"></div><div class="tasks" id="tasks"></div>
<label>状态<select id="kind"></select></label><button id="reset">重置当前线的两个点</button><textarea id="note" placeholder="可选备注"></textarea><button id="prev">← 上一个</button><button id="next">下一个 →</button><button id="save">保存当前地图草稿（S）</button><button id="lock">完成并锁定本地图</button><p id="feedback"></p>
</aside></main><script>
let dates=[],record={},current='',selected='',order=[],dirty=false;const image=document.getElementById('image'),overlay=document.getElementById('overlay'),viewport=document.getElementById('viewport'),feedback=document.getElementById('feedback');
function say(t,b=false){feedback.textContent=t;feedback.className=b?'bad':''}function isLine(id){return id[0]==='V'||id[0]==='H'}function task(){return isLine(selected)?record.lines[selected]:record.spot_checks[selected]}
function options(){return isLine(selected)?[['usable','usable（需点击两点）'],['missing_print','missing_print'],['occluded','occluded'],['ambiguous','ambiguous']]:[['locally_visible','locally_visible'],['locally_occluded','locally_occluded'],['locally_ambiguous','locally_ambiguous'],['missing_print','missing_print']]}
function lineFrom(p){const [a,b]=p;return [a[1]-b[1],b[0]-a[0],a[0]*b[1]-b[0]*a[1]]}function cross(a,b){const z=a[0]*b[1]-a[1]*b[0];if(Math.abs(z)<1e-9)return null;return [(a[1]*b[2]-a[2]*b[1])/z,(a[2]*b[0]-a[0]*b[2])/z]}
function derived(){const out={};for(let j=0;j<6;j++)for(let i=0;i<11;i++){const v=record.lines['V'+i],h=record.lines['H'+j];if(v.status==='usable'&&h.status==='usable'&&v.points_source_px.length===2&&h.points_source_px.length===2)out[`G[${i},${j}]`]=cross(lineFrom(v.points_source_px),lineFrom(h.points_source_px))}return out}
function add(tag,attrs,klass){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(klass)e.setAttribute('class',klass);overlay.appendChild(e);return e}
function render(){if(!record.lines)return;document.getElementById('tasks').innerHTML=order.map(id=>{const t=isLine(id)?record.lines[id]:record.spot_checks[id];return `<button class="task ${id===selected?'active':''} ${t.status!=='unreviewed'?'done':''}" data-id="${id}">${id}</button>`}).join('');document.querySelectorAll('.task').forEach(b=>b.onclick=()=>selectTask(b.dataset.id));overlay.innerHTML='';overlay.setAttribute('width',image.naturalWidth);overlay.setAttribute('height',image.naturalHeight);overlay.setAttribute('viewBox',`0 0 ${image.naturalWidth} ${image.naturalHeight}`);const r=record.automatic_rectangle_source_px;add('rect',{x:r.left,y:r.top,width:r.right-r.left,height:r.bottom-r.top},'autoRect');for(const [id,t] of Object.entries(record.lines)){const p=t.points_source_px.length===2?t.points_source_px:t.suggested_source_px;add('line',{x1:p[0][0],y1:p[0][1],x2:p[1][0],y2:p[1][1]},id===selected?'activeLine':(t.points_source_px.length===2?'line':'suggest'));for(const q of t.points_source_px)add('circle',{cx:q[0],cy:q[1],r:7},'click')}const pts=derived();for(const [id,p] of Object.entries(pts)){if(!p)continue;add('circle',{cx:p[0],cy:p[1],r:id===selected?15:4},id===selected?'spot':'derived')}}
function selectTask(id){selected=id;const t=task();document.getElementById('current').textContent=`${record.section} ${current}　${id}`;const kind=document.getElementById('kind');kind.innerHTML=options().map(x=>`<option value="${x[0]}">${x[1]}</option>`).join('');kind.value=t.status==='unreviewed'?options()[0][0]:t.status;document.getElementById('reset').style.display=isLine(id)?'block':'none';document.getElementById('note').value=t.note||'';render();const p=isLine(id)?(t.points_source_px[0]||t.suggested_source_px[0]):derived()[id];if(p)viewport.scrollTo({left:Math.max(0,p[0]-viewport.clientWidth/2),top:Math.max(0,p[1]-viewport.clientHeight/2),behavior:'smooth'})}
async function load(date){current=date;record=await fetch('/api/record/'+date).then(r=>r.json());dirty=false;order=[...Object.keys(record.lines),...Object.keys(record.spot_checks)];document.getElementById('date').value=date;image.src='/image/'+date+'?v='+Date.now();image.onload=()=>selectTask(order[0]);document.getElementById('lock').disabled=record.locked}
overlay.onclick=e=>{if(record.locked||!isLine(selected))return;const r=image.getBoundingClientRect(),t=task(),p=[Math.round((e.clientX-r.left)*image.naturalWidth/r.width),Math.round((e.clientY-r.top)*image.naturalHeight/r.height)];if(t.points_source_px.length>=2)t.points_source_px=[];t.points_source_px.push(p);t.status=t.points_source_px.length===2?'usable':'unreviewed';dirty=true;render();say(t.points_source_px.length===2?'两点完成，可继续下一条线':'请点击同一条线的第二个远端位置')};
document.getElementById('kind').onchange=e=>{const t=task();t.status=e.target.value;if(isLine(selected)&&t.status!=='usable')t.points_source_px=[];dirty=true;render()};document.getElementById('reset').onclick=()=>{const t=task();t.points_source_px=[];t.status='unreviewed';dirty=true;render()};document.getElementById('note').oninput=e=>{task().note=e.target.value;dirty=true};function step(d){const n=order.indexOf(selected)+d;if(n>=0&&n<order.length)selectTask(order[n])}document.getElementById('prev').onclick=()=>step(-1);document.getElementById('next').onclick=()=>step(1);
async function save(lock=false){const r=await fetch('/api/record/'+current,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(record)});if(!r.ok)return say(await r.text(),true);if(lock){const q=await fetch('/api/lock/'+current,{method:'POST'});if(!q.ok)return say(await q.text(),true)}await load(current);say(lock?'地图已锁定':'草稿已保存')};document.getElementById('save').onclick=()=>save(false);document.getElementById('lock').onclick=()=>{if(confirm('锁定后不可修改，确定？'))save(true)};document.getElementById('date').onchange=e=>{if(dirty){e.target.value=current;return say('请先保存当前地图',true)}load(e.target.value)};window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue=''}});document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA'||e.target.tagName==='SELECT')return;if(e.key==='s'){e.preventDefault();save(false)}else if(e.key==='ArrowRight'||e.key==='n'){e.preventDefault();step(1)}else if(e.key==='ArrowLeft'||e.key==='p'){e.preventDefault();step(-1)}else if(!isLine(selected)&&['1','2','3','4'].includes(e.key)){e.preventDefault();const o=options()[+e.key-1][0];document.getElementById('kind').value=o;document.getElementById('kind').dispatchEvent(new Event('change'));step(1)}});(async()=>{dates=await fetch('/api/dates').then(r=>r.json());document.getElementById('date').innerHTML=dates.map(d=>`<option>${d}</option>`).join('');await load(dates[0])})();
</script></body></html>'''


class Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], packet: Path):
        super().__init__(address, Handler)
        self.root = packet.resolve()
        self.images = self.root / "images"
        self.records = self.root / "records"
        self.dates = tuple(sorted(path.stem for path in self.records.glob("*.json")))
        if len(self.dates) != 14:
            raise ValueError("line packet must contain exactly 14 maps")


class Handler(BaseHTTPRequestHandler):
    server: Server

    def send_payload(self, payload: bytes, kind: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def fail(self, message: str, status: int = 400) -> None:
        self.send_payload(message.encode(), "text/plain; charset=utf-8", status)

    def date_from(self, prefix: str) -> str | None:
        value = urlparse(self.path).path.removeprefix(prefix)
        return value if value in self.server.dates else None

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            return self.send_payload(HTML.encode(), "text/html; charset=utf-8")
        if path == "/api/dates":
            return self.send_payload(json.dumps(self.server.dates).encode(), "application/json")
        if path.startswith("/api/record/"):
            date = self.date_from("/api/record/")
            return self.send_payload((self.server.records / f"{date}.json").read_bytes(), "application/json") if date else self.fail("invalid date", 404)
        if path.startswith("/image/"):
            date = self.date_from("/image/")
            return self.send_payload((self.server.images / f"{date}.png").read_bytes(), "image/png") if date else self.fail("invalid date", 404)
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/record/"):
            date = self.date_from("/api/record/")
            if not date:
                return self.fail("invalid date", 404)
            destination = self.server.records / f"{date}.json"
            current = json.loads(destination.read_text())
            if current.get("locked"):
                return self.fail("record is locked", 409)
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            except (ValueError, json.JSONDecodeError):
                return self.fail("invalid JSON")
            if payload.get("survey_date") != date or tuple(payload.get("lines", {})) != LINE_IDS or tuple(payload.get("spot_checks", {})) != SPOT_IDS:
                return self.fail("task inventory mismatch")
            for task in payload["lines"].values():
                if task.get("status") not in LINE_STATUSES:
                    return self.fail("invalid line status")
                points = task.get("points_source_px")
                if not isinstance(points, list) or len(points) > 2:
                    return self.fail("invalid line points")
            for task in payload["spot_checks"].values():
                if task.get("status") not in SPOT_STATUSES:
                    return self.fail("invalid spot status")
            atomic_json(destination, payload)
            return self.send_payload(b'{"saved":true}', "application/json")
        if path.startswith("/api/lock/"):
            date = self.date_from("/api/lock/")
            if not date:
                return self.fail("invalid date", 404)
            destination = self.server.records / f"{date}.json"
            payload = json.loads(destination.read_text())
            if payload.get("locked"):
                return self.fail("record already locked", 409)
            image = cv2.imread(str(self.server.images / f"{date}.png"), cv2.IMREAD_GRAYSCALE)
            try:
                payload["derived_intersections"] = derive_and_validate(payload, image.shape[:2])
            except ValueError as error:
                return self.fail(str(error))
            payload["locked"] = True
            payload["locked_at_utc"] = utc_now()
            atomic_json(destination, payload)
            return self.send_payload(b'{"locked":true}', "application/json")
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--point-packet", type=Path)
    parser.add_argument("--gate", action="append", type=PACKETS.parse_gate_spec)
    parser.add_argument("--preregistration", type=Path)
    parser.add_argument("--project-root", type=Path, default=ROOT.parent)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8772)
    args = parser.parse_args()
    if args.initialize:
        if args.point_packet is None or not args.gate or args.preregistration is None:
            parser.error("--initialize requires --point-packet, --gate, and --preregistration")
        initialize(args.point_packet.resolve(), args.gate, args.preregistration.resolve(), args.packet_root.resolve(), args.project_root.resolve())
    server = Server((args.host, args.port), args.packet_root)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", "status": STATUS, "maps": len(server.dates)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
