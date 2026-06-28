#!/usr/bin/env python3
"""Talaria per-watch heartbeat evaluator for the Hermes talaria skill."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

_COMPARATORS = frozenset({"gt", "gte", "lt", "lte", "eq", "ne", "present", "absent"})
_NUMERIC_COMPARATORS = frozenset({"gt", "gte", "lt", "lte", "eq", "ne"})
_ORPHAN_ALERT_AFTER = 3
_STALLED_INTERVALS = 3
_SELECTOR_CONNECTOR_RE = re.compile(r"^connectors\[([^\]]+)\]\.(.+)$")
_INTERVAL_RE = re.compile(r"^(?:every\s+)?([0-9]+(?:\.[0-9]+)?)([smhd])$", re.IGNORECASE)
_DEGRADED_REASONS = frozenset({"owner_degraded", "owner_error", "owner_absent"})
_CRON_FIELD_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


def _load_bridge() -> Any:
    path = Path(__file__).with_name("talaria_bridge.py")
    module_name = "talaria_bridge_watch_runtime"
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


def _watch_dir(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _skill_dir(hermes_home) / "watches"


def _wrapper_dir(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _skill_dir(hermes_home) / "wrappers"


def _config_path(watch_id: str, hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _watch_dir(hermes_home) / f"{watch_id}.json"


def _state_path(watch_id: str, hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _watch_dir(hermes_home) / f"{watch_id}.state.json"


def _orphan_path(watch_id: str, hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _watch_dir(hermes_home) / f"{watch_id}.orphan"


def _lock_path(watch_id: str, hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _watch_dir(hermes_home) / f"{watch_id}.lock"


def _wrapper_path(watch_id: str, hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _wrapper_dir(hermes_home) / f"talaria_watch_{watch_id}.py"


def _json_safe_load(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _fsync_dir(path: Path) -> None:
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, sort_keys=True, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
        _fsync_dir(path.parent)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
        _fsync_dir(path.parent)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _canonical_threshold(comparator: str, threshold: Any) -> Any:
    if comparator in _NUMERIC_COMPARATORS:
        return float(threshold)
    if threshold in (None, ""):
        return None
    return str(threshold)


def compute_watch_id(selector: str, comparator: str, threshold: Any) -> str:
    comparator = str(comparator or "").strip().lower()
    canonical = {
        "selector": str(selector or "").strip(),
        "comparator": comparator,
        "threshold": _canonical_threshold(comparator, threshold),
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def build_watch_config(selector: str, comparator: str, threshold: Any, schedule: str, label: str, channel: str | None = None) -> dict[str, Any]:
    comparator = str(comparator or "").strip().lower()
    canonical_threshold = _canonical_threshold(comparator, threshold)
    watch_id = compute_watch_id(selector, comparator, canonical_threshold)
    config = {
        "watch_id": watch_id,
        "selector": str(selector or "").strip(),
        "comparator": comparator,
        "threshold": canonical_threshold,
        "schedule": str(schedule or "").strip(),
        "label": str(label or "").strip() or str(selector or "").strip(),
    }
    if channel:
        config["channel"] = str(channel).strip()
    return config


def write_watch_config(config: dict[str, Any], *, hermes_home: str | os.PathLike[str] | None = None) -> None:
    _atomic_write_json(_config_path(str(config["watch_id"]), hermes_home), config)


def read_watch_config(watch_id: str, *, hermes_home: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    payload = _json_safe_load(_config_path(watch_id, hermes_home))
    return payload if _validate_config_shape(payload).get("ok") else None


def write_watch_state(watch_id: str, state: dict[str, Any], *, hermes_home: str | os.PathLike[str] | None = None) -> None:
    _atomic_write_json(_state_path(watch_id, hermes_home), state)


def read_watch_state(watch_id: str, *, hermes_home: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    return _json_safe_load(_state_path(watch_id, hermes_home))


class WatchLock:
    def __init__(self, path: Path, fh: Any) -> None:
        self.path = path
        self.fh = fh
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if os.name == "nt":
                import msvcrt  # type: ignore[import-not-found]

                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        finally:
            self.fh.close()

    def __enter__(self) -> "WatchLock":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()


def acquire_watch_lock(watch_id: str, *, hermes_home: str | os.PathLike[str] | None = None) -> WatchLock | None:
    path = _lock_path(watch_id, hermes_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt  # type: ignore[import-not-found]

            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        fh.close()
        return None
    return WatchLock(path, fh)


def _validate_config_shape(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {"ok": False, "error": "config_missing"}
    for key in ("watch_id", "selector", "comparator", "schedule", "label"):
        if not str(config.get(key) or "").strip():
            return {"ok": False, "error": "config_invalid", "detail": key}
    comparator = str(config.get("comparator") or "").lower()
    if comparator not in _COMPARATORS:
        return {"ok": False, "error": "invalid_comparator"}
    if comparator in _NUMERIC_COMPARATORS:
        try:
            value = float(config.get("threshold"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_threshold"}
        if not math.isfinite(value):
            return {"ok": False, "error": "invalid_threshold"}
    return {"ok": True}


def _schedule_seconds(schedule: str) -> float | None:
    normalized = " ".join(str(schedule or "").strip().split())
    match = _INTERVAL_RE.match(normalized.replace(" ", ""))
    if not match:
        match = _INTERVAL_RE.match(normalized)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2).lower()]
    return number * multiplier


def _expand_cron_field(field: str, minimum: int, maximum: int) -> set[int] | None:
    values: set[int] = set()
    for part in field.split(","):
        if not part:
            return None
        step = 1
        base = part
        if "/" in part:
            base, step_text = part.split("/", 1)
            if not step_text.isdigit():
                return None
            step = int(step_text)
            if step <= 0:
                return None
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            if not start_text.isdigit() or not end_text.isdigit():
                return None
            start, end = int(start_text), int(end_text)
        elif base.isdigit():
            start = end = int(base)
        else:
            return None
        if start < minimum or end > maximum or start > end:
            return None
        values.update(range(start, end + 1, step))
    return values


def _cron_schedule_seconds(schedule: str) -> float | None:
    fields = str(schedule or "").strip().split()
    if len(fields) != 5:
        return None
    expanded = [_expand_cron_field(field, *limits) for field, limits in zip(fields, _CRON_FIELD_RANGES)]
    if any(values is None for values in expanded):
        return None
    minutes, hours, days, months, weekdays = expanded
    if minutes is None or hours is None or days is None or months is None or weekdays is None:
        return None
    if 7 in weekdays:
        weekdays = {0 if day == 7 else day for day in weekdays}
    day_restricted = fields[2] != "*"
    weekday_restricted = fields[4] != "*"

    import datetime as _dt

    start = _dt.datetime(2026, 1, 1, 0, 0)
    previous: _dt.datetime | None = None
    smallest: float | None = None
    for offset in range(0, 400 * 24 * 60):
        current = start + _dt.timedelta(minutes=offset)
        if current.month not in months or current.hour not in hours or current.minute not in minutes:
            continue
        day_match = current.day in days
        weekday_match = (current.weekday() + 1) % 7 in weekdays
        if day_restricted and weekday_restricted:
            if not (day_match or weekday_match):
                continue
        elif not day_match or not weekday_match:
            continue
        if previous is not None:
            delta = (current - previous).total_seconds()
            smallest = delta if smallest is None else min(smallest, delta)
            if smallest <= 60:
                break
        previous = current
    return smallest


def _schedule_frequency_seconds(schedule: str) -> float | None:
    return _schedule_seconds(schedule) or _cron_schedule_seconds(schedule)


def _owner_for_selector(selector: str) -> tuple[str | None, str | None]:
    match = _SELECTOR_CONNECTOR_RE.match(selector)
    if match:
        owner = match.group(1)
        if owner in {"website-analytics", "relaticle"}:
            return owner, "derived_metric_connector"
        return owner, None
    if selector.startswith("metrics."):
        return "serenade-postgres", None
    return None, "unsupported_selector"


def _connector_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    connectors = snapshot.get("connectors") if isinstance(snapshot.get("connectors"), list) else []
    return {str(item.get("id")): item for item in connectors if isinstance(item, dict) and item.get("id")}


def _registration_snapshot(home: str | os.PathLike[str] | None, hermes_home: str | os.PathLike[str] | None) -> dict[str, Any]:
    bridge = _load_bridge()
    payload = bridge.read_operational(home=home, hermes_home=hermes_home)
    if not payload.get("ok"):
        return payload
    operational = payload.get("operational_snapshot") if isinstance(payload.get("operational_snapshot"), dict) else payload
    return operational if isinstance(operational, dict) else payload


def _validate_registration(config: dict[str, Any], *, home: str | os.PathLike[str] | None, hermes_home: str | os.PathLike[str] | None) -> dict[str, Any]:
    shape = _validate_config_shape(config)
    if not shape.get("ok"):
        return shape
    selector = str(config["selector"])
    owner, owner_error = _owner_for_selector(selector)
    if owner_error:
        return {"ok": False, "error": owner_error, "owner": owner}
    snapshot = _registration_snapshot(home, hermes_home)
    if not snapshot.get("ok", True) and snapshot.get("error"):
        return {"ok": False, "error": "cannot_evaluate", "detail": snapshot.get("error")}
    connectors = _connector_index(snapshot)
    if owner not in connectors:
        return {"ok": False, "error": "selector_unresolved", "owner": owner}
    try:
        floor = float(connectors[owner].get("freshness_floor_seconds") or connectors[owner].get("freshness_floor") or 0)
    except (TypeError, ValueError):
        floor = 0
    schedule_seconds = _schedule_frequency_seconds(str(config["schedule"]))
    if schedule_seconds is None:
        return {"ok": False, "error": "schedule_frequency_unknown", "owner": owner, "freshness_floor_seconds": floor}
    if schedule_seconds < floor:
        return {"ok": False, "error": "schedule_too_frequent", "owner": owner, "freshness_floor_seconds": floor}
    return {"ok": True, "owner": owner}


def _wrapper_content(watch_id: str) -> str:
    script = Path(__file__).resolve()
    return (
        "#!/usr/bin/env python3\n"
        "from __future__ import annotations\n"
        "import runpy\n"
        "from pathlib import Path\n"
        f"WATCH_ID = {watch_id!r}\n"
        f"SCRIPT = Path({str(script)!r})\n"
        "runpy.run_path(str(SCRIPT), init_globals={'TALARIA_WRAPPER_WATCH_ID': WATCH_ID}, run_name='__main__')\n"
    )


def _deliver_target(channel: str | None) -> str:
    selected = (channel or os.environ.get("SLACK_HOME_CHANNEL") or "").strip()
    return f"slack:{selected}" if selected else "slack"


def _create_cron(config: dict[str, Any], wrapper: Path, *, channel: str | None = None) -> dict[str, Any]:
    argv = [
        "hermes",
        "cron",
        "create",
        str(config["schedule"]),
        "--no-agent",
        "--script",
        str(wrapper),
        "--deliver",
        _deliver_target(channel or config.get("channel")),
        "--name",
        f"talaria-watch-{config['watch_id']}",
    ]
    result = subprocess.run(argv, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return {"ok": False, "error": "cron_create_failed", "detail": result.stderr or result.stdout}
    return {"ok": True, "stdout": result.stdout}


def register_watch(
    *,
    selector: str,
    comparator: str,
    threshold: Any,
    schedule: str,
    label: str,
    channel: str | None = None,
    home: str | os.PathLike[str] | None = None,
    hermes_home: str | os.PathLike[str] | None = None,
    create_cron: bool = True,
) -> dict[str, Any]:
    try:
        config = build_watch_config(selector, comparator, threshold, schedule, label, channel)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_threshold"}
    valid = _validate_registration(config, home=home, hermes_home=hermes_home)
    if not valid.get("ok"):
        return valid
    write_watch_config(config, hermes_home=hermes_home)
    wrapper = _wrapper_path(str(config["watch_id"]), hermes_home)
    _atomic_write_text(wrapper, _wrapper_content(str(config["watch_id"])))
    if os.name != "nt":
        with contextlib.suppress(OSError):
            wrapper.chmod(0o755)
    cron = {"ok": True}
    if create_cron:
        cron = _create_cron(config, wrapper, channel=channel)
        if not cron.get("ok"):
            with contextlib.suppress(OSError):
                wrapper.unlink()
            with contextlib.suppress(OSError):
                _config_path(str(config["watch_id"]), hermes_home).unlink()
            return cron
    return {"ok": True, "watch_id": config["watch_id"], "config": str(_config_path(str(config["watch_id"]), hermes_home)), "wrapper": str(wrapper), "cron": cron}


def _cron_ids_for_watch(watch_id: str) -> list[str]:
    result = subprocess.run(["hermes", "cron", "list", "--json"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    jobs = payload if isinstance(payload, list) else payload.get("jobs", []) if isinstance(payload, dict) else []
    ids: list[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("name") == f"talaria-watch-{watch_id}" and job.get("job_id"):
            ids.append(str(job["job_id"]))
        elif job.get("name") == f"talaria-watch-{watch_id}" and job.get("id"):
            ids.append(str(job["id"]))
    return ids


def remove_watch(watch_id: str, *, hermes_home: str | os.PathLike[str] | None = None, remove_cron: bool = True) -> dict[str, Any]:
    if remove_cron:
        for job_id in _cron_ids_for_watch(watch_id):
            subprocess.run(["hermes", "cron", "remove", job_id], check=False, capture_output=True, text=True)
    removed: list[str] = []
    for path in (_wrapper_path(watch_id, hermes_home), _config_path(watch_id, hermes_home), _state_path(watch_id, hermes_home), _orphan_path(watch_id, hermes_home), _lock_path(watch_id, hermes_home)):
        with contextlib.suppress(OSError):
            path.unlink()
            removed.append(str(path))
    return {"ok": True, "watch_id": watch_id, "removed": removed}


def _handle_missing_config(watch_id: str, *, hermes_home: str | os.PathLike[str] | None = None) -> str:
    sentinel = _orphan_path(watch_id, hermes_home)
    if _config_path(watch_id, hermes_home).exists():
        return ""
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_safe_load(sentinel) or {}
    count = int(payload.get("count") or 0) + 1
    if count == 1:
        line = f"⚠ watch {watch_id}: config_missing"
    else:
        line = ""
    if count >= _ORPHAN_ALERT_AFTER:
        remove_watch(watch_id, hermes_home=hermes_home)
        return line
    if _config_path(watch_id, hermes_home).exists():
        return ""
    try:
        _atomic_write_json(sentinel, {"count": count, "last_seen_at": time.time()})
    except OSError:
        remove_watch(watch_id, hermes_home=hermes_home)
    return line


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _compare(comparator: str, value: Any, threshold: Any) -> bool:
    if comparator == "present":
        return value is not None
    if comparator == "absent":
        return value is None
    left = float(value)
    right = float(threshold)
    if comparator == "gt":
        return left > right
    if comparator == "gte":
        return left >= right
    if comparator == "lt":
        return left < right
    if comparator == "lte":
        return left <= right
    if comparator == "eq":
        return left == right
    if comparator == "ne":
        return left != right
    raise ValueError(f"unknown comparator {comparator!r}")


def _resolve_selector(bridge: Any, payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    selector = str(config["selector"])
    comparator = str(config["comparator"])
    result = bridge.evaluate_operational_selector(payload, selector)
    if result.get("ok"):
        value = result.get("value")
        if comparator in _NUMERIC_COMPARATORS and not _is_numeric(value):
            return {"ok": False, "error": "cannot_evaluate", "owner": result.get("owner"), "reason": "non_numeric"}
        return result
    if comparator == "absent" and result.get("reason") == "selector_unresolved":
        return {"ok": True, "owner": result.get("owner"), "value": None}
    if comparator == "present" and result.get("reason") == "selector_unresolved":
        return {"ok": True, "owner": result.get("owner"), "value": None}
    return result


def _format_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _cannot_evaluate_line(config: dict[str, Any], resolved: dict[str, Any]) -> str:
    reason = resolved.get("reason") or resolved.get("error") or "cannot_evaluate"
    owner = resolved.get("owner") or "unknown"
    return f"⚠ watch {config['watch_id']} ({config['label']}): cannot_evaluate {owner} {reason}"


def _bridge_unavailable_line(config: dict[str, Any]) -> str:
    return f"⚠ watch {config['watch_id']} ({config['label']}): bridge_unavailable"


def _stalled_line(config: dict[str, Any]) -> str:
    return f"⚠ watch {config['watch_id']} ({config['label']}): stalled"


def _transition_line(config: dict[str, Any], value: Any, breached: bool, missed: bool) -> str:
    suffix = " (may have missed transitions while degraded)" if missed and not breached else ""
    if breached:
        return f"🔔 watch {config['watch_id']} ({config['label']}): {_format_value(value)} {config['comparator']} {config['threshold']}"
    return f"✅ watch {config['watch_id']} ({config['label']}): recovered{suffix}"


def _interval_seconds(config: dict[str, Any]) -> float:
    return _schedule_frequency_seconds(str(config.get("schedule") or "")) or 60.0


def _stalled_due(state: dict[str, Any] | None, config: dict[str, Any], now: float) -> bool:
    if not state or state.get("stalled_reported"):
        return False
    try:
        last = float(state.get("last_evaluated_at"))
    except (TypeError, ValueError):
        return False
    return now - last >= _STALLED_INTERVALS * _interval_seconds(config)


def _previous_status(state: dict[str, Any]) -> str:
    status = str(state.get("status") or "").strip()
    if status:
        return status
    if state.get("breached") is True:
        return "breached"
    return "healthy"


def evaluate_watch(watch_id: str, *, home: str | os.PathLike[str] | None = None, hermes_home: str | os.PathLike[str] | None = None) -> str:
    config = read_watch_config(watch_id, hermes_home=hermes_home)
    if config is None:
        return _handle_missing_config(watch_id, hermes_home=hermes_home)
    lock = acquire_watch_lock(watch_id, hermes_home=hermes_home)
    if lock is None:
        return ""
    with lock:
        config = read_watch_config(watch_id, hermes_home=hermes_home)
        if config is None:
            return _handle_missing_config(watch_id, hermes_home=hermes_home)
        state = read_watch_state(watch_id, hermes_home=hermes_home) or {}
        now = time.time()
        stalled = _stalled_due(state, config, now)
        bridge = _load_bridge()
        ready = bridge.ensure_ready(home)
        if not ready.get("ok"):
            line = _bridge_unavailable_line(config) if _previous_status(state) == "healthy" else ""
            state.update({"status": "bridge_unavailable", "last_evaluated_at": now})
            if stalled:
                state["stalled_reported"] = True
                line = line or _stalled_line(config)
            write_watch_state(watch_id, state, hermes_home=hermes_home)
            return line
        payload = bridge.read_operational(home=home, refresh=True, hermes_home=hermes_home)
        if not payload.get("ok"):
            resolved = {"ok": False, "error": "cannot_evaluate", "owner": None, "reason": payload.get("error") or "read_operational_failed"}
        else:
            resolved = _resolve_selector(bridge, payload, config)
        if not resolved.get("ok"):
            line = _cannot_evaluate_line(config, resolved) if _previous_status(state) == "healthy" else ""
            if resolved.get("reason") in _DEGRADED_REASONS:
                state["degraded_window"] = True
            state.update({"status": "cannot_evaluate", "last_evaluated_at": now})
            if stalled:
                state["stalled_reported"] = True
                line = line or _stalled_line(config)
            write_watch_state(watch_id, state, hermes_home=hermes_home)
            return line
        value = resolved.get("value")
        breached = _compare(str(config["comparator"]), value, config.get("threshold"))
        previous = state.get("breached") if isinstance(state.get("breached"), bool) else None
        line = ""
        if stalled:
            line = _stalled_line(config)
            state["stalled_reported"] = True
        elif breached and previous is not True:
            line = _transition_line(config, value, True, False)
        elif not breached and previous is True:
            line = _transition_line(config, value, False, bool(state.get("degraded_window")))
        state.update(
            {
                "status": "breached" if breached else "healthy",
                "breached": breached,
                "last_value": value,
                "last_evaluated_at": now,
            }
        )
        if not breached:
            state["degraded_window"] = False
        write_watch_state(watch_id, state, hermes_home=hermes_home)
        return line


def _safe_evaluate(watch_id: str, *, home: str | os.PathLike[str] | None, hermes_home: str | os.PathLike[str] | None) -> str:
    try:
        return evaluate_watch(watch_id, home=home, hermes_home=hermes_home)
    except Exception as exc:  # noqa: BLE001 - cron stdout must be one line, never traceback.
        return f"⚠ watch {watch_id}: evaluator_error {type(exc).__name__}: {exc}"


def main(argv: list[str] | None = None) -> int:
    wrapper_watch_id = globals().get("TALARIA_WRAPPER_WATCH_ID")
    if argv is None:
        argv = sys.argv[1:]
    if wrapper_watch_id and not argv:
        line = _safe_evaluate(str(wrapper_watch_id), home=None, hermes_home=None)
        if line:
            print(line)
        return 0

    parser = argparse.ArgumentParser(description="Talaria heartbeat watch registration/evaluation")
    parser.add_argument("--home", help="Talaria checkout root override")
    parser.add_argument("--hermes-home", help="Hermes home override for watch state")
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register")
    register.add_argument("selector")
    register.add_argument("comparator", choices=sorted(_COMPARATORS))
    register.add_argument("threshold")
    register.add_argument("schedule")
    register.add_argument("label")
    register.add_argument("--channel")
    eval_parser = sub.add_parser("eval")
    eval_parser.add_argument("watch_id", nargs="?")
    remove = sub.add_parser("remove-watch")
    remove.add_argument("watch_id")
    args = parser.parse_args(argv)

    if args.command == "register":
        result = register_watch(
            selector=args.selector,
            comparator=args.comparator,
            threshold=args.threshold,
            schedule=args.schedule,
            label=args.label,
            channel=args.channel,
            home=args.home,
            hermes_home=args.hermes_home,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("ok") else 1
    if args.command == "eval":
        watch_id = args.watch_id or wrapper_watch_id
        if not watch_id:
            print("⚠ watch unknown: config_missing")
            return 1
        line = _safe_evaluate(str(watch_id), home=args.home, hermes_home=args.hermes_home)
        if line:
            print(line)
        return 0
    if args.command == "remove-watch":
        result = remove_watch(args.watch_id, hermes_home=args.hermes_home)
        print(json.dumps(result, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
