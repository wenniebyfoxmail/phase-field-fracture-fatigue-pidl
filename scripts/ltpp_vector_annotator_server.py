#!/usr/bin/env python3
"""Local blind semantic-vector annotator for LTPP GeoForecast packets."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


WIDTH_PX = 1524
HEIGHT_PX = 500
MAX_X_M = 15.24
MAX_Y_M = 5.0
EDGE_TOLERANCE_M = 0.02
FAMILIES = {
    "transverse_crack",
    "longitudinal_crack",
    "fatigue_or_alligator_crack",
    "block_crack",
    "other_crack",
    "patch_or_patch_deterioration",
    "water_bleeding_and_pumping",
    "other_noncrack_distress",
    "lane_or_reference_boundary",
    "handwritten_code_or_calculation",
    "grid_or_printed_frame",
    "arrow_or_dimension",
    "wim_or_patch_box",
    "hatching_or_x_symbol",
    "other_noncrack_line",
    "uncertain",
}
BLIND_ID = re.compile(r"^[PS][0-9]{3}$")


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LTPP blind centerline annotator</title>
<style>
:root { --ink:#17211b; --paper:#f5f0e4; --red:#c43d2f; --teal:#167f78; --gold:#d59c2f; }
* { box-sizing:border-box; }
body { margin:0; color:var(--ink); background:linear-gradient(125deg,#e7ddca,#f8f3e9 50%,#dce9df); font-family:"Avenir Next",Avenir,"Trebuchet MS",sans-serif; }
header { display:flex; align-items:end; justify-content:space-between; padding:20px 28px 12px; border-bottom:2px solid var(--ink); }
h1 { margin:0; font-family:Georgia,serif; font-size:clamp(24px,3vw,42px); font-weight:500; }
.status { font-variant-numeric:tabular-nums; }
main { display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:18px; padding:18px 28px 28px; }
.stage { min-width:0; }
.canvas-wrap { position:relative; width:100%; aspect-ratio:1524/500; overflow:hidden; background:white; border:2px solid var(--ink); box-shadow:8px 8px 0 rgba(23,33,27,.15); }
canvas { width:100%; height:100%; display:block; cursor:crosshair; }
.hint { margin:14px 0 0; max-width:900px; line-height:1.45; }
aside { background:rgba(255,255,255,.72); border:1px solid var(--ink); padding:16px; }
label { display:block; margin:0 0 12px; font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }
select,input,textarea,button { width:100%; font:inherit; }
select,input,textarea { margin-top:5px; padding:8px; border:1px solid var(--ink); background:#fffdf7; }
textarea { min-height:62px; resize:vertical; }
.buttons { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:14px 0; }
button { padding:9px 7px; border:1px solid var(--ink); background:var(--paper); cursor:pointer; }
button.primary { color:white; background:var(--teal); }
button.danger { color:white; background:var(--red); }
button.lock { grid-column:1/-1; color:var(--ink); background:var(--gold); font-weight:800; }
button:disabled { opacity:.42; cursor:not-allowed; }
.lines { max-height:220px; overflow:auto; border-top:1px solid var(--ink); padding-top:8px; font-size:12px; }
.line-row { display:flex; justify-content:space-between; gap:8px; padding:4px 0; border-bottom:1px dotted #918b7d; }
.locked { color:var(--red); font-weight:800; }
@media (max-width:900px) { main { grid-template-columns:1fr; padding:14px; } header { padding:16px 14px 10px; } aside { order:-1; } }
</style>
</head>
<body>
<header><div><h1>Blind centerline desk</h1><div>No dates. No future maps. No automatic candidates.</div></div><div class="status" id="status">Loading...</div></header>
<main>
<section class="stage">
  <div class="canvas-wrap"><canvas id="canvas" width="1524" height="500"></canvas></div>
  <p class="hint">Click along one visible target structure. Use <b>Finish line</b> after at least two points. For hard-negative mode, annotate only non-crack marks that could be mistaken for cracks: grid/frame, boundary, handwriting, arrow/dimension, WIM/patch box, hatching/X, or other non-crack line. Ambiguous geometry belongs in <b>uncertain</b>. Coordinates are stored in metres in the lower-left road frame.</p>
</section>
<aside>
  <label>Blind map<select id="map"></select></label>
  <label>Geometry<select id="geometry-kind"><option value="centerline">Crack centerline</option><option value="area">Distress area polygon</option></select></label>
  <label>Distress family<select id="family"></select></label>
  <label>Confidence<select id="confidence"><option>high</option><option selected>medium</option><option>low</option></select></label>
  <label>Evidence note<textarea id="note" placeholder="Visible stroke evidence; why it is not grid/text/boundary"></textarea></label>
  <div class="buttons">
    <button id="undo">Undo point</button><button id="finish" class="primary">Finish geometry</button>
    <button id="delete" class="danger">Delete last geometry</button><button id="save" class="primary">Save draft</button>
    <button id="lock" class="lock">Lock this map</button>
  </div>
  <div id="feedback" aria-live="polite"></div>
  <div id="lock-state"></div>
  <div class="lines" id="lines"></div>
</aside>
</main>
<script>
const canvas=document.getElementById('canvas'),ctx=canvas.getContext('2d');
const mapSelect=document.getElementById('map'), family=document.getElementById('family');
const geometryKind=document.getElementById('geometry-kind'),feedback=document.getElementById('feedback');
const confidence=document.getElementById('confidence'),note=document.getElementById('note');
let maps=[],current=null,imageObj=new Image(),features=[],draft=[],locked=false,lastGeometryKind='centerline';
const colors={transverse_crack:'#d62929',longitudinal_crack:'#1261a0',fatigue_or_alligator_crack:'#e07a1f',block_crack:'#8b5a2b',other_crack:'#7a3ea1',patch_or_patch_deterioration:'#9a5b13',water_bleeding_and_pumping:'#008b8b',other_noncrack_distress:'#4f6575',lane_or_reference_boundary:'#555f68',handwritten_code_or_calculation:'#777777',grid_or_printed_frame:'#c23b22',arrow_or_dimension:'#b24c9b',wim_or_patch_box:'#936f1c',hatching_or_x_symbol:'#6d4c9b',other_noncrack_line:'#37474f',uncertain:'#6b6b61'};
const familyByGeometry={centerline:['transverse_crack','longitudinal_crack','other_crack','water_bleeding_and_pumping','other_noncrack_distress','lane_or_reference_boundary','handwritten_code_or_calculation','grid_or_printed_frame','arrow_or_dimension','wim_or_patch_box','hatching_or_x_symbol','other_noncrack_line','uncertain'],area:['fatigue_or_alligator_crack','block_crack','patch_or_patch_deterioration','other_crack','other_noncrack_distress','wim_or_patch_box','hatching_or_x_symbol','uncertain']};
function physicalToPixel(c){return [c[0]*100,500-c[1]*100]}
function pixelToPhysical(x,y){return [Math.round(x)/100,Math.round(500-y)/100]}
function setFeedback(message,isError=false){feedback.textContent=message;feedback.style.color=isError?'#c43d2f':'#167f78';feedback.style.fontWeight='700';}
function refreshFamilies(){const allowed=familyByGeometry[geometryKind.value];const previous=family.value;family.innerHTML=allowed.map(value=>`<option value="${value}">${value}</option>`).join('');if(allowed.includes(previous))family.value=previous;}
function featurePoints(feature){return feature.geometry.type==='Polygon'?feature.geometry.coordinates[0]:feature.geometry.coordinates;}
function nextFeatureId(kind){const marker=kind==='area'?'A':'L';const used=new Set(features.map(f=>f.properties.feature_id||f.properties.line_id));let index=1;while(used.has(`${current}-${marker}${String(index).padStart(3,'0')}`))index++;return `${current}-${marker}${String(index).padStart(3,'0')}`;}
function draw(){ctx.clearRect(0,0,1524,500);ctx.drawImage(imageObj,0,0,1524,500);ctx.lineJoin='round';ctx.lineCap='round';
  for(const f of features){const pts=featurePoints(f).map(physicalToPixel);ctx.strokeStyle=colors[f.properties.distress_family]||'#d62929';ctx.lineWidth=4;ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));if(f.geometry.type==='Polygon'){ctx.closePath();ctx.save();ctx.globalAlpha=.16;ctx.fillStyle=ctx.strokeStyle;ctx.fill();ctx.restore();}ctx.stroke();}
  if(draft.length){ctx.strokeStyle='#00a66b';ctx.lineWidth=3;ctx.beginPath();draft.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.stroke();for(const p of draft){ctx.fillStyle='#00a66b';ctx.beginPath();ctx.arc(p[0],p[1],4,0,Math.PI*2);ctx.fill();}}
  document.getElementById('lines').innerHTML=features.map((f,i)=>`<div class="line-row"><span>${i+1}. ${f.properties.distress_family}</span><span>${f.geometry.type} | ${featurePoints(f).length} pts</span></div>`).join('')||'No finished geometries.';
}
function setControls(){for(const id of ['undo','finish','delete','save','lock'])document.getElementById(id).disabled=locked;document.getElementById('lock-state').innerHTML=locked?'<p class="locked">LOCKED: server rejects further edits.</p>':'<p>Draft is editable.</p>';}
async function loadMap(id){current=id;draft=[];const label=await fetch(`/api/label/${id}`).then(r=>r.json());features=label.features||[];locked=!!label.properties.locked;imageObj.onload=draw;imageObj.src=`/image/${id}?v=${Date.now()}`;setControls();document.getElementById('status').textContent=`${id} | ${features.length} geometries`;}
canvas.addEventListener('click',e=>{if(locked)return;const r=canvas.getBoundingClientRect();draft.push([(e.clientX-r.left)*1524/r.width,(e.clientY-r.top)*500/r.height]);draw();});
document.getElementById('undo').onclick=()=>{draft.pop();draw()};
document.getElementById('finish').onclick=()=>{const isArea=geometryKind.value==='area';const minimum=isArea?3:2;if(draft.length<minimum)return alert(`${isArea?'An area':'A line'} needs at least ${minimum} points.`);let coordinates=draft.map(p=>pixelToPhysical(...p));if(isArea)coordinates=[...coordinates,coordinates[0]];const featureId=nextFeatureId(geometryKind.value);features.push({type:'Feature',properties:{blind_map_id:current,feature_id:featureId,line_id:featureId,geometry_role:isArea?'distress_extent':'centerline',distress_family:family.value,confidence:confidence.value,review_status:'draft',evidence_note:note.value.trim()},geometry:{type:isArea?'Polygon':'LineString',coordinates:isArea?[coordinates]:coordinates}});draft=[];note.value='';setFeedback('Geometry finished locally. Save draft when this map is complete.');draw();};
document.getElementById('delete').onclick=()=>{features.pop();draw()};
async function save(lockIt=false){if(draft.length)return alert('Finish or undo the active geometry first.');const payload={type:'FeatureCollection',name:`ltpp_geoforecast_${current}`,schema_version:'line_area_v3',coordinate_reference:{origin:'lower_left',units:'metres',extent:[0,0,15.24,5]},properties:{blind_map_id:current,source_image:`${current}.png`,locked:false,automatic_candidates_seen:false,other_dates_seen:false},features};let response=await fetch(`/api/label/${current}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok){setFeedback(await response.text(),true);return;}const saved=await response.json();if(lockIt){response=await fetch(`/api/lock/${current}`,{method:'POST'});if(!response.ok){setFeedback(await response.text(),true);return;}}await loadMap(current);await refreshMaps();setFeedback(lockIt?`${current} locked with ${saved.features} geometries.`:`${current} saved successfully with ${saved.features} geometries.`);}
document.getElementById('save').onclick=()=>save(false);
document.getElementById('lock').onclick=()=>{if(confirm('Lock this map? Further edits will be rejected.'))save(true)};
mapSelect.onchange=()=>loadMap(mapSelect.value);
async function refreshMaps(){maps=await fetch('/api/maps').then(r=>r.json());mapSelect.innerHTML=maps.map(m=>`<option value="${m.blind_id}">${m.blind_id} | ${m.features} geometries${m.locked?' | LOCKED':''}</option>`).join('');if(current)mapSelect.value=current;}
geometryKind.onchange=()=>{if(draft.length){geometryKind.value=lastGeometryKind;return alert('Finish or undo the active geometry before changing geometry type.');}lastGeometryKind=geometryKind.value;refreshFamilies();setFeedback(geometryKind.value==='area'?'Area mode: click around the mapped distress extent; the polygon closes automatically.':'Centerline mode: click along one visible mapped crack stroke.');};
refreshFamilies();
(async()=>{await refreshMaps();current=maps[0].blind_id;mapSelect.value=current;await loadMap(current)})();
</script>
</body></html>"""


class AnnotationServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], packet_root: Path, role: str):
        super().__init__(address, AnnotationHandler)
        self.packet_root = packet_root.resolve()
        self.role = role
        self.role_root = (self.packet_root / role).resolve()
        self.image_root = self.role_root / "images"
        self.label_root = self.role_root / "geojson"
        prefix = "P" if role == "primary" else "S"
        discovered = sorted(path.stem for path in self.label_root.glob(f"{prefix}[0-9][0-9][0-9].geojson"))
        if not discovered:
            raise ValueError(f"no blind labels found for role {role}: {self.label_root}")
        self.allowed_ids = tuple(discovered)


class AnnotationHandler(BaseHTTPRequestHandler):
    server: AnnotationServer

    def send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: object, status: int = 200) -> None:
        self.send_bytes(json.dumps(payload).encode("utf-8"), "application/json", status)

    def fail(self, message: str, status: int = 400) -> None:
        self.send_bytes(message.encode("utf-8"), "text/plain; charset=utf-8", status)

    def valid_id(self, blind_id: str) -> bool:
        return bool(BLIND_ID.fullmatch(blind_id)) and blind_id in self.server.allowed_ids

    def label_path(self, blind_id: str) -> Path:
        return self.server.label_root / f"{blind_id}.geojson"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_bytes(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/maps":
            rows = []
            for blind_id in self.server.allowed_ids:
                payload = json.loads(self.label_path(blind_id).read_text(encoding="utf-8"))
                rows.append({"blind_id": blind_id, "locked": bool(payload["properties"].get("locked")), "features": len(payload.get("features", []))})
            self.send_json(rows)
            return
        if path.startswith("/api/label/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid_id(blind_id):
                self.fail("invalid blind id", HTTPStatus.NOT_FOUND)
                return
            self.send_bytes(self.label_path(blind_id).read_bytes(), "application/geo+json")
            return
        if path.startswith("/image/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid_id(blind_id):
                self.fail("invalid blind id", HTTPStatus.NOT_FOUND)
                return
            self.send_bytes((self.server.image_root / f"{blind_id}.png").read_bytes(), "image/png")
            return
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def read_json_body(self) -> object:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2_000_000:
            raise ValueError("invalid body length")
        return json.loads(self.rfile.read(length))

    def validate_label(self, blind_id: str, payload: object) -> dict:
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise ValueError("payload must be a FeatureCollection")
        properties = payload.get("properties")
        if not isinstance(properties, dict) or properties.get("blind_map_id") != blind_id:
            raise ValueError("blind_map_id mismatch")
        if properties.get("locked"):
            raise ValueError("client cannot self-declare a lock")
        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("features must be a list")
        seen = set()
        for feature in features:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ValueError("each item must be a Feature")
            geometry = feature.get("geometry")
            attrs = feature.get("properties")
            if not isinstance(geometry, dict) or geometry.get("type") not in {"LineString", "Polygon"}:
                raise ValueError("geometry must be LineString or Polygon")
            coordinates = geometry.get("coordinates")
            if geometry["type"] == "LineString":
                if not isinstance(coordinates, list) or len(coordinates) < 2:
                    raise ValueError("LineString needs at least two coordinates")
                path = coordinates
                inferred_role = "centerline"
            else:
                if not isinstance(coordinates, list) or len(coordinates) != 1:
                    raise ValueError("Polygon must contain one exterior ring and no holes")
                path = coordinates[0]
                if not isinstance(path, list) or len(path) < 4 or path[0] != path[-1]:
                    raise ValueError("Polygon exterior ring needs three vertices and closure")
                if len({tuple(point) for point in path[:-1]}) < 3:
                    raise ValueError("Polygon needs at least three distinct vertices")
                inferred_role = "distress_extent"
            for coordinate in path:
                if not isinstance(coordinate, list) or len(coordinate) != 2:
                    raise ValueError("coordinate must be [x_m,y_m]")
                x_value, y_value = coordinate
                if not isinstance(x_value, (int, float)) or not isinstance(y_value, (int, float)):
                    raise ValueError("coordinates must be numeric")
                if (
                    x_value < -EDGE_TOLERANCE_M
                    or x_value > MAX_X_M + EDGE_TOLERANCE_M
                    or y_value < -EDGE_TOLERANCE_M
                    or y_value > MAX_Y_M + EDGE_TOLERANCE_M
                ):
                    raise ValueError("coordinate outside physical extent")
                coordinate[0] = min(MAX_X_M, max(0.0, float(x_value)))
                coordinate[1] = min(MAX_Y_M, max(0.0, float(y_value)))
            if not isinstance(attrs, dict):
                raise ValueError("feature properties missing")
            required = {"blind_map_id", "line_id", "distress_family", "confidence", "review_status", "evidence_note"}
            if not required.issubset(attrs):
                raise ValueError("feature properties incomplete")
            if attrs["blind_map_id"] != blind_id:
                raise ValueError("feature blind_map_id mismatch")
            if attrs["distress_family"] not in FAMILIES:
                raise ValueError("invalid distress_family")
            if attrs["line_id"] in seen:
                raise ValueError("duplicate line_id")
            seen.add(attrs["line_id"])
            attrs.setdefault("feature_id", attrs["line_id"])
            attrs.setdefault("geometry_role", inferred_role)
        payload["properties"]["locked"] = False
        payload["properties"]["annotator_role"] = self.server.role
        return payload

    def atomic_write(self, destination: Path, payload: dict) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
            json.dump(payload, handle, indent=2)
            temporary = Path(handle.name)
        temporary.replace(destination)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/label/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid_id(blind_id):
                self.fail("invalid blind id", HTTPStatus.NOT_FOUND)
                return
            destination = self.label_path(blind_id)
            current = json.loads(destination.read_text(encoding="utf-8"))
            if current["properties"].get("locked"):
                self.fail("map is locked", HTTPStatus.CONFLICT)
                return
            try:
                payload = self.validate_label(blind_id, self.read_json_body())
            except (ValueError, json.JSONDecodeError) as exc:
                self.fail(str(exc))
                return
            self.atomic_write(destination, payload)
            self.send_json({"saved": True, "blind_id": blind_id, "features": len(payload["features"])})
            return
        if path.startswith("/api/lock/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid_id(blind_id):
                self.fail("invalid blind id", HTTPStatus.NOT_FOUND)
                return
            destination = self.label_path(blind_id)
            payload = json.loads(destination.read_text(encoding="utf-8"))
            if payload["properties"].get("locked"):
                self.fail("map is already locked", HTTPStatus.CONFLICT)
                return
            payload["properties"]["locked"] = True
            for feature in payload.get("features", []):
                feature["properties"]["review_status"] = f"{self.server.role}_locked"
            self.atomic_write(destination, payload)
            self.send_json({"locked": True, "blind_id": blind_id})
            return
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--role", choices=("primary", "secondary"), required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = AnnotationServer((args.host, args.port), args.packet_root, args.role)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", "role": args.role, "maps": len(server.allowed_ids)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
