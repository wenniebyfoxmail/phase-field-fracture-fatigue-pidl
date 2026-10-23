#!/usr/bin/env python3
"""Maintain an append-only decision ledger inside a PIDL/FEM Experiment.

Schema v2 binds an attempt to Storyline/Experiment/protocol identity and an
independent review. Existing schema-v1 GPT-Pro records remain readable and
validatable; compatibility does not upgrade their scientific status.

This script records decisions. It never launches a producer Run or accepts a
scientific claim.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ATTEMPT_STATUSES = {
    "open",
    "implemented",
    "tested",
    "accepted",
    "rejected",
    "quarantined",
    "superseded",
}
EXECUTION_STATUSES = {"", "prepared", "running", "succeeded", "failed", "cancelled", "unknown"}
RETRIEVAL_STATUSES = {"", "pending", "partial", "verified"}
SCIENTIFIC_VERDICTS = {"", "supports", "mixed", "negative", "inconclusive", "inadmissible"}

V1_REQUIRED_FIELDS = [
    "attempt_id",
    "created_at_local",
    "project",
    "attempt_type",
    "status",
    "motivation",
    "trigger",
    "current_claim_before_attempt",
    "gpt_pro_required",
    "gpt_pro_question",
    "gpt_pro_advice_path",
    "gpt_pro_advice_sha256",
    "gpt_pro_advice_summary",
    "adopted_decision",
    "rejected_or_modified_advice",
    "decision_rationale",
    "code_changes",
    "input_assets",
    "output_assets",
    "tests",
    "success_criteria",
    "failure_criteria",
    "result_interpretation",
    "claim_after_attempt",
    "next_action",
    "human_decision_required",
    "closed_at_local",
]

V2_REQUIRED_FIELDS = [
    "schema_version",
    "attempt_id",
    "created_at_local",
    "project",
    "storyline_id",
    "experiment_id",
    "protocol_revision",
    "run_id",
    "attempt_type",
    "status",
    "motivation",
    "trigger",
    "current_claim_before_attempt",
    "primary_gate",
    "stop_rule",
    "independent_review_required",
    "independent_review_question",
    "independent_review_path",
    "independent_review_sha256",
    "independent_review_summary",
    "adopted_decision",
    "rejected_or_modified_review",
    "decision_rationale",
    "code_changes",
    "input_assets",
    "output_assets",
    "tests",
    "success_criteria",
    "failure_criteria",
    "execution_status",
    "retrieval_status",
    "scientific_verdict",
    "result_interpretation",
    "claim_after_attempt",
    "next_action",
    "human_decision_required",
    "closed_at_local",
]


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_records(ledger: Path) -> list[dict[str, Any]]:
    if not ledger.exists():
        return []
    records: list[dict[str, Any]] = []
    with ledger.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{ledger}:{line_no}: invalid JSONL: {exc}") from exc
    return records


def write_records(ledger: Path, records: list[dict[str, Any]]) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    tmp = ledger.with_suffix(ledger.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, ledger)


def attempt_dir(ledger: Path, attempt_id: str) -> Path:
    return ledger.parent / "attempts" / attempt_id


def find_record(records: list[dict[str, Any]], attempt_id: str) -> dict[str, Any]:
    matches = [record for record in records if record.get("attempt_id") == attempt_id]
    if not matches:
        raise SystemExit(f"attempt_id not found: {attempt_id}")
    if len(matches) > 1:
        raise SystemExit(f"duplicate attempt_id in ledger: {attempt_id}")
    return matches[0]


def comma_items(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_asset(spec: str, required_default: bool = True) -> dict[str, Any]:
    parts = spec.split("|")
    path = parts[0].strip()
    role = parts[1].strip() if len(parts) > 1 else ""
    required = required_default
    if len(parts) > 2 and parts[2].strip():
        required = parts[2].strip().lower() in {"1", "true", "yes", "required"}
    resolved = Path(path).expanduser()
    exists = resolved.exists()
    return {
        "path": path,
        "role": role,
        "required": required,
        "exists": exists,
        "sha256": sha256_file(resolved) if exists and resolved.is_file() else "",
    }


def refresh_assets(record: dict[str, Any]) -> None:
    for key in ("input_assets", "output_assets"):
        for asset in record.get(key, []):
            resolved = Path(asset.get("path", "")).expanduser()
            exists = resolved.exists()
            asset["exists"] = exists
            asset["sha256"] = sha256_file(resolved) if exists and resolved.is_file() else ""


def parse_change(spec: str) -> dict[str, Any]:
    parts = spec.split("|")
    path = parts[0].strip()
    summary = parts[1].strip() if len(parts) > 1 else ""
    change_type = parts[2].strip() if len(parts) > 2 else "modify"
    resolved = Path(path).expanduser()
    return {
        "file": path,
        "change_summary": summary,
        "change_type": change_type,
        "sha256_after": sha256_file(resolved) if resolved.exists() and resolved.is_file() else "",
    }


def schema_version(record: dict[str, Any]) -> int:
    return int(record.get("schema_version", 1))


def review_fields(record: dict[str, Any]) -> tuple[bool, str, str, str]:
    if schema_version(record) >= 2:
        return (
            bool(record.get("independent_review_required")),
            str(record.get("independent_review_path", "")),
            str(record.get("independent_review_sha256", "")),
            str(record.get("independent_review_summary", "")),
        )
    return (
        bool(record.get("gpt_pro_required")),
        str(record.get("gpt_pro_advice_path", "")),
        str(record.get("gpt_pro_advice_sha256", "")),
        str(record.get("gpt_pro_advice_summary", "")),
    )


def validate_record(record: dict[str, Any], ledger: Path) -> list[str]:
    errors: list[str] = []
    required = V2_REQUIRED_FIELDS if schema_version(record) >= 2 else V1_REQUIRED_FIELDS
    for field in required:
        if field not in record:
            errors.append(f"missing field: {field}")

    if record.get("status") not in ATTEMPT_STATUSES:
        errors.append(f"invalid attempt status: {record.get('status')}")

    if schema_version(record) >= 2:
        for field in ("storyline_id", "experiment_id", "protocol_revision", "primary_gate", "stop_rule"):
            if not str(record.get(field, "")).strip():
                errors.append(f"schema v2 requires non-empty {field}")
        if record.get("execution_status", "") not in EXECUTION_STATUSES:
            errors.append(f"invalid execution_status: {record.get('execution_status')}")
        if record.get("retrieval_status", "") not in RETRIEVAL_STATUSES:
            errors.append(f"invalid retrieval_status: {record.get('retrieval_status')}")
        if record.get("scientific_verdict", "") not in SCIENTIFIC_VERDICTS:
            errors.append(f"invalid scientific_verdict: {record.get('scientific_verdict')}")

    review_required, review_path, _, review_summary = review_fields(record)
    if review_required and not review_summary:
        errors.append("independent review is required but its summary is empty")
    if review_path:
        resolved = Path(review_path).expanduser()
        if not resolved.is_absolute():
            resolved = ledger.parent / resolved
        if not resolved.exists():
            errors.append(f"independent review file missing: {review_path}")

    for key in ("input_assets", "output_assets"):
        for asset in record.get(key, []):
            if asset.get("required") and not Path(asset.get("path", "")).expanduser().exists():
                errors.append(f"required {key[:-1]} missing: {asset.get('path')}")
    return errors


def render_markdown(record: dict[str, Any]) -> str:
    def bullet(items: list[Any], formatter=lambda item: str(item)) -> str:
        if not items:
            return "- None\n"
        return "".join(f"- {formatter(item)}\n" for item in items)

    def fmt_change(item: dict[str, Any]) -> str:
        return f"{item.get('change_type', '')}: `{item.get('file', '')}` - {item.get('change_summary', '')}"

    def fmt_asset(item: dict[str, Any]) -> str:
        flag = "exists" if item.get("exists") else "missing"
        return f"`{item.get('path', '')}` ({item.get('role', '')}; {flag})"

    def fmt_test(item: dict[str, Any]) -> str:
        return f"{item.get('status', '')}: {item.get('test_name', '')} - {item.get('key_observation', '')}"

    review_required, review_path, review_hash, review_summary = review_fields(record)
    lines = [
        f"# Attempt {record.get('attempt_id', '')}",
        "",
        f"- Schema: `{schema_version(record)}`",
        f"- Status: `{record.get('status', '')}`",
        f"- Created: {record.get('created_at_local', '')}",
        f"- Closed: {record.get('closed_at_local', '')}",
        f"- Storyline / Experiment / protocol: `{record.get('storyline_id', '')}` / `{record.get('experiment_id', '')}` / `{record.get('protocol_revision', '')}`",
        f"- Run: `{record.get('run_id', '')}`",
        f"- Type: `{record.get('attempt_type', '')}`",
        f"- Execution / retrieval / verdict: `{record.get('execution_status', '')}` / `{record.get('retrieval_status', '')}` / `{record.get('scientific_verdict', '')}`",
        f"- Human decision required: {record.get('human_decision_required', True)}",
        "",
        "## Motivation",
        record.get("motivation", "") or "Not recorded.",
        "",
        "## Trigger",
        record.get("trigger", "") or "Not recorded.",
        "",
        "## Current Claim Before Attempt",
        record.get("current_claim_before_attempt", "") or "Not recorded.",
        "",
        "## Primary Gate And Stop Rule",
        f"- Primary gate: {record.get('primary_gate', '') or 'Not recorded.'}",
        f"- Stop rule: {record.get('stop_rule', '') or 'Not recorded.'}",
        "",
        "## Independent Review",
        f"- Required: {review_required}",
        f"- Review path: `{review_path}`",
        f"- Review sha256: `{review_hash}`",
        "",
        review_summary or "Not recorded.",
        "",
        "## Adopted Decision",
        record.get("adopted_decision", "") or "Not recorded.",
        "",
        "## Rejected Or Modified Review",
        record.get("rejected_or_modified_review", record.get("rejected_or_modified_advice", "")) or "Not recorded.",
        "",
        "## Decision Rationale",
        record.get("decision_rationale", "") or "Not recorded.",
        "",
        "## Success Criteria",
        bullet(record.get("success_criteria", [])),
        "## Failure Criteria",
        bullet(record.get("failure_criteria", [])),
        "## Code Changes",
        bullet(record.get("code_changes", []), fmt_change),
        "## Input Assets",
        bullet(record.get("input_assets", []), fmt_asset),
        "## Output Assets",
        bullet(record.get("output_assets", []), fmt_asset),
        "## Tests",
        bullet(record.get("tests", []), fmt_test),
        "## Result Interpretation",
        record.get("result_interpretation", "") or "Not recorded.",
        "",
        "## Claim After Attempt",
        record.get("claim_after_attempt", "") or "Not recorded.",
        "",
        "## Next Action",
        record.get("next_action", "") or "Not recorded.",
        "",
    ]
    return "\n".join(lines)


def cmd_new(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    if any(record.get("attempt_id") == args.attempt_id for record in records):
        raise SystemExit(f"attempt already exists: {args.attempt_id}")
    record = {field: "" for field in V2_REQUIRED_FIELDS}
    record.update(
        {
            "schema_version": 2,
            "attempt_id": args.attempt_id,
            "created_at_local": now_local(),
            "project": args.project,
            "storyline_id": args.storyline_id,
            "experiment_id": args.experiment_id,
            "protocol_revision": args.protocol_revision,
            "run_id": args.run_id,
            "attempt_type": args.type,
            "status": "open",
            "motivation": args.motivation,
            "trigger": args.trigger,
            "current_claim_before_attempt": args.current_claim,
            "primary_gate": args.primary_gate,
            "stop_rule": args.stop_rule,
            "independent_review_required": args.independent_review_required,
            "independent_review_question": args.independent_review_question,
            "human_decision_required": args.human_decision_required,
            "code_changes": [],
            "input_assets": [parse_asset(spec, True) for spec in args.input_asset],
            "output_assets": [parse_asset(spec, False) for spec in args.output_asset],
            "tests": [],
            "success_criteria": comma_items(args.success_criteria),
            "failure_criteria": comma_items(args.failure_criteria),
            "execution_status": args.execution_status,
            "retrieval_status": args.retrieval_status,
            "scientific_verdict": "",
            "closed_at_local": None,
        }
    )
    attempt_dir(ledger, args.attempt_id).mkdir(parents=True, exist_ok=True)
    records.append(record)
    write_records(ledger, records)
    print(f"created {args.attempt_id}")


def cmd_attach_review(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    review = Path(args.review_file).expanduser()
    if schema_version(record) >= 2:
        record["independent_review_path"] = str(review)
        record["independent_review_sha256"] = sha256_file(review) if review.exists() else ""
        record["independent_review_summary"] = args.summary
    else:
        record["gpt_pro_advice_path"] = str(review)
        record["gpt_pro_advice_sha256"] = sha256_file(review) if review.exists() else ""
        record["gpt_pro_advice_summary"] = args.summary
    write_records(ledger, records)
    print(f"attached independent review to {args.attempt_id}")


def cmd_decide(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    record["adopted_decision"] = args.decision
    if schema_version(record) >= 2:
        record["rejected_or_modified_review"] = args.rejected_or_modified
    else:
        record["rejected_or_modified_advice"] = args.rejected_or_modified
    record["decision_rationale"] = args.rationale
    write_records(ledger, records)
    print(f"recorded decision for {args.attempt_id}")


def cmd_change(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    record.setdefault("code_changes", []).append(parse_change(args.change))
    if args.status:
        record["status"] = args.status
    write_records(ledger, records)
    print(f"recorded change for {args.attempt_id}")


def cmd_test(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    record.setdefault("tests", []).append(
        {
            "test_name": args.name,
            "command": args.command,
            "status": args.status,
            "log_path": args.log,
            "key_observation": args.observation,
        }
    )
    if args.status == "pass" and record.get("status") in {"open", "implemented"}:
        record["status"] = "tested"
    write_records(ledger, records)
    print(f"recorded test for {args.attempt_id}")


def cmd_close(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    record["status"] = args.status
    record["result_interpretation"] = args.interpretation
    record["claim_after_attempt"] = args.claim_after
    record["next_action"] = args.next_action
    record["closed_at_local"] = now_local()
    if schema_version(record) >= 2:
        record["execution_status"] = args.execution_status
        record["retrieval_status"] = args.retrieval_status
        record["scientific_verdict"] = args.scientific_verdict
    write_records(ledger, records)
    print(f"closed {args.attempt_id} as {args.status}")


def cmd_render(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    refresh_assets(record)
    write_records(ledger, records)
    output = Path(args.out).expanduser() if args.out else attempt_dir(ledger, args.attempt_id) / "attempt.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(record), encoding="utf-8")
    print(output)


def cmd_validate(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    for record in records:
        refresh_assets(record)
    write_records(ledger, records)
    candidates = [find_record(records, args.attempt_id)] if args.attempt_id else records
    all_errors: list[str] = []
    for record in candidates:
        for error in validate_record(record, ledger):
            all_errors.append(f"{record.get('attempt_id', '<unknown>')}: {error}")
    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"validated {len(candidates)} attempt(s)")


def common_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--ledger", required=True, help="Path to attempts.jsonl")
    parent.add_argument("--attempt-id", required=True)
    return parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    shared = common_parent()

    command = sub.add_parser("new")
    command.add_argument("--ledger", required=True)
    command.add_argument("--attempt-id", required=True)
    command.add_argument("--project", default="PIDL/FEM phase-field fracture")
    command.add_argument("--storyline-id", required=True)
    command.add_argument("--experiment-id", required=True)
    command.add_argument("--protocol-revision", required=True)
    command.add_argument("--run-id", default="")
    command.add_argument("--type", required=True)
    command.add_argument("--motivation", required=True)
    command.add_argument("--trigger", default="")
    command.add_argument("--current-claim", default="")
    command.add_argument("--primary-gate", required=True)
    command.add_argument("--stop-rule", required=True)
    command.add_argument("--independent-review-required", action=argparse.BooleanOptionalAction, default=False)
    command.add_argument("--independent-review-question", default="")
    command.add_argument("--human-decision-required", action=argparse.BooleanOptionalAction, default=True)
    command.add_argument("--success-criteria", default="")
    command.add_argument("--failure-criteria", default="")
    command.add_argument("--execution-status", choices=sorted(EXECUTION_STATUSES - {""}), default="prepared")
    command.add_argument("--retrieval-status", choices=sorted(RETRIEVAL_STATUSES - {""}), default="pending")
    command.add_argument("--input-asset", action="append", default=[], help="path|role|required")
    command.add_argument("--output-asset", action="append", default=[], help="path|role|required")
    command.set_defaults(func=cmd_new)

    command = sub.add_parser("attach-review", parents=[shared])
    command.add_argument("--review-file", required=True)
    command.add_argument("--summary", required=True)
    command.set_defaults(func=cmd_attach_review)

    command = sub.add_parser("attach-advice", parents=[shared], help="legacy alias for attach-review")
    command.add_argument("--advice-file", dest="review_file", required=True)
    command.add_argument("--summary", required=True)
    command.set_defaults(func=cmd_attach_review)

    command = sub.add_parser("decide", parents=[shared])
    command.add_argument("--decision", required=True)
    command.add_argument("--rationale", required=True)
    command.add_argument("--rejected-or-modified", default="")
    command.set_defaults(func=cmd_decide)

    command = sub.add_parser("change", parents=[shared])
    command.add_argument("--change", required=True, help="file|summary|add|modify|delete")
    command.add_argument("--status", choices=sorted(ATTEMPT_STATUSES), default="")
    command.set_defaults(func=cmd_change)

    command = sub.add_parser("test", parents=[shared])
    command.add_argument("--name", required=True)
    command.add_argument("--command", required=True)
    command.add_argument("--status", choices=["pass", "fail", "skipped"], required=True)
    command.add_argument("--log", default="")
    command.add_argument("--observation", required=True)
    command.set_defaults(func=cmd_test)

    command = sub.add_parser("close", parents=[shared])
    command.add_argument("--status", choices=["accepted", "rejected", "quarantined", "superseded"], required=True)
    command.add_argument("--execution-status", choices=sorted(EXECUTION_STATUSES - {""}), default="unknown")
    command.add_argument("--retrieval-status", choices=sorted(RETRIEVAL_STATUSES - {""}), default="pending")
    command.add_argument("--scientific-verdict", choices=sorted(SCIENTIFIC_VERDICTS - {""}), required=True)
    command.add_argument("--interpretation", required=True)
    command.add_argument("--claim-after", required=True)
    command.add_argument("--next-action", required=True)
    command.set_defaults(func=cmd_close)

    command = sub.add_parser("render", parents=[shared])
    command.add_argument("--out", default="")
    command.set_defaults(func=cmd_render)

    command = sub.add_parser("validate")
    command.add_argument("--ledger", required=True)
    command.add_argument("--attempt-id", default="")
    command.set_defaults(func=cmd_validate)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
