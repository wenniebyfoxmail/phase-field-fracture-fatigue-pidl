#!/usr/bin/env python3
"""Exploratory geometry-assisted 66-point review UI; never a Tier B control source."""

from __future__ import annotations

import argparse
import hashlib
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


DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)
POST1991_DATES = DATES[1:]
EXPECTED_OWNER_SHA256 = "3f86fc7c0d28d578387d5e8d99295faf8e9bc4d45e437f4d1e181940e96a4803"
MARGIN_PX = 48
STATUS = "EXPLORATORY_AI_ASSISTED_CONTROL_PILOT__NOT_INDEPENDENT"
VALID_STATUSES = {"usable", "missing_print", "occluded", "ambiguous", "unreviewed"}
DEVELOPMENT = ((5, 0), (5, 5), (0, 2), (0, 3), (10, 2), (10, 3), (3, 1), (7, 4))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def candidate_id(i: int, j: int) -> str:
    return f"G[{i},{j}]"


def task_order(profile: str = "all66") -> list[str]:
    if profile == "development8":
        return [candidate_id(i, j) for i, j in DEVELOPMENT]
    if profile != "all66":
        raise ValueError(f"unknown task profile: {profile}")
    return [candidate_id(i, j) for j in range(5, -1, -1) for i in range(11)]


def crop_bounds(points: list[list[float]], shape: tuple[int, ...]) -> tuple[int, int, int, int]:
    height, width = shape[:2]
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (
        max(0, math.floor(min(xs)) - MARGIN_PX),
        max(0, math.floor(min(ys)) - MARGIN_PX),
        min(width, math.ceil(max(xs)) + MARGIN_PX + 1),
        min(height, math.ceil(max(ys)) + MARGIN_PX + 1),
    )


def suggested_source_points(points: list[list[float]]) -> dict[str, list[float]]:
    source = np.asarray(points, dtype=np.float32)
    if source.shape != (4, 2):
        raise ValueError("four TL/TR/BR/BL points are required")
    logical_corners = np.asarray(((0, 0), (1, 0), (1, 1), (0, 1)), dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(logical_corners, source)
    result = {}
    for j in range(6):
        for i in range(11):
            logical = np.asarray([[[i / 10.0, (5 - j) / 5.0]]], dtype=np.float32)
            x, y = cv2.perspectiveTransform(logical, matrix)[0, 0]
            result[candidate_id(i, j)] = [round(float(x), 3), round(float(y), 3)]
    return result


def atomic_json(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def initialize(
    owner_packet: Path,
    pilot_root: Path,
    preregistration: Path,
    profile: str = "all66",
    dates: tuple[str, ...] = DATES,
) -> None:
    if pilot_root.exists():
        raise ValueError(f"refusing to overwrite pilot: {pilot_root}")
    owner_file = owner_packet / "owner_corners.json"
    if sha256(owner_file) != EXPECTED_OWNER_SHA256:
        raise ValueError("unexpected owner-corner receipt")
    owner = json.loads(owner_file.read_text(encoding="utf-8"))
    records = {row["survey_date"]: row for row in owner["records"]}
    if tuple(records) != DATES or any(not records[date].get("locked") for date in dates):
        raise ValueError("exact locked eight-date owner packet required")
    images = pilot_root / "images"
    record_dir = pilot_root / "records"
    images.mkdir(parents=True)
    record_dir.mkdir()
    input_rows = []
    for date in dates:
        record = records[date]
        source_path = owner_packet / "images" / f"{date}.png"
        if sha256(source_path) != record["source_sha256"]:
            raise ValueError(f"source hash mismatch: {date}")
        image = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"cannot read source: {date}")
        left, top, right, bottom = crop_bounds(record["points_source_px"], image.shape)
        target = images / f"{date}.png"
        if not cv2.imwrite(str(target), image[top:bottom, left:right]):
            raise ValueError(f"cannot write pilot image: {date}")
        suggestions = suggested_source_points(record["points_source_px"])
        tasks = {}
        for candidate in task_order(profile):
            source_x, source_y = suggestions[candidate]
            crop_point = [round(source_x - left, 3), round(source_y - top, 3)]
            tasks[candidate] = {
                "status": "unreviewed",
                "suggested_crop_px": crop_point,
                "reviewed_crop_px": crop_point,
                "note": "",
            }
        atomic_json(record_dir / f"{date}.json", {
            "schema_version": "ltpp_geometry_assisted_grid_control_pilot_v1",
            "classification": STATUS,
            "survey_date": date,
            "task_profile": profile,
            "locked": False,
            "crop_source_px": {"left": left, "top": top, "right": right, "bottom": bottom},
            "tasks": tasks,
        })
        input_rows.append({
            "survey_date": date,
            "source_sha256": record["source_sha256"],
            "pilot_image_sha256": sha256(target),
            "crop_source_px": {"left": left, "top": top, "right": right, "bottom": bottom},
        })
    atomic_json(pilot_root / "input_receipt.json", {
        "status": STATUS,
        "created_at_utc": utc_now(),
        "owner_corners_sha256": sha256(owner_file),
        "preregistration_sha256": sha256(preregistration),
        "assistance": "four-corner projective suggestion only; human-adjusted development pilot",
        "task_profile": profile,
        "task_ids": task_order(profile),
        "dates": list(dates),
        "formal_tier_b_controls_created": False,
        "final_gate_run": False,
        "inputs": input_rows,
    })


HTML = r'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>格网点辅助校正 Pilot</title>
<style>*{box-sizing:border-box}body{margin:0;font:15px system-ui;background:#f3efe5;color:#17211b}header{padding:12px 18px;background:white;border-bottom:2px solid #17211b}.warn{color:#a3172a;font-weight:800}main{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:12px;padding:12px}.viewport{height:72vh;overflow:auto;border:1px solid #333;background:#999}.stage{position:relative;width:max-content;background:white}.stage img{display:block}.stage svg{position:absolute;inset:0}.side{background:#fff;padding:12px;border:1px solid #333}.legend{padding:10px;background:#e9f8f8;border-left:6px solid #00a7b5;line-height:1.55}.current{font-size:18px;font-weight:800;padding:10px;background:#fff0b8}.tasks{height:260px;overflow:auto;display:grid;grid-template-columns:repeat(6,1fr);gap:3px}.task{padding:5px 2px;border:1px solid #bbb;background:#eee;cursor:pointer;font-size:12px}.task.active{background:#ffdc56;border:2px solid #9b1c31}.task.done{color:#087443;background:#e5f6ec}button,select,textarea{width:100%;margin:5px 0;padding:8px}textarea{height:48px}.rowcol{stroke-width:4;stroke-dasharray:12 8;opacity:.72}.dot{fill:#18a55b;stroke:white;stroke-width:2}.activeDot{fill:#ff2d75;stroke:#111;stroke-width:4}.label{font:700 22px system-ui;fill:#9b1c31;paint-order:stroke;stroke:white;stroke-width:5px}.footer{font-size:12px;color:#666}@media(max-width:900px){main{grid-template-columns:1fr}.viewport{height:55vh}}</style></head><body>
<header><b>格网点几何辅助校正 Pilot</b>　<span class="warn">开发期辅助记录，不是独立 Tier B / final controls</span></header>
<main><section class="viewport" id="viewport"><div class="stage"><img id="image"><svg id="overlay"></svg></div></section><aside class="side">
<div class="legend"><b>先认方向：</b><br>① <b>i = 横向位置</b>，从左→右 0–10，对应竖直打印线。<br>② <b>j = 纵向位置</b>，从下→上 0–5，对应水平打印线。<br>粉色点是当前目标；青色竖导线显示 i，橙色横导线显示 j。</div>
<label>日期<select id="date"></select></label><div class="current" id="current"></div><div class="tasks" id="tasks"></div>
<button id="accept">建议点正确 → usable</button><label>或标记<select id="kind"><option value="usable">usable（点击图像可移动）</option><option value="missing_print">missing_print</option><option value="occluded">occluded</option><option value="ambiguous">ambiguous</option></select></label>
<textarea id="note" placeholder="可选备注"></textarea><button id="prev">← 上一个</button><button id="next">下一个 →</button><button id="save">保存当前日期草稿</button><button id="lock">完成当前任务并锁定本日期</button><p id="feedback"></p><p class="footer">绿色小点=几何建议；点击图像会把当前粉色点移动到你的点击位置。只校正打印格网，不沿裂缝找点。</p>
</aside></main><script>
let dates=[],record={},current='',selected='',order=[];const image=document.getElementById('image'),overlay=document.getElementById('overlay'),feedback=document.getElementById('feedback'),viewport=document.getElementById('viewport');
function parseId(id){const m=id.match(/G\[(\d+),(\d+)\]/);return [+m[1],+m[2]]}function say(t,bad=false){feedback.textContent=t;feedback.style.color=bad?'#a3172a':'#087443'}
function selectTask(id){selected=id;const [i,j]=parseId(id);document.getElementById('current').innerHTML=`${id}<br><small>i=${i}：左→右第 ${i+1} 条竖线　|　j=${j}：下→上第 ${j+1} 条横线</small>`;const t=record.tasks[id];document.getElementById('kind').value=t.status==='unreviewed'?'usable':t.status;document.getElementById('note').value=t.note||'';render();const p=t.reviewed_crop_px;viewport.scrollTo({left:Math.max(0,p[0]-viewport.clientWidth/2),top:Math.max(0,p[1]-viewport.clientHeight/2),behavior:'smooth'})}
function render(){if(!record.tasks)return;document.getElementById('tasks').innerHTML=order.map(id=>`<button class="task ${id===selected?'active':''} ${record.tasks[id].status!=='unreviewed'?'done':''}" data-id="${id}">${id.replace('G','')}</button>`).join('');document.querySelectorAll('.task').forEach(b=>b.onclick=()=>selectTask(b.dataset.id));overlay.innerHTML='';overlay.setAttribute('width',image.naturalWidth);overlay.setAttribute('height',image.naturalHeight);overlay.setAttribute('viewBox',`0 0 ${image.naturalWidth} ${image.naturalHeight}`);for(const id of order){const t=record.tasks[id],p=t.reviewed_crop_px,c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',p[0]);c.setAttribute('cy',p[1]);c.setAttribute('r',id===selected?14:5);c.setAttribute('class',id===selected?'activeDot':'dot');overlay.appendChild(c)}if(selected){const p=record.tasks[selected].reviewed_crop_px;for(const [x1,y1,x2,y2,color] of [[p[0],0,p[0],image.naturalHeight,'#00b7c7'],[0,p[1],image.naturalWidth,p[1],'#ff8a00']]){const l=document.createElementNS('http://www.w3.org/2000/svg','line');for(const [k,v] of Object.entries({x1,y1,x2,y2}))l.setAttribute(k,v);l.setAttribute('stroke',color);l.setAttribute('class','rowcol');overlay.appendChild(l)}const tx=document.createElementNS('http://www.w3.org/2000/svg','text');tx.setAttribute('x',p[0]+18);tx.setAttribute('y',p[1]-18);tx.setAttribute('class','label');tx.textContent=selected;overlay.appendChild(tx)}}
async function load(date){current=date;record=await fetch('/api/record/'+date).then(r=>r.json());order=Object.keys(record.tasks);image.src='/image/'+date+'?v='+Date.now();image.onload=()=>{selectTask(order[0])};document.getElementById('lock').disabled=record.locked}
overlay.onclick=e=>{if(record.locked||!selected)return;const r=image.getBoundingClientRect();record.tasks[selected].reviewed_crop_px=[Math.round((e.clientX-r.left)*image.naturalWidth/r.width),Math.round((e.clientY-r.top)*image.naturalHeight/r.height)];record.tasks[selected].status='usable';render();say(selected+' 已移动并标为 usable')};
document.getElementById('accept').onclick=()=>{record.tasks[selected].status='usable';render();say(selected+' 接受建议点')};document.getElementById('kind').onchange=e=>{record.tasks[selected].status=e.target.value;render()};document.getElementById('note').oninput=e=>record.tasks[selected].note=e.target.value;
function step(d){const n=order.indexOf(selected)+d;if(n>=0&&n<order.length)selectTask(order[n])}document.getElementById('prev').onclick=()=>step(-1);document.getElementById('next').onclick=()=>step(1);
async function save(lock=false){const r=await fetch('/api/record/'+current,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(record)});if(!r.ok)return say(await r.text(),true);if(lock){const q=await fetch('/api/lock/'+current,{method:'POST'});if(!q.ok)return say(await q.text(),true)}await load(current);say(lock?'本日期已锁定':'草稿已保存')}
document.getElementById('save').onclick=()=>save(false);document.getElementById('lock').onclick=()=>{if(Object.values(record.tasks).some(t=>t.status==='unreviewed'))return say('仍有未审阅点',true);if(confirm('锁定本日期？'))save(true)};document.getElementById('date').onchange=e=>load(e.target.value);
(async()=>{dates=await fetch('/api/dates').then(r=>r.json());document.getElementById('date').innerHTML=dates.map(d=>`<option>${d}</option>`).join('');await load(dates[0])})();
</script></body></html>'''


class Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], pilot_root: Path):
        super().__init__(address, Handler)
        self.root = pilot_root.resolve()
        self.images = self.root / "images"
        self.records = self.root / "records"
        self.dates = tuple(sorted(path.stem for path in self.records.glob("*.json")))
        if not self.dates or any(date not in DATES for date in self.dates):
            raise ValueError("pilot must contain a nonempty frozen date subset")


class Handler(BaseHTTPRequestHandler):
    server: Server

    def send(self, payload: bytes, kind: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def fail(self, message: str, status: int = 400) -> None:
        self.send(message.encode(), "text/plain; charset=utf-8", status)

    def date_from(self, prefix: str) -> str | None:
        value = urlparse(self.path).path.removeprefix(prefix)
        return value if value in self.server.dates else None

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            return self.send(HTML.encode(), "text/html; charset=utf-8")
        if path == "/api/dates":
            return self.send(json.dumps(self.server.dates).encode(), "application/json")
        if path.startswith("/api/record/"):
            date = self.date_from("/api/record/")
            return self.send((self.server.records / f"{date}.json").read_bytes(), "application/json") if date else self.fail("invalid date", 404)
        if path.startswith("/image/"):
            date = self.date_from("/image/")
            return self.send((self.server.images / f"{date}.png").read_bytes(), "image/png") if date else self.fail("invalid date", 404)
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
            if payload.get("survey_date") != date or set(payload.get("tasks", {})) != set(current["tasks"]):
                return self.fail("task inventory mismatch")
            for task in payload["tasks"].values():
                if task.get("status") not in VALID_STATUSES:
                    return self.fail("invalid status")
                point = task.get("reviewed_crop_px")
                if not isinstance(point, list) or len(point) != 2 or not all(isinstance(value, (int, float)) for value in point):
                    return self.fail("invalid reviewed point")
            atomic_json(destination, payload)
            return self.send(b'{"saved":true}', "application/json")
        if path.startswith("/api/lock/"):
            date = self.date_from("/api/lock/")
            if not date:
                return self.fail("invalid date", 404)
            destination = self.server.records / f"{date}.json"
            payload = json.loads(destination.read_text())
            if any(task["status"] == "unreviewed" for task in payload["tasks"].values()):
                return self.fail("all tasks require review")
            payload["locked"] = True
            payload["locked_at_utc"] = utc_now()
            atomic_json(destination, payload)
            return self.send(b'{"locked":true}', "application/json")
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-packet", type=Path, required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--profile", choices=("all66", "development8"), default="all66")
    parser.add_argument("--date-profile", choices=("all8", "post1991_7"), default="all8")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    dates = DATES if args.date_profile == "all8" else POST1991_DATES
    if args.initialize:
        initialize(args.owner_packet.resolve(), args.pilot_root.resolve(), args.preregistration.resolve(), args.profile, dates)
    server = Server((args.host, args.port), args.pilot_root)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", "status": STATUS, "dates": len(server.dates)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
