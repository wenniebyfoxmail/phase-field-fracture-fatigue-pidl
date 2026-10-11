import importlib.util
from pathlib import Path
import pytest

S = importlib.util.spec_from_file_location("baseline", Path(__file__).parents[1]/"scripts/aa2024_cycle_baselines.py")
M = importlib.util.module_from_spec(S)
S.loader.exec_module(M)

def rows(count=20):
    return [{"stage": str(i+1), "cycles": str(i*10), "cracklength": str(2+i),
             "current_stage_relative_date": str(i)} for i in range(count)]

def test_exact_ties_merge_without_label_average():
    rs = rows()
    rs.insert(1, {**rs[0], "stage": "100", "current_stage_relative_date": ".5"})
    gs = M.groups_from_rows(rs)
    assert len(gs) == 20 and gs[0]["stages"] == [1,100]
    bad = rows(); bad.insert(1, {**bad[0], "stage": "100", "cracklength": "2.000000000000001"})
    with pytest.raises(ValueError, match="discordant"): M.groups_from_rows(bad)

def test_split_is_target_group_based_and_exhaustive():
    gs = M.groups_from_rows(rows(114)); manifest = M.manifest_for(gs)
    assert [len(manifest["target_indices"][k]) for k in ("train","dev","holdout")] == [66,23,23]
    assert sorted(sum(manifest["target_indices"].values(), [])) == list(range(2,114))

def test_secant_uses_past_only_and_is_exact_for_linear_growth():
    gs = M.groups_from_rows(rows())
    pred = M.predictions(gs, M.manifest_for(gs))
    assert all(float(r["secant_error"]) == 0 for r in pred)
    changed = M.groups_from_rows(rows()); changed[10]["cracklength"] = "1000"
    p2 = M.predictions(changed, M.manifest_for(changed))
    assert p2[8]["secant"] == pred[8]["secant"]  # target index 10 changed, prediction unchanged

def test_cycle_date_decrease_blocks():
    rs=rows(); rs[3]["cycles"]="5"
    with pytest.raises(ValueError, match="ordering"): M.groups_from_rows(rs)

def test_manifest_tampering_blocks():
    gs=M.groups_from_rows(rows()); ma=M.manifest_for(gs); ma["target_indices"]["holdout"]=[2]
    with pytest.raises(ValueError,match="manifest"): M.predictions(gs,ma)

def test_no_horizon_clipping_or_monotonic_growth_clipping():
    gs=M.groups_from_rows(rows()); gs[3]["cracklength"]="0"
    pred=M.predictions(gs,M.manifest_for(gs))
    assert float(pred[2]["secant"]) < 0  # unmodified past-only decreasing slope

def test_nonzero_subfloat_errors_remain_nonzero_in_metrics():
    pred = [{"split": split, "persistence_error": "1e-400", "secant_error": "2e-400"}
            for split in ("train", "dev", "holdout")]
    scores=M.metrics(pred)
    from decimal import Decimal
    assert Decimal(scores["holdout"]["persistence"]["mae"]) == Decimal("1e-400")
    assert Decimal(scores["holdout"]["persistence"]["rmse"]) == Decimal("1e-400")
    assert Decimal(scores["holdout"]["secant_to_persistence_mae_ratio"]) == 2

def test_high_precision_history_is_not_rounded_before_prediction():
    from decimal import Decimal, localcontext
    gs=M.groups_from_rows(rows())
    with localcontext() as ctx:
        ctx.prec=150
        for i,g in enumerate(gs): g["cracklength"]=str(Decimal(1)+Decimal(i)*Decimal("1e-80"))
    pred=M.predictions(gs,M.manifest_for(gs))
    assert all(Decimal(r["secant_error"]) == 0 for r in pred)
    assert all(Decimal(r["persistence_error"]) == Decimal("-1e-80") for r in pred)

@pytest.mark.parametrize("label_case", ("ordinary_linear", "large_linear", "subfloat_quadratic"))
def test_complete_modes_and_receipt_bound_mutation(tmp_path, monkeypatch, label_case):
    import hashlib, json, zipfile
    from decimal import Decimal, localcontext
    parser=M.dependency()
    archive=tmp_path/"synthetic.zip"
    schema="ID; x_undef; y_undef; z_undef; u; v; w; epsx; epsy; epsxy; epseqv\n"
    with zipfile.ZipFile(archive,"w") as z:
        for stage in range(1,11):
            with localcontext() as ctx:
                ctx.prec=150
                label = (Decimal(stage) if label_case == "ordinary_linear" else
                         Decimal(10)**60+stage-1 if label_case == "large_linear" else
                         Decimal(stage-1)**2 * Decimal("1e-400"))
            fields={"current_stage_index":stage,"current_stage_relative_date":stage,
                    "reference_stage_index":1,"cycles":stage*10,"cracklength":label,
                    "time":stage,"force":100,"displacement":1}
            header="".join(f"# {k} : {v}\n" for k,v in fields.items())+schema+"1; numerical body sentinel\n"
            z.writestr(f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",header)
            z.writestr(f"global_3d_dic/Connections/global_3d_dic_results_1_{stage}_connections.txt","")
    original=parser.audit
    parser.audit=lambda path: original(path,expected_size=archive.stat().st_size,
                                       expected_md5=hashlib.md5(archive.read_bytes()).hexdigest())
    monkeypatch.setattr(M,"dependency",lambda:parser)
    monkeypatch.setattr(M,"ROOT",(tmp_path/"run").resolve())
    monkeypatch.setattr(M.subprocess,"check_output",lambda args,**_: "synthetic-commit\n" if "rev-parse" in args else "")
    monkeypatch.setattr(M.sys,"argv",["runner","prepare","--archive",str(archive)])
    M.main()
    monkeypatch.setattr(M.sys,"argv",["runner","evaluate"])
    if label_case == "subfloat_quadratic":
        with pytest.raises(ValueError,match="plot float representation"):
            M.main()
    else:
        M.main()
    scores=json.loads((M.ROOT/"evaluate/metrics.json").read_text())
    if label_case == "subfloat_quadratic":
        hold=scores["scores"]["holdout"]
        assert Decimal(hold["persistence"]["mae"]) == Decimal("1.6e-399")
        assert Decimal(hold["secant"]["mae"]) == Decimal("2e-400")
        assert Decimal(hold["secant_to_persistence_mae_ratio"]) == Decimal(".125")
        assert json.loads((M.ROOT/"evaluate/execution_receipt.json").read_text())["status"] == "failed"
    else:
        assert Decimal(scores["scores"]["holdout"]["secant"]["mae"]) == 0
        assert (M.ROOT/"evaluate/holdout_baselines.png").stat().st_size > 1000
    # Rewriting a lock without its already-recorded receipt cannot admit altered data.
    prepared=M.ROOT/"prepare"
    lock=json.loads((prepared/"preparation_lock.json").read_text())
    lock["groups.json"]="0"*64
    (prepared/"preparation_lock.json").write_text(json.dumps(lock))
    with pytest.raises(ValueError,match="receipt artifact mismatch"):
        M.evaluate(prepared,tmp_path/"unused")

def test_squared_subfloat_error_rmse_remains_nonzero():
    from decimal import Decimal
    pred=[{"split":s,"persistence_error":"1e-200","secant_error":"0"} for s in ("train","dev","holdout")]
    hold=M.metrics(pred)["holdout"]
    assert Decimal(hold["persistence"]["rmse"]) == Decimal("1e-200")
