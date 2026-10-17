#!/usr/bin/env python3
"""Local, single-owner MnROAD crack-centreline annotation tool.

The tool deliberately separates a blinded geometry pass from chronological
crack-identity linking.  It is an annotation aid, not a crack-recognition or
model-readiness claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


STATUS = "CONDITIONAL_GO_MANUAL_VECTORISATION_PILOT__NO_GO_MODEL_READY_TRAJECTORY"
SECTION = "22-D-2016"
DATES = (
    "2017-03-20", "2018-03-14", "2018-04-27", "2018-08-23",
    "2019-03-22", "2019-04-16", "2019-10-23",
)
# The 2018 source PDFs were scanned in the opposite quarter-turn from the
# 2017/2019 PDFs.  Keep annotations in source-image coordinates and vary only
# the browser presentation transform so every landscape view reads 0' -> 50'
# from left to right.
CLOCKWISE_LANDSCAPE_DATES = frozenset({
    "2018-03-14", "2018-04-27", "2018-08-23",
})
CUTOFF = "2019-10-24"
MAPS = {
    "2017-03-20": ("2017", "Cell 22 3-20-17.pdf", "6b711ab4342776fddb2d6ed0cb5c7b7433bfa2720bc0a900ce667785f43a14b2"),
    "2018-03-14": ("2018", "Cell 22 March, 2018.pdf", "4398ad6e3a89a7cc1c8bacb9947510289f98be006ddfa681038aaeb0b98f1204"),
    "2018-04-27": ("2018", "Cell 22 April, 2018.pdf", "6cba5cba55b4ac6781a5dfd1fd196122ee4a30a0e9ea4c017da1473abe4ffc1e"),
    "2018-08-23": ("2018", "Cell 22 August, 2018.pdf", "84087a16ba08ff8ad71fdc7af5fd95667c317a3e0f4349727df634689977e96a"),
    "2019-03-22": ("2019", "Cell 22 March, 2019.pdf", "785dfee8e08f75088a72fe6759b08b3fd37e65648256c3808692ff78fcda610d"),
    "2019-04-16": ("2019", "Cell 22 April, 2019.pdf", "fea435e60d5e1d5555d0035c5964cd0fb9901019c8557f0d13192289b131a6d4"),
    "2019-10-23": ("2019", "Cell 22 Fall, 2019.pdf", "1cfffe52251bec1952616da94275a2ffb06584e6c39ecbc5109e4c55cc5a0b80"),
}
BASE_URL = "https://infopave.fhwa.dot.gov/InfoPave_Repository/mn_files/mnroad_media/DISTRESS-MAPS"
LANES = {"Driving", "Passing", "shoulder", "joint"}
CLASSES = {"NWP", "WP", "construction_joint", "other", "unresolvable"}
SEVERITIES = {"L", "M", "H", "unknown"}
TRISTATE = {"yes", "no", "unknown"}
OWNER_DATES = {"current", "earlier", "unknown"}
CONFIDENCE = {"high", "medium", "low"}
CHANGE_TYPES = {"persistent", "extension", "nucleation", "not_observed", "unresolvable"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def image_size(path: Path) -> tuple[int, int]:
    """Read JPEG/PNG dimensions without optional image libraries."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] != b"\xff\xd8":
        raise ValueError(f"unsupported image: {path}")
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in (0xD8, 0xD9):
            continue
        length = int.from_bytes(data[offset:offset + 2], "big")
        if marker in range(0xC0, 0xC4):
            return int.from_bytes(data[offset + 5:offset + 7], "big"), int.from_bytes(data[offset + 3:offset + 5], "big")
        offset += length
    raise ValueError(f"cannot read image dimensions: {path}")


def landscape_rotation_degrees(survey_date: str) -> int:
    return 90 if survey_date in CLOCKWISE_LANDSCAPE_DATES else -90


def download_and_render(work: Path, dpi: int = 120) -> Path:
    pdfs, rendered = work / "pdfs", work / "rendered"
    pdfs.mkdir(parents=True, exist_ok=True)
    rendered.mkdir(parents=True, exist_ok=True)
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm is required")
    for date in DATES:
        year, name, expected = MAPS[date]
        pdf = pdfs / f"{date}.pdf"
        if not pdf.exists() or sha256(pdf) != expected:
            url = f"{BASE_URL}/{year}/{urllib.parse.quote(name)}"
            temporary = pdf.with_suffix(".download")
            urllib.request.urlretrieve(url, temporary)
            if sha256(temporary) != expected:
                temporary.unlink(missing_ok=True)
                raise ValueError(f"hash mismatch for {date}")
            os.replace(temporary, pdf)
        target = rendered / date
        target.mkdir(exist_ok=True)
        if len(list(target.glob("page-*.jpg"))) != 10:
            for old in target.glob("page-*.jpg"):
                old.unlink()
            subprocess.run([
                "pdftoppm", "-jpeg", "-r", str(dpi), "-f", "1", "-l", "10",
                "-jpegopt", "quality=92", str(pdf), str(target / "page")
            ], check=True, stdout=subprocess.DEVNULL)
            generated = sorted(target.glob("page-*.jpg"))
            if len(generated) != 10:
                raise ValueError(f"expected 10 pages for {date}, got {len(generated)}")
            for index, source in enumerate(generated, 1):
                destination = target / f"page-{index:02d}.jpg"
                if source != destination:
                    source.replace(destination)
    return rendered


def _schedule(primary: list[dict], repeats: list[dict], seed: int) -> list[dict]:
    """Insert repeats at non-adjacent, concealed positions after their source."""
    rng = random.Random(seed + 1)
    schedule = list(primary)
    rng.shuffle(repeats)
    for repeat in repeats:
        source_index = next(i for i, row in enumerate(schedule) if row["source_key"] == repeat["source_key"])
        low = min(len(schedule), source_index + 8)
        candidates = list(range(low, len(schedule) + 1)) or [len(schedule)]
        position = rng.choice(candidates)
        schedule.insert(position, repeat)
    for index, row in enumerate(schedule, 1):
        row["display_order"] = index
    return schedule


def prepare_packet(render_root: Path, packet: Path, seed: int = 22016) -> dict:
    if packet.exists():
        raise ValueError(f"refusing to overwrite packet: {packet}")
    images, records = packet / "images", packet / "records"
    images.mkdir(parents=True)
    records.mkdir()
    primary: list[dict] = []
    for date_index, date in enumerate(DATES):
        for page in range(1, 11):
            source = render_root / date / f"page-{page:02d}.jpg"
            if not source.is_file():
                raise FileNotFoundError(source)
            task_id = f"M{len(primary) + 1:04d}"
            source_key = f"{date}_p{page:02d}"
            destination = images / f"{source_key}.jpg"
            shutil.copy2(source, destination)
            width, height = image_size(destination)
            primary.append({
                "task_id": task_id, "source_key": source_key, "survey_date": date,
                "page": page, "page_start_ft": (page - 1) * 50,
                "page_end_ft": page * 50, "image": destination.name,
                "image_width_px": width, "image_height_px": height,
                "is_repeat": False, "primary_task_id": task_id,
                "date_index": date_index,
            })
    rng = random.Random(seed)
    chosen = rng.sample(primary, 14)
    repeats = []
    for index, source in enumerate(chosen, 1):
        row = dict(source)
        row.update(task_id=f"M{70 + index:04d}", is_repeat=True, primary_task_id=source["task_id"])
        repeats.append(row)
    schedule = _schedule(primary, repeats, seed)
    public = []
    private = {}
    for row in schedule:
        task_id = row["task_id"]
        public_row = {key: row[key] for key in (
            "task_id", "survey_date", "page", "page_start_ft", "page_end_ft",
            "image_width_px", "image_height_px", "display_order",
        )}
        public.append(public_row)
        private[task_id] = row
        record = {
            "type": "FeatureCollection",
            "schema_version": "mnroad_single_owner_crack_centrelines_v1",
            "task_id": task_id,
            "section_id": SECTION,
            "survey_date": row["survey_date"],
            "page_start_ft": row["page_start_ft"],
            "page_end_ft": row["page_end_ft"],
            "coordinate_system": "source_image_pixels_top_left_origin",
            "no_target_confirmed": False,
            "phase1_locked": False,
            "phase2_locked": False,
            "features": [],
        }
        atomic_json(records / f"{task_id}.geojson", record)
    manifest = {
        "schema_version": "mnroad_single_owner_packet_v1", "status": STATUS,
        "created_at_utc": utc_now(), "section_id": SECTION,
        "eligible_dates": list(DATES), "first_relevant_intervention": CUTOFF,
        "primary_tasks": 70, "concealed_repeat_tasks": 14, "total_tasks": 84,
        "first_pass_policy": "No Excel totals, no other survey image, no crack_id linking.",
        "tasks": public,
    }
    atomic_json(packet / "manifest.json", manifest)
    atomic_json(packet / "private_repeat_key.json", {"seed": seed, "tasks": private})
    receipt_files = sorted(images.glob("*.jpg")) + [packet / "manifest.json"]
    (packet / "frozen_inputs.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(packet)}\n" for path in receipt_files), encoding="ascii"
    )
    return manifest


def validate_record(payload: dict, expected: dict, phase: int) -> None:
    if payload.get("type") != "FeatureCollection" or payload.get("task_id") != expected["task_id"]:
        raise ValueError("record identity mismatch")
    if payload.get("section_id") != SECTION or payload.get("survey_date") != expected["survey_date"]:
        raise ValueError("section/date mismatch")
    if not isinstance(payload.get("features"), list):
        raise ValueError("features must be a list")
    if "no_target_confirmed" in payload and not isinstance(payload["no_target_confirmed"], bool):
        raise ValueError("no_target_confirmed must be boolean")
    if payload.get("features") and payload.get("no_target_confirmed"):
        raise ValueError("a task cannot contain features and be confirmed empty")
    seen = set()
    for feature in payload["features"]:
        if feature.get("type") != "Feature" or feature.get("geometry", {}).get("type") != "LineString":
            raise ValueError("every feature must be a GeoJSON LineString")
        coordinates = feature["geometry"].get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise ValueError("LineString needs at least two points")
        if any(not isinstance(point, list) or len(point) != 2 or not all(math.isfinite(float(value)) for value in point) for point in coordinates):
            raise ValueError("invalid coordinates")
        props = feature.get("properties", {})
        segment_id = props.get("segment_id")
        if not isinstance(segment_id, str) or not segment_id or segment_id in seen:
            raise ValueError("segment_id must be unique and non-empty")
        seen.add(segment_id)
        checks = (
            ("lane", LANES), ("distress_class", CLASSES), ("severity", SEVERITIES),
            ("sealed", TRISTATE), ("mark_owner_date", OWNER_DATES), ("confidence", CONFIDENCE),
        )
        for key, allowed in checks:
            if props.get(key) not in allowed:
                raise ValueError(f"invalid {key}")
        reference_task = props.get("owner_reference_task_id")
        if reference_task:
            if props.get("mark_owner_date") != "earlier":
                raise ValueError("cross-time owner reference requires mark_owner_date=earlier")
            if reference_task != expected.get("previous_task_id"):
                raise ValueError("owner reference is not the previous same-station task")
            if props.get("owner_reference_survey_date") != expected.get("previous_survey_date"):
                raise ValueError("owner reference survey date mismatch")
            if props.get("temporal_confirmation") != "same_station_prior_map":
                raise ValueError("invalid temporal confirmation")
        if phase == 1 and (props.get("crack_id") or props.get("change_type")):
            raise ValueError("phase 1 cannot contain crack identity")
        if phase == 2:
            if props.get("change_type") not in CHANGE_TYPES:
                raise ValueError("phase 2 requires change_type")
            if props["change_type"] != "unresolvable" and not str(props.get("crack_id", "")).strip():
                raise ValueError("phase 2 requires crack_id unless unresolvable")


HTML = r'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>MnROAD 裂缝中心线标注器</title>
<style>*{box-sizing:border-box}body{margin:0;background:#171a1d;color:#e9ecef;font:14px system-ui}header{height:54px;padding:9px 14px;background:#20252a;border-bottom:1px solid #59616a;display:flex;align-items:center;gap:18px}.badge{background:#ffc857;color:#111;padding:5px 9px;border-radius:4px;font-weight:800}.warn{color:#ffc857}main{display:grid;grid-template-columns:minmax(0,1fr) 370px;gap:8px;height:calc(100vh - 54px);padding:8px}.viewport{overflow:auto;background:#54585c;border:1px solid #77808a;position:relative}.stage{position:relative}.rotator{position:absolute;left:0;top:0;transform-origin:0 0}.rotator img{display:block;user-select:none}.rotator svg{position:absolute;inset:0;cursor:crosshair}.side{background:#252a2f;border:1px solid #59616a;padding:10px;overflow:auto}.row{display:grid;grid-template-columns:1fr 1fr;gap:7px}.meta{padding:8px;background:#15191c;line-height:1.55;margin-bottom:8px}.help{border-left:4px solid #42d3ff;background:#17333b;padding:8px;line-height:1.45}.cross-time{border-left:4px solid #ffca4b;background:#493713;padding:7px;margin:6px 0;line-height:1.4}.instructions{background:#30373d;border:1px solid #68727b;padding:7px;margin:7px 0;line-height:1.45}.instructions summary{cursor:pointer;font-weight:800;color:#9ce8ff}.instructions ol{padding-left:20px;margin:7px 0}.instructions p{margin:6px 0}.zero{background:#765515;color:white;border:1px solid #ffca4b}.zero.confirmed{background:#167f59;border-color:#54e5ad}button,select,input,textarea{width:100%;padding:7px;margin:3px 0;background:#f6f7f8;color:#111;border:1px solid #aaa;border-radius:3px}button{cursor:pointer;font-weight:650}button.primary{background:#20b486;color:white;border:0}button.cross{background:#8c681d;color:white;border:1px solid #ffca4b}button.danger{background:#8e3140;color:white;border:0}button:disabled{opacity:.45;cursor:not-allowed}textarea{height:55px}.line{fill:none;stroke:#00e0ff;stroke-width:3;vector-effect:non-scaling-stroke}.line.selected{stroke:#ffcf33;stroke-width:5}.draft{fill:none;stroke:#ff4d7d;stroke-width:4;stroke-dasharray:8 5;vector-effect:non-scaling-stroke}.vertex{fill:#ffcf33;stroke:#111;stroke-width:1}.status{min-height:22px;color:#67e8a5}.bad{color:#ff8294}.progress{height:8px;background:#111}.progress div{height:100%;background:#20b486}.small{font-size:12px;color:#bbc2c9}label{display:block;margin-top:5px}kbd{background:#111;padding:2px 5px;border-radius:3px}@media(max-width:900px){main{grid-template-columns:1fr;height:auto}.viewport{height:60vh}}</style></head><body>
<header><b>MnROAD Cell 22 裂缝中心线标注器</b><span id="phaseBadge" class="badge"></span><span class="warn">仅用于人工矢量化资格验证</span></header>
<main><section class="viewport" id="viewport"><div class="stage" id="stage"><div class="rotator" id="rotator"><img id="image" draggable="false"><svg id="overlay"></svg></div></div></section><aside class="side">
<div class="meta" id="meta"></div><div class="progress"><div id="progress"></div></div><div class="small" id="progressText"></div>
<div class="help" id="help"></div>
<details class="instructions" id="instructions" open><summary>什么时候点击什么？</summary><ol><li>先只检查黑色虚线与 10-foot shoulder 之间的 <b>Driving lane</b>。</li><li>若有 NWP：点“新裂缝线”，沿裂缝中心逐点点击，按 Enter，填写属性，再保存。</li><li>若确认没有 Driving-lane NWP：不要画线，点“确认本页无目标裂缝”，再保存并锁定。</li><li>若痕迹存在但无法判断：画线，Class 选 <b>unresolvable</b>，不要当成零。</li></ol><p class="small">忽略网格、车道虚线、路肩边线、黄色/印刷参考线、文字和北向箭头。第一阶段不要查看 Excel 总量。</p></details>
<div class="row"><button id="prev">← 上一任务</button><button id="next">下一任务 →</button></div>
<div class="row"><button id="newLine" class="primary">新裂缝线 N</button><button id="finishLine">结束当前线 Enter</button></div>
<div class="row"><button id="undoPoint">撤销点 Z</button><button id="deleteLine" class="danger">删除选中线</button></div>
<button id="noTarget" class="zero">确认本页无目标裂缝（0）</button>
<label>选中 segment</label><select id="featureSelect"></select>
<div class="row"><label>Lane<select id="lane"><option>Driving</option><option>Passing</option><option>shoulder</option><option>joint</option></select></label><label>Class<select id="distress"><option>NWP</option><option>WP</option><option>construction_joint</option><option>other</option><option>unresolvable</option></select></label></div>
<div class="row"><label>Severity<select id="severity"><option>L</option><option>M</option><option>H</option><option>unknown</option></select></label><label>Sealed<select id="sealed"><option>no</option><option>yes</option><option>unknown</option></select></label></div>
<div class="row"><label>Mark owner<select id="owner"><option>current</option><option>earlier</option><option>unknown</option></select></label><label>Confidence<select id="confidence"><option>high</option><option>medium</option><option>low</option></select></label></div>
<div id="ownerEvidence" class="small"></div><div class="row"><button id="priorMap" class="cross">打开上一期同站点图</button><button id="confirmEarlier" class="cross">选中线：跨期确认 earlier</button></div><div id="crossTimeBadge"></div>
<div id="linkFields"><div class="row"><label>Lineage ID<input id="crackId" placeholder="L001"></label><label>Legacy change<select id="change"><option>persistent</option><option>extension</option><option>nucleation</option><option>not_observed</option><option>unresolvable</option></select></label></div><div id="lineageEvidence" class="cross-time"></div></div>
<label>Note<textarea id="note"></textarea></label><div class="row"><button id="save" class="primary">保存草稿 S</button><button id="lock">锁定本任务</button></div>
<button id="orientation">切换为纵向视图</button><div class="row"><button id="zoomOut">− 缩小</button><button id="zoomIn">＋ 放大</button></div><div id="feedback" class="status"></div>
</aside></main><script>
let phase=location.pathname==='/link'?2:1,tasks=[],index=0,currentTask=null,record=null,selected=-1,draft=[],dirty=false,zoom=1,landscape=localStorage.getItem('mnroad_orientation')!=='portrait';
const requestedTask=new URLSearchParams(location.search).get('task');
const $=id=>document.getElementById(id),image=$('image'),overlay=$('overlay'),stage=$('stage'),rotator=$('rotator'),feedback=$('feedback');
function say(t,b=false){feedback.textContent=t;feedback.className=b?'status bad':'status'}
function esc(t){return String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function props(){return selected>=0?record.features[selected].properties:null}
function line(points,klass){const p=document.createElementNS('http://www.w3.org/2000/svg','polyline');p.setAttribute('points',points.map(q=>q.join(',')).join(' '));p.setAttribute('class',klass);overlay.appendChild(p);return p}
function render(){if(!record)return;overlay.innerHTML='';overlay.setAttribute('width',image.naturalWidth);overlay.setAttribute('height',image.naturalHeight);overlay.setAttribute('viewBox',`0 0 ${image.naturalWidth} ${image.naturalHeight}`);record.features.forEach((f,i)=>{const path=line(f.geometry.coordinates,'line '+(i===selected?'selected':''));path.onclick=e=>{if(phase!==2)return;e.stopPropagation();selected=i;render();say(`已选择 ${f.properties.segment_id} · ${f.properties.lineage_id||f.properties.crack_id||'未决'} · ${f.properties.relation_type||f.properties.change_type||'未分类'}`)};f.geometry.coordinates.forEach(q=>{if(i!==selected)return;const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',q[0]);c.setAttribute('cy',q[1]);c.setAttribute('r',5);c.setAttribute('class','vertex');overlay.appendChild(c)})});if(draft.length)line(draft,'draft');$('featureSelect').innerHTML='<option value="-1">— 未选择 —</option>'+record.features.map((f,i)=>`<option value="${i}">${esc(f.properties.segment_id)} · ${esc(f.properties.lineage_id||f.properties.crack_id||'未决')} · ${esc(f.properties.relation_type||f.properties.change_type||'未分类')}${f.properties.owner_reference_task_id?' ✓跨期':''}</option>`).join('');$('featureSelect').value=selected;const empty=!!record.no_target_confirmed;$('noTarget').textContent=empty?'✓ 已确认：本页无目标裂缝':'确认本页无目标裂缝（0）';$('noTarget').className=empty?'zero confirmed':'zero';$('noTarget').disabled=phase===2||record.phase1_locked;$('priorMap').disabled=!currentTask?.previous_task_id;$('confirmEarlier').disabled=!props()||!currentTask?.previous_task_id||record[`phase${phase}_locked`];const viewed=record.cross_time_reference_viewed;$('crossTimeBadge').innerHTML=viewed?`<div class="cross-time"><b>跨期确认模式</b><br>已查看 ${esc(viewed.survey_date)} · ${esc(viewed.task_id)}；本任务不再属于单页盲标。</div>`:'';fillFields();}
function fillFields(){const p=props();for(const id of ['lane','distress','severity','sealed','owner','confidence','note','crackId','change'])$(id).disabled=!p||record[`phase${phase}_locked`];$('ownerEvidence').textContent=p?.owner_reference_task_id?`✓ earlier 已由 ${p.owner_reference_survey_date} · ${p.owner_reference_task_id} 同站点地图确认`:'';$('lineageEvidence').style.display=phase===2&&p?'block':'none';$('lineageEvidence').innerHTML=p?`<b>${esc(p.relation_type||'未分类')}</b> · confidence ${esc(p.mapping_confidence||'未记录')}<br>前驱 segment：${esc((p.predecessor_segment_ids||[]).join(', ')||'无')}`:'';if(!p)return;$('lane').value=p.lane;$('distress').value=p.distress_class;$('severity').value=p.severity;$('sealed').value=p.sealed;$('owner').value=p.mark_owner_date;$('confidence').value=p.confidence;$('note').value=p.note||'';$('crackId').value=p.lineage_id||p.crack_id||'';$('change').value=p.change_type||'unresolvable'}
function setView(v=zoom){zoom=Math.max(.35,Math.min(3,v));const w=image.naturalWidth,h=image.naturalHeight;if(!w||!h)return;if(landscape){const clockwise=currentTask?.landscape_rotation_deg===90;stage.style.width=`${h*zoom}px`;stage.style.height=`${w*zoom}px`;rotator.style.transform=clockwise?`translate(${h*zoom}px,0) rotate(90deg) scale(${zoom})`:`translate(0,${w*zoom}px) rotate(-90deg) scale(${zoom})`;$('orientation').textContent='切换为纵向视图'}else{stage.style.width=`${w*zoom}px`;stage.style.height=`${h*zoom}px`;rotator.style.transform=`scale(${zoom})`;$('orientation').textContent='切换为横向视图'}}
async function load(i){if(dirty&&!confirm('当前任务尚未保存，放弃改动？'))return;index=Math.max(0,Math.min(tasks.length-1,i));const t=tasks[index];currentTask=t;record=await fetch(`/api/record/${t.task_id}?phase=${phase}`).then(async r=>{if(!r.ok)throw Error(await r.text());return r.json()});selected=record.features.length?0:-1;draft=[];dirty=false;$('meta').innerHTML=`<b>${esc(t.task_id)}</b>　${esc(t.survey_date)}<br>Station ${t.page_start_ft}–${t.page_end_ft} ft　Page ${t.page}/10<br>Target: Driving lane / NWP　方向：0′ → 50′（左 → 右）`;$('progress').style.width=`${100*(index+1)/tasks.length}%`;$('progressText').textContent=`任务 ${index+1}/${tasks.length}`;image.src=`/image/${t.task_id}`;image.onload=()=>{setView(zoom);render()};$('lock').disabled=record[`phase${phase}_locked`];if(phase===1&&t.task_id==='M0061')$('help').innerHTML='<b>M0061 已重开：</b>请重新区分 FL 与 NWP。保留、删除或重画由你依据原图决定；只提交 Driving lane / NWP，完成后保存并锁定阶段1。不要用 maintenance-censored 代替类别判断。';else if(phase===1&&t.task_id==='M0042')$('help').innerHTML='<b>M0042 已重开：</b>你判断右侧约 32–50 ft 为 FL。请逐条选择并删除该非目标区域的线，只保留或重画 Driving lane / NWP；完成后保存并锁定阶段1。';else if(phase===1&&t.task_id==='M0032')$('help').innerHTML='<b>M0032 已重开：</b>请补画你确认漏掉的 Driving lane / NWP 中心线；不要为了匹配 Excel 50 ft 而扩线。完成后保存并锁定阶段1。';render()}
function newLine(){if(phase===2)return say('阶段 2 只连接身份，不修改几何',true);record.no_target_confirmed=false;selected=-1;draft=[];dirty=true;render();say('逐点点击裂缝中心线；Enter 或双击结束')}
function finish(){if(phase===2||draft.length<2)return say('至少需要两个点',true);record.no_target_confirmed=false;const id=`${record.task_id}-S${String(record.features.length+1).padStart(3,'0')}`;record.features.push({type:'Feature',geometry:{type:'LineString',coordinates:draft},properties:{section_id:'22-D-2016',survey_date:record.survey_date,page_start_ft:record.page_start_ft,lane:'Driving',distress_class:'NWP',severity:'unknown',sealed:'unknown',segment_id:id,mark_owner_date:'unknown',confidence:'medium',note:'',crack_id:'',change_type:''}});selected=record.features.length-1;draft=[];dirty=true;render();say('中心线已加入，请填写属性')}
overlay.onclick=e=>{if(phase===2||record.phase1_locked)return;const matrix=overlay.getScreenCTM();if(!matrix)return;const local=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix.inverse()),p=[Math.round(local.x),Math.round(local.y)];if(p[0]<0||p[1]<0||p[0]>image.naturalWidth||p[1]>image.naturalHeight)return;draft.push(p);dirty=true;render()};overlay.ondblclick=e=>{e.preventDefault();if(draft.length>2)draft.pop();finish()};
function bind(id,key){$(id).onchange=e=>{const p=props();if(!p)return;p[key]=e.target.value;dirty=true;render()}}
bind('lane','lane');bind('distress','distress_class');bind('severity','severity');bind('sealed','sealed');bind('confidence','confidence');bind('note','note');bind('crackId','crack_id');bind('change','change_type');
$('owner').onchange=e=>{const p=props();if(!p)return;p.mark_owner_date=e.target.value;if(p.mark_owner_date!=='earlier'){delete p.owner_reference_task_id;delete p.owner_reference_survey_date;delete p.temporal_confirmation}dirty=true;render()};
$('featureSelect').onchange=e=>{selected=+e.target.value;render()};$('newLine').onclick=newLine;$('finishLine').onclick=finish;$('undoPoint').onclick=()=>{if(draft.length)draft.pop();else if(selected>=0&&record.features[selected].geometry.coordinates.length>2)record.features[selected].geometry.coordinates.pop();dirty=true;render()};$('deleteLine').onclick=()=>{if(selected<0||phase===2)return;if(confirm('删除选中的中心线？')){record.features.splice(selected,1);selected=Math.min(selected,record.features.length-1);dirty=true;render()}};
$('noTarget').onclick=()=>{if(record.features.length||draft.length)return say('已有线段或未完成线；请先核对并删除，不能同时标记为零。',true);record.no_target_confirmed=!record.no_target_confirmed;dirty=true;render();say(record.no_target_confirmed?'已记录“人工检查后为零”；请保存并锁定。':'已取消零裂缝确认。')};
async function save(lock=false){if(draft.length)return say('请先结束或清空当前未完成线',true);const t=tasks[index],r=await fetch(`/api/record/${t.task_id}?phase=${phase}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(record)});if(!r.ok)return say(await r.text(),true);if(lock){const q=await fetch(`/api/lock/${t.task_id}?phase=${phase}`,{method:'POST'});if(!q.ok)return say(await q.text(),true)}dirty=false;await refresh();await load(index);say(lock?'任务已锁定':'草稿已原子保存')}
async function refresh(){const r=await fetch(`/api/tasks?phase=${phase}`);if(!r.ok)throw Error(await r.text());tasks=await r.json()}
$('save').onclick=()=>save(false);$('lock').onclick=()=>{if(confirm('锁定后本阶段不可修改，确定？'))save(true)};$('prev').onclick=()=>load(index-1);$('next').onclick=()=>load(index+1);$('zoomIn').onclick=()=>setView(zoom+.15);$('zoomOut').onclick=()=>setView(zoom-.15);$('orientation').onclick=()=>{landscape=!landscape;localStorage.setItem('mnroad_orientation',landscape?'landscape':'portrait');setView(zoom)};
$('priorMap').onclick=()=>{if(!currentTask?.previous_task_id)return say('没有上一期同站点地图',true);if(!confirm('打开前期地图后，本任务将标记为“跨期确认”，不再属于严格单页盲标。继续？'))return;record.cross_time_reference_viewed={task_id:currentTask.previous_task_id,survey_date:currentTask.previous_survey_date,viewed_at:new Date().toISOString()};dirty=true;render();window.open(`/reference/${currentTask.previous_task_id}`,'_blank','noopener');say('已打开上一期同站点图；请保存当前任务以保留跨期查看记录。')};
$('confirmEarlier').onclick=()=>{const p=props();if(!p||!currentTask?.previous_task_id)return say('请先选择一条线，并打开上一期地图核对',true);if(!record.cross_time_reference_viewed)return say('请先打开上一期同站点图核对',true);p.mark_owner_date='earlier';p.owner_reference_task_id=currentTask.previous_task_id;p.owner_reference_survey_date=currentTask.previous_survey_date;p.temporal_confirmation='same_station_prior_map';dirty=true;render();say(`已标记：earlier，由 ${currentTask.previous_survey_date} · ${currentTask.previous_task_id} 跨期确认`)};
document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName))return;if(e.key==='n'){e.preventDefault();newLine()}else if(e.key==='Enter'){e.preventDefault();finish()}else if(e.key==='z'){e.preventDefault();$('undoPoint').click()}else if(e.key==='s'){e.preventDefault();save(false)}else if(e.key==='ArrowRight')load(index+1);else if(e.key==='ArrowLeft')load(index-1)});window.onbeforeunload=e=>{if(dirty){e.preventDefault();e.returnValue=''}};
(async()=>{$('phaseBadge').textContent=phase===1?'阶段 1：盲化几何':'阶段 2：时间谱系';$('linkFields').style.display=phase===2?'block':'none';$('newLine').disabled=phase===2;$('finishLine').disabled=phase===2;if(phase===2)$('instructions').innerHTML='<summary>怎么看自动映射？</summary><ol><li>点击青色线，或在 segment 下拉框中选择一条线。</li><li>查看 Lineage ID、relation 和前驱 segment；同一 lineage 可跨日期复用。</li><li>bridging_merge / split_redraw 表示后一期覆盖、连接或重分段，不是自动新生。</li><li>阶段2只有 70 个主页面；重复 QC 页已排除。</li></ol>';$('help').innerHTML=phase===1?'只看当前页。沿裂缝<b>中心</b>逐点点击；不要看 Excel 总量，不跨车道猜测。模糊痕迹使用 <b>unresolvable</b>。':'几何已冻结。这里显示的是跨期<b>谱系关系</b>：continuation / extension / redraw / split_redraw / bridging_merge / nucleation。严禁跨越 2019-10-24。';try{await refresh();const requestedIndex=tasks.findIndex(t=>t.task_id===requestedTask);await load(requestedIndex>=0?requestedIndex:0)}catch(e){say(e.message,true)}})();
</script></body></html>'''


class Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], packet: Path):
        super().__init__(address, Handler)
        self.packet = packet.resolve()
        self.manifest = json.loads((self.packet / "manifest.json").read_text())
        self.private = json.loads((self.packet / "private_repeat_key.json").read_text())["tasks"]
        primary = {
            (row["survey_date"], row["page"]): task_id
            for task_id, row in self.private.items() if not row["is_repeat"]
        }
        date_index = {date: index for index, date in enumerate(DATES)}
        self.tasks = []
        for row in self.manifest["tasks"]:
            index = date_index[row["survey_date"]]
            previous_date = DATES[index - 1] if index else None
            self.tasks.append({
                **row,
                "landscape_rotation_deg": landscape_rotation_degrees(row["survey_date"]),
                "is_concealed_repeat": self.private[row["task_id"]]["is_repeat"],
                "previous_task_id": primary.get((previous_date, row["page"])) if previous_date else None,
                "previous_survey_date": previous_date,
            })
        self.by_id = {row["task_id"]: row for row in self.tasks}

    def all_phase1_locked(self) -> bool:
        return all(json.loads((self.packet / "records" / f"{row['task_id']}.geojson").read_text())["phase1_locked"] for row in self.tasks)


class Handler(BaseHTTPRequestHandler):
    server: Server

    def send(self, payload: bytes, kind: str, status: int = 200) -> None:
        self.send_response(status); self.send_header("Content-Type", kind); self.send_header("Content-Length", str(len(payload))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(payload)

    def fail(self, message: str, status: int = 400) -> None:
        self.send(message.encode(), "text/plain; charset=utf-8", status)

    def phase(self) -> int:
        return int(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("phase", ["1"])[0])

    def task_id(self, prefix: str) -> str | None:
        value = urllib.parse.urlparse(self.path).path.removeprefix(prefix)
        return value if value in self.server.by_id else None

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/link"):
            return self.send(HTML.encode(), "text/html; charset=utf-8")
        if path == "/api/tasks":
            phase = self.phase()
            if phase == 2 and not self.server.all_phase1_locked():
                return self.fail("阶段 2 尚未开放：请先锁定全部 84 个阶段 1 任务。", 409)
            tasks = self.server.tasks if phase == 1 else sorted(
                (row for row in self.server.tasks if not row["is_concealed_repeat"]),
                key=lambda row: (row["survey_date"], row["page"], row["display_order"]),
            )
            return self.send(json.dumps(tasks).encode(), "application/json")
        if path.startswith("/api/record/"):
            task = self.task_id("/api/record/")
            return self.send((self.server.packet / "records" / f"{task}.geojson").read_bytes(), "application/geo+json") if task else self.fail("invalid task", 404)
        if path.startswith("/image/"):
            task = self.task_id("/image/")
            if not task:
                return self.fail("invalid task", 404)
            name = self.server.private[task]["image"]
            return self.send((self.server.packet / "images" / name).read_bytes(), "image/jpeg")
        if path.startswith("/reference/"):
            task = self.task_id("/reference/")
            if not task:
                return self.fail("invalid task", 404)
            row = self.server.by_id[task]
            angle = row["landscape_rotation_deg"]
            html = f'''<!doctype html><meta charset="utf-8"><title>跨期参考 {task}</title>
<style>body{{margin:0;background:#20252a;color:#fff;font:16px system-ui}}header{{padding:10px 14px;background:#111820;position:sticky;top:0;z-index:2}}canvas{{display:block;background:white;max-width:none}}</style>
<header><b>跨期参考：{task}</b>　{row["survey_date"]}　Station {row["page_start_ft"]}–{row["page_end_ft"]} ft<br><small>仅用于确认 earlier 来源；此窗口不写入标注。</small></header>
<canvas id="c"></canvas><img id="i" src="/image/{task}" hidden><script>const i=document.getElementById('i'),c=document.getElementById('c');i.onload=()=>{{c.width=i.naturalHeight;c.height=i.naturalWidth;const x=c.getContext('2d');if({angle}===90){{x.translate(i.naturalHeight,0);x.rotate(Math.PI/2)}}else{{x.translate(0,i.naturalWidth);x.rotate(-Math.PI/2)}}x.drawImage(i,0,0)}};</script>'''
            return self.send(html.encode(), "text/html; charset=utf-8")
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        prefix = "/api/record/" if path.startswith("/api/record/") else "/api/lock/" if path.startswith("/api/lock/") else None
        if not prefix:
            return self.fail("not found", 404)
        task = self.task_id(prefix)
        if not task:
            return self.fail("invalid task", 404)
        phase = self.phase()
        if phase not in (1, 2) or (phase == 2 and not self.server.all_phase1_locked()):
            return self.fail("phase not available", 409)
        target = self.server.packet / "records" / f"{task}.geojson"
        current = json.loads(target.read_text())
        if current.get(f"phase{phase}_locked"):
            return self.fail("phase is locked", 409)
        if prefix == "/api/record/":
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                validate_record(payload, self.server.private[task], phase)
                if phase == 2 and payload.get("features") != current.get("features"):
                    if len(payload["features"]) != len(current["features"]):
                        raise ValueError("phase 2 cannot add or remove geometry")
                    for old, new in zip(current["features"], payload["features"]):
                        if old["geometry"] != new["geometry"] or old["properties"]["segment_id"] != new["properties"]["segment_id"]:
                            raise ValueError("phase 2 cannot alter geometry or segment_id")
                payload[f"phase{phase}_saved_at_utc"] = utc_now()
                atomic_json(target, payload)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                return self.fail(str(error))
            return self.send(b'{"saved":true}', "application/json")
        try:
            validate_record(current, self.server.private[task], phase)
        except ValueError as error:
            return self.fail(str(error))
        if phase == 1 and not current["features"] and not current.get("no_target_confirmed"):
            return self.fail("空白页必须先点击“确认本页无目标裂缝（0）”，才能锁定。")
        current[f"phase{phase}_locked"] = True
        current[f"phase{phase}_locked_at_utc"] = utc_now()
        atomic_json(target, current)
        return self.send(b'{"locked":true}', "application/json")

    def log_message(self, format: str, *args: object) -> None:
        pass


def feature_length(feature: dict, pixels_per_foot: float) -> float:
    points = feature["geometry"]["coordinates"]
    return sum(math.dist(a, b) for a, b in zip(points, points[1:])) / pixels_per_foot


def _densify(feature: dict, step_px: float = 5.0) -> list[list[float]]:
    output = []
    points = feature["geometry"]["coordinates"]
    for first, second in zip(points, points[1:]):
        length = math.dist(first, second)
        count = max(1, int(math.ceil(length / step_px)))
        output.extend([[first[0] + (second[0] - first[0]) * i / count, first[1] + (second[1] - first[1]) * i / count] for i in range(count)])
    output.append(points[-1])
    return output


def _point_segment_distance(point: list[float], first: list[float], second: list[float]) -> float:
    dx, dy = second[0] - first[0], second[1] - first[1]
    denom = dx * dx + dy * dy
    if denom == 0:
        return math.dist(point, first)
    t = max(0.0, min(1.0, ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy) / denom))
    return math.hypot(point[0] - (first[0] + t * dx), point[1] - (first[1] + t * dy))


def symmetric_vector_distance(first: list[dict], second: list[dict], pixels_per_foot: float) -> float | None:
    if not first and not second:
        return 0.0
    if not first or not second:
        return None
    def directed(source: list[dict], target: list[dict]) -> list[float]:
        segments = [(a, b) for feature in target for a, b in zip(feature["geometry"]["coordinates"], feature["geometry"]["coordinates"][1:])]
        return [min(_point_segment_distance(point, a, b) for a, b in segments) for feature in source for point in _densify(feature)]
    values = directed(first, second) + directed(second, first)
    values.sort()
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    return median / pixels_per_foot


def _target_features(record: dict) -> list[dict]:
    return [feature for feature in record["features"] if feature["properties"]["lane"] == "Driving" and feature["properties"]["distress_class"] == "NWP"]


def crack_id_length_agreement(first: list[dict], second: list[dict], pixels_per_foot: float) -> float | None:
    def lengths(features: list[dict]) -> dict[str, float]:
        result = {}
        for feature in features:
            crack_id = str(feature["properties"].get("crack_id", "")).strip()
            if not crack_id:
                return {}
            result[crack_id] = result.get(crack_id, 0.0) + feature_length(feature, pixels_per_foot)
        return result
    a, b = lengths(first), lengths(second)
    if not a and not b:
        return 1.0 if not first and not second else None
    if not a or not b:
        return None
    denominator = max(sum(a.values()), sum(b.values()))
    return 1.0 if denominator == 0 else sum(min(a.get(key, 0.0), b.get(key, 0.0)) for key in set(a) | set(b)) / denominator


def export_packet(packet: Path, output: Path, pixels_per_foot: float) -> dict:
    manifest = json.loads((packet / "manifest.json").read_text())
    private = json.loads((packet / "private_repeat_key.json").read_text())["tasks"]
    primary_features, all_features, repeat_rows = [], [], []
    records = {}
    for task in manifest["tasks"]:
        task_id = task["task_id"]
        record = json.loads((packet / "records" / f"{task_id}.geojson").read_text())
        records[task_id] = record
        for feature in record["features"]:
            item = json.loads(json.dumps(feature))
            item["properties"].update(task_id=task_id, page=task["page"], is_concealed_repeat=private[task_id]["is_repeat"])
            all_features.append(item)
            if not private[task_id]["is_repeat"]:
                primary_features.append(item)
    phase1_locked = sum(bool(record.get("phase1_locked")) for record in records.values())
    phase2_locked = sum(bool(record.get("phase2_locked")) for record in records.values())
    qc_ready = phase1_locked == len(records) and phase2_locked == len(records)
    for task_id, row in private.items():
        if not row["is_repeat"]:
            continue
        first, second = records[row["primary_task_id"]], records[task_id]
        first_target, second_target = _target_features(first), _target_features(second)
        a = sum(feature_length(feature, pixels_per_foot) for feature in first_target)
        b = sum(feature_length(feature, pixels_per_foot) for feature in second_target)
        repeat_rows.append({
            "primary_task_id": row["primary_task_id"], "repeat_task_id": task_id,
            "length_a_ft": a, "length_b_ft": b,
            "total_length_agreement": 1.0 if max(a, b) == 0 else min(a, b) / max(a, b),
            "crack_id_length_agreement": crack_id_length_agreement(first_target, second_target, pixels_per_foot),
            "median_symmetric_distance_ft": symmetric_vector_distance(first_target, second_target, pixels_per_foot),
        })
    crack_id_scores = [row["crack_id_length_agreement"] for row in repeat_rows if row["crack_id_length_agreement"] is not None]
    distances = sorted(row["median_symmetric_distance_ft"] for row in repeat_rows if row["median_symmetric_distance_ft"] is not None)
    median_distance = None if not distances else distances[len(distances) // 2] if len(distances) % 2 else (distances[len(distances)//2 - 1] + distances[len(distances)//2]) / 2
    summary = {
        "status": STATUS, "created_at_utc": utc_now(), "pixels_per_foot": pixels_per_foot,
        "primary_feature_count": len(primary_features), "all_feature_count": len(all_features),
        "completion": {"phase1_locked": phase1_locked, "phase2_locked": phase2_locked, "total_tasks": len(records), "qc_ready": qc_ready},
        "repeat_pairs": repeat_rows,
        "mean_repeat_total_length_agreement": sum(r["total_length_agreement"] for r in repeat_rows) / len(repeat_rows),
        "mean_repeat_crack_id_length_agreement": None if not crack_id_scores else sum(crack_id_scores) / len(crack_id_scores),
        "median_repeat_symmetric_distance_ft": median_distance,
        "repeat_gate": {
            "crack_id_length_agreement_at_least_0_8": None if not qc_ready or not crack_id_scores else sum(crack_id_scores) / len(crack_id_scores) >= 0.8,
            "median_symmetric_distance_at_most_1_ft": None if not qc_ready or median_distance is None else median_distance <= 1.0,
        },
        "limitations": ["Pixel-to-foot length and distance use the supplied scale.", "Lane leakage and Excel reconciliation still require review.", "Export metrics do not by themselves establish persistent physical-crack identity."],
    }
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "mnroad_22d2016_primary.geojson", {"type": "FeatureCollection", "features": primary_features})
    atomic_json(output / "mnroad_22d2016_all_with_repeats.geojson", {"type": "FeatureCollection", "features": all_features})
    atomic_json(output / "qc_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--packet", type=Path, required=True)
    prep.add_argument("--render-root", type=Path)
    prep.add_argument("--download-work", type=Path)
    prep.add_argument("--seed", type=int, default=22016)
    serve = sub.add_parser("serve")
    serve.add_argument("--packet", type=Path, required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8776)
    export = sub.add_parser("export")
    export.add_argument("--packet", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--pixels-per-foot", type=float, default=21.4)
    args = parser.parse_args()
    if args.command == "prepare":
        if bool(args.render_root) == bool(args.download_work):
            parser.error("prepare requires exactly one of --render-root or --download-work")
        root = args.render_root.resolve() if args.render_root else download_and_render(args.download_work.resolve())
        result = prepare_packet(root, args.packet.resolve(), args.seed)
        print(json.dumps({"packet": str(args.packet.resolve()), "tasks": result["total_tasks"], "status": STATUS}, ensure_ascii=False))
        return 0
    if args.command == "export":
        print(json.dumps(export_packet(args.packet.resolve(), args.output.resolve(), args.pixels_per_foot), ensure_ascii=False, indent=2))
        return 0
    server = Server((args.host, args.port), args.packet)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", "link_url": f"http://{args.host}:{args.port}/link", "tasks": len(server.tasks), "status": STATUS}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
