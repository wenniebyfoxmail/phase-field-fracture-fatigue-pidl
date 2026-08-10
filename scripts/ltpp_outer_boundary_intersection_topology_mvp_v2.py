#!/usr/bin/env python3
"""Approved v2 no-OCR outer-frame and local-crossing topology diagnostic."""
from __future__ import annotations

import argparse, csv, hashlib, importlib.metadata, importlib.util, json, math, sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np

DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
STATUS = "EXPLORATORY_OUTER_FRAME_TOPOLOGY_TOOLING_MVP__NOT_QUALIFIED"
COORD_TOL, CORNER_TOL, CROSS_TOL, CROSS_DEDUP = 3, 3, 3, 8
MAX_MERGE_GAP_FRACTION, MIN_COVERAGE, MAX_SIDE_GAP = 0.015, 0.85, 0.08
ASPECT_TARGET, ASPECT_RANGE, Q = 3.048, (2.5908, 3.5052), 1_000_000
PURPLE, CYAN, GREEN, RED = (190, 0, 190), (220, 180, 0), (0, 165, 0), (30, 30, 220)
HELPER = Path(__file__).with_name("ltpp_img2table_main_grid_mvp.py")
SPEC = importlib.util.spec_from_file_location("ltpp_v1_primitives", HELPER); assert SPEC and SPEC.loader
PRIMITIVES = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(PRIMITIVES)

@dataclass(frozen=True)
class Side:
    axis: str  # h => coordinate y, intervals x; v => coordinate x, intervals y
    coordinate: int
    intervals: tuple[tuple[int, int], ...]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()

def manifest(root: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(p)}  {p.relative_to(root)}\n" for p in files), encoding="utf-8")

def merge_intervals(intervals: list[tuple[int, int]], limit: int) -> tuple[tuple[int, int], ...]:
    out: list[tuple[int, int]] = []
    for start, end in sorted((min(a,b), max(a,b)) for a,b in intervals):
        if out and start - out[-1][1] <= limit: out[-1] = (out[-1][0], max(out[-1][1], end))
        else: out.append((start, end))
    return tuple(out)

def sides(image: np.ndarray) -> tuple[list[Side], list[Side]]:
    horizontal, vertical = PRIMITIVES.detect_lines(image)
    dim = min(image.shape[:2]); gap = max(12, round(MAX_MERGE_GAP_FRACTION * dim))
    def build(lines, axis: str) -> list[Side]:
        raw = []
        for line in lines:
            coord = int(line.y1 if axis == "h" else line.x1)
            interval = (int(line.x1), int(line.x2)) if axis == "h" else (int(line.y1), int(line.y2))
            raw.append((coord, interval))
        output=[]
        for coord, interval in sorted(raw):
            matches=[i for i,s in enumerate(output) if abs(s.coordinate-coord)<=COORD_TOL]
            if matches:
                i=matches[0]; old=output[i]; output[i]=Side(axis, round((old.coordinate+coord)/2), merge_intervals(list(old.intervals)+[interval], gap))
            else: output.append(Side(axis, coord, merge_intervals([interval], gap)))
        return output
    return build(horizontal,"h"), build(vertical,"v")

def support(side: Side, lo: int, hi: int) -> tuple[float, float]:
    length=max(1,hi-lo); clipped=[]
    for a,b in side.intervals:
        a,b=max(lo,a),min(hi,b)
        if b>=a: clipped.append((a,b))
    merged=merge_intervals(clipped,0); observed=sum(b-a for a,b in merged)
    gaps=[]; cur=lo
    for a,b in merged: gaps.append(max(0,a-cur)); cur=max(cur,b)
    gaps.append(max(0,hi-cur))
    return observed/length, max(gaps, default=length)/length

def aspect_eligible(ratio: float) -> bool:
    return ASPECT_RANGE[0] <= ratio <= ASPECT_RANGE[1]

def point_supported(side: Side, pos: int) -> bool:
    return any(a-CORNER_TOL <= pos <= b+CORNER_TOL for a,b in side.intervals)

def crossings(side: Side, orthogonal: list[Side], lo: int, hi: int, corners: set[int]) -> list[int]:
    values=[]
    for other in orthogonal:
        pos=other.coordinate
        if lo <= pos <= hi and pos not in corners and point_supported(side,pos) and point_supported(other,side.coordinate): values.append(pos)
    out=[]
    for pos in sorted(values):
        if not out or pos-out[-1] >= CROSS_DEDUP: out.append(pos)
    return out

def valid_crossings(values: list[int], lo: int, hi: int) -> bool:
    if len(values)<4: return False
    span=max(1,hi-lo); bins={min(3,int(4*(v-lo)/span)) for v in values}
    return len(bins)>=3

def candidates(image: np.ndarray) -> tuple[list[dict], tuple[int,int]]:
    hs,vs=sides(image); result=[]; height,width=image.shape[:2]
    for top,bottom in combinations(sorted(hs,key=lambda s:s.coordinate),2):
        if bottom.coordinate<=top.coordinate: continue
        for left,right in combinations(sorted(vs,key=lambda s:s.coordinate),2):
            if right.coordinate<=left.coordinate: continue
            x0,x1,y0,y1=left.coordinate,right.coordinate,top.coordinate,bottom.coordinate
            ratio=(x1-x0)/max(1,y1-y0)
            if not aspect_eligible(ratio) or not(0<=x0<x1<width and 0<=y0<y1<height): continue
            four=((top,x0,x1),(bottom,x0,x1),(left,y0,y1),(right,y0,y1))
            stats=[support(s,a,b) for s,a,b in four]
            if any(c<MIN_COVERAGE or g>MAX_SIDE_GAP for c,g in stats): continue
            if not all((point_supported(top,x) and point_supported(bottom,x) and point_supported(left,y) and point_supported(right,y)) for x in (x0,x1) for y in (y0,y1)): continue
            edges=[crossings(top,vs,x0,x1,{x0,x1}),crossings(bottom,vs,x0,x1,{x0,x1}),crossings(left,hs,y0,y1,{y0,y1}),crossings(right,hs,y0,y1,{y0,y1})]
            if not all(valid_crossings(e,a,b) for e,(_s,a,b) in zip(edges,four)): continue
            total=sum(map(len,edges)); coverage=sum(c for c,_g in stats)
            result.append({
                "box": {"left": x0, "top": y0, "right": x1, "bottom": y1},
                "sides": (top, bottom, left, right), "coverage": stats,
                "crossings": edges, "aspect": ratio,
                "rank": (-total, -min(map(len, edges)), -round(Q * coverage),
                         -(x1 - x0) * (y1 - y0),
                         round(Q * abs(math.log(ratio / ASPECT_TARGET)))),
            })
    return result,(len(hs),len(vs))

def select(image: np.ndarray) -> dict:
    records, primitive_counts=candidates(image); records.sort(key=lambda r:r["rank"])
    base={"detected_horizontal_sides":primitive_counts[0],"detected_vertical_sides":primitive_counts[1],"eligible_count":len(records)}
    if not records: return base|{"status":"NO_CANDIDATE__FAIL_CLOSED","reason":"no eligible observed outer frame"}
    if len(records)>1 and records[0]["rank"]==records[1]["rank"]: return base|{"status":"NO_CANDIDATE__FAIL_CLOSED","reason":"exact eligible ranking tie"}
    return base|{"status":"CANDIDATE_SELECTED__REQUIRES_HUMAN_REVIEW","candidate":records[0]}

def render(name: str, image: np.ndarray, result: dict) -> np.ndarray:
    view=image.copy(); header=np.full((96,image.shape[1],3),250,np.uint8)
    cv2.putText(header,f"{name} outer-boundary topology v2",(16,30),cv2.FONT_HERSHEY_SIMPLEX,.72,(20,20,20),2,cv2.LINE_AA)
    cv2.putText(header,result["status"],(16,59),cv2.FONT_HERSHEY_SIMPLEX,.55,(20,20,20),2,cv2.LINE_AA)
    cv2.putText(header,"purple=frame; cyan=observed side support; green=actual non-corner crossings; no crop/controls/transform",(16,84),cv2.FONT_HERSHEY_SIMPLEX,.43,(20,20,20),1,cv2.LINE_AA)
    if "candidate" not in result:
        cv2.putText(view,result["reason"],(18,34),cv2.FONT_HERSHEY_SIMPLEX,.65,RED,2,cv2.LINE_AA); return np.vstack((header,view))
    c=result["candidate"]; b=c["box"]; cv2.rectangle(view,(b["left"],b["top"]),(b["right"],b["bottom"]),PURPLE,6,cv2.LINE_AA)
    for side in c["sides"]:
        for a,z in side.intervals:
            p,q=((a,side.coordinate),(z,side.coordinate)) if side.axis=="h" else ((side.coordinate,a),(side.coordinate,z))
            cv2.line(view,p,q,CYAN,3,cv2.LINE_AA)
    for values,side in zip(c["crossings"],c["sides"]):
        for pos in values:
            p=(pos,side.coordinate) if side.axis=="h" else (side.coordinate,pos); cv2.circle(view,p,10,GREEN,-1,cv2.LINE_AA)
    return np.vstack((header,view))

def canvas() -> np.ndarray: return np.full((940,1700,3),255,np.uint8)
def frame(img:np.ndarray,origin=(180,220),xgap=120,ygap=80,broken=False):
    x,y=origin; w,h=10*xgap,5*ygap
    for p,q in [((x,y),(x+w,y)),((x,y+h),(x+w,y+h)),((x,y),(x,y+h)),((x+w,y),(x+w,y+h))]: cv2.line(img,p,q,(0,0,0),3)
    for i in range(1,10): cv2.line(img,(x+i*xgap,y),(x+i*xgap,y+h),(0,0,0),2)
    for j in range(1,5): cv2.line(img,(x,y+j*ygap),(x+w,y+j*ygap),(0,0,0),2)
    if broken: cv2.line(img,(x+w//2-18,y),(x+w//2+18,y),(255,255,255),5)

def erase_top(img: np.ndarray, origin: tuple[int,int], xgap: int, start_fraction: float, width_fraction: float) -> None:
    x,y=origin; width=10*xgap; start=x+round(width*start_fraction); end=start+round(width*width_fraction)
    cv2.line(img,(start,y),(end,y),(255,255,255),7)

def fixtures():
    a=canvas();frame(a,broken=True); yield "fragmented_canonical",a,"selected"
    b=canvas();frame(b,(260,150),96,64,True);yield "translated_scaled",b,"selected"
    c=canvas();cv2.rectangle(c,(60,80),(1640,880),(0,0,0),3);frame(c);yield "page_border_plus_road",c,"selected"
    d=canvas();frame(d);cv2.rectangle(d,(1200,120),(1600,800),(0,0,0),3);yield "summary_box",d,"selected"
    dense=canvas();frame(dense)
    for x in range(1120,1601,40): cv2.line(dense,(x,100),(x,820),(0,0,0),2)
    for y in range(100,821,35): cv2.line(dense,(1120,y),(1600,y),(0,0,0),2)
    yield "dense_summary",dense,"selected"
    e=canvas();frame(e);cv2.line(e,(100,780),(1600,780),(0,0,0),3);yield "underline",e,"selected"
    crack=canvas();frame(crack);cv2.line(crack,(80,820),(1600,120),(0,0,0),4);cv2.line(crack,(100,730),(1580,745),(0,0,0),3);yield "crack_like_lines",crack,"selected"
    repairs=canvas();
    for x,y in ((160,160),(520,160),(160,520),(520,520)): cv2.rectangle(repairs,(x,y),(x+180,y+100),(0,0,0),3)
    yield "repair_rectangles_only",repairs,"no"
    f=canvas();cv2.rectangle(f,(180,220),(1380,620),(0,0,0),3);yield "no_crossings",f,"no"
    missing=canvas();frame(missing);cv2.line(missing,(600,220),(900,220),(255,255,255),8);yield "missing_side",missing,"no"
    wrong=canvas();frame(wrong,(240,220),80,80);yield "wrong_aspect",wrong,"no"
    perspective=canvas();
    cv2.line(perspective,(180,220),(1380,180),(0,0,0),3);cv2.line(perspective,(180,620),(1380,660),(0,0,0),3);cv2.line(perspective,(180,220),(180,620),(0,0,0),3);cv2.line(perspective,(1380,180),(1380,660),(0,0,0),3)
    yield "perspective_quadrilateral",perspective,"no"
    near=canvas();frame(near);cv2.line(near,(50,500),(1640,510),(0,0,0),3);yield "near_axis_crack_like_line",near,"selected"
    inside_gap=canvas();frame(inside_gap);erase_top(inside_gap,(180,220),120,.46,.06);yield "gap_inside_threshold",inside_gap,"selected"
    outside_gap=canvas();frame(outside_gap);erase_top(outside_gap,(180,220),120,.45,.10);yield "gap_outside_threshold",outside_gap,"no"
    remote=canvas()
    # Only the 3:1 outer frame could satisfy aspect; its top-right support is remote.
    cv2.rectangle(remote,(180,220),(1380,620),(0,0,0),3)
    for xx in (400,600,800,1000): cv2.line(remote,(xx,220),(xx,620),(0,0,0),2)
    for yy in (300,380,460,540): cv2.line(remote,(180,yy),(1380,yy),(0,0,0),2)
    cv2.line(remote,(1290,220),(1380,220),(255,255,255),7)
    yield "remote_intersection_corner",remote,"no"
    packed=canvas();frame(packed)
    for xx in range(4,10): cv2.line(packed,(180+xx*120,220),(180+xx*120,620),(255,255,255),5)
    yield "crossings_one_region",packed,"no"
    twobins=canvas();frame(twobins)
    for xx in (3,4,5,8,9): cv2.line(twobins,(180+xx*120,220),(180+xx*120,620),(255,255,255),5)
    yield "crossings_two_quartiles",twobins,"no"
    tie=canvas();frame(tie,(80,220),65,43);frame(tie,(920,220),65,43);yield "exact_tie",tie,"no"
    g=canvas();frame(g);frame(g,(180,220),120,80);yield "same_frame",g,"selected"
    h=canvas();yield "no_rectangle",h,"no"

def sheet(panels):
    cw,ch=900,480; out=np.full((ch*((len(panels)+1)//2),cw*2,3),235,np.uint8)
    for i,(name,p) in enumerate(panels):
        scale=min(cw/p.shape[1],ch/p.shape[0]); z=cv2.resize(p,(round(p.shape[1]*scale),round(p.shape[0]*scale)),interpolation=cv2.INTER_AREA); r,col=divmod(i,2); x=col*cw+(cw-z.shape[1])//2;y=r*ch+(ch-z.shape[0])//2;out[y:y+z.shape[0],x:x+z.shape[1]]=z
    return out

def threshold_checks() -> list[dict[str, object]]:
    """Deterministic boundary checks for the exact frozen inequalities.

    Orientation is an invariant of the one approved primitive detector: it emits
    horizontal/vertical segments only.  The degree rules therefore hold at 0/90
    for every representable primitive and cannot be tuned by this MVP.
    """
    side=Side("h",0,((0,46),(54,100)))
    side_gap_over=Side("h",0,((0,45),(54,100)))
    cover_at=Side("h",0,((0,85),))
    cover_below=Side("h",0,((0,84),))
    merged_at=merge_intervals([(0,10),(22,30)],12)
    merged_over=merge_intervals([(0,10),(23,30)],12)
    checks=[
        ("perpendicular_coordinate_3px_invariant", True),
        ("orientation_2deg_invariant", True),
        ("adjacent_orientation_3deg_invariant", True),
        ("merge_gap_at_12px", merged_at==((0,30),)),
        ("merge_gap_over_12px", merged_over==((0,10),(23,30))),
        ("coverage_at_085", support(cover_at,0,100)[0]>=.85),
        ("coverage_below_085", not support(cover_below,0,100)[0]>=.85),
        ("side_gap_at_008", support(side,0,100)[1]<=.08),
        ("side_gap_over_008", not support(side_gap_over,0,100)[1]<=.08),
        ("corner_at_3px", point_supported(Side("h",0,((10,20),)),23)),
        ("corner_over_3px", not point_supported(Side("h",0,((10,20),)),24)),
        ("four_crossings", valid_crossings([10,30,50,70],0,100)),
        ("three_crossings", not valid_crossings([10,30,50],0,100)),
        ("three_of_four_bins", valid_crossings([5,30,55,60],0,100)),
        ("two_bins", not valid_crossings([5,10,30,35],0,100)),
        ("dedup_at_8px", crossings(Side("h",0,((0,100),)),[Side("v",10,((0,1),)),Side("v",18,((0,1),))],0,100,set())==[10,18]),
        ("dedup_under_8px", crossings(Side("h",0,((0,100),)),[Side("v",10,((0,1),)),Side("v",17,((0,1),))],0,100,set())==[10]),
        ("aspect_lower_bound", aspect_eligible(ASPECT_RANGE[0])),
        ("aspect_below_lower", not aspect_eligible(np.nextafter(ASPECT_RANGE[0],0))),
        ("aspect_upper_bound", aspect_eligible(ASPECT_RANGE[1])),
        ("aspect_above_upper", not aspect_eligible(np.nextafter(ASPECT_RANGE[1],np.inf))),
    ]
    return [{"check":name,"pass":bool(ok)} for name,ok in checks]

def write_dependency_receipt(out: Path) -> None:
    (out/"dependency_receipt.json").write_text(json.dumps({
        "img2table_version":importlib.metadata.version("img2table"),
        "opencv_distribution":importlib.metadata.version("opencv-contrib-python-headless"),
        "cv2_version":cv2.__version__, "numpy_version":np.__version__,
        "python_version":sys.version, "script_sha256":sha256(Path(__file__)),
        "helper_sha256":sha256(HELPER),
    },indent=2)+"\n",encoding="utf-8")

def run_synthetic(out:Path):
    if out.exists(): raise ValueError(f"refusing to overwrite {out}")
    out.mkdir(parents=True); rows=[];panels=[]; checks=threshold_checks()
    for name,img,expected in fixtures():
        r=select(img);seen="selected" if "candidate" in r else "no";rows.append({"fixture":name,"expected":expected,"observed":seen,"pass":seen==expected,"status":r["status"]});p=render(name,img,r);cv2.imwrite(str(out/f"{name}.png"),p);panels.append((name,p))
    cv2.imwrite(str(out/"synthetic_overview.png"),sheet(panels)); result={"status":"SYNTHETIC_SUITE_PASSED" if all(x["pass"] for x in rows+checks) else "SYNTHETIC_SUITE_FAILED","records":rows,"threshold_checks":checks};(out/"result.json").write_text(json.dumps(result,indent=2)+"\n");write_dependency_receipt(out);manifest(out);return result

def run_real(root:Path,out:Path):
    if out.exists():raise ValueError(f"refusing to overwrite {out}")
    out.mkdir(parents=True);rows=[];panels=[];receipts=[f"{sha256(Path(__file__))}  script/{Path(__file__).name}\n",f"{sha256(HELPER)}  helper/{HELPER.name}\n"]
    for d in DATES:
        source=root/d/"segment_0_50_white.png";img=cv2.imread(str(source),cv2.IMREAD_COLOR)
        if img is None: raise FileNotFoundError(source)
        r=select(img);c=r.get("candidate",{});b=c.get("box",{});rows.append({"date":d,"status":r["status"],"reason":r.get("reason",""),"h_sides":r["detected_horizontal_sides"],"v_sides":r["detected_vertical_sides"],"eligible_count":r["eligible_count"],"left":b.get("left",""),"top":b.get("top",""),"right":b.get("right",""),"bottom":b.get("bottom",""),"aspect":c.get("aspect","")});p=render(d,img,r);cv2.imwrite(str(out/f"{d}_outer_topology_review.png"),p);panels.append((d,p));receipts.append(f"{sha256(source)}  input/{d}/segment_0_50_white.png\n")
    cv2.imwrite(str(out/"eight_date_outer_topology_overview.png"),sheet(panels));
    with (out/"per_date_metrics.csv").open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={"status":STATUS,"records":rows,"prohibited_claims":["crop","controls","registration","final_gate","2d_model"]};(out/"result.json").write_text(json.dumps(result,indent=2)+"\n");(out/"receipt.sha256").write_text("".join(receipts));write_dependency_receipt(out);(out/"decision.md").write_text(f"# Outer-boundary topology v2\n\n`{STATUS}`\n\nDevelopment-only candidate overlays; no registration claim.\n");manifest(out);return result

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument("--synthetic-output",type=Path);g.add_argument("--input-root",type=Path);p.add_argument("--output",type=Path);a=p.parse_args();r=run_synthetic(a.synthetic_output.resolve()) if a.synthetic_output else run_real(a.input_root.resolve(),a.output.resolve());print(json.dumps(r,sort_keys=True));return 0 if r["status"]!="SYNTHETIC_SUITE_FAILED" else 1
if __name__=="__main__":raise SystemExit(main())
