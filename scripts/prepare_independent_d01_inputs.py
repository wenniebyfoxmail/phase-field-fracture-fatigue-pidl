"""Strip historical answers from geometry and profile containers for E018."""
import argparse
import json
from pathlib import Path
import numpy as np

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    raw = a.archive_root / "S03-E012-D01/runs/S03-E012-D01-R001"
    old = a.archive_root / "S03-E015-D01/runs"
    lock = json.loads((old / "S03-E015-D01-R000/first_frame_transects_lock.json").read_text())
    groups = json.loads((raw / "selected_sequences_before_pixel_access.json").read_text())["groups"]
    safe = {}
    for b in (4, 5, 6):
        g = lock["beams"][str(b)]
        safe[str(b)] = {"native_shape": g["native_shape"], "working_shape": g["working_shape"],
                       "transects": [{k: t[k] for k in ("id", "center", "normal")} for t in g["transects"]],
                       "stages": [{"beam": s["beam"], "nominal_load_kN": s["nominal_load_kN"],
                                   "filename_time_s": s["filename_time_s"],
                                   "source_image": str(raw / "raw_images" / s["saved_as"]),
                                   "bytes": s["entry"]["uncompressed_bytes"], "crc32": s["entry"]["crc32"]}
                                  for s in groups[str(b)]]}
        with np.load(old / f"S03-E015-D01-R001/Beam{b}_profiles.npz") as z:
            arrays = {k: z[k] for k in ("normal_offsets_native_px", "profiles", "loads_kN")}
        with np.load(raw / f"Beam{b}_stage_fields.npz") as z:
            arrays["homographies"] = z["homographies"]
        np.savez_compressed(a.output / f"Beam{b}_inputs.npz", **arrays)
    (a.output / "geometry.json").write_text(json.dumps({"beams": safe}, indent=2)+"\n")
    print("Sanitized inputs: 3 NPZ files (offsets/profiles/loads/H only); geometry without origin_qc.")

if __name__ == "__main__":
    main()
