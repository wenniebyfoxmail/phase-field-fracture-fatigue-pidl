import hashlib
import importlib.util
from pathlib import Path

import cv2
import numpy as np


SCRIPT = Path(__file__).parents[1] / "scripts" / "ltpp_render_owner_corner_carrier_mvp.py"
SPEC = importlib.util.spec_from_file_location("carrier", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_exact_physical_carrier_quantisation():
    assert (MODULE.WIDTH_PX, MODULE.HEIGHT_PX) == (1501, 451)
    assert MODULE.METRES_PER_PIXEL == 0.01016
    assert np.array_equal(MODULE.TARGET, np.float32([[0, 0], [1500, 0], [1500, 450], [0, 450]]))


def test_synthetic_projective_warp_reprojects_corners_and_preserves_orientation():
    image = np.full((500, 1600, 3), 255, np.uint8)
    source = np.float32([[70, 55], [1530, 25], [1560, 470], [45, 490]])
    cv2.polylines(image, [source.astype(np.int32)], True, (0, 0, 0), 5)
    validated = MODULE.validate_source_points(source.tolist(), image.shape[1], image.shape[0])
    warped, matrix, error, determinant = MODULE.transform_and_warp(image, validated)
    assert warped.shape == (451, 1501, 3)
    assert np.isfinite(matrix).all()
    assert error < 1e-3
    assert determinant > 0


def test_red_cyan_encoding():
    previous = np.full((5, 5, 3), 255, np.uint8)
    current = previous.copy()
    previous[1, 1] = 0
    current[3, 3] = 0
    rgb = cv2.cvtColor(MODULE.red_cyan(previous, current), cv2.COLOR_BGR2RGB)
    assert tuple(rgb[1, 1]) == (255, 0, 0)
    assert tuple(rgb[3, 3]) == (0, 255, 255)


def test_manifest_verification_fails_closed(tmp_path):
    payload = tmp_path / "payload.txt"
    payload.write_text("frozen")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    (tmp_path / "manifest.sha256").write_text(f"{digest}  payload.txt\n")
    MODULE.verify_manifest(tmp_path)
    payload.write_text("changed")
    try:
        MODULE.verify_manifest(tmp_path)
    except ValueError as error:
        assert "mismatch" in str(error)
    else:
        raise AssertionError("manifest mutation must fail closed")
