"""Pure graph/geometry checks; no producer execution or optimization."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "SENS_tensile"))
from s04_e018_global_local import anchor_component_geometry, damage_geometry


def fixture():
    # Node 2 is the opposite corner of node 0: diagonal is NOT an edge.
    xy = np.array([[-.5, 0.], [-.4, 0.], [-.4, .1], [-.5, .1]])
    conn = np.array([[0, 1, 2, 3]], dtype=np.int64)
    return xy, conn, np.array([.2, .3, .9, 0.]), np.array([.1, .2, .3, .4])


def test_unique_anchor_exclusion_counts_and_caller_damage_unchanged():
    xy, conn, damage, mass = fixture()
    damage[1] = 0  # active diagonal corner remains isolated
    saved = damage.copy()
    saved_mask = damage > .1
    g = anchor_component_geometry(xy, damage, conn, mass)
    assert g["component_count"] == 2
    assert g["anchor_component_nodes"] == 1
    assert g["damage_nodes"] == 2
    assert g["excluded_damage_nodes"] == 1
    assert g["damage_mass"] == pytest.approx(.4)
    assert g["anchor_component_mass"] == pytest.approx(.1)
    assert g["excluded_damage_mass"] == pytest.approx(.3)
    assert g["support_mass"] == pytest.approx(.1)
    assert g["lower"] == [-.5, 0.]
    assert g["upper"] == [-.5, 0.]
    assert g["scale"] == [.02, .02]
    assert g["components"][1]["minimum_node_id"] == 2
    np.testing.assert_array_equal(damage, saved)
    np.testing.assert_array_equal(damage > .1, saved_mask)
    assert damage[2] > .1  # excluded from support, still in loss/sampler A
    assert damage_geometry(xy, damage, mass)["damage_nodes"] == 2
    json.dumps(g, allow_nan=False)


def test_consecutive_edge_connectivity_and_deterministic_element_order():
    xy, conn, damage, mass = fixture()
    g = anchor_component_geometry(xy, damage, conn, mass)
    assert g["component_count"] == 1
    assert g["anchor_component_nodes"] == 3
    assert g["excluded_damage_nodes"] == 0
    # Cyclic rotation/reversal of the same edge cycle preserves metadata.
    repeated = np.concatenate((np.roll(conn, 1, axis=1), conn[:, ::-1], conn))
    assert anchor_component_geometry(xy, damage, repeated, mass) == g
    assert anchor_component_geometry(xy, damage, conn) ["components"][0]["mass"] is None


def test_missing_anchor_fails_closed():
    xy, conn, damage, mass = fixture()
    damage[0] = 0
    with pytest.raises(ValueError, match="found 0"):
        anchor_component_geometry(xy, damage, conn, mass)


def test_multiple_anchor_components_fail_closed():
    # Opposite active corners are both on anchor, but never joined diagonally.
    xy = np.array([[-.5, -.01], [-.4, -.01], [-.5, .01], [-.4, .01]])
    damage = np.array([1., 0., 1., 0.])
    with pytest.raises(ValueError, match="found 2"):
        anchor_component_geometry(xy, damage, np.array([[0, 1, 2, 3]]))


@pytest.mark.parametrize("conn", [np.array([[0, 1, 2, 9]]), np.array([[0., 1., 2., 3.]]),
                                 np.array([[0, 0, 2, 3]]), np.array([[0, 1, 2]])])
def test_invalid_connectivity_fails_closed(conn):
    xy, _, damage, mass = fixture()
    with pytest.raises(ValueError):
        anchor_component_geometry(xy, damage, conn, mass)
