"""Local zero-step validation of D5 locks, real masks and static execution boundaries."""
import ast
import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.io import loadmat

from centerline_core import centreline_metrics, soft_centreline_field

HERE = Path(__file__).resolve().parent
LOCK = json.loads((HERE / "d5_data_lock.json").read_text())


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def mask_from_zip(path, suffix):
    with zipfile.ZipFile(path) as archive:
        name = next(name for name in sorted(archive.namelist()) if name.endswith(suffix))
        with Image.open(io.BytesIO(archive.read(name))) as image: return np.asarray(image.convert("L")) > 0


def main():
    root = Path("/Users/wenxiaofang/Downloads/CRACK500_official_20261011/inner_archives")
    matrix = HERE.parent/"runs/HQ-ROAD-UQ-MATRIX-001-R001/retrieved_2026-10-19/HQ-ROAD-UQ-MATRIX-001-R001"
    paths = {"trainzip":root/"traincrop.zip","valzip":root/"valcrop.zip",
             "gapszip":Path("/Users/wenxiaofang/Downloads/GAPS384_FPHBN_official_20261019/GAPs384_raw_img_gt.zip"),
             "weights":Path("/Users/wenxiaofang/Downloads/resnet18-f37072fd.pth"),
             "d1_checkpoint":HERE.parent/"runs/HQ-ROAD-UQ-FEAS-001-R001/retrieved_2026-10-11/HQ-ROAD-UQ-FEAS-001-R001/best.pt",
             "d2_checkpoint":HERE.parent/"runs/HQ-ROAD-UQ-FEAS-002-R001/retrieved_2026-10-19/HQ-ROAD-UQ-FEAS-002-R001/best.pt",
             "d3_old_cfd_csv":matrix/"old_cfd_metrics.csv", "d3_old_gaps_csv":matrix/"old_gaps384_metrics.csv",
             "d3_repair_cfd_csv":matrix/"repair_cfd_metrics.csv", "d3_repair_gaps_csv":matrix/"repair_gaps384_metrics.csv"}
    identities = {}
    for key, path in paths.items():
        identities[key] = {"bytes":path.stat().st_size,"sha256":sha256(path)}
        assert identities[key] == {name:LOCK[key][name] for name in ("bytes","sha256")}, key
    crack = mask_from_zip(paths["trainzip"], ".png")
    gaps = mask_from_zip(paths["gapszip"], "_mask.png")
    cfd_path = sorted(Path("/Users/wenxiaofang/Downloads/CFD_official_20261011/groundTruth").glob("*.mat"))[0]
    cfd = np.asarray(loadmat(cfd_path,squeeze_me=True,struct_as_record=False)["groundTruth"].Boundaries)>0
    real = {}
    for name, mask in {"CRACK500":crack,"CFD":cfd,"GAPS384":gaps}.items():
        field=soft_centreline_field(mask); metrics=centreline_metrics(field,mask)
        assert np.isfinite(field).all() and 0 <= field.min() <= field.max() <= 1
        real[name]={"shape":list(mask.shape),"field_nonzero":int((field>0).sum()),"self_cl4_f1":metrics["cl4_f1"]}
    tree=ast.parse((HERE/"d5_runner.py").read_text()); arguments={node.arg for node in ast.walk(tree) if isinstance(node,ast.arg)}
    assert not any("road420" in name.lower() for name in arguments)
    receipt={"status":"PASS_LOCAL_ZERO_STEP","identities":identities,"real_mask_transform":real,
             "training_steps":0,"optimizer_steps":0,"road420_access":False}
    (HERE/"local_validation_receipt.json").write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))


if __name__=="__main__":main()
