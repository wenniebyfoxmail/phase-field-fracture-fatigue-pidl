#!/usr/bin/env python3
"""Lightweight training monitor server."""
import re
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG_FILE = "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile/training_caseC_8x400_mono.log"
DISP_TOTAL = 24  # total displacement steps for monotonic loading

def parse_log():
    try:
        with open(LOG_FILE, "r", errors="replace") as f:
            content = f.read()
    except FileNotFoundError:
        return {"steps": [], "current_step": None, "losses": [], "latest_loss": None}

    steps = sorted(set(re.findall(r"U_p: ([0-9.e+\-]+)", content)), key=float)
    losses = re.findall(r"loss=(-?[0-9]+\.[0-9]+)", content)
    latest_loss = losses[-1] if losses else None
    current_step = steps[-1] if steps else None
    return {"steps": steps, "current_step": current_step,
            "losses": losses[-200:], "latest_loss": latest_loss}

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="10">
<title>Training Monitor — 8×400 mono</title>
<style>
  body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 24px; }}
  h2 {{ color: #569cd6; }}
  .card {{ background: #252526; border-radius: 8px; padding: 16px; margin: 12px 0; }}
  .label {{ color: #9cdcfe; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
  .value {{ font-size: 28px; font-weight: bold; color: #4ec9b0; margin: 4px 0; }}
  .loss {{ color: #ce9178; }}
  .bar-bg {{ background: #3c3c3c; border-radius: 4px; height: 18px; margin-top: 8px; }}
  .bar-fg {{ background: #569cd6; border-radius: 4px; height: 18px; transition: width 0.5s; }}
  .step-list {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .step {{ background: #0e639c; color: #fff; border-radius: 4px; padding: 3px 8px; font-size: 12px; }}
  .refresh {{ color: #666; font-size: 12px; margin-top: 16px; }}
</style>
</head>
<body>
<h2>Training Monitor — 8×400 fatigue-on monotonic</h2>
<div class="card">
  <div class="label">当前加载步</div>
  <div class="value">{current_step}</div>
  <div class="label">进度 {done}/{total} 步</div>
  <div class="bar-bg"><div class="bar-fg" style="width:{pct}%"></div></div>
</div>
<div class="card">
  <div class="label">最新 loss</div>
  <div class="value loss">{latest_loss}</div>
</div>
<div class="card">
  <div class="label">已完成步骤</div>
  <div class="step-list">{steps_html}</div>
</div>
<div class="refresh">每 10 秒自动刷新</div>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = parse_log()
        done = len(data["steps"])
        pct = round(done / DISP_TOTAL * 100, 1)
        steps_html = "".join(f'<span class="step">{s}</span>' for s in data["steps"]) or "—"
        html = HTML_TEMPLATE.format(
            current_step=data["current_step"] or "等待中…",
            done=done,
            total=DISP_TOTAL,
            pct=pct,
            latest_loss=data["latest_loss"] or "—",
            steps_html=steps_html,
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *args):
        pass  # suppress access logs

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 7007), Handler)
    print("Monitor running on http://localhost:7007")
    server.serve_forever()
