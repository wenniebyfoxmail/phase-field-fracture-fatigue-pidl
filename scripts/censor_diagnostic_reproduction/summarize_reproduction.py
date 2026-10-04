"""Report cross-platform drift; do not invent a new scientific acceptance gate."""
import argparse,csv,json,math
from pathlib import Path

def rows(path):
    with path.open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def write(path,data):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def main():
    p=argparse.ArgumentParser();p.add_argument("fresh",type=Path);p.add_argument("prior",type=Path);p.add_argument("out",type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    mapping={"region/region_energy_attribution.csv":"region_energy_attribution.csv","region/field_region_metrics.csv":"field_region_metrics.csv","region/decomposition_summary.csv":"decomposition_summary.csv","region/state_bound_audit.csv":"state_bound_audit.csv","gp_crossswap_equilibrium/gp_crossswap_metrics.csv":"gp_crossswap_equilibrium/gp_crossswap_metrics.csv","gp_crossswap_equilibrium/bounded_alpha_counterfactual.csv":"gp_crossswap_equilibrium/bounded_alpha_counterfactual.csv","gp_crossswap_equilibrium/fixed_damage_equilibrium.csv":"gp_crossswap_equilibrium/fixed_damage_equilibrium.csv"}
    drifts=[]
    for fresh,prior in mapping.items():
        x,y=rows(a.fresh/fresh),rows(a.prior/prior)
        if len(x)!=len(y):raise ValueError("row count changed: "+fresh)
        for i,(r,s) in enumerate(zip(x,y)):
            if set(r)!=set(s):raise ValueError("schema changed: "+fresh)
            for k,v in r.items():
                try: vf,vs=float(v),float(s[k])
                except (ValueError,TypeError):
                    if v!=s[k]:raise ValueError(f"label changed {fresh} {i} {k}")
                    continue
                if not math.isfinite(vf) or not math.isfinite(vs):raise ValueError("nonfinite metric")
                drifts.append({"table":fresh,"row":i,"field":k,"prior":vs,"fresh":vf,"absolute_difference":abs(vf-vs),"relative_difference":abs(vf-vs)/abs(vs) if vs else ""})
    write(a.out/"cross_platform_numeric_drift.csv",drifts)
    replay=[]
    for c in (76,82,83):
        d=json.loads((a.fresh/f"operator_replay/c{c}_operator_replay.json").read_text())
        replay.append({"cycle":c,"status":d["status"],"damage_max_abs":d["damage_gp"]["max_abs"],"strain_max_abs":max(d[k]["max_abs"] for k in ("strain_xx","strain_yy","engineering_shear_gamma_xy")),"psi_raw_relative_l2":d["psi_raw_gp"]["relative_l2"],"active_relative_l2":d["psi_active_gp"]["relative_l2"],"minimum_det_j":d["minimum_det_j"]})
    write(a.out/"operator_replay_summary.csv",replay)
    summary={"replay_pass_count":sum(r["status"]=="PASS" for r in replay),"compared_numeric_cells":len(drifts),"tables":len(mapping),"finite":True,"new_scientific_threshold":False,"operator_threshold_source":"unchanged audit_native_q4_operator.py","claim_boundary":"Reproduction only. Drift in near-zero equilibrium residuals must not be interpreted by relative error alone."}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary))
if __name__=="__main__":main()
