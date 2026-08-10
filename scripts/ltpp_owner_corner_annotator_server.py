#!/usr/bin/env python3
"""Owner-reviewed four-corner collector for the exploratory LTPP carrier MVP."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont


EXPECTED_DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)
EXPECTED_SHA256 = {
    "19910610": "b8943157993279f2f84bd04570b9328965c02c053148285af1efcf2557cc5212",
    "19951024": "cef8a827e4f85e8b9be75b9e0480db8861ffc5220454d61296238e39de5a7fb8",
    "19970228": "782c32c76cf85b17fe21e2500e0ee5fccc0afbf7c63d1918df3000c05a09bd5c",
    "19980407": "8d82c6f1bb2d1fc9aa4d57c41e99690d79ec631e5b72c8148c645bc4dbe2d8da",
    "20010913": "78671332803fa7e7b36a371c59bb580ccba63f9a6114c9f78c3eb78e93c47221",
    "20030514": "060ec9143db4260cf556118fbdfbc3b5c6ece1e9a6f4544c557c43265c9acd0d",
    "20071106": "0ddb2c388f8701c7a8a0fb45a8654a78767e6493dcb7c1006a957264c0dd6c06",
    "20120417": "17a2c90d478aabba45e1c673d1d9542697b03a69a81f44fe7035005f6d28f90b",
}
POINTS = (
    ("TL", "左上", (0.0, 15.0)),
    ("TR", "右上", (50.0, 15.0)),
    ("BR", "右下", (50.0, 0.0)),
    ("BL", "左下", (0.0, 0.0)),
)
STATUS_INCOMPLETE = "OWNER_CORNER_COLLECTION_INCOMPLETE__EXPLORATORY_ONLY"
STATUS_LOCKED = "OWNER_CORNERS_LOCKED_PENDING_VISUAL_REVIEW__EXPLORATORY_ONLY"
PREREGISTRATION = Path(__file__).resolve().parents[1] / "docs" / "experiments" / "ltpp_geoforecast_owner_corner_carrier_mvp_preregistration_20260810.md"


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
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def initial_record(date: str, source_sha256: str, width: int, height: int) -> dict:
    return {
        "survey_date": date,
        "classification": "exploratory_owner_construction_controls_only",
        "source_sha256": source_sha256,
        "source_width_px": width,
        "source_height_px": height,
        "point_order": [item[0] for item in POINTS],
        "points_source_px": [],
        "locked": False,
        "locked_at_utc": None,
    }


def validate_points(points: object, width: int, height: int, require_complete: bool = False) -> str | None:
    if not isinstance(points, list) or len(points) > 4:
        return "points must be a list containing at most four clicks"
    if require_complete and len(points) != 4:
        return "exactly four points are required before lock"
    parsed: list[tuple[int, int]] = []
    for point in points:
        if not isinstance(point, list) or len(point) != 2 or not all(isinstance(value, int) for value in point):
            return "every point must contain two integer source-pixel coordinates"
        x, y = point
        if not (0 <= x < width and 0 <= y < height):
            return "point outside source image"
        parsed.append((x, y))
    if len(set(parsed)) != len(parsed):
        return "points must be unique"
    if len(parsed) < 4:
        return None
    tl, tr, br, bl = parsed
    if not (tl[0] < tr[0] and bl[0] < br[0] and tl[1] < bl[1] and tr[1] < br[1]):
        return "point order is not TL, TR, BR, BL"
    crosses = []
    for index in range(4):
        a, b, c = parsed[index], parsed[(index + 1) % 4], parsed[(index + 2) % 4]
        crosses.append((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
    if any(value <= 0 for value in crosses):
        return "the four points must form one clockwise convex quadrilateral"
    area2 = sum(parsed[i][0] * parsed[(i + 1) % 4][1] - parsed[(i + 1) % 4][0] * parsed[i][1] for i in range(4))
    if area2 < width * height * 0.10:
        return "quadrilateral is implausibly small; check outer-frame corners"
    return None


def initialize_packet(source_root: Path, packet_root: Path, expected_hashes: dict[str, str] | None = None) -> None:
    if packet_root.exists():
        raise ValueError(f"refusing to overwrite packet: {packet_root}")
    expected_hashes = EXPECTED_SHA256 if expected_hashes is None else expected_hashes
    images = packet_root / "images"
    records = packet_root / "records"
    images.mkdir(parents=True)
    records.mkdir()
    inputs = []
    try:
        for date in EXPECTED_DATES:
            source = source_root / date / "segment_0_50_white.png"
            digest = sha256(source)
            if digest != expected_hashes[date]:
                raise ValueError(f"source hash mismatch for {date}: {digest}")
            with Image.open(source) as image:
                width, height = image.size
            destination = images / f"{date}.png"
            shutil.copyfile(source, destination)
            if sha256(destination) != digest:
                raise ValueError(f"copied image hash mismatch for {date}")
            atomic_json(records / f"{date}.json", initial_record(date, digest, width, height))
            inputs.append({"survey_date": date, "source_path": str(source.resolve()), "source_sha256": digest,
                           "width_px": width, "height_px": height, "packet_image": str(destination.relative_to(packet_root))})
        atomic_json(packet_root / "packet.json", {
            "status": STATUS_INCOMPLETE,
            "created_at_utc": utc_now(),
            "kind": "owner_reviewed_outer_corner_carrier_mvp",
            "implementation_path": str(Path(__file__).resolve()),
            "implementation_sha256": sha256(Path(__file__).resolve()),
            "preregistration_path": str(PREREGISTRATION),
            "preregistration_sha256": sha256(PREREGISTRATION),
            "dates": list(EXPECTED_DATES),
            "point_order": [item[0] for item in POINTS],
            "physical_rectangle_ft": {"width": 50.0, "height": 15.0},
            "physical_rectangle_m": {"width": 15.24, "height": 4.572},
            "controls": "owner-reviewed construction controls; not blind or independent audit controls",
            "prohibited_inputs": ["crack geometry", "WIM box", "repair or distress mark", "cross-date crack shape"],
            "prohibited_claims": ["registration qualification", "independent validation", "v2 final gate", "2-D model authorization"],
            "inputs": inputs,
        })
    except Exception:
        shutil.rmtree(packet_root)
        raise


def figure_sidecar(date: str) -> str:
    return (
        f"# {date} owner-corner review overlay\n\n"
        "## Question\n\nDo the four large labelled markers fall on the centreline intersections of the printed outer solid road-grid boundary?\n\n"
        "## Provenance and encoding\n\nThe background is the SHA-256-frozen `segment_0_50_white.png`. "
        "The cyan polygon joins the owner clicks in fixed order TL, TR, BR, BL. Marker colours and labels identify the four construction controls.\n\n"
        "## Limitation and claim boundary\n\nThese owner-visible clicks are exploratory construction controls. "
        "The overlay does not measure registration error, validate a homography, alter v1, or authorize a 2-D model.\n"
    )


def render_review_assets(packet_root: Path) -> None:
    overlay_dir = packet_root / "review_overlays"
    overlay_dir.mkdir(exist_ok=False)
    thumbnails = []
    colours = ((214, 0, 255), (255, 120, 0), (0, 110, 255), (0, 190, 80))
    for date in EXPECTED_DATES:
        record = json.loads((packet_root / "records" / f"{date}.json").read_text())
        if not record.get("locked"):
            raise ValueError(f"cannot render before all dates are locked: {date}")
        image = Image.open(packet_root / "images" / f"{date}.png").convert("RGB")
        draw = ImageDraw.Draw(image)
        points = [tuple(point) for point in record["points_source_px"]]
        draw.line(points + [points[0]], fill=(0, 210, 220), width=10, joint="curve")
        radius = max(18, round(image.width / 110))
        for (code, chinese, _), point, colour in zip(POINTS, points, colours):
            x, y = point
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(255, 255, 255), outline=colour, width=8)
            draw.line((x-radius*2, y, x+radius*2, y), fill=colour, width=4)
            draw.line((x, y-radius*2, x, y+radius*2), fill=colour, width=4)
            draw.text((x + radius + 7, y - radius - 7), f"{code} {chinese}", fill=colour, stroke_width=3, stroke_fill=(255, 255, 255))
        output = overlay_dir / f"{date}_owner_corner_overlay.png"
        image.save(output)
        output.with_suffix(".md").write_text(figure_sidecar(date), encoding="utf-8")
        thumb = image.copy(); thumb.thumbnail((900, 320)); thumbnails.append((date, thumb))
    panel_width = max(image.width for _, image in thumbnails)
    panel_height = max(image.height for _, image in thumbnails) + 32
    sheet = Image.new("RGB", (panel_width * 2, panel_height * 4), "white")
    for index, (date, image) in enumerate(thumbnails):
        x, y = (index % 2) * panel_width, (index // 2) * panel_height
        ImageDraw.Draw(sheet).text((x + 8, y + 6), date, fill="black")
        sheet.paste(image, (x, y + 30))
    contact = packet_root / "owner_corner_review_contact_sheet.png"
    sheet.save(contact)
    contact.with_suffix(".md").write_text(
        "# Eight-date owner-corner review contact sheet\n\n"
        "This sheet asks whether every labelled corner lies on the outer solid printed frame. "
        "It combines the eight same-source overlays for visual review only. It is not registration qualification evidence.\n",
        encoding="utf-8",
    )


def finalize_if_complete(packet_root: Path) -> bool:
    records = [json.loads((packet_root / "records" / f"{date}.json").read_text()) for date in EXPECTED_DATES]
    if not all(record.get("locked") for record in records):
        return False
    output = packet_root / "owner_corners.json"
    if output.exists():
        return True
    atomic_json(output, {
        "status": STATUS_LOCKED,
        "created_at_utc": utc_now(),
        "classification": "exploratory_owner_construction_controls_only",
        "physical_corner_order": [{"id": code, "label_zh": label, "coordinate_ft": list(coordinate)} for code, label, coordinate in POINTS],
        "records": records,
        "qualification_metrics_computed": False,
        "final_gate_run": False,
    })
    render_review_assets(packet_root)
    packet = json.loads((packet_root / "packet.json").read_text())
    packet["status"] = STATUS_LOCKED
    packet["all_dates_locked_at_utc"] = utc_now()
    atomic_json(packet_root / "packet.json", packet)
    files = sorted(path for path in packet_root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (packet_root / "manifest.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(packet_root)}\n" for path in files), encoding="utf-8"
    )
    return True


HTML = r'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>LTPP 四角审阅</title>
<style>
:root{--ink:#17211b;--paper:#f4f0e6;--cyan:#00cbd1}*{box-sizing:border-box}body{margin:0;font:15px system-ui;color:var(--ink);background:var(--paper)}header{padding:12px 18px;border-bottom:2px solid var(--ink);background:#fff}main{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:12px;padding:12px}.viewport{height:76vh;overflow:auto;border:1px solid var(--ink);background:#bbb}.stage{position:relative;width:max-content;background:white}.stage img{display:block;max-width:none}.stage svg{position:absolute;inset:0;overflow:visible;cursor:crosshair}.side{background:#fff;padding:12px;border:1px solid var(--ink)}button,select{width:100%;padding:8px;margin:5px 0}.date{padding:6px;border-bottom:1px dotted #aaa;cursor:pointer}.date.active{background:#ffe28a}.date.locked{color:#087443;font-weight:700}.steps{line-height:1.6;padding-left:24px}.next{font-size:18px;font-weight:800;color:#9b1c31}.loupe{width:260px;height:180px;border:1px solid #333;background:#fff}.warn{color:#a3172a}.ok{color:#087443}.legend span{display:inline-block;margin-right:8px;font-weight:700}@media(max-width:900px){main{grid-template-columns:1fr}.viewport{height:58vh}}
</style></head><body><header><b>LTPP 0–50 ft 外框四角（探索性构造点）</b>　<span class="warn">不是最终审计，不使用裂缝形状</span></header>
<main><section class="viewport" id="viewport"><div class="stage" id="stage"><img id="image"><svg id="overlay"></svg></div></section><aside class="side">
<div id="dates"></div><p class="next" id="next"></p><ol class="steps"><li>左上 TL：外侧实线交点</li><li>右上 TR：外侧实线交点</li><li>右下 BR：外侧实线交点</li><li>左下 BL：外侧实线交点</li></ol>
<p class="legend"><span style="color:#d600ff">TL</span><span style="color:#ff7800">TR</span><span style="color:#006eff">BR</span><span style="color:#00a850">BL</span></p>
<label>缩放<select id="zoom"><option value="0.5">50%</option><option value="0.75">75%</option><option value="1" selected>100%</option><option value="1.5">150%</option><option value="2">200%</option><option value="3">300%</option></select></label>
<canvas class="loupe" id="loupe" width="260" height="180"></canvas><button id="undo">撤销最后一点</button><button id="reset">重置本年</button><button id="save">保存草稿</button><button id="lock">锁定本年四角</button><p id="feedback"></p>
<p><small>只点最外侧矩形实线的四个交点。不要点内部虚线交点、裂缝与虚线交点、尺寸刻度或手写标记。</small></p></aside></main>
<script>
const names=['TL 左上','TR 右上','BR 右下','BL 左下'],colors=['#d600ff','#ff7800','#006eff','#00a850'];let dates=[],current='',record=null,zoom=1;
const image=document.getElementById('image'),stage=document.getElementById('stage'),overlay=document.getElementById('overlay'),feedback=document.getElementById('feedback'),loupe=document.getElementById('loupe'),ctx=loupe.getContext('2d');
function say(text,bad=false){feedback.textContent=text;feedback.className=bad?'warn':'ok'}
function pointMarkup(p,i){const x=p[0]*zoom,y=p[1]*zoom,r=17;return `<g><circle cx="${x}" cy="${y}" r="${r}" fill="white" stroke="${colors[i]}" stroke-width="7"/><line x1="${x-r*1.7}" y1="${y}" x2="${x+r*1.7}" y2="${y}" stroke="${colors[i]}" stroke-width="4"/><line x1="${x}" y1="${y-r*1.7}" x2="${x}" y2="${y+r*1.7}" stroke="${colors[i]}" stroke-width="4"/><text x="${x+r+8}" y="${y-r}" fill="${colors[i]}" font-size="24" font-weight="800" paint-order="stroke" stroke="white" stroke-width="5">${names[i]}</text></g>`}
function render(){if(!record)return;const w=record.source_width_px*zoom,h=record.source_height_px*zoom;image.style.width=w+'px';image.style.height=h+'px';stage.style.width=w+'px';stage.style.height=h+'px';overlay.setAttribute('width',w);overlay.setAttribute('height',h);overlay.setAttribute('viewBox',`0 0 ${w} ${h}`);let html='';if(record.points_source_px.length>1){const ps=record.points_source_px.map(p=>`${p[0]*zoom},${p[1]*zoom}`).join(' ');html+=`<polyline points="${ps}" fill="none" stroke="#00cbd1" stroke-width="8"/>`}if(record.points_source_px.length===4){const p=record.points_source_px[0];html+=`<line x1="${record.points_source_px[3][0]*zoom}" y1="${record.points_source_px[3][1]*zoom}" x2="${p[0]*zoom}" y2="${p[1]*zoom}" stroke="#00cbd1" stroke-width="8"/>`}record.points_source_px.forEach((p,i)=>html+=pointMarkup(p,i));overlay.innerHTML=html;document.getElementById('next').textContent=record.locked?'本年已锁定':record.points_source_px.length<4?'下一点：'+names[record.points_source_px.length]:'四点齐全，请检查青色围合线';['undo','reset','save','lock'].forEach(id=>document.getElementById(id).disabled=record.locked);document.getElementById('lock').disabled=record.locked||record.points_source_px.length!==4;document.getElementById('dates').innerHTML=dates.map(d=>`<div data-date="${d.survey_date}" class="date ${d.survey_date===current?'active':''} ${d.locked?'locked':''}">${d.survey_date}　${d.locked?'✓ 已锁定':d.count+'/4'}</div>`).join('');document.querySelectorAll('.date').forEach(el=>el.onclick=()=>load(el.dataset.date));}
async function refreshDates(){dates=await fetch('/api/dates').then(r=>r.json())}
async function load(date){current=date;record=await fetch('/api/record/'+date).then(r=>r.json());image.src='/image/'+date+'?v='+Date.now();image.onload=render;await refreshDates();render();say(record.locked?'该年份已锁定。':'请按固定顺序点击。')}
overlay.onclick=e=>{if(record.locked||record.points_source_px.length>=4)return;const box=overlay.getBoundingClientRect();record.points_source_px.push([Math.round((e.clientX-box.left)/zoom),Math.round((e.clientY-box.top)/zoom)]);render();say('已记录 '+names[record.points_source_px.length-1])};
overlay.onmousemove=e=>{if(!image.complete)return;const box=overlay.getBoundingClientRect(),x=(e.clientX-box.left)/zoom,y=(e.clientY-box.top)/zoom,sw=52,sh=36;ctx.fillStyle='white';ctx.fillRect(0,0,260,180);ctx.imageSmoothingEnabled=false;ctx.drawImage(image,x-sw/2,y-sh/2,sw,sh,0,0,260,180);ctx.strokeStyle='#e00035';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(130,0);ctx.lineTo(130,180);ctx.moveTo(0,90);ctx.lineTo(260,90);ctx.stroke()};
async function save(){const response=await fetch('/api/record/'+current,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(record)});const text=await response.text();if(!response.ok){say(text,true);return false}await refreshDates();render();say('草稿已保存。');return true}
document.getElementById('undo').onclick=()=>{record.points_source_px.pop();render();say('已撤销。')};document.getElementById('reset').onclick=()=>{if(confirm('重置本年四点？')){record.points_source_px=[];render();say('本年已重置。')}};document.getElementById('save').onclick=save;
document.getElementById('lock').onclick=async()=>{if(!confirm('确认四点都在外侧实线交点，并锁定本年？锁定后本包不能修改。'))return;if(!await save())return;const response=await fetch('/api/lock/'+current,{method:'POST'});const text=await response.text();if(!response.ok)return say(text,true);await refreshDates();const next=dates.find(d=>!d.locked);if(next)await load(next.survey_date);else{await load(current);say('8 年均已锁定；审阅叠加图已生成。')}};
document.getElementById('zoom').onchange=e=>{zoom=Number(e.target.value);render()};(async()=>{await refreshDates();await load(dates[0].survey_date)})();
</script></body></html>'''


class Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], packet_root: Path):
        super().__init__(address, Handler)
        self.packet_root = packet_root.resolve()
        self.records = self.packet_root / "records"
        self.images = self.packet_root / "images"
        if not (self.packet_root / "packet.json").is_file():
            raise ValueError("packet.json is missing")


class Handler(BaseHTTPRequestHandler):
    server: Server

    def send(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def fail(self, message: str, status: int = 400) -> None:
        self.send(message.encode(), "text/plain; charset=utf-8", status)

    def valid_date(self, date: str) -> bool:
        return date in EXPECTED_DATES

    def record_path(self, date: str) -> Path:
        return self.server.records / f"{date}.json"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            return self.send(HTML.encode(), "text/html; charset=utf-8")
        if path == "/api/dates":
            rows = []
            for date in EXPECTED_DATES:
                record = json.loads(self.record_path(date).read_text())
                rows.append({"survey_date": date, "count": len(record["points_source_px"]), "locked": record["locked"]})
            return self.send(json.dumps(rows).encode(), "application/json")
        if path.startswith("/api/record/"):
            date = path.rsplit("/", 1)[-1]
            if not self.valid_date(date): return self.fail("invalid date", HTTPStatus.NOT_FOUND)
            return self.send(self.record_path(date).read_bytes(), "application/json")
        if path.startswith("/image/"):
            date = path.rsplit("/", 1)[-1]
            if not self.valid_date(date): return self.fail("invalid date", HTTPStatus.NOT_FOUND)
            return self.send((self.server.images / f"{date}.png").read_bytes(), "image/png")
        return self.fail("not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/record/"):
            date = path.rsplit("/", 1)[-1]
            if not self.valid_date(date): return self.fail("invalid date", HTTPStatus.NOT_FOUND)
            destination = self.record_path(date)
            current = json.loads(destination.read_text())
            if current.get("locked"): return self.fail("date is locked", HTTPStatus.CONFLICT)
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            except (ValueError, json.JSONDecodeError):
                return self.fail("invalid JSON")
            immutable = ("survey_date", "classification", "source_sha256", "source_width_px", "source_height_px", "point_order")
            if not isinstance(payload, dict) or any(payload.get(key) != current.get(key) for key in immutable) or payload.get("locked"):
                return self.fail("immutable record fields changed")
            error = validate_points(payload.get("points_source_px"), current["source_width_px"], current["source_height_px"])
            if error: return self.fail(error)
            clean = dict(current)
            clean["points_source_px"] = payload["points_source_px"]
            atomic_json(destination, clean)
            return self.send(b'{"saved":true}', "application/json")
        if path.startswith("/api/lock/"):
            date = path.rsplit("/", 1)[-1]
            if not self.valid_date(date): return self.fail("invalid date", HTTPStatus.NOT_FOUND)
            destination = self.record_path(date)
            record = json.loads(destination.read_text())
            if record.get("locked"): return self.fail("date already locked", HTTPStatus.CONFLICT)
            error = validate_points(record["points_source_px"], record["source_width_px"], record["source_height_px"], True)
            if error: return self.fail(error)
            record["locked"] = True
            record["locked_at_utc"] = utc_now()
            atomic_json(destination, record)
            complete = finalize_if_complete(self.server.packet_root)
            return self.send(json.dumps({"locked": True, "all_complete": complete}).encode(), "application/json")
        return self.fail("not found", HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8784)
    args = parser.parse_args()
    packet_root = args.packet_root.resolve()
    if args.initialize:
        if args.source_root is None: raise ValueError("--source-root is required with --initialize")
        initialize_packet(args.source_root.resolve(), packet_root)
    server = Server((args.host, args.port), packet_root)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", "packet_root": str(packet_root), "dates": 8}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
