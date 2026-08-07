#!/usr/bin/env python3
"""Local human workbench for the frozen LTPP dual-blind adjudication queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


BLIND_ID = re.compile(r"^[PS][0-9]{3}$")
QUEUE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LTPP 双标注裁决台</title>
<style>
:root{--ink:#16221b;--paper:#f6f0e2;--red:#d43a35;--blue:#1769aa;--teal:#147c74;--gold:#dda735;--muted:#6d716d}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:linear-gradient(130deg,#e8dfcd,#fbf7ee 55%,#dce9df);font-family:"Avenir Next",Avenir,"PingFang SC",sans-serif}
header{display:flex;justify-content:space-between;gap:18px;align-items:end;padding:18px 26px 12px;border-bottom:2px solid var(--ink)}h1{margin:0;font-family:Georgia,"Songti SC",serif;font-weight:500;font-size:clamp(25px,3vw,40px)}
main{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:18px;padding:18px 26px 28px}.stage{min-width:0}.canvas-wrap{background:white;border:2px solid var(--ink);box-shadow:7px 7px 0 #17211b20;margin-bottom:16px}.panel-title{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:9px 12px;border-bottom:1px solid var(--ink);font-weight:900}.panel-title small{font-weight:500;color:var(--muted)}canvas{width:100%;display:block}.full{aspect-ratio:1524/500}.swatch{display:inline-block;width:20px;height:4px;margin-right:6px;vertical-align:middle}.p{background:var(--red)}.s{background:var(--blue)}.h{background:var(--gold)}
aside{background:#ffffffc9;border:1px solid var(--ink);padding:16px;align-self:start;position:sticky;top:12px}label{display:block;font-size:12px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin:0 0 12px}select,textarea,button{width:100%;font:inherit}select,textarea{margin-top:5px;padding:8px;border:1px solid var(--ink);background:#fffdf7}textarea{min-height:72px;resize:vertical}.buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px}.buttons button,.bulk button{padding:10px 7px;border:1px solid var(--ink);background:var(--paper);cursor:pointer}.buttons .save{grid-column:1/-1;background:var(--teal);color:white;font-weight:800}.buttons button:disabled,.bulk button:disabled{opacity:.45;cursor:not-allowed}.bulk{display:grid;gap:7px;margin:14px 0;padding:12px;background:#efe8d7;border:1px solid #9a8e73}.bulk-title{font-size:13px;font-weight:900}.bulk .human{background:#dce8f2}.bulk .both{background:#eadff1}.bulk .semantic{background:#d9eee7}.meta{font-size:13px;line-height:1.45;border-top:1px solid var(--ink);padding-top:10px;margin-top:12px}.feature{padding:8px;margin:7px 0;background:#f3f0e8;border-left:4px solid var(--muted);overflow-wrap:anywhere}.feature.primary{border-color:var(--red)}.feature.secondary{border-color:var(--blue)}.feedback{min-height:24px;font-weight:800;margin-top:10px}.done{color:var(--teal)}.pending{color:#a46700}.nav{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.nav button{padding:8px;border:1px solid var(--ink);background:white;cursor:pointer}.progress{font-variant-numeric:tabular-nums;font-weight:800}.small{font-size:12px;color:var(--muted)}
@media(max-width:900px){main{grid-template-columns:1fr;padding:12px}header{padding:14px 12px 10px;align-items:start;flex-direction:column}aside{position:static;order:-1}}
</style></head>
<body><header><div><h1>LTPP 双标注裁决台</h1><div>原图、AI 完整标注、人工完整标注分开显示；金色描边 = 当前待裁决对象。</div></div><div class="progress" id="progress">载入中…</div></header>
<main><section class="stage"><div class="canvas-wrap"><div class="panel-title"><span>1. 原图（无标注）</span><small id="original-info">裁决依据</small></div><canvas class="full" id="original" width="1524" height="500"></canvas></div><div class="canvas-wrap"><div class="panel-title"><span><i class="swatch p"></i>2. AI 标注</span><small id="ai-info">载入中…</small></div><canvas class="full" id="ai" width="1524" height="500"></canvas></div><div class="canvas-wrap"><div class="panel-title"><span><i class="swatch s"></i>3. 人工标注</span><small id="human-info">载入中…</small></div><canvas class="full" id="human" width="1524" height="500"></canvas></div><p class="small"><i class="swatch h"></i>金色外描边仅强调当前候选；三张图来自同一原图，AI／人工面板显示各自完整锁定 GeoJSON。裁决只写入队列，不修改原标注。</p></section>
<aside><div class="nav"><button id="prev">← 上一项</button><button id="next">下一项 →</button></div><label>差异地图／日期<select id="asset"></select></label><label>当前差异项<select id="item"></select></label><label>裁决（数字键选择）<select id="disposition"><option value="">请选择…</option></select></label><label>说明（可留空）<textarea id="note" placeholder="为何采用、删除或标为不确定"></textarea></label><div class="buttons"><button id="pending">下一条未完成</button><button id="pending-asset">下一张未完成图</button><button id="clear">清除此项裁决</button><button id="save" class="save">保存并进入下一项（Enter）</button></div><div class="bulk"><div class="bulk-title" id="group">本图批量复核</div><button class="human" id="bulk-human">本图以人工为准：收人工、拒AI</button><button class="both" id="bulk-both">本图双方独有裂缝都保留</button><button class="semantic" id="bulk-semantic">接受本图全部 WIM／抽水修正</button><button id="bulk-clear">清除本图全部裁决</button></div><div class="feedback" id="feedback"></div><div class="meta" id="meta"></div></aside></main>
<script>
const original=document.getElementById('original'),oc=original.getContext('2d'),ai=document.getElementById('ai'),ac=ai.getContext('2d'),human=document.getElementById('human'),hc=human.getContext('2d');
const assetSelect=document.getElementById('asset'),itemSelect=document.getElementById('item'),disp=document.getElementById('disposition'),note=document.getElementById('note'),meta=document.getElementById('meta'),feedback=document.getElementById('feedback');
let queue=null,index=0,state=null,drawToken=0;const color={primary:'#d43a35',secondary:'#1769aa'};
const labels={accept_primary:'采用 AI',accept_secondary:'采用人工',merge:'合并两者',reject:'不是目标裂缝／删除',uncertain:'不确定，保留遮罩',accept_candidate:'接受语义修正',keep_current:'保持原类别'};
function pts(feature){if(!feature)return[];const c=feature.geometry.coordinates;return feature.geometry.type==='Polygon'?c[0]:c}
function px(c){return[c[0]*100,500-c[1]*100]}
function drawFeature(ctx,feature,role,alpha=.75,widthScale=.65,stroke=null,dashed=null){if(!feature)return;const p=pts(feature).map(px);ctx.save();ctx.globalAlpha=alpha;ctx.strokeStyle=stroke||color[role];ctx.lineWidth=(role==='primary'?6:4)*widthScale;ctx.lineJoin='round';ctx.lineCap='round';ctx.setLineDash(dashed===null?(role==='secondary'?[12,7]:[]):dashed);ctx.beginPath();p.forEach((q,i)=>i?ctx.lineTo(...q):ctx.moveTo(...q));if(feature.geometry.type==='Polygon'){ctx.closePath();if(!stroke){ctx.globalAlpha=.13*alpha;ctx.fillStyle=color[role];ctx.fill();ctx.globalAlpha=alpha}}ctx.stroke();ctx.restore()}
function highlight(ctx,feature,role){if(!feature)return;drawFeature(ctx,feature,role,.95,2.4,'#dda735',[]);drawFeature(ctx,feature,role,1,1,null,[])}
function groupItems(x){return queue.items.filter(row=>row.asset_key===x.asset_key)}
async function draw(){const x=queue.items[index],token=++drawToken;try{const nextState=await fetch('/api/state/'+encodeURIComponent(x.asset_key)).then(r=>{if(!r.ok)throw new Error('标注状态载入失败');return r.json()});const image=new Image();image.onload=()=>{if(token!==drawToken)return;state=nextState;for(const ctx of [oc,ac,hc]){ctx.clearRect(0,0,1524,500);ctx.drawImage(image,0,0,1524,500)}for(const feature of state.primary_label.features)drawFeature(ac,feature,'primary');for(const feature of state.secondary_label.features)drawFeature(hc,feature,'secondary');highlight(ac,x.primary_feature,'primary');highlight(hc,x.secondary_feature,'secondary');document.getElementById('ai-info').textContent=`${state.primary_blind_id} · ${state.primary_label.features.length} 个完整标注`;document.getElementById('human-info').textContent=`${state.secondary_blind_id} · ${state.secondary_label.features.length} 个完整标注`;document.getElementById('original-info').textContent=`${x.section} · ${x.survey_date}`};image.onerror=()=>{feedback.textContent='原图载入失败。';feedback.style.color='#d43a35'};image.src=nextState.clean_image_url+'?v='+Date.now()}catch(err){feedback.textContent=err.message;feedback.style.color='#d43a35'}}
function featureHtml(feature,role){if(!feature)return'';const p=feature.properties;return `<div class="feature ${role}"><b>${role==='primary'?'AI primary':'人工 secondary'} · ${p.feature_id}</b><br>类别：${p.distress_family}<br>置信度：${p.confidence||'—'}<br>原说明：${p.evidence_note||'—'}</div>`}
function load(i){index=(i+queue.items.length)%queue.items.length;const x=queue.items[index],group=groupItems(x),groupDone=group.filter(row=>row.disposition).length;assetSelect.value=x.asset_key;itemSelect.innerHTML=group.map(row=>{const j=queue.items.indexOf(row);return `<option value="${j}">${row.disposition?'✓':'○'} ${j+1}. ${row.kind}</option>`}).join('');itemSelect.value=String(index);disp.innerHTML='<option value="">请选择…</option>'+x.allowed_dispositions.map((v,j)=>`<option value="${v}">${j+1}. ${labels[v]||v}</option>`).join('');disp.value=x.disposition||'';note.value=x.review_note||'';const state=x.disposition?'<span class="done">已完成</span>':'<span class="pending">待裁决</span>';document.getElementById('group').textContent=`本图批量复核：${groupDone}/${group.length} 已完成`;document.getElementById('bulk-semantic').disabled=!group.some(row=>row.kind==='semantic_candidate');meta.innerHTML=`<b>${index+1}/${queue.items.length} · ${state}</b><br>${x.section} · ${x.survey_date}<br>类型：${x.kind}${x.candidate_family?'<br>候选语义：'+x.candidate_family+' ('+x.candidate_confidence+')':''}${featureHtml(x.primary_feature,'primary')}${featureHtml(x.secondary_feature,'secondary')}`;feedback.textContent='';draw();updateProgress()}
function updateProgress(){const n=queue.items.filter(x=>x.disposition).length;document.getElementById('progress').textContent=`${n}/${queue.items.length} 已裁决 · ${queue.items.length-n} 待处理`}
async function refresh(){queue=await fetch('/api/queue').then(r=>r.json());const assets=[];for(const x of queue.items){if(!assets.some(a=>a.asset_key===x.asset_key))assets.push({asset_key:x.asset_key,section:x.section,survey_date:x.survey_date})}assetSelect.innerHTML=assets.map(a=>{const g=queue.items.filter(x=>x.asset_key===a.asset_key),n=g.filter(x=>x.disposition).length;return `<option value="${a.asset_key}">${n===g.length?'✓':'○'} ${a.section} ${a.survey_date} · ${n}/${g.length}</option>`}).join('');load(Math.min(index,queue.items.length-1))}
async function save(clear=false){const x=queue.items[index],value=clear?null:disp.value;if(!clear&&!value){feedback.textContent='请先选择裁决。';feedback.style.color='#d43a35';return}const r=await fetch('/api/item/'+encodeURIComponent(x.queue_id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({disposition:value,review_note:clear?'':note.value.trim()})});if(!r.ok){feedback.textContent=await r.text();feedback.style.color='#d43a35';return}await refresh();if(!clear)nextPending();else{feedback.textContent='已清除。';feedback.style.color='#147c74'}}
async function bulk(mode,label){const x=queue.items[index];if(!confirm(`${label}\n\n将为本图符合条件的每个差异写入独立裁决，可随时用“清除本图全部裁决”撤销。`))return;const r=await fetch('/api/bulk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_key:x.asset_key,mode})});if(!r.ok){feedback.textContent=await r.text();feedback.style.color='#d43a35';return}const result=await r.json();await refresh();feedback.textContent=`本图已写入 ${result.affected} 项裁决。`;feedback.style.color='#147c74'}
function nextPending(){const start=index;for(let k=1;k<=queue.items.length;k++){const j=(start+k)%queue.items.length;if(!queue.items[j].disposition){load(j);return}}load(index);feedback.textContent='全部项目已有裁决；请进行冻结校验。';feedback.style.color='#147c74'}
function nextPendingAsset(){const keys=[...new Set(queue.items.map(x=>x.asset_key))],current=queue.items[index].asset_key,start=keys.indexOf(current);for(let k=1;k<=keys.length;k++){const key=keys[(start+k)%keys.length],j=queue.items.findIndex(x=>x.asset_key===key&&!x.disposition);if(j>=0){load(j);return}}nextPending()}
document.getElementById('prev').onclick=()=>load(index-1);document.getElementById('next').onclick=()=>load(index+1);document.getElementById('pending').onclick=nextPending;document.getElementById('pending-asset').onclick=nextPendingAsset;document.getElementById('save').onclick=()=>save(false);document.getElementById('clear').onclick=()=>save(true);document.getElementById('bulk-human').onclick=()=>bulk('human_reference','本图所有人工独有裂缝采用、AI独有裂缝拒绝、类别冲突采用人工');document.getElementById('bulk-both').onclick=()=>bulk('keep_both','本图所有人工和AI独有裂缝都采用；类别冲突保持未处理');document.getElementById('bulk-semantic').onclick=()=>bulk('accept_semantics','接受本图全部 WIM／抽水语义候选修正');document.getElementById('bulk-clear').onclick=()=>bulk('clear_asset','清除本图全部已有裁决');assetSelect.onchange=()=>{const j=queue.items.findIndex(x=>x.asset_key===assetSelect.value&&!x.disposition);load(j>=0?j:queue.items.findIndex(x=>x.asset_key===assetSelect.value))};itemSelect.onchange=()=>load(Number(itemSelect.value));
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA')return;if(e.key==='ArrowRight')load(index+1);else if(e.key==='ArrowLeft')load(index-1);else if(e.key==='Enter')save(false);else if(/^[1-5]$/.test(e.key)){const option=disp.options[Number(e.key)];if(option)disp.value=option.value}});refresh();
</script></body></html>"""


class AdjudicationServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], packet_root: Path, queue_path: Path):
        super().__init__(address, AdjudicationHandler)
        self.packet_root = packet_root.resolve()
        self.queue_path = queue_path.resolve()
        if not self.queue_path.is_file() or self.queue_path.parent != self.packet_root:
            raise ValueError("queue must be a file directly under packet root")
        queue = json.loads(self.queue_path.read_text(encoding="utf-8"))
        self.allowed_queue_ids = {item["queue_id"] for item in queue["items"]}
        queue_asset_keys = {item["asset_key"] for item in queue["items"]}
        self.allowed_assets = {
            item[key]
            for item in queue["items"]
            for key in ("primary_image", "secondary_image")
            if item.get(key)
        }
        mapping_path = self.packet_root / "sealed_do_not_open_during_annotation" / "blind_id_asset_mapping.json"
        pairing_path = self.packet_root / "pairing_result.json"
        pairing = json.loads(pairing_path.read_text(encoding="utf-8"))
        if pairing.get("sealed_mapping_read") is not True:
            raise ValueError("adjudication state view requires the completed sealed-mapping gate")
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        primary = {row["asset_key"]: row for row in mapping["primary"]}
        secondary = {row["asset_key"]: row for row in mapping["secondary"]}
        self.asset_states = {}
        self.state_images = {}
        for asset_key in queue_asset_keys:
            if asset_key not in primary or asset_key not in secondary:
                raise ValueError(f"missing blind mapping for queue asset: {asset_key}")
            p_row = primary[asset_key]
            s_row = secondary[asset_key]
            p_image = self.packet_root / "primary" / "images" / f"{p_row['blind_id']}.png"
            s_image = self.packet_root / "secondary" / "images" / f"{s_row['blind_id']}.png"
            if hashlib.sha256(p_image.read_bytes()).digest() != hashlib.sha256(s_image.read_bytes()).digest():
                raise ValueError(f"role image mismatch for asset: {asset_key}")
            p_label = self.packet_root / "primary" / "geojson" / f"{p_row['blind_id']}.geojson"
            s_label = self.packet_root / "secondary" / "geojson" / f"{s_row['blind_id']}.geojson"
            for role, row, image_path, label_path in (
                ("primary", p_row, p_image, p_label),
                ("secondary", s_row, s_image, s_label),
            ):
                label = json.loads(label_path.read_text(encoding="utf-8"))
                if label.get("properties", {}).get("locked") is not True:
                    raise ValueError(f"unlocked role label in adjudication view: {label_path}")
                self.state_images[(role, row["blind_id"])] = image_path
            self.asset_states[asset_key] = {
                "asset_key": asset_key,
                "primary_blind_id": p_row["blind_id"],
                "secondary_blind_id": s_row["blind_id"],
                "primary_label_path": p_label,
                "secondary_label_path": s_label,
            }


class AdjudicationHandler(BaseHTTPRequestHandler):
    server: AdjudicationServer

    def send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status);self.send_header("Content-Type", content_type);self.send_header("Content-Length", str(len(content)));self.send_header("Cache-Control", "no-store");self.end_headers();self.wfile.write(content)

    def send_json(self, payload: object, status: int = 200) -> None:
        self.send_bytes(json.dumps(payload).encode("utf-8"), "application/json", status)

    def fail(self, message: str, status: int = 400) -> None:
        self.send_bytes(message.encode("utf-8"), "text/plain; charset=utf-8", status)

    def read_queue(self) -> dict:
        return json.loads(self.server.queue_path.read_text(encoding="utf-8"))

    def atomic_write(self, payload: dict) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.server.queue_path.parent, delete=False) as handle:
            json.dump(payload, handle, indent=2);handle.write("\n");temporary = Path(handle.name)
        temporary.replace(self.server.queue_path)


    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 50_000:
            raise ValueError("invalid body length")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("body must be a JSON object")
        return payload

    def update_queue_status(self, queue: dict) -> int:
        completed = sum(row.get("disposition") is not None for row in queue["items"])
        queue["completed_items"] = completed
        queue["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        queue["status"] = (
            "ADJUDICATION_COMPLETE_PENDING_FREEZE"
            if completed == len(queue["items"])
            else "PENDING_HUMAN_ADJUDICATION"
        )
        return completed

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/": self.send_bytes(HTML.encode("utf-8"), "text/html; charset=utf-8");return
        if path == "/api/queue": self.send_json(self.read_queue());return
        if path.startswith("/api/state/"):
            asset_key = unquote(path[len("/api/state/"):])
            state = self.server.asset_states.get(asset_key)
            if state is None:
                self.fail("state not found", HTTPStatus.NOT_FOUND);return
            primary_label = json.loads(state["primary_label_path"].read_text(encoding="utf-8"))
            secondary_label = json.loads(state["secondary_label_path"].read_text(encoding="utf-8"))
            self.send_json(
                {
                    "asset_key": asset_key,
                    "primary_blind_id": state["primary_blind_id"],
                    "secondary_blind_id": state["secondary_blind_id"],
                    "clean_image_url": f"/state-image/primary/{state['primary_blind_id']}",
                    "primary_image_url": f"/state-image/primary/{state['primary_blind_id']}",
                    "secondary_image_url": f"/state-image/secondary/{state['secondary_blind_id']}",
                    "primary_label": primary_label,
                    "secondary_label": secondary_label,
                }
            );return
        if path.startswith("/state-image/"):
            parts = path.split("/")
            if len(parts) != 4 or parts[1] != "state-image":
                self.fail("image not found", HTTPStatus.NOT_FOUND);return
            role, blind_id = parts[2], parts[3]
            if role not in {"primary", "secondary"} or not BLIND_ID.fullmatch(blind_id):
                self.fail("image not found", HTTPStatus.NOT_FOUND);return
            target = self.server.state_images.get((role, blind_id))
            if target is None or not target.is_file():
                self.fail("image not found", HTTPStatus.NOT_FOUND);return
            self.send_bytes(target.read_bytes(), "image/png");return
        if path.startswith("/asset/"):
            relative = unquote(path[len("/asset/"):])
            if relative not in self.server.allowed_assets:
                self.fail("asset not allowed", HTTPStatus.NOT_FOUND);return
            target = (self.server.packet_root / relative).resolve()
            if not target.is_relative_to(self.server.packet_root) or not target.is_file():
                self.fail("asset not found", HTTPStatus.NOT_FOUND);return
            self.send_bytes(target.read_bytes(), "image/png");return
        self.fail("not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/bulk":
            try:
                body = self.read_json_body()
            except (ValueError, json.JSONDecodeError) as exc:
                self.fail(str(exc));return
            asset_key = body.get("asset_key")
            mode = body.get("mode")
            if not isinstance(asset_key, str) or len(asset_key) > 200:
                self.fail("invalid asset key");return
            if mode not in {"human_reference", "keep_both", "accept_semantics", "clear_asset"}:
                self.fail("invalid bulk mode");return
            queue = self.read_queue()
            group = [row for row in queue["items"] if row["asset_key"] == asset_key]
            if not group:
                self.fail("asset not found", HTTPStatus.NOT_FOUND);return
            now = datetime.now(timezone.utc).isoformat()
            affected = 0
            for item in group:
                disposition = None
                if mode == "human_reference":
                    disposition = {
                        "unmatched_secondary": "accept_secondary",
                        "unmatched_primary": "reject",
                        "family_disagreement": "accept_secondary",
                    }.get(item["kind"])
                elif mode == "keep_both":
                    disposition = {
                        "unmatched_secondary": "accept_secondary",
                        "unmatched_primary": "accept_primary",
                    }.get(item["kind"])
                elif mode == "accept_semantics" and item["kind"] == "semantic_candidate":
                    disposition = "accept_candidate"
                elif mode == "clear_asset":
                    item["disposition"] = None
                    item["review_note"] = ""
                    item["reviewed_at_utc"] = None
                    affected += 1
                    continue
                if disposition is None:
                    continue
                if disposition not in item["allowed_dispositions"]:
                    self.fail(f"bulk disposition not allowed for {item['queue_id']}");return
                item["disposition"] = disposition
                item["review_note"] = f"bulk_review:{mode}"
                item["reviewed_at_utc"] = now
                affected += 1
            completed = self.update_queue_status(queue)
            self.atomic_write(queue)
            self.send_json(
                {
                    "saved": True,
                    "asset_key": asset_key,
                    "mode": mode,
                    "affected": affected,
                    "completed_items": completed,
                    "total_items": len(queue["items"]),
                    "status": queue["status"],
                }
            )
            return
        if not path.startswith("/api/item/"):
            self.fail("not found", HTTPStatus.NOT_FOUND);return
        queue_id = unquote(path[len("/api/item/"):])
        if not QUEUE_ID.fullmatch(queue_id) or queue_id not in self.server.allowed_queue_ids:
            self.fail("invalid queue id", HTTPStatus.NOT_FOUND);return
        try: body = self.read_json_body()
        except (ValueError, json.JSONDecodeError) as exc: self.fail(str(exc));return
        queue = self.read_queue();item = next(row for row in queue["items"] if row["queue_id"] == queue_id)
        disposition = body.get("disposition")
        if disposition is not None and disposition not in item["allowed_dispositions"]:
            self.fail("disposition not allowed for this item");return
        review_note = body.get("review_note", "")
        if not isinstance(review_note, str) or len(review_note) > 2000:
            self.fail("invalid review note");return
        item["disposition"] = disposition;item["review_note"] = review_note.strip();item["reviewed_at_utc"] = datetime.now(timezone.utc).isoformat() if disposition else None
        completed = self.update_queue_status(queue)
        self.atomic_write(queue);self.send_json({"saved": True, "queue_id": queue_id, "completed_items": completed, "total_items": len(queue["items"]), "status": queue["status"]})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser();parser.add_argument("--packet-root", type=Path, required=True);parser.add_argument("--queue", type=Path);parser.add_argument("--host", default="127.0.0.1");parser.add_argument("--port", type=int, default=8767);args = parser.parse_args()
    packet_root = args.packet_root.resolve();queue_path = (args.queue or packet_root / "adjudication_queue.json").resolve();server = AdjudicationServer((args.host, args.port), packet_root, queue_path)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", "queue": str(queue_path), "items": len(server.allowed_queue_ids)}), flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__ == "__main__": raise SystemExit(main())
