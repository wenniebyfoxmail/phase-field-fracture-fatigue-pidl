#!/usr/bin/env python3
"""Append-only PIDL/FEM attempt ledger.

This script records decision-critical attempts as JSONL plus optional Markdown.
It deliberately does not launch PIDL/FEM runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any


STATUSES = {
    "open",
    "implemented",
    "tested",
    "accepted",
    "rejected",
    "quarantined",
    "superseded",
}

REQUIRED_FIELDS = [
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


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_records(ledger: Path) -> list[dict[str, Any]]:
    if not ledger.exists():
        return []
    records: list[dict[str, Any]] = []
    with ledger.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
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
    with tmp.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, ledger)


def attempt_dir(ledger: Path, attempt_id: str) -> Path:
    return ledger.parent / "attempts" / attempt_id


def find_record(records: list[dict[str, Any]], attempt_id: str) -> dict[str, Any]:
    matches = [r for r in records if r.get("attempt_id") == attempt_id]
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
    p = Path(path).expanduser()
    exists = p.exists()
    return {
        "path": path,
        "role": role,
        "required": required,
        "exists": exists,
        "sha256": sha256_file(p) if exists and p.is_file() else "",
    }


def refresh_assets(record: dict[str, Any]) -> None:
    for key in ("input_assets", "output_assets"):
        for asset in record.get(key, []):
            p = Path(asset.get("path", "")).expanduser()
            exists = p.exists()
            asset["exists"] = exists
            asset["sha256"] = sha256_file(p) if exists and p.is_file() else ""


def parse_change(spec: str) -> dict[str, Any]:
    parts = spec.split("|")
    path = parts[0].strip()
    summary = parts[1].strip() if len(parts) > 1 else ""
    change_type = parts[2].strip() if len(parts) > 2 else "modify"
    p = Path(path).expanduser()
    return {
        "file": path,
        "change_summary": summary,
        "change_type": change_type,
        "sha256_after": sha256_file(p) if p.exists() and p.is_file() else "",
    }


def validate_record(record: dict[str, Any], ledger: Path) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing field: {field}")
    if record.get("status") not in STATUSES:
        errors.append(f"invalid status: {record.get('status')}")
    if record.get("gpt_pro_required") and not record.get("gpt_pro_advice_summary"):
        errors.append("gpt_pro_required=true but gpt_pro_advice_summary is empty")
    for key in ("input_assets", "output_assets"):
        for asset in record.get(key, []):
            if asset.get("required") and not Path(asset.get("path", "")).expanduser().exists():
                errors.append(f"required {key[:-1]} missing: {asset.get('path')}")
    if record.get("gpt_pro_advice_path"):
        advice = Path(record["gpt_pro_advice_path"]).expanduser()
        if not advice.is_absolute():
            advice = ledger.parent / advice
        if not advice.exists():
            errors.append(f"GPT Pro advice file missing: {record['gpt_pro_advice_path']}")
    return errors


def render_markdown(record: dict[str, Any]) -> str:
    def bullet(items: list[Any], formatter=lambda x: str(x)) -> str:
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

    lines = [
        f"# Attempt {record.get('attempt_id', '')}",
        "",
        f"- Status: `{record.get('status', '')}`",
        f"- Created: {record.get('created_at_local', '')}",
        f"- Closed: {record.get('closed_at_local', '')}",
        f"- Type: `{record.get('attempt_type', '')}`",
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
        "## GPT Pro Advice",
        f"- Required: {record.get('gpt_pro_required', False)}",
        f"- Advice path: `{record.get('gpt_pro_advice_path', '')}`",
        f"- Advice sha256: `{record.get('gpt_pro_advice_sha256', '')}`",
        "",
        record.get("gpt_pro_advice_summary", "") or "Not recorded.",
        "",
        "## Adopted Decision",
        record.get("adopted_decision", "") or "Not recorded.",
        "",
        "## Rejected Or Modified Advice",
        record.get("rejected_or_modified_advice", "") or "Not recorded.",
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
    if any(r.get("attempt_id") == args.attempt_id for r in records):
        raise SystemExit(f"attempt already exists: {args.attempt_id}")
    record = {field: "" for field in REQUIRED_FIELDS}
    record.update(
        {
            "attempt_id": args.attempt_id,
            "created_at_local": now_local(),
            "project": args.project,
            "attempt_type": args.type,
            "status": "open",
            "motivation": args.motivation,
            "trigger": args.trigger,
            "current_claim_before_attempt": args.current_claim,
            "gpt_pro_required": args.gpt_pro_required,
            "gpt_pro_question": args.gpt_pro_question,
            "human_decision_required": args.human_decision_required,
            "code_changes": [],
            "input_assets": [parse_asset(s, True) for s in args.input_asset],
            "output_assets": [parse_asset(s, False) for s in args.output_asset],
            "tests": [],
            "success_criteria": comma_items(args.success_criteria),
            "failure_criteria": comma_items(args.failure_criteria),
            "closed_at_local": None,
        }
    )
    attempt_dir(ledger, args.attempt_id).mkdir(parents=True, exist_ok=True)
    records.append(record)
    write_records(ledger, records)
    print(f"created {args.attempt_id}")


def cmd_attach_advice(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    advice = Path(args.advice_file).expanduser()
    record["gpt_pro_advice_path"] = str(advice)
    record["gpt_pro_advice_sha256"] = sha256_file(advice) if advice.exists() else ""
    record["gpt_pro_advice_summary"] = args.summary
    write_records(ledger, records)
    print(f"attached advice to {args.attempt_id}")


def cmd_decide(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    record["adopted_decision"] = args.decision
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
    if args.status not in STATUSES - {"open", "implemented", "tested"}:
        raise SystemExit(f"close status must be final-ish, got {args.status}")
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    record["status"] = args.status
    record["result_interpretation"] = args.interpretation
    record["claim_after_attempt"] = args.claim_after
    record["next_action"] = args.next_action
    record["closed_at_local"] = now_local()
    write_records(ledger, records)
    print(f"closed {args.attempt_id} as {args.status}")


def cmd_render(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    record = find_record(records, args.attempt_id)
    refresh_assets(record)
    out = Path(args.out).expanduser() if args.out else attempt_dir(ledger, args.attempt_id) / "attempt.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(record), encoding="utf-8")
    print(out)


def cmd_validate(args: argparse.Namespace) -> None:
    ledger = Path(args.ledger).expanduser()
    records = read_records(ledger)
    for record in records:
        refresh_assets(record)
    if args.attempt_id:
        candidates = [find_record(records, args.attempt_id)]
    else:
        candidates = records
    all_errors: list[str] = []
    for record in candidates:
        for err in validate_record(record, ledger):
            all_errors.append(f"{record.get('attempt_id', '<unknown>')}: {err}")
    if all_errors:
        for err in all_errors:
            print(f"ERROR: {err}")
        raise SystemExit(1)
    print(f"validated {len(candidates)} attempt(s)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument("--ledger", required=True, help="Path to attempts.jsonl")
    common_parent.add_argument("--attempt-id", required=True)

    sp = sub.add_parser("new")
    sp.add_argument("--ledger", required=True)
    sp.add_argument("--attempt-id", required=True)
    sp.add_argument("--project", default="PIDL/FEM phase-field fracture alignment")
    sp.add_argument("--type", required=True)
    sp.add_argument("--motivation", required=True)
    sp.add_argument("--trigger", default="")
    sp.add_argument("--current-claim", default="")
    sp.add_argument("--gpt-pro-required", action=argparse.BooleanOptionalAction, default=True)
    sp.add_argument("--gpt-pro-question", default="")
    sp.add_argument("--human-decision-required", action=argparse.BooleanOptionalAction, default=True)
    sp.add_argument("--success-criteria", default="")
    sp.add_argument("--failure-criteria", default="")
    sp.add_argument("--input-asset", action="append", default=[], help="path|role|required")
    sp.add_argument("--output-asset", action="append", default=[], help="path|role|required")
    sp.set_defaults(func=cmd_new)

    sp = sub.add_parser("attach-advice", parents=[common_parent])
    sp.add_argument("--advice-file", required=True)
    sp.add_argument("--summary", required=True)
    sp.set_defaults(func=cmd_attach_advice)

    sp = sub.add_parser("decide", parents=[common_parent])
    sp.add_argument("--decision", required=True)
    sp.add_argument("--rationale", required=True)
    sp.add_argument("--rejected-or-modified", default="")
    sp.set_defaults(func=cmd_decide)

    sp = sub.add_parser("change", parents=[common_parent])
    sp.add_argument("--change", required=True, help="file|summary|add|modify|delete")
    sp.add_argument("--status", choices=sorted(STATUSES), default="")
    sp.set_defaults(func=cmd_change)

    sp = sub.add_parser("test", parents=[common_parent])
    sp.add_argument("--name", required=True)
    sp.add_argument("--command", required=True)
    sp.add_argument("--status", choices=["pass", "fail", "skipped"], required=True)
    sp.add_argument("--log", default="")
    sp.add_argument("--observation", required=True)
    sp.set_defaults(func=cmd_test)

    sp = sub.add_parser("close", parents=[common_parent])
    sp.add_argument("--status", choices=["accepted", "rejected", "quarantined", "superseded"], required=True)
    sp.add_argument("--interpretation", required=True)
    sp.add_argument("--claim-after", required=True)
    sp.add_argument("--next-action", required=True)
    sp.set_defaults(func=cmd_close)

    sp = sub.add_parser("render", parents=[common_parent])
    sp.add_argument("--out", default="")
    sp.set_defaults(func=cmd_render)

    sp = sub.add_parser("validate")
    sp.add_argument("--ledger", required=True)
    sp.add_argument("--attempt-id", default="")
    sp.set_defaults(func=cmd_validate)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
