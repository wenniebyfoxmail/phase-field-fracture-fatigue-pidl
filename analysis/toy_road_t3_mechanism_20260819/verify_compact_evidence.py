from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.toy_road_t3_mechanism_20260819.evidence import verify_compact_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify compact T3 evidence.")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_compact_evidence(args.root), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
