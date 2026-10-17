"""E037 observer-guided per-frame candidates; no material-position mapping."""
import argparse,csv,hashlib,json,os,socket,subprocess,sys,time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageOps
from scipy.ndimage import distance_transform_edt
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components,dijkstra
from skimage.morphology import skeletonize
from md01_early_relative import save,now

PROTOCOL="per-frame-visible-geometry-v1"
METRICS=("area_px2","length_px","thickness_mean_px","thickness_p10_px","thickness_p50_px","thickness_p90_px")


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def guard(lock):
    if not all(sha(p)==h for p,h in lock["protected_old_hashes"].items()):raise ValueError("Protected old result changed")


def read_frame(f,roi):
    p=Path(f["source"])
    if p.stat().st_size!=f["bytes"] or sha(p)!=f["sha256"]:raise ValueError("Source identity mismatch")
    with Image.open(p) as raw:
        im=ImageOps.exif_transpose(raw).convert("RGB")
        if im.size!=(6000,4000):raise ValueError("Native image geometry changed")
        return np.asarray(im.crop(roi))


def extract(rgb,support,roi):
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(np.float32);shape=gray.shape
    excluded=np.zeros(shape,np.uint8)
    for poly in support["exclude_polygons"]:
        cv2.fillPoly(excluded,[np.rint(np.array(poly)-np.array(roi[:2])).astype(np.int32)],1)
    seed=np.zeros(shape,np.uint8)
    if support["visible_trace"]:
        points=np.rint(np.array(support["coarse_guide_xy"])-np.array(roi[:2])).astype(np.int32)
        cv2.polylines(seed,[points],False,1,thickness=1)
    mask=np.zeros(shape,bool)
    if np.any(seed):
        guide_distance=distance_transform_edt(~seed.astype(bool))
        bg=cv2.boxFilter(gray,-1,(101,101),borderType=cv2.BORDER_REFLECT)
        candidate=(gray<=100)&(bg-gray>=20)&(guide_distance<=60)&~excluded.astype(bool)
        count,labels,stats,_=cv2.connectedComponentsWithStats(candidate.astype(np.uint8),8)
        near=np.unique(labels[(guide_distance<=12)&candidate])
        keep=[int(k) for k in near if k>0 and stats[k,cv2.CC_STAT_HEIGHT]>=30]
        mask=np.isin(labels,keep) if keep else mask
    safe=distance_transform_edt(~excluded.astype(bool))>60
    safe[:60]=False;safe[-60:]=False;safe[:,:60]=False;safe[:,-60:]=False
    return mask,excluded.astype(bool),safe


def dominant_paths(skeleton):
    coords=np.argwhere(skeleton);n=len(coords)
    if not n:return []
    lookup=np.full(skeleton.shape,-1,np.int32);lookup[tuple(coords.T)]=np.arange(n)
    rr=[];cc=[];ww=[]
    height,width=skeleton.shape
    for dy,dx in ((0,1),(1,0),(1,1),(1,-1)):
        p=coords+np.array([dy,dx]);inside=(p[:,0]>=0)&(p[:,0]<height)&(p[:,1]>=0)&(p[:,1]<width)
        source=np.flatnonzero(inside);q=p[inside];target=lookup[tuple(q.T)];ok=target>=0
        source,target,q=source[ok],target[ok],q[ok]
        if dy and dx:
            c=coords[source];ok=~(skeleton[c[:,0],q[:,1]]|skeleton[q[:,0],c[:,1]])
            source,target=source[ok],target[ok]
        rr.extend(source.tolist());cc.extend(target.tolist());ww.extend([float(np.hypot(dx,dy))]*len(source))
    graph=coo_matrix((ww+ww,(rr+cc,cc+rr)),shape=(n,n)).tocsr()
    k,labels=connected_components(graph,directed=False);out=[]
    for label in range(k):
        nodes=np.flatnonzero(labels==label)
        if len(nodes)<2:continue
        sub=graph[nodes][:,nodes];d=dijkstra(sub,directed=False,indices=0);u=int(np.argmax(d))
        d,pred=dijkstra(sub,directed=False,indices=u,return_predecessors=True);v=int(np.argmax(d));chain=[v]
        while chain[-1]!=u:
            previous=int(pred[chain[-1]])
            if previous<0 or len(chain)>len(nodes):raise ValueError("Invalid graph path")
            chain.append(previous)
        xy=coords[nodes[np.array(chain[::-1])]][:,::-1].astype(float)
        if xy[0,1]>xy[-1,1]:xy=xy[::-1]
        s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
        out.append(dict(xy=xy,s=s,length=float(s[-1])))
    return out


def metrics(mask,safe,roi,subroi=None):
    region=np.ones(mask.shape,bool)
    if subroi is not None:
        region[:]=False;x0,y0,x1,y1=np.array(subroi)-np.array([roi[0],roi[1],roi[0],roi[1]])
        region[y0:y1,x0:x1]=True
    measured=mask&region;skel=skeletonize(measured);paths=dominant_paths(skel)
    thickness=2*distance_transform_edt(mask);traces=[];allwidths=[];pointcount=0
    for i,p in enumerate(paths):
        xy=p["xy"].astype(int);valid=safe[xy[:,1],xy[:,0]];widths=thickness[xy[:,1],xy[:,0]]
        pointcount+=len(widths);allwidths.extend(widths[valid].tolist())
        endpoints=[dict(xy_native=(p["xy"][j]+np.array(roi[:2])).tolist(),near_roi_or_exclusion_boundary=bool(not valid[j]),
                        interpretation="possible visible-support cut, not a confirmed crack tip") for j in (0,-1)]
        traces.append(dict(segment=i,xy_native=(p["xy"]+np.array(roi[:2])).tolist(),arc_length_px=p["s"].tolist(),endpoints=endpoints,
                           local_mask_thickness_px=[float(w) if v else None for w,v in zip(widths,valid)],length_px=p["length"]))
    good=bool(paths and np.any(measured));values=dict(valid=good,reason="candidate_extracted" if good else "no_candidate_identified",support_scope="visible_only",
        area_px2=int(measured.sum()) if good else None,length_px=float(sum(p["length"] for p in paths)) if good else None,
        fragments=len(paths),boundary_near_endpoints=sum(e["near_roi_or_exclusion_boundary"] for p in traces for e in p["endpoints"]),thickness_points=len(allwidths),path_points=pointcount,
        thickness_withheld_fraction=1-len(allwidths)/pointcount if pointcount else None)
    for k,v in (("thickness_mean_px",np.mean(allwidths) if allwidths else None),
                ("thickness_p10_px",np.percentile(allwidths,10) if allwidths else None),
                ("thickness_p50_px",np.percentile(allwidths,50) if allwidths else None),
                ("thickness_p90_px",np.percentile(allwidths,90) if allwidths else None)):values[k]=float(v) if v is not None else None
    return values,traces,skel


def predictions(rows):
    rows={r["stage"]:r for r in rows};out={}
    for key in METRICS:
        a,b=(rows[s]["common"][key] for s in (21,22))
        valid=a is not None and b is not None and all(rows[s]["comparison_band_clear"] for s in (21,22))
        out[key]=dict(unit="px2" if key=="area_px2" else "px",persistence=float(max(0,b)) if valid else None,
                      trend=float(max(0,2*b-a)) if valid else None,raw_trend=float(2*b-a) if valid else None)
    return out


def compare(pred,target):
    out=[]
    for key,p in pred.items():
        ref=target["common"][key];valid=ref is not None and target["comparison_band_clear"] and p["persistence"] is not None and p["trend"] is not None
        ae0=abs(p["persistence"]-ref) if valid else None;ae1=abs(p["trend"]-ref) if valid else None
        out.append(dict(metric=key,unit=p["unit"],reference=ref,**{k:v for k,v in p.items() if k!="unit"},scored=bool(valid),
                   persistence_ae=ae0,trend_ae=ae1,delta_ae=ae1-ae0 if valid else None,gain=ae0-ae1 if valid else None))
    return out


def similarity(first,later):
    # Broad upper beam, not original four anchors, no mask warping or material map.
    def get(path):
        with Image.open(path) as im:return np.asarray(ImageOps.exif_transpose(im).convert("L").crop((1600,350,5600,1900)).resize((1600,620)))
    orb=cv2.ORB_create(nfeatures=2500);a,da=orb.detectAndCompute(get(first),None);b,db=orb.detectAndCompute(get(later),None)
    if da is None or db is None:return dict(available=False,reason="features_missing")
    pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2);matches=[p[0] for p in pairs if len(p)==2 and p[0].distance<.75*p[1].distance]
    if len(matches)<6:return dict(available=False,reason="too_few_matches",matches=len(matches))
    cv2.setRNGSeed(20261017)
    matrix,inliers=cv2.estimateAffinePartial2D(np.float32([a[p.queryIdx].pt for p in matches]),np.float32([b[p.trainIdx].pt for p in matches]),method=cv2.RANSAC,ransacReprojThreshold=2,maxIters=2000,confidence=.99)
    if matrix is None:return dict(available=False,reason="similarity_not_estimated",matches=len(matches))
    return dict(available=True,matches=len(matches),inliers=int(inliers.sum()),scale=float(np.hypot(matrix[0,0],matrix[1,0])),rotation_deg=float(np.degrees(np.arctan2(matrix[1,0],matrix[0,0]))),
                translation_crop_resized_px=matrix[:,2].tolist(),diagnostic_only=True,no_warp_applied=True,material_correspondence=False)


def run(a):
    start=time.monotonic();cpu=time.process_time();lock=json.loads(a.lock.read_text());support=json.loads(a.support.read_text());guard(lock)
    if lock["protocol"]!=PROTOCOL or support["protocol"]!=PROTOCOL:raise ValueError("Protocol identity")
    a.output.mkdir(parents=True,exist_ok=False);receipt=dict(protocol=PROTOCOL,phase=a.phase,started_at_utc=now(),command=sys.argv,host=socket.gethostname(),pid=os.getpid(),runtime=sys.executable,
        commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),lock_sha256=sha(a.lock),support_sha256=sha(a.support),execution="running")
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>110:raise TimeoutError("110s phase cap")
    try:
        stages=[12,13,15,16,18,19,21,22] if a.phase=="history" else [23];rows=[]
        if a.phase=="target":
            closed=json.loads((a.history/"geometry_predictions_before_target.json").read_text());frozen={p:p.read_bytes() for p in a.history.rglob("*") if p.is_file()}
            if closed["protocol"]!=PROTOCOL or closed["lock_sha256"]!=sha(a.lock) or closed["support_sha256"]!=sha(a.support):raise ValueError("History lock conflict")
        for f in lock["frames"]:
            if f["stage"] not in stages:continue
            budget();s=f["stage"];out=a.output/f"step{s}";out.mkdir();rgb=read_frame(f,lock["roi_xyxy"])
            mask,excluded,safe=extract(rgb,support["frames"][str(s)],lock["roi_xyxy"])
            full,paths,skel=metrics(mask,safe,lock["roi_xyxy"]);common,cpaths,cskel=metrics(mask,safe,lock["roi_xyxy"],lock["forecast_roi_xyxy"])
            x0,y0,x1,y1=np.array(lock["forecast_roi_xyxy"])-np.array([3800,900,3800,900])
            row=dict(stage=s,filename=f["filename"],source_sha256=f["sha256"],source_only_guide=True,old_anchor_matching_required=False,
                     visibility="visible_candidate" if full["valid"] else "unidentified_not_zero",excluded_fraction=float(excluded.mean()),
                     comparison_band_clear=bool(not excluded[y0:y1,x0:x1].any()),full=full,common=common)
            np.savez_compressed(out/"geometry_arrays.npz",mask=mask,excluded=excluded,safe=safe,skeleton=skel,common_skeleton=cskel)
            save(out/"paths.json",dict(full=paths,common=cpaths));save(out/"metrics.json",row);rows.append(row)
            print(s,full["reason"],"area",full["area_px2"],"common",common["area_px2"],flush=True)
        save(a.output/"frame_metrics.json",rows)
        if a.phase=="history":
            saved=dict(protocol=PROTOCOL,lock_sha256=sha(a.lock),support_sha256=sha(a.support),predictions=predictions(rows),saved_at_utc=now(),target_already_exposed=True,role="retrospective development replay")
            save(a.output/"geometry_predictions_before_target.json",saved)
        else:
            scores=compare(closed["predictions"],rows[0]);save(a.output/"comparison.json",scores)
            sources={f["stage"]:f["source"] for f in lock["frames"]};diag={str(s):similarity(sources[21],sources[s]) for s in (22,23)}
            save(a.output/"view_consistency.json",dict(same_camera_provenance=True,native_dimensions=[6000,4000],fixed_image_space_band=lock["forecast_roi_xyxy"],not_material_point_tracking=True,similarity_diagnostics=diag))
            if any(p.read_bytes()!=data for p,data in frozen.items()):raise ValueError("History geometry/predictions changed")
            print(json.dumps(scores,indent=2))
        guard(lock);budget();receipt.update(execution="succeeded",retrieval="verified_local",old_results_unchanged=True)
    except Exception as error:receipt.update(execution="failed",error=repr(error));raise
    finally:
        receipt.update(ended_at_utc=now(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu);save(a.output/"run_receipt.json",receipt)


def tests():
    m=np.zeros((300,240),bool);m[40:260,100:111]=True;safe=np.ones_like(m);v,p,sk=metrics(m,safe,[0,0,240,300]);assert v["area_px2"]==2420 and 200<v["length_px"]<230 and v["thickness_p50_px"]==12
    # Solid rectangular mask isnot half-depth width; centre-grid EDT diameter12 for11pixel mask.
    m[140:160]=False;v2,p2,sk2=metrics(m,safe,[0,0,240,300]);assert len(p2)==2 and v2["area_px2"]<v["area_px2"]
    assert metrics(np.zeros_like(m),safe,[0,0,240,300])[0]["area_px2"] is None
    support=dict(visible_trace=True,coarse_guide_xy=[[100,40],[100,260]],exclude_polygons=[[[0,140],[240,140],[240,160],[0,160]]])
    rgb=np.full((300,240,3),180,np.uint8);rgb[40:260,96:105]=20;mask,ex,ss=extract(rgb,support,[0,0,240,300]);assert not(mask&ex).any() and not mask[150].any()
    fake=[dict(stage=s,comparison_band_clear=True,common={k:v for k in METRICS}) for s,v in ((21,10.),(22,15.))];pred=predictions(fake);cmp=compare(pred,dict(comparison_band_clear=True,common={k:17. for k in METRICS}));assert all(r["gain"]==-1 for r in cmp)
    print("Newmask area,disconnected lengths,EDT convention,exclusion/nulls,baseline arithmetic: passed")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("self-test","history","target"))
    for name in ("lock","support","history","output"):p.add_argument("--"+name,type=Path)
    a=p.parse_args()
    if a.phase=="self-test":tests()
    else:run(a)
