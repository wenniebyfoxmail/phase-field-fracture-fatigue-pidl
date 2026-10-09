# HQ-PUBLIC-REF-001 execution preparation

2026-10-09. User explicitly authorized execution in the current conversation: 授权 请执行. Scope is the reviewed single-model diagnostic, 40epochs/6 GPUhours training+validation, at most1 further GPUhour final inference. No results exist. No authority to stop other users/services.

Owner: HQ public published-reference diagnostic. Isolated branch codex/hq-public-reference-launch-20261009, base origin/main389f618b7a042e0a4e4d11a3ab24a7164f6902cc. In-scope only research_hq/HQ-PUBLIC-REF-001; legacy routes, registries and shared logs excluded. This preparation ID is not falsely presented as a registered Sxx experiment; formal attribution remains required before launch.

Reviewed code snapshot93a3b0b9cf9928022af646fb974c8ba8809a255f47ed402f35c28657bbeaaa7b, verified input lock19f0e55ba20c8758a06f72f3b3300bd25b6821d241b01f690a75777ff3c794d8. Source files copied byte-identically. No training runner edits. R1 evidence domain is real public surface imagery, not real-road/physical-truth qualification; formal domain annotation must retain this distinction.

Taobo hostname GPUServer8 reached. /mnt/data2 free756G, /mnt/data3 free914G. All8 GPUs have live resident processes; memory usedMiB by GPU0–7:7465,22384,14642,9302,21321,19140,23170,11122. GPU0 includes uvicorn service PID1344818 and app.py PID3887899. Device utilization0% in sampled output is not proof of availability. Did not terminate, move or inspect service contents.

Status: BLOCKED_GPU_ALLOCATION, not started. No remote data/code write or job launched. No fallback machine used. No external notification sent. Need one safely assigned GPU, or explicit coordination establishing acceptable bounded co-tenancy; this is a concrete current resource blocker, not a repeat request for experiment authorization.

Raw data remains local in Downloads/METU_recovered_20261009 and Downloads/BuildCrack_official_20261009 (~950MiB total). Deployment/environment identity and launch receipt are not fabricated. Once allocation is known, recheck live utilization, preflight CUDA and exact source/data/environment; create fresh producer directory and detached job. Do not launch automatically based on stale device snapshots.

Read-only producer environment (CUDA_VISIBLE_DEVICES=-1, no GPU allocation): Python3.10.12, torch2.7.0+cu126, numpy1.24.4, Pillow11.1.0, matplotlib3.10.3, CUDA build12.6. This differs from Mac validation; producer-compatible synthetic/CUDA preflight remains required before training.
