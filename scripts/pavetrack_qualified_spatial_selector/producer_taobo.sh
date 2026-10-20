#!/bin/bash
# Re-enter a clean non-interactive shell before any checksum or Python command.
unset LD_PRELOAD LD_LIBRARY_PATH BASH_ENV ENV PYTHONPATH PYTHONHOME
exec /usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 /bin/bash --noprofile --norc -c '
set -euo pipefail
source_root="$1"
reviewed_commit="$2"
manifest_sha="$3"
approval="$4"
cd "$source_root"
manifest="docs/research/S01/S01-E029/taobo_source_manifest.json"
printf "%s  %s\n" "$manifest_sha" "$manifest" | sha256sum --check --status
sed -n '\''s/^    "\([A-Za-z0-9_./-]*\)": "\([a-f0-9]\{64\}\)"[,]\{0,1\}$/\2  \1/p'\'' "$manifest" | sha256sum --check --status
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=5 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
exec /usr/bin/python3 -I scripts/pavetrack_qualified_spatial_selector/producer_taobo.py --reviewed-commit "$reviewed_commit" --manifest-sha256 "$manifest_sha" --approval "$approval"
' _ "$@"
