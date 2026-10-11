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
