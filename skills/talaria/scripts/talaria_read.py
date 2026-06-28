#!/usr/bin/env python3
"""Talaria LOOK CLI/rendering surface for the Hermes talaria skill."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

RENDER_BUDGET = 35000
_OUT_TTL_SECONDS = 24 * 60 * 60
_OUT_MAX_BYTES = 20 * 1024 * 1024
_DEGRADED_STATUSES = frozenset({"degraded", "blocked", "failed", "disabled", "reconcile_required"})


def _load_bridge() -> Any:
    path = Path(__file__).with_name("talaria_bridge.py")
    module_name = "talaria_bridge_runtime"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load talaria_bridge.py from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _as_path(value: str | os.PathLike[str] | None) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    return Path(value).expanduser().resolve()


def _default_hermes_home() -> Path:
    env = _as_path(os.environ.get("HERMES_HOME"))
    if env is not None:
        if env.parent.name == "profiles":
            return env.parent.parent
        return env
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData" / "Local") / "hermes"
    return Path.home() / ".hermes"


def _skill_dir(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return (_as_path(hermes_home) or _default_hermes_home()) / "talaria-skill"


def _out_dir(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _skill_dir(hermes_home) / "out"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def _degraded_connectors(payload: dict[str, Any]) -> list[str]:
    degraded: list[str] = []
    connectors = payload.get("connectors") if isinstance(payload.get("connectors"), list) else []
    for connector in connectors:
        if not isinstance(connector, dict):
            continue
        status = str(connector.get("status") or "").lower()
        if status in _DEGRADED_STATUSES or connector.get("last_error"):
            degraded.append(str(connector.get("id") or "unknown"))
    return degraded


def _operational_timestamp(payload: dict[str, Any], *, last_cached_timestamp: str | None = None) -> str:
    for key in ("response_generated_at", "last_successful_snapshot_at", "snapshot_created_at"):
        value = payload.get(key)
        if value:
            return str(value)
    operational = payload.get("operational_snapshot") if isinstance(payload.get("operational_snapshot"), dict) else {}
    for key in ("response_generated_at", "last_successful_snapshot_at", "snapshot_created_at"):
        value = operational.get(key)
        if value:
            return str(value)
    return last_cached_timestamp or "degraded — no fresh timestamp"


def _footer(payload: dict[str, Any], *, last_cached_timestamp: str | None = None) -> str:
    source_confidence = str(payload.get("source_confidence") or "unknown")
    ts = _operational_timestamp(payload, last_cached_timestamp=last_cached_timestamp)
    parts = [f"source_confidence={source_confidence}", f"operational_ts={ts}"]
    degraded = _degraded_connectors(payload)
    if degraded:
        parts.append("⚠ degraded: " + ", ".join(degraded))
    return " | ".join(parts)


def _table(rows: list[list[Any]]) -> str:
    if not rows:
        return "``\n(no rows)\n``"
    widths = [max(len(str(row[idx])) for row in rows) for idx in range(len(rows[0]))]
    rendered = []
    for row in rows:
        rendered.append(" | ".join(str(cell).ljust(widths[idx]) for idx, cell in enumerate(row)))
    return "```\n" + "\n".join(rendered) + "\n```"


def _render_connectors(connectors: list[Any]) -> str:
    rows = [["id", "status", "confidence", "error"]]
    for connector in connectors:
        if not isinstance(connector, dict):
            continue
        last_error = connector.get("last_error") if isinstance(connector.get("last_error"), dict) else {}
        rows.append(
            [
                connector.get("id", "unknown"),
                connector.get("status", "unknown"),
                connector.get("confidence", ""),
                last_error.get("code", "") if last_error else "",
            ]
        )
    return _table(rows)


def _mrkdwn_body(kind: str, payload: dict[str, Any], *, last_cached_timestamp: str | None = None) -> str:
    degraded = _degraded_connectors(payload)
    prefix = "uncertain — " if degraded or payload.get("degraded") else ""
    lines = [f"{prefix}*Talaria {kind}*", ""]
    connectors = payload.get("connectors") if isinstance(payload.get("connectors"), list) else []
    if connectors:
        lines.extend(["connectors", _render_connectors(connectors), ""])
    if payload.get("metrics") is not None:
        lines.extend(["metrics", "```", _json_dumps(payload.get("metrics")), "```", ""])
    if payload.get("panes") is not None:
        lines.extend(["panes", "```", _json_dumps(payload.get("panes")), "```", ""])
    if not connectors and payload.get("metrics") is None and payload.get("panes") is None:
        lines.extend(["```", _json_dumps(payload), "```", ""])
    lines.append(_footer(payload, last_cached_timestamp=last_cached_timestamp))
    return "\n".join(lines)


def _gc_out_dir(path: Path) -> None:
    now = time.time()
    try:
        files = [item for item in path.iterdir() if item.is_file()]
    except OSError:
        return
    for item in files:
        with contextlib.suppress(OSError):
            if now - item.stat().st_mtime > _OUT_TTL_SECONDS:
                item.unlink()
    try:
        files = sorted([item for item in path.iterdir() if item.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return
    total = 0
    for item in files:
        try:
            size = item.stat().st_size
        except OSError:
            continue
        total += size
        if total > _OUT_MAX_BYTES:
            with contextlib.suppress(OSError):
                item.unlink()


def _spill_text(body: str, *, hermes_home: str | os.PathLike[str] | None = None) -> Path:
    directory = _out_dir(hermes_home)
    directory.mkdir(parents=True, exist_ok=True)
    _gc_out_dir(directory)
    fd, tmp_name = tempfile.mkstemp(prefix=".talaria-read.", suffix=".tmp", dir=directory)
    final = directory / f"talaria-read-{int(time.time() * 1000)}-{os.getpid()}.md"
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, final)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    return final


def _truncate_preserving_footer(body: str, *, budget: int) -> str:
    if len(body) <= budget:
        return body
    footer = body.splitlines()[-1] if body.splitlines() else ""
    prefix = "\n".join(body.splitlines()[:-1]) if footer else body
    return _truncate_preserving_suffix(prefix, suffix=footer, budget=budget)


def _truncate_preserving_suffix(body: str, *, suffix: str, budget: int) -> str:
    if len(body) + len(suffix) + 1 <= budget:
        return (body.rstrip() + "\n" + suffix).strip()
    marker = "\n…\n"
    head_budget = max(0, budget - len(suffix) - len(marker))
    if head_budget <= 0:
        return ("…\n" + suffix)[-budget:]
    return body[:head_budget].rstrip() + marker + suffix


def _truncate_with_spill_warning(body: str, *, budget: int) -> str:
    lines = body.splitlines()
    footer = lines[-1] if lines else ""
    prefix = "\n".join(lines[:-1]) if footer else body
    suffix = "full output unavailable" + ("\n" + footer if footer else "")
    return _truncate_preserving_suffix(prefix, suffix=suffix, budget=budget)


def render_payload(
    kind: str,
    payload: dict[str, Any],
    *,
    mrkdwn: bool = False,
    render_budget: int = RENDER_BUDGET,
    hermes_home: str | os.PathLike[str] | None = None,
    last_cached_timestamp: str | None = None,
) -> dict[str, Any]:
    body = _mrkdwn_body(kind, payload, last_cached_timestamp=last_cached_timestamp) if mrkdwn else _json_dumps(payload)
    if len(body) <= render_budget:
        return {"spilled": False, "format": "mrkdwn" if mrkdwn else "json", "body": body}
    preview = _truncate_preserving_footer(body, budget=render_budget)
    try:
        path = _spill_text(body, hermes_home=hermes_home)
    except Exception:
        fallback = _truncate_with_spill_warning(body, budget=render_budget)
        return {"spilled": False, "format": "mrkdwn" if mrkdwn else "json", "body": fallback, "warning": "full output unavailable"}
    return {"spilled": True, "format": "mrkdwn" if mrkdwn else "json", "path": str(path), "preview": preview}


def _footer_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in ("response_generated_at", "last_successful_snapshot_at", "snapshot_created_at")
        if key in payload
    }


def _select_connector(payload: dict[str, Any], connector_id: str) -> dict[str, Any]:
    connectors = payload.get("connectors") if isinstance(payload.get("connectors"), list) else []
    for connector in connectors:
        if isinstance(connector, dict) and str(connector.get("id")) == connector_id:
            return {
                "ok": True,
                "connector": connector,
                "source_confidence": payload.get("source_confidence"),
                "connectors": [connector],
                **_footer_fields(payload),
            }
    return {"ok": False, "error": "cannot_evaluate", "detail": f"connector {connector_id!r} not found"}


def _select_pane(payload: dict[str, Any], pane_id: str) -> dict[str, Any]:
    panes = payload.get("panes") if isinstance(payload.get("panes"), dict) else {}
    if pane_id in panes:
        return {
            "ok": True,
            "pane_id": pane_id,
            "pane": panes[pane_id],
            "source_confidence": payload.get("source_confidence"),
            **_footer_fields(payload),
        }
    return {"ok": False, "error": "cannot_evaluate", "detail": f"pane {pane_id!r} not found"}


def _print_result(kind: str, result: dict[str, Any], *, mrkdwn: bool, hermes_home: str | os.PathLike[str] | None) -> int:
    rendered = render_payload(kind, result, mrkdwn=mrkdwn, hermes_home=hermes_home)
    if rendered.get("spilled"):
        print(json.dumps(rendered, sort_keys=True, ensure_ascii=False))
    else:
        print(rendered.get("body", ""))
    return 0 if result.get("ok", True) else 1


def _json_arg(value: str | None) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("payload must be a JSON object")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Talaria LOOK/DO CLI")
    parser.add_argument("--home", help="Talaria checkout root override")
    parser.add_argument("--hermes-home", help="Hermes home override for skill cache/out dirs")
    parser.add_argument("--mrkdwn", action="store_true", help="render compact Slack mrkdwn instead of JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    operational = sub.add_parser("operational")
    operational.add_argument("--refresh", action="store_true")
    sub.add_parser("snapshot")
    sub.add_parser("observations")
    connector = sub.add_parser("connector")
    connector.add_argument("connector_id")
    pane = sub.add_parser("pane")
    pane.add_argument("pane_id")
    sub.add_parser("health")
    sub.add_parser("doctor")
    act = sub.add_parser("act")
    act.add_argument("kind", choices=["ack", "triage"])
    act.add_argument("--payload", default="{}")

    args = parser.parse_args(argv)
    bridge = _load_bridge()
    try:
        if args.command == "operational":
            result = bridge.read_operational(home=args.home, refresh=args.refresh, hermes_home=args.hermes_home)
        elif args.command == "snapshot":
            result = bridge.read_snapshot(home=args.home)
        elif args.command == "observations":
            result = bridge.read_observations(home=args.home)
        elif args.command == "health":
            result = bridge.read_health(home=args.home)
        elif args.command == "doctor":
            result = bridge.doctor(home=args.home, hermes_home=args.hermes_home)
        elif args.command == "connector":
            operational_result = bridge.read_operational(home=args.home, hermes_home=args.hermes_home)
            result = _select_connector(operational_result, args.connector_id) if operational_result.get("ok") else operational_result
        elif args.command == "pane":
            operational_result = bridge.read_operational(home=args.home, hermes_home=args.hermes_home)
            result = _select_pane(operational_result, args.pane_id) if operational_result.get("ok") else operational_result
        elif args.command == "act":
            kind = "ack_observation" if args.kind == "ack" else "kanban_triage"
            payload = _json_arg(args.payload)
            idempotency_key = f"ack:{payload.get('observation_id')}" if kind == "ack_observation" and payload.get("observation_id") else None
            result = bridge.act(kind, payload, idempotency_key=idempotency_key, home=args.home)
        else:  # pragma: no cover - argparse owns this.
            result = {"ok": False, "error": "unknown_action_kind"}
    except Exception as exc:  # noqa: BLE001 - CLI contract: never traceback.
        result = {"ok": False, "error": "state_import_failed", "detail": str(exc)}
    return _print_result(args.command, result, mrkdwn=args.mrkdwn, hermes_home=args.hermes_home)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
