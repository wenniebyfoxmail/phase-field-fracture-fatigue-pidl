#!/usr/bin/env python3
"""Local blind Tier B grid-control annotator; no crack annotation or transform fitting."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BLIND_ID = re.compile(r"^[AB][0-9]{2}$")
STATUSES = {"usable", "missing_print", "occluded", "ambiguous"}


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>Blind grid controls</title>
<style>body{font:15px system-ui;margin:0;background:#f4f0e8;color:#19231e}header{padding:14px 20px;border-bottom:2px solid #19231e}main{display:grid;grid-template-columns:1fr 310px;gap:14px;padding:14px}.viewport{height:70vh;overflow:auto;background:white;border:1px solid #19231e}.canvas{position:relative;width:max-content}.canvas img{display:block;width:auto;height:auto;image-rendering:auto}.marker{position:absolute;width:10px;height:10px;border:2px solid #d62828;border-radius:50%;transform:translate(-50%,-50%);pointer-events:none}.side{background:#fffdf8;border:1px solid #19231e;padding:12px}select,textarea,button{width:100%;margin:7px 0;padding:8px}textarea{height:65px}.tasklist{height:270px;overflow:auto;border-top:1px solid #999}.task{padding:5px;border-bottom:1px dotted #aaa;cursor:pointer}.active{background:#e7cf83}.done{color:#19734b;font-weight:700}@media(max-width:850px){main{grid-template-columns:1fr}.viewport{height:55vh}}</style></head><body>
<header><b>Blind Tier B printed-grid controls</b><span id="status"></span></header><main><section class="viewport" id="viewport"><div class="canvas" id="canvas"><img id="image"></div></section><aside class="side"><label>Blind map<select id="map"></select></label><div class="tasklist" id="tasks"></div><p id="selected">Select a grid ID.</p><label>Status<select id="kind"><option value="usable">usable (then click centre)</option><option value="missing_print">missing_print</option><option value="occluded">occluded</option><option value="ambiguous">ambiguous</option></select></label><label>Short note<textarea id="note"></textarea></label><button id="record">Record selected task</button><button id="save">Save draft</button><button id="lock">Lock map</button><p id="feedback"></p></aside></main>
<script>let maps=[],current='',record={},selected='';const image=document.getElementById('image'),canvas=document.getElementById('canvas'),tasks=document.getElementById('tasks'),feedback=document.getElementById('feedback');function say(t,bad=false){feedback.textContent=t;feedback.style.color=bad?'#b21f2d':'#19734b'}function render(){tasks.innerHTML=Object.entries(record.tasks).map(([id,t])=>`<div class="task ${id===selected?'active':''} ${t.status?'done':''}" data-id="${id}">${id} ${t.status?'— '+t.status:''}</div>`).join('');tasks.querySelectorAll('.task').forEach(x=>x.onclick=()=>{selected=x.dataset.id;document.getElementById('selected').textContent='Selected '+selected;document.getElementById('kind').value=record.tasks[selected].status||'usable';document.getElementById('note').value=record.tasks[selected].note||'';render()});canvas.querySelectorAll('.marker').forEach(x=>x.remove());for(const [id,t] of Object.entries(record.tasks)){if(t.status==='usable'&&t.click_crop_px){const m=document.createElement('span');m.className='marker';m.title=id;m.style.left=t.click_crop_px[0]+'px';m.style.top=t.click_crop_px[1]+'px';canvas.appendChild(m)}}document.getElementById('status').textContent='  '+current+' | '+Object.values(record.tasks).filter(t=>t.status).length+'/66';}
async function load(id){current=id;record=await fetch('/api/record/'+id).then(r=>r.json());image.src='/image/'+id+'?v='+Date.now();image.onload=render;document.getElementById('lock').disabled=record.locked;document.getElementById('record').disabled=record.locked;document.getElementById('save').disabled=record.locked;}
image.onclick=e=>{if(!selected||record.locked||document.getElementById('kind').value!=='usable')return;const r=image.getBoundingClientRect();record.tasks[selected].click_crop_px=[Math.round((e.clientX-r.left)*image.naturalWidth/r.width),Math.round((e.clientY-r.top)*image.naturalHeight/r.height)];say('Centre clicked for '+selected+'. Record it.');render()};document.getElementById('record').onclick=()=>{if(!selected)return say('Select a task first.',true);const status=document.getElementById('kind').value,t=record.tasks[selected];t.status=status;t.note=document.getElementById('note').value.trim();if(status==='usable'&&!t.click_crop_px)return say('Click the printed-grid centre before recording usable.',true);if(status!=='usable')t.click_crop_px=null;render();say('Recorded '+selected+'.')};async function save(lockIt=false){const r=await fetch('/api/record/'+current,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(record)});if(!r.ok)return say(await r.text(),true);if(lockIt){const q=await fetch('/api/lock/'+current,{method:'POST'});if(!q.ok)return say(await q.text(),true)}await load(current);say(lockIt?'Locked.':'Saved.')};document.getElementById('save').onclick=()=>save(false);document.getElementById('lock').onclick=()=>{if(Object.values(record.tasks).some(t=>!t.status))return say('Every task needs one status before lock.',true);if(confirm('Lock this blind map?'))save(true)};document.getElementById('map').onchange=e=>load(e.target.value);(async()=>{maps=await fetch('/api/maps').then(r=>r.json());document.getElementById('map').innerHTML=maps.map(x=>'<option>'+x+'</option>').join('');await load(maps[0])})();</script></body></html>"""


class Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], packet: Path, role: str):
        super().__init__(address, Handler)
        self.root = (packet / role).resolve()
        self.images = self.root / "images"
        self.records = self.root / "records"
        self.ids = tuple(sorted(path.stem for path in self.records.glob("[AB][0-9][0-9].json")))
        if len(self.ids) != 8:
            raise ValueError("packet role must contain exactly eight blinded maps")


class Handler(BaseHTTPRequestHandler):
    server: Server

    def send(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(content))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(content)

    def fail(self, message: str, status: int = 400) -> None:
        self.send(message.encode(), "text/plain; charset=utf-8", status)

    def valid(self, blind_id: str) -> bool:
        return bool(BLIND_ID.fullmatch(blind_id)) and blind_id in self.server.ids

    def path_for(self, blind_id: str) -> Path:
        return self.server.records / f"{blind_id}.json"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/": return self.send(HTML.encode(), "text/html; charset=utf-8")
        if path == "/api/maps": return self.send(json.dumps(self.server.ids).encode(), "application/json")
        if path.startswith("/api/record/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid(blind_id): return self.fail("invalid blind map", HTTPStatus.NOT_FOUND)
            return self.send(self.path_for(blind_id).read_bytes(), "application/json")
        if path.startswith("/image/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid(blind_id): return self.fail("invalid blind map", HTTPStatus.NOT_FOUND)
            return self.send((self.server.images / f"{blind_id}.png").read_bytes(), "image/png")
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/record/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid(blind_id): return self.fail("invalid blind map", HTTPStatus.NOT_FOUND)
            destination = self.path_for(blind_id); current = json.loads(destination.read_text())
            if current.get("locked"): return self.fail("map is locked", HTTPStatus.CONFLICT)
            try: payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            except (ValueError, json.JSONDecodeError): return self.fail("invalid JSON")
            if not isinstance(payload, dict) or payload.get("blind_map_id") != blind_id or payload.get("locked"):
                return self.fail("invalid record")
            if set(payload.get("tasks", {})) != set(current["tasks"]): return self.fail("task inventory mismatch")
            for task in payload["tasks"].values():
                if task.get("status") not in STATUSES | {None}: return self.fail("invalid status")
                click = task.get("click_crop_px")
                if task.get("status") == "usable" and (not isinstance(click, list) or len(click) != 2 or not all(isinstance(v, int) for v in click)):
                    return self.fail("usable task requires integer crop-pixel click")
                if task.get("status") != "usable" and click is not None: return self.fail("non-usable task cannot retain click")
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
                json.dump(payload, handle, indent=2); temp = Path(handle.name)
            temp.replace(destination)
            return self.send(b'{"saved":true}', "application/json")
        if path.startswith("/api/lock/"):
            blind_id = path.rsplit("/", 1)[-1]
            if not self.valid(blind_id): return self.fail("invalid blind map", HTTPStatus.NOT_FOUND)
            destination = self.path_for(blind_id); payload = json.loads(destination.read_text())
            if payload.get("locked"): return self.fail("map already locked", HTTPStatus.CONFLICT)
            if any(task.get("status") is None for task in payload["tasks"].values()): return self.fail("all 66 tasks require status")
            payload["locked"] = True; destination.write_text(json.dumps(payload, indent=2) + "\n")
            return self.send(b'{"locked":true}', "application/json")
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None: pass


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--packet-root", type=Path, required=True); parser.add_argument("--role", choices=("annotator_a", "annotator_b"), required=True); parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8770); args = parser.parse_args()
    server = Server((args.host, args.port), args.packet_root.resolve(), args.role)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", "role": args.role, "maps": len(server.ids)}), flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__": raise SystemExit(main())
