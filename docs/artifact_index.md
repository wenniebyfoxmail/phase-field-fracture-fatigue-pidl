# Artifact Index

This file records important raw or packaged artifacts that should not be stored
directly in Git.  Keep entries short and factual: what it is, where it lives,
who produced it, and which summary doc uses it.

## Local Mac Artifacts

| Artifact | Location | Notes |
|---|---|---|
| Taobo PIDL archive pull, 2026-06-08 | `result/taobo_pidl_archive_20260608/` | Large local download/package root. Keep out of Git; use manifests inside the folder for remote inventory. |
| Matched BC/notch experiment package, 2026-06-08 | `experiment/matched_bc_notch_20260608/` | Local package with scripts, provenance, and summary tables. Promote only concise summaries if needed. |
| FEM result packages | `fem_result/` | Local FEM/OneDrive package mirror. Keep payloads out of Git; record stable package names in handover docs. |
| Brian review snapshot note | `BRIAN_README_2026-06-07.md` | Local untracked review-package note. Decide separately whether a cleaned version belongs in `docs/`. |

## External / Producer Artifacts

| Artifact | Location | Notes |
|---|---|---|
| Taobo PIDL archives | `/mnt/data2/drtao/pidl_archives/` | Remote archive root for GPU runs. Record run-specific archive paths in handovers or result docs. |
| Taobo project workspaces | `/mnt/data2/drtao/projects/` | Remote code/run workspaces. Do not mirror full trees into Git. |
| Windows FEM/PIDL handoffs | `~/Downloads/_pidl_handoff_v2/` and OneDrive `PIDL result/` packages | Producer package locations. Use `docs/handovers/windows_fem_outbox.md` and `docs/handovers/windows_pidl_outbox.md` as authoritative handover records. |
| CSD3 work area | `~/rds/hpc-work/` on CSD3 | HPC-side code, logs, and archives. Use `docs/handovers/csd3_outbox.md` for returned results. |

## Indexing Template

Use this template for new important artifacts:

```markdown
| Short name, date | `path/or/remote/location` | Producer, commit SHA if known, purpose, and linked summary doc. |
```

When a package becomes the basis of a written conclusion, add or update the
corresponding summary in `docs/` and keep this index as the pointer to the raw
payload.
