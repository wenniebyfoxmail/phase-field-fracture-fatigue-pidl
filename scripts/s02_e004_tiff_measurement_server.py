#!/usr/bin/env python3
"""Local blind measurement UI for an S02-E004 round directory.

The server is deliberately packet-only: it neither accepts nor reads the sealed
directory, source ZIPs, workbooks, specimen IDs, cycles, or cross-round keys.
TIFFs are decoded by Pillow and streamed as lossless PNGs for browser display;
coordinates are stored in the original 4112 x 3008 TIFF pixel system.
"""

from __future__ import annotations

import argparse
import csv
from io import BytesIO
import json
import math
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import urllib.parse

from PIL import Image


FIELDS = [
    "blind_id", "image_file", "visibility_status", "ruler_start_px",
    "ruler_end_px", "ruler_span_mm", "reference_plane_x_px", "tip_x_px",
    "projected_length_mm", "operator_notes",
]
NUMERIC_FIELDS = [
    "ruler_start_px", "ruler_end_px", "ruler_span_mm",
    "reference_plane_x_px", "tip_x_px", "projected_length_mm",
]
STATUSES = {"resolved", "ambiguous", "not_visible"}


def read_rows(round_dir: Path) -> list[dict[str, str]]:
    path = round_dir / "annotations.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"unexpected annotation schema: {reader.fieldnames}")
        rows = list(reader)
    if len(rows) != 15 or len({row["blind_id"] for row in rows}) != 15:
        raise ValueError("annotation table must contain 15 unique blind IDs")
    for row in rows:
        if row["image_file"] != f"m_{row['blind_id']}.tif":
            raise ValueError(f"blind ID/image mismatch: {row['blind_id']}")
        if not (round_dir / row["image_file"]).is_file():
            raise FileNotFoundError(round_dir / row["image_file"])
    expected = {row["image_file"] for row in rows}
    actual = {path.name for path in round_dir.glob("*.tif")}
    if actual != expected:
        raise ValueError("TIFF set does not match annotations.csv")
    return rows


def image_geometry(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        if image.format != "TIFF":
            raise ValueError(f"not a TIFF: {path.name}")
        image.load()
        if image.mode != "L":
            raise ValueError(f"unexpected image mode: {path.name} {image.mode}")
        return image.size


def parse_finite(payload: dict, field: str) -> float:
    value = float(payload[field])
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def validate_measurement(payload: dict, expected: dict[str, str], width: int) -> dict[str, str]:
    if payload.get("blind_id") != expected["blind_id"] or payload.get("image_file") != expected["image_file"]:
        raise ValueError("annotation identity is immutable")
    status = str(payload.get("visibility_status", "")).strip()
    if status not in STATUSES:
        raise ValueError("choose resolved, ambiguous, or not_visible")
    output = {field: "" for field in FIELDS}
    output["blind_id"] = expected["blind_id"]
    output["image_file"] = expected["image_file"]
    output["visibility_status"] = status
    output["operator_notes"] = str(payload.get("operator_notes", "")).replace("\r", " ").replace("\n", " ").strip()
    if status != "resolved":
        return output
    values = {field: parse_finite(payload, field) for field in NUMERIC_FIELDS}
    for field in ("ruler_start_px", "ruler_end_px", "reference_plane_x_px", "tip_x_px"):
        if not 0 <= values[field] < width:
            raise ValueError(f"{field} is outside the source image")
    ruler_pixels = abs(values["ruler_end_px"] - values["ruler_start_px"])
    if ruler_pixels <= 0 or values["ruler_span_mm"] <= 0 or values["projected_length_mm"] < 0:
        raise ValueError("invalid ruler or projected length")
    computed = abs(values["tip_x_px"] - values["reference_plane_x_px"]) * values["ruler_span_mm"] / ruler_pixels
    if abs(computed - values["projected_length_mm"]) > 0.01:
        raise ValueError("projected length does not match the frozen formula within 0.01 mm")
    for field in NUMERIC_FIELDS:
        output[field] = f"{values[field]:.6f}".rstrip("0").rstrip(".")
    return output


def atomic_write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def png_bytes(path: Path) -> bytes:
    with Image.open(path) as image:
        if image.format != "TIFF":
            raise ValueError("source image is not TIFF")
        image.load()
        original = image.tobytes()
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=False)
        buffer.seek(0)
        with Image.open(buffer) as check:
            check.load()
            if check.size != image.size or check.mode != image.mode or check.tobytes() != original:
                raise ValueError("lossless browser rendering identity check failed")
        return buffer.getvalue()


HTML = r'''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>S02-E004 TIFF 盲测量</title><style>
*{box-sizing:border-box}body{margin:0;font:14px system-ui;background:#eef2f5;color:#17212b}
header{height:58px;background:#15202b;color:white;display:flex;align-items:center;padding:0 16px;gap:16px}
header b{font-size:17px}.badge{background:#334554;padding:5px 9px;border-radius:12px}
main{display:grid;grid-template-columns:minmax(600px,1fr) 330px;height:calc(100vh - 58px)}
#view{overflow:auto;background:#20262c;padding:14px;position:relative}#stage{position:relative;margin:auto;transform-origin:top left}
#img{display:block;width:100%;height:auto}.line{position:absolute;top:0;bottom:0;width:2px;pointer-events:none}.line span{position:absolute;top:5px;left:4px;background:#111c;color:white;padding:2px 5px;border-radius:3px;white-space:nowrap}
#rs,#re{background:#f2c94c}#ref{background:#2d9cdb}#tip{background:#eb5757}
aside{padding:15px;background:white;overflow:auto;border-left:1px solid #ccd4dc}label{display:block;margin:11px 0 4px;font-weight:600}
input,select,textarea,button{width:100%;padding:8px;border:1px solid #aeb9c3;border-radius:5px;font:inherit}textarea{height:60px}
.buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.buttons button{background:#e7edf2}.point.active{outline:3px solid #4f87ff;background:#dce9ff}
#save{background:#1769aa;color:white;border:0;font-weight:700;margin-top:12px}#msg{min-height:40px;margin-top:10px;padding:8px;background:#f2f5f7;border-radius:5px}
.nav{display:flex;gap:8px}.nav button{width:auto;flex:1}.small{font-size:12px;color:#52616f}.done{color:#19733b}.pending{color:#955400}
</style></head><body><header><b>S02-E004 匿名 TIFF 测量</b><span class="badge" id="counter"></span><span class="badge">原始像素坐标 · 无密封区访问</span></header>
<main><div id="view"><div id="stage"><img id="img"><div class="line" id="rs"><span>尺起点</span></div><div class="line" id="re"><span>尺终点</span></div><div class="line" id="ref"><span>参考面</span></div><div class="line" id="tip"><span>裂尖</span></div></div></div>
<aside><div class="nav"><button id="prev">← 上一张</button><button id="next">下一张 →</button></div>
<label>匿名任务</label><div id="identity"></div><div id="progress" class="small"></div>
<label>可见性</label><select id="status"><option value="">请选择</option><option value="resolved">resolved：裂尖可判定</option><option value="ambiguous">ambiguous：裂尖有歧义</option><option value="not_visible">not_visible：不可见</option></select>
<div id="measure"><label>选择坐标（点击按钮，再点击图像）</label><div class="buttons"><button class="point" data-key="ruler_start_px">1 尺起点</button><button class="point" data-key="ruler_end_px">2 尺终点</button><button class="point" data-key="reference_plane_x_px">3 参考面</button><button class="point" data-key="tip_x_px">4 最远可见裂尖</button></div>
<div class="small" id="coords"></div><label>上述两个尺刻度之间的真实跨度（mm）</label><input id="span" type="number" min="0" step="any" placeholder="例如 10">
<label>自动计算的投影裂缝长度（mm）</label><input id="length" readonly></div>
<label>操作备注</label><textarea id="notes" placeholder="可留空；仅记录可见性或定位困难"></textarea>
<button id="save">保存当前张</button><div id="msg">先选择可见性；resolved 时依次点四个位置。</div>
<p class="small">黄色：尺标区间；蓝色：加载线/左参考面；红色：最远可见裂尖。坐标始终换算回原 TIFF 像素，不受窗口缩放影响。</p></aside></main>
<script>
let tasks=[],i=0,active='',points={};
const $=id=>document.getElementById(id), keys=['ruler_start_px','ruler_end_px','reference_plane_x_px','tip_x_px'];
const lineIds={ruler_start_px:'rs',ruler_end_px:'re',reference_plane_x_px:'ref',tip_x_px:'tip'};
async function boot(){tasks=await (await fetch('/api/tasks')).json();const q=new URLSearchParams(location.search);i=Math.max(0,tasks.findIndex(x=>x.blind_id===q.get('id')));if(i<0)i=0;show()}
function show(){const t=tasks[i];$('counter').textContent=`${i+1} / ${tasks.length}`;$('identity').textContent=t.blind_id;$('progress').textContent=`已填写 ${tasks.filter(x=>x.visibility_status).length} / ${tasks.length}`;$('status').value=t.visibility_status||'';$('span').value=t.ruler_span_mm||'';$('notes').value=t.operator_notes||'';points={};keys.forEach(k=>{if(t[k]!==''&&t[k]!=null)points[k]=Number(t[k])});$('img').src='/image/'+encodeURIComponent(t.blind_id);$('img').onload=layout;update();history.replaceState(null,'','?id='+encodeURIComponent(t.blind_id))}
function layout(){const max=Math.max(400,$('view').clientWidth-28),w=$('img').naturalWidth;$('stage').style.width=Math.min(max,w)+'px';update()}
function update(){const resolved=$('status').value==='resolved';$('measure').style.display=resolved?'block':'none';const span=Number($('span').value),rp=points.reference_plane_x_px,tp=points.tip_x_px,rs=points.ruler_start_px,re=points.ruler_end_px;let len='';if(resolved&&span>0&&[rp,tp,rs,re].every(Number.isFinite)&&rs!==re)len=Math.abs(tp-rp)*span/Math.abs(re-rs);$('length').value=Number.isFinite(len)?len.toFixed(6):'';$('coords').textContent=keys.map(k=>`${k.replace('_px','')}: ${Number.isFinite(points[k])?points[k].toFixed(2):'—'}`).join(' | ');keys.forEach(k=>{const el=$(lineIds[k]),x=points[k];el.style.display=resolved&&Number.isFinite(x)?'block':'none';if(Number.isFinite(x))el.style.left=(x/$('img').naturalWidth*100)+'%'});document.querySelectorAll('.point').forEach(b=>b.classList.toggle('active',b.dataset.key===active))}
document.querySelectorAll('.point').forEach(b=>b.onclick=()=>{active=b.dataset.key;update()});
$('stage').onclick=e=>{if(!active||$('status').value!=='resolved')return;const r=$('img').getBoundingClientRect();if(e.clientX<r.left||e.clientX>=r.right||e.clientY<r.top||e.clientY>=r.bottom)return;points[active]=(e.clientX-r.left)*$('img').naturalWidth/r.width;active='';update()};
$('status').onchange=()=>{if($('status').value!=='resolved'){points={};$('span').value=''}update()};$('span').oninput=update;
let busy=false;function controls(disabled){$('save').disabled=disabled;$('prev').disabled=disabled;$('next').disabled=disabled}
async function save(){if(busy)return;busy=true;controls(true);const saveId=tasks[i].blind_id,t={...tasks[i]},status=$('status').value,p={blind_id:t.blind_id,image_file:t.image_file,visibility_status:status,operator_notes:$('notes').value};if(status==='resolved'){keys.forEach(k=>p[k]=points[k]);p.ruler_span_mm=Number($('span').value);p.projected_length_mm=Number($('length').value)}try{const res=await fetch('/api/annotation/'+encodeURIComponent(saveId),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});const txt=await res.text();if(!res.ok){$('msg').textContent='未保存：'+txt;return}tasks=await (await fetch('/api/tasks')).json();i=tasks.findIndex(x=>x.blind_id===saveId);if(i<0)throw new Error('保存后找不到原任务');show();$('msg').innerHTML='<span class="done">已保存并通过算术校验。</span>'}catch(e){$('msg').textContent='未保存：'+e.message}finally{busy=false;controls(false)}}
$('save').onclick=save;$('prev').onclick=()=>{i=(i+tasks.length-1)%tasks.length;show()};$('next').onclick=()=>{i=(i+1)%tasks.length;show()};window.onresize=layout;boot();
</script></body></html>'''


class Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], round_dir: Path):
        self.round_dir = round_dir
        self.rows = read_rows(round_dir)
        self.by_id = {row["blind_id"]: row for row in self.rows}
        self.geometry = {row["blind_id"]: image_geometry(round_dir / row["image_file"]) for row in self.rows}
        self.write_lock = threading.Lock()
        super().__init__(address, Handler)

    def refresh(self) -> None:
        self.rows = read_rows(self.round_dir)
        self.by_id = {row["blind_id"]: row for row in self.rows}


class Handler(BaseHTTPRequestHandler):
    server: Server

    def send(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def fail(self, message: str, status: int = 400) -> None:
        self.send(message.encode("utf-8"), "text/plain; charset=utf-8", status)

    def blind_id(self, prefix: str) -> str | None:
        value = urllib.parse.unquote(urllib.parse.urlparse(self.path).path.removeprefix(prefix))
        return value if value in self.server.by_id else None

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            return self.send(HTML.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/tasks":
            self.server.refresh()
            return self.send(json.dumps(self.server.rows).encode("utf-8"), "application/json")
        if path.startswith("/image/"):
            blind_id = self.blind_id("/image/")
            if not blind_id:
                return self.fail("unknown blind ID", HTTPStatus.NOT_FOUND)
            try:
                payload = png_bytes(self.server.round_dir / self.server.by_id[blind_id]["image_file"])
            except ValueError as error:
                return self.fail(str(error), 500)
            return self.send(payload, "image/png")
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if not urllib.parse.urlparse(self.path).path.startswith("/api/annotation/"):
            return self.fail("not found", HTTPStatus.NOT_FOUND)
        blind_id = self.blind_id("/api/annotation/")
        if not blind_id:
            return self.fail("unknown blind ID", HTTPStatus.NOT_FOUND)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                raise ValueError("invalid request length")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("JSON payload must be an object")
            width, _ = self.server.geometry[blind_id]
            updated = validate_measurement(payload, self.server.by_id[blind_id], width)
            with self.server.write_lock:
                rows = read_rows(self.server.round_dir)
                for index, row in enumerate(rows):
                    if row["blind_id"] == blind_id:
                        rows[index] = updated
                        break
                atomic_write_rows(self.server.round_dir / "annotations.csv", rows)
                self.server.refresh()
        except (ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            return self.fail(str(error))
        self.send(json.dumps(updated).encode("utf-8"), "application/json")

    def log_message(self, format: str, *args: object) -> None:
        pass


def check_packet(round_dir: Path) -> None:
    rows = read_rows(round_dir)
    geometries = {row["blind_id"]: image_geometry(round_dir / row["image_file"]) for row in rows}
    # Exercise the lossless TIFF-to-browser path on every image.
    for row in rows:
        png_bytes(round_dir / row["image_file"])
    print(json.dumps({
        "status": "PASS_PACKET_ONLY_UI_CHECK",
        "round_dir": str(round_dir),
        "rows": len(rows),
        "unique_images": len({row["image_file"] for row in rows}),
        "geometries": sorted({geometry for geometry in geometries.values()}),
        "filled_rows": sum(bool(row["visibility_status"]) for row in rows),
    }, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-dir", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    round_dir = args.round_dir.expanduser().resolve()
    if args.check_only:
        check_packet(round_dir)
        return 0
    server = Server((args.host, args.port), round_dir)
    print(f"S02-E004 blind measurement UI: http://{args.host}:{args.port}/")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
