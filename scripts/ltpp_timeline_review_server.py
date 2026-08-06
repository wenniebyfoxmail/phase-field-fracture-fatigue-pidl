#!/usr/bin/env python3
"""Read-only chronological viewer for frozen LTPP dual annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


CRACK_FAMILIES = {
    "transverse_crack", "longitudinal_crack", "fatigue_or_alligator_crack",
    "block_crack", "other_crack",
}


def read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def line_length(points: list[list[float]]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def polygon_area(ring: list[list[float]]) -> float:
    if ring and ring[0] != ring[-1]:
        ring = [*ring, ring[0]]
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))) / 2


def geometry_summary(payload: dict) -> dict:
    families: Counter[str] = Counter()
    line_m = area_m2 = 0.0
    for feature in payload.get("features", []):
        family = feature.get("properties", {}).get("distress_family", "unknown")
        families[family] += 1
        if family not in CRACK_FAMILIES:
            continue
        geometry = feature.get("geometry", {})
        if geometry.get("type") == "LineString":
            line_m += line_length(geometry.get("coordinates", []))
        elif geometry.get("type") == "Polygon":
            rings = geometry.get("coordinates", [])
            if rings:
                area_m2 += polygon_area(rings[0])
    return {
        "feature_count": len(payload.get("features", [])),
        "crack_line_length_m": line_m,
        "crack_area_m2": area_m2,
        "family_counts": dict(sorted(families.items())),
    }


def load_catalog(packet_root: Path) -> dict:
    packet_root = packet_root.resolve()
    manifest = read_json(packet_root / "adjudicated" / "adjudicated_manifest.json")
    if manifest.get("status") != "PASS_ADJUDICATED_LABELS_FROZEN":
        raise ValueError("adjudicated labels are not frozen")
    mapping = read_json(packet_root / "sealed_do_not_open_during_annotation" / "blind_id_asset_mapping.json")
    pairing = read_json(packet_root / "pairing_result.json")
    if pairing.get("sealed_mapping_read") is not True:
        raise ValueError("sealed pairing gate has not completed")
    primary = {row["asset_key"]: row for row in mapping["primary"]}
    secondary = {row["asset_key"]: row for row in mapping["secondary"]}

    out_dates: dict[str, str] = {}
    transitions_path = packet_root / "adjudicated_transitions" / "transitions.json"
    if transitions_path.is_file():
        for row in read_json(transitions_path):
            if row.get("out_of_study_date"):
                out_dates[row["section"]] = row["out_of_study_date"]

    states: dict[str, dict] = {}
    sections: dict[str, list[dict]] = defaultdict(list)
    for final_path in sorted((packet_root / "adjudicated" / "geojson").glob("*.geojson")):
        final_label = read_json(final_path)
        props = final_label.get("properties", {})
        if props.get("locked") is not True or props.get("adjudicated") is not True:
            raise ValueError(f"unfrozen adjudicated label: {final_path}")
        asset_key = props["asset_key"]
        p_row, s_row = primary.get(asset_key), secondary.get(asset_key)
        if not p_row or not s_row:
            raise ValueError(f"missing blind mapping: {asset_key}")
        p_image = packet_root / "primary" / "images" / f"{p_row['blind_id']}.png"
        s_image = packet_root / "secondary" / "images" / f"{s_row['blind_id']}.png"
        if hashlib.sha256(p_image.read_bytes()).digest() != hashlib.sha256(s_image.read_bytes()).digest():
            raise ValueError(f"role image mismatch: {asset_key}")
        p_path = packet_root / "primary" / "geojson" / f"{p_row['blind_id']}.geojson"
        s_path = packet_root / "secondary" / "geojson" / f"{s_row['blind_id']}.geojson"
        p_label, s_label = read_json(p_path), read_json(s_path)
        if p_label.get("properties", {}).get("locked") is not True:
            raise ValueError(f"primary label is not locked: {p_path}")
        if s_label.get("properties", {}).get("locked") is not True:
            raise ValueError(f"secondary label is not locked: {s_path}")
        section, survey_date = props["section"], props["survey_date"]
        out_date = out_dates.get(section)
        state = {
            "asset_key": asset_key, "section": section, "survey_date": survey_date,
            "construction_number": props["construction_number"],
            "state_id": props["state_id"], "primary_blind_id": p_row["blind_id"],
            "secondary_blind_id": s_row["blind_id"],
            "after_out_of_study": bool(out_date and survey_date >= out_date),
            "out_of_study_date": out_date,
            "summary": geometry_summary(final_label),
            "primary_feature_count": len(p_label.get("features", [])),
            "secondary_feature_count": len(s_label.get("features", [])),
            "image_path": p_image,
            "primary_label_path": p_path, "secondary_label_path": s_path,
            "final_label_path": final_path,
        }
        states[asset_key] = state
        sections[section].append(state)
    if len(states) != manifest.get("state_count"):
        raise ValueError(f"expected {manifest.get('state_count')} states, found {len(states)}")
    for rows in sections.values():
        rows.sort(key=lambda row: (row["survey_date"], row["construction_number"], row["asset_key"]))
        previous = None
        for row in rows:
            row["delta_crack_line_length_m"] = None if previous is None else (
                row["summary"]["crack_line_length_m"] - previous["summary"]["crack_line_length_m"]
            )
            row["delta_crack_area_m2"] = None if previous is None else (
                row["summary"]["crack_area_m2"] - previous["summary"]["crack_area_m2"]
            )
            previous = row
    return {"packet_root": packet_root, "states": states, "sections": sections}


def public_state(row: dict) -> dict:
    keys = (
        "asset_key", "section", "survey_date", "construction_number", "state_id",
        "primary_blind_id", "secondary_blind_id", "after_out_of_study", "out_of_study_date",
        "summary", "primary_feature_count", "secondary_feature_count",
        "delta_crack_line_length_m", "delta_crack_area_m2",
    )
    return {key: row[key] for key in keys}


HTML = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LTPP 路段损伤时间轴</title><style>
:root{--ink:#17211b;--paper:#f5f0e5;--muted:#6b716d;--green:#1b7467;--gold:#d79b26;--red:#d63b35;--blue:#1769aa}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#e5dfd2,#fbf8f1 58%,#dce9e2);color:var(--ink);font-family:"Avenir Next","PingFang SC",sans-serif}header{padding:18px 26px 13px;border-bottom:2px solid var(--ink);display:flex;justify-content:space-between;gap:18px;align-items:end}h1{font:500 clamp(26px,3vw,40px) Georgia,"Songti SC",serif;margin:0}.sub{color:var(--muted);margin-top:5px}.controls{display:flex;gap:8px;align-items:end}.controls label{font-size:12px;font-weight:800}.controls select,.controls button{display:block;margin-top:4px;padding:8px 11px;background:white;border:1px solid var(--ink);font:inherit}.controls button{cursor:pointer}
main{padding:16px 26px 30px}.timeline{display:flex;gap:7px;overflow-x:auto;padding:4px 1px 14px}.date{min-width:132px;border:1px solid var(--ink);background:#fffdf8;padding:8px;text-align:left;cursor:pointer}.date.active{background:var(--green);color:white}.date.post{border-top:5px solid var(--gold)}.date b,.date span{display:block}.date span{font-size:11px;margin-top:3px}.summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin-bottom:14px}.metric{background:#ffffffc9;border:1px solid #9b9d96;padding:10px}.metric b{display:block;font-size:20px}.metric small{color:var(--muted)}.warning{padding:9px 12px;background:#fff1c8;border-left:5px solid var(--gold);margin-bottom:13px}.hidden{display:none}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.panel{background:white;border:2px solid var(--ink);box-shadow:6px 6px 0 #17211b18}.title{padding:8px 11px;border-bottom:1px solid var(--ink);display:flex;justify-content:space-between;gap:10px;font-weight:900}.title small{color:var(--muted);font-weight:500}canvas{display:block;width:100%;aspect-ratio:1524/500}.legend{font-size:12px;color:var(--muted);padding:12px 0}.dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin:0 4px 0 10px}.table-wrap{margin-top:16px;overflow:auto;background:#ffffffb5;border:1px solid var(--ink)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:7px 9px;border-bottom:1px solid #d6d2c8;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}tbody tr{cursor:pointer}tbody tr.active{background:#dcebe6}tbody tr.post{box-shadow:inset 5px 0 var(--gold)}
@media(max-width:900px){header{padding:14px 12px;display:block}.controls{margin-top:10px}main{padding:12px}.grid{grid-template-columns:1fr}.summary{grid-template-columns:1fr 1fr}.metric:last-child{grid-column:1/-1}}
</style></head><body><header><div><h1>LTPP 路段损伤时间轴</h1><div class="sub">同一路段按真实调查日期排序 · 原图／AI／人工／最终裁决 · 只读</div></div><div class="controls"><label>路段<select id="section"></select></label><button id="prev">← 上一期</button><button id="next">下一期 →</button></div></header>
<main><div id="timeline" class="timeline"></div><div id="warning" class="warning hidden"></div><section class="summary"><div class="metric"><small>调查日期</small><b id="date">—</b></div><div class="metric"><small>最终裂缝线长度</small><b id="length">—</b></div><div class="metric"><small>较上期变化</small><b id="delta">—</b></div><div class="metric"><small>最终裂缝面积</small><b id="area">—</b></div><div class="metric"><small>标注数量（AI / 人工 / 最终）</small><b id="counts">—</b></div></section>
<section class="grid"><div class="panel"><div class="title"><span>1. 原图</span><small>无覆盖标记</small></div><canvas id="original" width="1524" height="500"></canvas></div><div class="panel"><div class="title"><span>2. AI 标注</span><small id="ai-id"></small></div><canvas id="ai" width="1524" height="500"></canvas></div><div class="panel"><div class="title"><span>3. 人工标注</span><small id="human-id"></small></div><canvas id="human" width="1524" height="500"></canvas></div><div class="panel"><div class="title"><span>4. 最终裁决</span><small id="final-id"></small></div><canvas id="final" width="1524" height="500"></canvas></div></section>
<div class="legend">最终裁决颜色：<i class="dot" style="background:#d62929"></i>横向裂缝 <i class="dot" style="background:#1261a0"></i>纵向裂缝 <i class="dot" style="background:#e07a1f"></i>疲劳裂缝 <i class="dot" style="background:#9a5b13"></i>非裂缝病害 <i class="dot" style="background:#6b6b61"></i>不确定。数值不是强制单调；标注差异、不可见区域和未记录事件均可能使其下降。</div>
<div class="table-wrap"><table><thead><tr><th>日期</th><th>最终线长 m</th><th>较上期 Δm</th><th>最终面积 m²</th><th>AI</th><th>人工</th><th>最终</th></tr></thead><tbody id="rows"></tbody></table></div></main>
<script>
const colors={transverse_crack:'#d62929',longitudinal_crack:'#1261a0',fatigue_or_alligator_crack:'#e07a1f',block_crack:'#8b5a2b',other_crack:'#7a3ea1',patch_or_patch_deterioration:'#9a5b13',water_bleeding_and_pumping:'#008b8b',other_noncrack_distress:'#4f6575',uncertain:'#6b6b61'};
const cvs=['original','ai','human','final'].map(id=>document.getElementById(id)),ctx=cvs.map(x=>x.getContext('2d'));let sections=[],timeline=[],index=0;
const fmt=(x,d=2)=>x==null?'—':Number(x).toFixed(d);function points(f){const c=f.geometry.coordinates;return f.geometry.type==='Polygon'?c[0]:c}function px(p){return[p[0]*100,500-p[1]*100]}
function drawFeature(c,f,color,dashed=false){const p=points(f).map(px);if(!p.length)return;c.save();c.strokeStyle=color;c.lineWidth=5;c.lineJoin='round';c.lineCap='round';c.setLineDash(dashed?[11,7]:[]);c.beginPath();p.forEach((q,i)=>i?c.lineTo(...q):c.moveTo(...q));if(f.geometry.type==='Polygon'){c.closePath();c.globalAlpha=.16;c.fillStyle=color;c.fill();c.globalAlpha=.9}c.stroke();c.restore()}
async function loadSections(){sections=await fetch('/api/sections').then(r=>r.json());const select=document.getElementById('section');select.innerHTML=sections.map(s=>`<option value="${s.section}">${s.section} · ${s.count}期 · ${s.first_date} → ${s.last_date}</option>`).join('');select.onchange=()=>loadTimeline(select.value);await loadTimeline(select.value)}
async function loadTimeline(section){timeline=await fetch('/api/timeline?section='+encodeURIComponent(section)).then(r=>r.json());index=0;renderTimeline();await loadState()}
function renderTimeline(){document.getElementById('timeline').innerHTML=timeline.map((s,i)=>`<button class="date ${i===index?'active':''} ${s.after_out_of_study?'post':''}" data-i="${i}"><b>${s.survey_date}</b><span>${fmt(s.summary.crack_line_length_m)} m · ${s.summary.feature_count}项${s.after_out_of_study?' · Out-of-Study后':''}</span></button>`).join('');document.querySelectorAll('.date').forEach(b=>b.onclick=()=>go(Number(b.dataset.i)));document.getElementById('rows').innerHTML=timeline.map((s,i)=>`<tr data-i="${i}" class="${i===index?'active':''} ${s.after_out_of_study?'post':''}"><td>${s.survey_date}</td><td>${fmt(s.summary.crack_line_length_m,3)}</td><td>${s.delta_crack_line_length_m==null?'—':(s.delta_crack_line_length_m>=0?'+':'')+fmt(s.delta_crack_line_length_m,3)}</td><td>${fmt(s.summary.crack_area_m2,3)}</td><td>${s.primary_feature_count}</td><td>${s.secondary_feature_count}</td><td>${s.summary.feature_count}</td></tr>`).join('');document.querySelectorAll('tbody tr').forEach(r=>r.onclick=()=>go(Number(r.dataset.i)))}
async function loadState(){const s=timeline[index],data=await fetch('/api/state/'+encodeURIComponent(s.asset_key)).then(r=>r.json()),image=new Image();image.onload=()=>{ctx.forEach(c=>{c.clearRect(0,0,1524,500);c.drawImage(image,0,0,1524,500)});data.primary_label.features.forEach(f=>drawFeature(ctx[1],f,'#d43a35'));data.secondary_label.features.forEach(f=>drawFeature(ctx[2],f,'#1769aa',true));data.final_label.features.forEach(f=>drawFeature(ctx[3],f,colors[f.properties.distress_family]||'#555f68'));};image.src=data.clean_image_url+'?v='+encodeURIComponent(s.state_id);document.getElementById('date').textContent=s.survey_date;document.getElementById('length').textContent=fmt(s.summary.crack_line_length_m,3)+' m';document.getElementById('delta').textContent=s.delta_crack_line_length_m==null?'首期':(s.delta_crack_line_length_m>=0?'+':'')+fmt(s.delta_crack_line_length_m,3)+' m';document.getElementById('area').textContent=fmt(s.summary.crack_area_m2,3)+' m²';document.getElementById('counts').textContent=`${data.primary_label.features.length} / ${data.secondary_label.features.length} / ${data.final_label.features.length}`;document.getElementById('ai-id').textContent=data.primary_blind_id;document.getElementById('human-id').textContent=data.secondary_blind_id;document.getElementById('final-id').textContent=data.state_id;const w=document.getElementById('warning');if(s.after_out_of_study){w.classList.remove('hidden');w.textContent=`注意：该调查晚于 LTPP Out-of-Study 日期 ${s.out_of_study_date}。图仍是有效观测，但不应自动解释为研究期内连续状态。`}else w.classList.add('hidden')}
async function go(i){index=(i+timeline.length)%timeline.length;renderTimeline();await loadState();document.querySelector('.date.active')?.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}document.getElementById('prev').onclick=()=>go(index-1);document.getElementById('next').onclick=()=>go(index+1);document.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')go(index-1);if(e.key==='ArrowRight')go(index+1)});loadSections();
</script></body></html>"""


class TimelineServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], packet_root: Path, default_section: str | None = None):
        super().__init__(address, TimelineHandler)
        catalog = load_catalog(packet_root)
        self.packet_root = catalog["packet_root"]
        self.states = catalog["states"]
        self.sections = catalog["sections"]
        self.default_section = default_section if default_section in self.sections else sorted(self.sections)[0]


class TimelineHandler(BaseHTTPRequestHandler):
    server: TimelineServer

    def send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: object, status: int = 200) -> None:
        self.send_bytes(json.dumps(payload).encode(), "application/json; charset=utf-8", status)

    def fail(self, message: str, status: int) -> None:
        self.send_bytes(message.encode(), "text/plain; charset=utf-8", status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_bytes(HTML.encode(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/sections":
            rows = []
            for section, states in sorted(self.server.sections.items()):
                rows.append({"section": section, "count": len(states), "first_date": states[0]["survey_date"], "last_date": states[-1]["survey_date"], "default": section == self.server.default_section})
            self.send_json(rows)
            return
        if parsed.path == "/api/timeline":
            section = parse_qs(parsed.query).get("section", [self.server.default_section])[0]
            if section not in self.server.sections:
                self.fail("section not found", HTTPStatus.NOT_FOUND)
                return
            self.send_json([public_state(row) for row in self.server.sections[section]])
            return
        if parsed.path.startswith("/api/state/"):
            asset_key = unquote(parsed.path[len("/api/state/"):])
            row = self.server.states.get(asset_key)
            if row is None:
                self.fail("state not found", HTTPStatus.NOT_FOUND)
                return
            payload = public_state(row)
            payload.update({
                "clean_image_url": "/image/" + quote(asset_key, safe=""),
                "primary_label": read_json(row["primary_label_path"]),
                "secondary_label": read_json(row["secondary_label_path"]),
                "final_label": read_json(row["final_label_path"]),
            })
            self.send_json(payload)
            return
        if parsed.path.startswith("/image/"):
            asset_key = unquote(parsed.path[len("/image/"):])
            row = self.server.states.get(asset_key)
            if row is None or not row["image_path"].is_file():
                self.fail("image not found", HTTPStatus.NOT_FOUND)
                return
            self.send_bytes(row["image_path"].read_bytes(), "image/png")
            return
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        self.fail("read-only viewer", HTTPStatus.METHOD_NOT_ALLOWED)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--section", default="06-1253")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8769)
    args = parser.parse_args()
    server = TimelineServer((args.host, args.port), args.packet_root, args.section)
    print(f"LTPP timeline viewer: http://{args.host}:{args.port}/ ({len(server.states)} frozen states)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
