#!/usr/bin/env python3
"""Talaria in-process bridge foundation for the Hermes talaria skill.

This file deliberately avoids HTTP and ``sys.path`` mutation. It locates a
Talaria checkout, verifies it is the Talaria plugin surface (not the older
operator-dashboard predecessor), and imports Talaria's state/connector modules
by file path under synthetic module names.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_CACHE_TTL_SECONDS = 60.0
_LEASE_STALE_SECONDS = 90.0
_DEGRADED_STATUSES = frozenset({"degraded", "blocked", "failed", "disabled", "reconcile_required"})
_DERIVED_METRIC_CONNECTORS = frozenset({"website-analytics", "relaticle"})
_SELECTOR_CONNECTOR_RE = re.compile(r"^connectors\[([^\]]+)\]\.(.+)$")
_RETRY_AFTER_RE = re.compile(r"(?:Retry-After|retry_after_seconds=)\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)

ERROR_HINTS = {
    "talaria_not_found": "Set TALARIA_HOME to the Talaria checkout, or set TALARIA_PLUGIN_ROOTS to candidate checkout roots.",
    "state_import_failed": "Verify Talaria plugins/talaria/state.py imports under the selected HERMES_PYTHON interpreter.",
    "connectors_import_failed": "Verify Talaria connector dependencies import; state-only reads and proposal actions may still work.",
    "state_dir_unavailable": "Verify the Hermes Talaria state directory is writable and not locked by the OS.",
    "state_corrupt": "Repair or move ~/.hermes/talaria/state.json; doctor refuses to report green on unreadable state.",
    "unknown_action_kind": "Allowed Talaria actions are ack_observation and kanban_triage.",
    "observation_gone": "Observation gone — re-read local Talaria observations before approving.",
    "observation_already_resolved": "Observation already resolved — re-read local Talaria observations.",
    "source_identifier_required": "Needs an order/ticket/thread/payment ref before triage; see TAL-004.",
    "observation_refreshed": "Observation changed since you saw it — re-read before approving.",
    "unknown_workspace": "Unknown workspace — choose one of Talaria's configured workspaces.",
    "missing_board": "Configured Kanban board is missing — create/select the board before triage.",
    "workspace_mismatch": "Observation belongs to a different workspace — re-read and use the observation workspace.",
    "state_not_writable": "Local Talaria state not writable — check ~/.hermes/talaria permissions/disk.",
    "not_directly_actionable": "Connector observations are not directly actionable in this cut; use a local operator observation.",
    "invalid_action_payload": "Action payload is missing required fields.",
}

_ACTIONS = {"ack_observation", "kanban_triage"}
_IMPORT_CACHE: dict[tuple[str, str], Any] = {}
_IMPORT_LOCK = threading.RLock()


def _as_path(value: str | os.PathLike[str] | None) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    return Path(value).expanduser().resolve()


def _failure(code: str, *, detail: Any = None, hint: str | None = None, **extra: Any) -> dict[str, Any]:
    payload = {"ok": False, "error": code, "hint": hint or ERROR_HINTS.get(code, "See Talaria skill setup guidance.")}
    if detail is not None:
        payload["detail"] = str(detail)
    payload.update(extra)
    return payload


def _ok(**payload: Any) -> dict[str, Any]:
    payload.setdefault("ok", True)
    return payload


def _plugin_dir(candidate: Path) -> Path | None:
    """Return the talaria plugin dir for either a checkout root or plugin dir."""
    direct = candidate / "plugins" / "talaria"
    if direct.exists():
        return direct
    if candidate.name == "talaria" and (candidate / "state.py").exists() and (candidate / "connectors").exists():
        return candidate
    return None


def _checkout_root(candidate: Path, plugin: Path) -> Path:
    if plugin == candidate:
        # .../<root>/plugins/talaria -> <root>
        return plugin.parents[1]
    return candidate


def _aggregate_exports_snapshot(aggregate_path: Path) -> bool:
    try:
        parsed = ast.parse(aggregate_path.read_text(encoding="utf-8"), filename=str(aggregate_path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    for node in parsed.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "aggregate_workspace_snapshot":
            return True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "aggregate_workspace_snapshot":
                    return True
    return False


def _verified_root(candidate: Path) -> Path | None:
    plugin = _plugin_dir(candidate)
    if plugin is None:
        return None
    state_path = plugin / "state.py"
    aggregate_path = plugin / "connectors" / "aggregate.py"
    if not state_path.exists() or not aggregate_path.exists():
        return None
    if not _aggregate_exports_snapshot(aggregate_path):
        return None
    return _checkout_root(candidate, plugin)


def _split_env_paths(value: str | None) -> list[Path]:
    if not value:
        return []
    return [Path(part).expanduser() for part in value.split(os.pathsep) if part.strip()]


def _probe_candidates() -> list[Path]:
    candidates: list[Path] = []
    candidates.extend(_split_env_paths(os.environ.get("TALARIA_PLUGIN_ROOTS")))
    candidates.extend(_split_env_paths(os.environ.get("HERMES_PLUGIN_ROOTS")))

    cwd = Path.cwd().resolve()
    cwd_lineage = [cwd, *cwd.parents]
    candidates.extend(cwd_lineage)
    for path in cwd_lineage:
        candidates.append(path / "Talaria")
        candidates.append(path / "talaria")

    hermes_home = _as_path(os.environ.get("HERMES_HOME"))
    if hermes_home is not None:
        candidates.append(hermes_home)
        candidates.append(hermes_home / "hermes-agent")

    default_home = _default_hermes_home()
    candidates.append(default_home)
    candidates.append(default_home / "hermes-agent")

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            deduped.append(resolved)
    return deduped


def resolve_home(home: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Resolve and verify a Talaria checkout root.

    ``TALARIA_HOME`` is treated as an explicit operator assertion: if it points
    at the predecessor or any non-Talaria tree, fail loudly instead of silently
    falling through to another checkout.
    """
    explicit = _as_path(home) or _as_path(os.environ.get("TALARIA_HOME"))
    if explicit is not None:
        verified = _verified_root(explicit)
        if verified is None:
            return _failure("talaria_not_found", detail=explicit)
        return _ok(path=str(verified), plugin_path=str(_plugin_dir(verified) or explicit))

    for candidate in _probe_candidates():
        verified = _verified_root(candidate)
        if verified is not None:
            return _ok(path=str(verified), plugin_path=str(_plugin_dir(verified) or candidate))
    return _failure("talaria_not_found")


def _prefix(root: Path) -> str:
    digest = hashlib.sha256(str(root).encode("utf-8", "replace")).hexdigest()[:12]
    return f"talaria_bridge_{os.getpid()}_{digest}"


def _runtime_dependency_roots(root: Path) -> list[Path]:
    """Return nearby Python roots needed by the live Talaria plugin.

    The live state module imports Hermes runtime helpers (for example
    hermes_constants). Kanban workspaces normally sit next to both Talaria and a
    hermes-agent checkout, so probe sibling hermes-agent* directories instead of
    requiring every smoke command to spell out PYTHONPATH.
    """
    candidates: list[Path] = []
    for start in [root, Path.cwd().resolve()]:
        for parent in [start, *start.parents]:
            for child in parent.glob("hermes-agent*"):
                if child.is_dir() and (child / "hermes_constants.py").exists():
                    candidates.append(child)
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate.resolve()))
        if key not in seen:
            seen.add(key)
            deduped.append(candidate.resolve())
    return deduped


@contextlib.contextmanager
def _temporary_sys_path(paths: list[Path]) -> Iterator[None]:
    if not paths:
        yield
        return
    original = list(sys.path)
    try:
        for path in reversed([str(item) for item in paths]):
            if path not in sys.path:
                sys.path.insert(0, path)
        yield
    finally:
        sys.path[:] = original


def _load_module(name: str, path: Path, *, package_dir: Path | None = None, extra_sys_paths: list[Path] | None = None) -> Any:
    with _IMPORT_LOCK:
        cache_key = (name, str(path))
        if cache_key in _IMPORT_CACHE:
            return _IMPORT_CACHE[cache_key]
        kwargs: dict[str, Any] = {}
        if package_dir is not None:
            kwargs["submodule_search_locations"] = [str(package_dir)]
        spec = importlib.util.spec_from_file_location(name, path, **kwargs)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load module {name} from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            with _temporary_sys_path(extra_sys_paths or []):
                spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
        _IMPORT_CACHE[cache_key] = module
        return module


def _load_state(root: Path) -> Any:
    plugin = root / "plugins" / "talaria"
    return _load_module(f"{_prefix(root)}_state", plugin / "state.py", extra_sys_paths=_runtime_dependency_roots(root))


def _load_contracts(root: Path) -> Any:
    plugin = root / "plugins" / "talaria"
    return _load_module(f"{_prefix(root)}_contracts", plugin / "connectors" / "contracts.py", extra_sys_paths=_runtime_dependency_roots(root))


def _load_connectors(root: Path) -> Any:
    plugin = root / "plugins" / "talaria"
    package_dir = plugin / "connectors"
    return _load_module(f"{_prefix(root)}_connectors", package_dir / "__init__.py", package_dir=package_dir, extra_sys_paths=_runtime_dependency_roots(root))


def _err(code: str, exc: BaseException | None = None) -> dict[str, Any]:
    item = {"code": code, "hint": ERROR_HINTS[code]}
    if exc is not None:
        item["detail"] = str(exc)
    return item


def ensure_ready(home: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    resolved = resolve_home(home)
    if not resolved.get("ok"):
        not_found = _err("talaria_not_found")
        not_found["detail"] = str(resolved.get("detail", ""))
        return {
            "ok": False,
            "home": None,
            "state_ok": False,
            "connectors_ok": False,
            "errors": [not_found],
        }

    root = Path(str(resolved["path"]))
    errors: list[dict[str, Any]] = []
    state_ok = False
    connectors_ok = False

    try:
        _load_state(root)
        state_ok = True
    except Exception as exc:  # noqa: BLE001 - surfaced as structured readiness.
        errors.append(_err("state_import_failed", exc))

    try:
        _load_contracts(root)
        _load_connectors(root)
        connectors_ok = True
    except Exception as exc:  # noqa: BLE001 - connector import is allowed to degrade.
        errors.append(_err("connectors_import_failed", exc))

    return {
        "ok": state_ok and connectors_ok,
        "home": str(root),
        "state_ok": state_ok,
        "connectors_ok": connectors_ok,
        "errors": errors,
    }


def _first_error(ready: dict[str, Any], preferred: str | None = None) -> dict[str, Any]:
    errors = ready.get("errors") or []
    if preferred:
        for err in errors:
            if err.get("code") == preferred:
                return err
    return errors[0] if errors else _err("talaria_not_found")


def _state_module_or_error(home: str | os.PathLike[str] | None = None) -> tuple[Any | None, dict[str, Any] | None]:
    ready = ensure_ready(home)
    if not ready.get("state_ok"):
        err = _first_error(ready, "state_import_failed")
        return None, _failure(str(err.get("code") or "state_import_failed"), detail=err.get("detail"))
    assert ready.get("home")
    try:
        return _load_state(Path(str(ready["home"]))), None
    except Exception as exc:  # pragma: no cover - ensure_ready just loaded it; defensive.
        return None, _failure("state_import_failed", detail=exc)


def _classify_state_exception(exc: BaseException) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return "state_corrupt"
    if isinstance(exc, OSError):
        return "state_dir_unavailable"
    return "state_corrupt" if exc.__class__.__name__ == "JSONDecodeError" else "state_import_failed"


def _call_state(method: str, *, home: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    state, error = _state_module_or_error(home)
    if error is not None:
        return error
    try:
        value = getattr(state, method)()
    except Exception as exc:  # noqa: BLE001 - entry points return structured errors.
        code = _classify_state_exception(exc)
        return _failure(code, detail=exc)
    return _ok(**{method: value})


def read_state(home: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    return _call_state("read_state", home=home)


def read_observations(home: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    result = _call_state("list_observations", home=home)
    if result.get("ok"):
        result["observations"] = result.pop("list_observations")
    return result


def read_health(home: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    result = _call_state("health", home=home)
    if result.get("ok"):
        result["health"] = result.pop("health")
    return result


def read_snapshot(home: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    result = _call_state("snapshot", home=home)
    if result.get("ok"):
        result["snapshot"] = result.pop("snapshot")
    return result


def _connector_error_snapshot(state: Any, exc: BaseException) -> dict[str, Any]:
    sanitize = getattr(state, "sanitize_dto", lambda value: value)
    return {
        "schema": "hermes.talaria.snapshot.v1",
        "workspace": "serenade",
        "workspace_meta": {"id": "serenade", "label": "Serenade"},
        "source_confidence": "unknown",
        "connectors": [],
        "metrics": {},
        "panes": {
            "overview": {"metrics": {}, "degraded_connectors": ["connector-aggregation"]},
            "health_sources": {"connectors": []},
        },
        "observations": [],
        "last_error": {"code": "connector_aggregation_failed", "safe_summary": sanitize(str(exc))},
    }


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


def _talaria_skill_dir(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    base = _as_path(hermes_home) or _default_hermes_home()
    return base / "talaria-skill"


def _cache_path(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _talaria_skill_dir(hermes_home) / "snapshot.json"


def _lease_path(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _talaria_skill_dir(hermes_home) / "snapshot.lock"


def _backoff_dir(hermes_home: str | os.PathLike[str] | None = None) -> Path:
    return _talaria_skill_dir(hermes_home) / "backoff"


def _read_cache_entry(hermes_home: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    entry = _json_safe_load(_cache_path(hermes_home))
    if not entry or not isinstance(entry.get("operational_snapshot"), dict):
        return None
    return entry


def _cache_age(entry: dict[str, Any]) -> float | None:
    try:
        return max(0.0, time.time() - float(entry.get("cached_at")))
    except (TypeError, ValueError):
        return None


def _cache_fresh(entry: dict[str, Any], *, ttl: float = _CACHE_TTL_SECONDS) -> bool:
    age = _cache_age(entry)
    return age is not None and age <= ttl


def _fully_degraded(snapshot: dict[str, Any]) -> bool:
    return snapshot.get("source_confidence") == "unknown" and not snapshot.get("connectors")


def _safe_vendor_name(vendor: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(vendor).strip())
    return cleaned.strip(".-_") or "unknown"


def write_vendor_backoff(
    vendor: str,
    *,
    retry_after_seconds: float,
    hermes_home: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    retry_after = max(0.0, min(float(retry_after_seconds), 3600.0))
    payload = {
        "vendor": _safe_vendor_name(vendor),
        "created_at": time.time(),
        "not_before": time.time() + retry_after,
        "retry_after_seconds": retry_after,
    }
    _atomic_write_json(_backoff_dir(hermes_home) / f"{payload['vendor']}.json", payload)
    return payload


def _active_backoffs(hermes_home: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    directory = _backoff_dir(hermes_home)
    try:
        paths = list(directory.glob("*.json"))
    except OSError:
        return []
    now = time.time()
    active: list[dict[str, Any]] = []
    for path in paths:
        payload = _json_safe_load(path)
        if not payload:
            continue
        try:
            not_before = float(payload.get("not_before"))
        except (TypeError, ValueError):
            continue
        if not_before > now:
            active.append(payload)
        else:
            with contextlib.suppress(OSError):
                path.unlink()
    return active


def _retry_after_from_connector(connector: dict[str, Any]) -> float | None:
    last_error = connector.get("last_error") if isinstance(connector.get("last_error"), dict) else {}
    code = str(last_error.get("code") or "")
    summary = str(last_error.get("safe_summary") or "")
    if "rate_limited" not in code and "retry" not in summary.lower():
        return None
    match = _RETRY_AFTER_RE.search(summary)
    if not match:
        return None
    try:
        return max(0.0, min(float(match.group(1)), 3600.0))
    except ValueError:
        return None


def _persist_backoffs_from_snapshot(snapshot: dict[str, Any], *, hermes_home: str | os.PathLike[str] | None = None) -> None:
    connectors = snapshot.get("connectors") if isinstance(snapshot.get("connectors"), list) else []
    for connector in connectors:
        if not isinstance(connector, dict):
            continue
        retry_after = _retry_after_from_connector(connector)
        if retry_after is not None:
            write_vendor_backoff(str(connector.get("id") or "unknown"), retry_after_seconds=retry_after, hermes_home=hermes_home)


def _write_lease(path: Path, *, acquired_at: float) -> None:
    payload = {"pid": os.getpid(), "acquired_at": acquired_at, "updated_at": time.time()}
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _lease_heartbeat_interval() -> float:
    return max(0.01, min(5.0, _LEASE_STALE_SECONDS / 4.0))


def _start_lease_heartbeat(path: Path, *, acquired_at: float) -> tuple[threading.Event, threading.Thread]:
    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(_lease_heartbeat_interval()):
            with contextlib.suppress(OSError):
                _write_lease(path, acquired_at=acquired_at)

    thread = threading.Thread(target=heartbeat, name="talaria-snapshot-lease-heartbeat", daemon=True)
    thread.start()
    return stop, thread


def _lease_stale(path: Path) -> bool:
    payload = _json_safe_load(path)
    if payload:
        try:
            stamp = float(payload.get("updated_at") or payload.get("acquired_at"))
        except (TypeError, ValueError):
            stamp = 0.0
    else:
        try:
            stamp = path.stat().st_mtime
        except OSError:
            return True
    return time.time() - stamp >= _LEASE_STALE_SECONDS


def _try_acquire_lease(hermes_home: str | os.PathLike[str] | None = None) -> tuple[bool, float | None]:
    path = _lease_path(hermes_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        acquired_at = time.time()
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _lease_stale(path):
                with contextlib.suppress(OSError):
                    path.unlink()
                continue
            return False, None
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "acquired_at": acquired_at, "updated_at": acquired_at}, fh, sort_keys=True)
        return True, acquired_at
    return False, None


def _release_lease(hermes_home: str | os.PathLike[str] | None = None) -> None:
    with contextlib.suppress(OSError):
        _lease_path(hermes_home).unlink()


def _aggregate_snapshot(root: Path, state: Any, ready: dict[str, Any], *, refresh: bool) -> tuple[dict[str, Any], bool]:
    if not ready.get("connectors_ok"):
        err = _first_error(ready, "connectors_import_failed")
        return _connector_error_snapshot(state, RuntimeError(str(err.get("detail") or "connectors import failed"))), True
    try:
        connectors = _load_connectors(root)
        return connectors.aggregate_workspace_snapshot(refresh=refresh), False
    except Exception as exc:  # noqa: BLE001 - degraded snapshot mirrors plugin_api.
        return _connector_error_snapshot(state, exc), True


def _cached_operational_snapshot(
    root: Path,
    state: Any,
    ready: dict[str, Any],
    *,
    refresh: bool,
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    active_backoffs = _active_backoffs(hermes_home)
    cache = _read_cache_entry(hermes_home)
    if active_backoffs:
        if cache is not None:
            return dict(cache["operational_snapshot"]), {"cache_status": "backoff", "backoff": active_backoffs}
        return None, {"cache_status": "cannot_evaluate", "reason": "vendor_backoff", "backoff": active_backoffs}

    if cache is not None and _cache_fresh(cache) and not refresh:
        return dict(cache["operational_snapshot"]), {"cache_status": "hit", "cache_age_seconds": _cache_age(cache)}

    acquired, acquired_at = _try_acquire_lease(hermes_home)
    if not acquired:
        loser_cache = _read_cache_entry(hermes_home)
        if loser_cache is not None:
            return dict(loser_cache["operational_snapshot"]), {"cache_status": "served_by_loser", "cache_age_seconds": _cache_age(loser_cache)}
        return None, {"cache_status": "cannot_evaluate", "reason": "refresh_in_progress_no_cache"}

    try:
        cache = _read_cache_entry(hermes_home)
        if cache is not None and _cache_fresh(cache) and not refresh:
            return dict(cache["operational_snapshot"]), {"cache_status": "hit_after_lease", "cache_age_seconds": _cache_age(cache)}
        heartbeat: tuple[threading.Event, threading.Thread] | None = None
        if acquired_at is not None:
            lease_path = _lease_path(hermes_home)
            _write_lease(lease_path, acquired_at=acquired_at)
            heartbeat = _start_lease_heartbeat(lease_path, acquired_at=acquired_at)
        try:
            snapshot, degraded = _aggregate_snapshot(root, state, ready, refresh=refresh)
        finally:
            if heartbeat is not None:
                stop, thread = heartbeat
                stop.set()
                thread.join(timeout=1.0)
        _persist_backoffs_from_snapshot(snapshot, hermes_home=hermes_home)
        existing = _read_cache_entry(hermes_home)
        if degraded and _fully_degraded(snapshot) and existing is not None and _cache_fresh(existing) and not _fully_degraded(existing["operational_snapshot"]):
            return dict(existing["operational_snapshot"]), {"cache_status": "preserved_fresh_good", "degraded_refresh": True}
        entry = {"cached_at": time.time(), "operational_snapshot": snapshot, "degraded": degraded}
        _atomic_write_json(_cache_path(hermes_home), entry)
        return snapshot, {"cache_status": "refreshed", "degraded_refresh": degraded}
    finally:
        _release_lease(hermes_home)


def _merge_operational_payload(state_snapshot: Any, operational: dict[str, Any], cache_meta: dict[str, Any]) -> dict[str, Any]:
    payload = dict(state_snapshot) if isinstance(state_snapshot, dict) else {}
    payload["operational_snapshot"] = operational
    payload["workspace_meta"] = operational.get("workspace_meta", {})
    payload["source_confidence"] = operational.get("source_confidence", "unknown")
    payload["metrics"] = operational.get("metrics", {})
    payload["panes"] = operational.get("panes", {})
    payload["connector_observations"] = operational.get("observations", [])
    payload["connectors"] = operational.get("connectors", [])
    for key in ("response_generated_at", "snapshot_created_at", "last_successful_snapshot_at"):
        if key in operational:
            payload[key] = operational.get(key)
    if operational.get("last_error"):
        payload["last_error"] = operational["last_error"]
    if _fully_degraded(operational) or cache_meta.get("degraded_refresh"):
        payload["degraded"] = True
    payload["cache"] = cache_meta
    return _ok(**payload)


def read_operational(
    home: str | os.PathLike[str] | None = None,
    *,
    refresh: bool = False,
    hermes_home: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    ready = ensure_ready(home)
    if not ready.get("state_ok"):
        err = _first_error(ready, "state_import_failed")
        return _failure(str(err.get("code") or "state_import_failed"), detail=err.get("detail"))
    root = Path(str(ready["home"]))
    state = _load_state(root)
    try:
        state_snapshot = state.snapshot()
    except Exception as exc:  # noqa: BLE001 - entry points return structured errors.
        code = _classify_state_exception(exc)
        return _failure(code, detail=exc)
    operational, cache_meta = _cached_operational_snapshot(root, state, ready, refresh=refresh, hermes_home=hermes_home)
    if operational is None:
        return _failure("cannot_evaluate", detail=cache_meta.get("reason"), cache=cache_meta, hint="Operational snapshot refresh is already in progress and no readable cache exists.")
    return _merge_operational_payload(state_snapshot, operational, cache_meta)


def _connector_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    connectors = snapshot.get("connectors") if isinstance(snapshot.get("connectors"), list) else []
    return {str(item.get("id")): item for item in connectors if isinstance(item, dict) and item.get("id")}


def _nested_get(value: Any, path: str) -> tuple[bool, Any]:
    current = value
    for part in [item for item in path.split(".") if item]:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _owner_degraded(connectors: dict[str, dict[str, Any]], owner: str) -> str | None:
    connector = connectors.get(owner)
    if connector is None:
        return "owner_absent"
    if str(connector.get("status") or "").lower() in _DEGRADED_STATUSES:
        return "owner_degraded"
    if connector.get("last_error"):
        return "owner_error"
    return None


def evaluate_operational_selector(payload: dict[str, Any], selector: str) -> dict[str, Any]:
    snapshot = payload.get("operational_snapshot") if isinstance(payload.get("operational_snapshot"), dict) else payload
    connectors = _connector_index(snapshot)
    connector_match = _SELECTOR_CONNECTOR_RE.match(selector)
    if connector_match:
        owner, path = connector_match.group(1), connector_match.group(2)
        if owner in _DERIVED_METRIC_CONNECTORS:
            return {"ok": False, "error": "cannot_evaluate", "owner": owner, "reason": "derived_metric_connector"}
        reason = _owner_degraded(connectors, owner)
        if reason:
            return {"ok": False, "error": "cannot_evaluate", "owner": owner, "reason": reason}
        found, value = _nested_get(connectors[owner], path)
        if not found or value is None:
            return {"ok": False, "error": "cannot_evaluate", "owner": owner, "reason": "selector_unresolved"}
        return {"ok": True, "owner": owner, "value": value}

    if selector.startswith("metrics."):
        owner = "serenade-postgres"
        reason = _owner_degraded(connectors, owner)
        if reason:
            return {"ok": False, "error": "cannot_evaluate", "owner": owner, "reason": reason}
        found, value = _nested_get(snapshot.get("metrics") or {}, selector.removeprefix("metrics."))
        if not found or value is None:
            return {"ok": False, "error": "cannot_evaluate", "owner": owner, "reason": "selector_unresolved"}
        return {"ok": True, "owner": owner, "value": value}

    return {"ok": False, "error": "cannot_evaluate", "owner": None, "reason": "unsupported_selector"}


def _action_state_or_error(kind: str, home: str | os.PathLike[str] | None = None) -> tuple[Any | None, dict[str, Any] | None]:
    state, error = _state_module_or_error(home)
    if error is not None:
        return None, error
    action_kind = str(kind or "").strip()
    try:
        allowed = set(getattr(state, "allowed_action_kinds")())
    except Exception as exc:  # noqa: BLE001 - state-side gate must fail closed.
        return None, _failure("state_import_failed", detail=exc)
    if action_kind not in allowed or action_kind not in _ACTIONS:
        return None, _failure("unknown_action_kind", detail=action_kind)
    return state, None


def _action_error(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, (PermissionError, OSError)):
        return _failure("state_not_writable", detail=exc)

    reason = getattr(exc, "reason", None)
    if reason:
        detail = exc.to_detail() if hasattr(exc, "to_detail") else exc
        mapping = {
            "observation_missing": "observation_gone",
            "observation_not_open": "observation_already_resolved",
            "source_identifier_required": "source_identifier_required",
            "observation_refreshed": "observation_refreshed",
            "preview_revision_mismatch": "observation_refreshed",
        }
        return _failure(mapping.get(str(reason), "observation_refreshed"), detail=detail, reason=str(reason))

    if isinstance(exc, ValueError):
        detail = str(exc)
        lowered = detail.lower()
        if "unknown observation" in lowered or "observation_missing" in lowered:
            return _failure("observation_gone", detail=detail)
        if "unknown workspace" in lowered:
            return _failure("unknown_workspace", detail=detail)
        if "configured board" in lowered and "does not exist" in lowered:
            return _failure("missing_board", detail=detail)
        if "does not belong to workspace" in lowered:
            return _failure("workspace_mismatch", detail=detail)
        return _failure("invalid_action_payload", detail=detail)

    code = _classify_state_exception(exc)
    return _failure(code, detail=exc)


def _action_message(action: dict[str, Any]) -> str:
    if action.get("idempotent_replay") or action.get("duplicate"):
        return "already applied (no-op)"
    if action.get("kind") == "ack_observation":
        return "acknowledged"
    if action.get("kind") == "kanban_triage":
        return "triage card created"
    return "applied"


def act_ack(
    observation_id: str,
    *,
    actor: str = "operator",
    idempotency_key: str | None = None,
    home: str | os.PathLike[str] | None = None,
    state: Any | None = None,
) -> dict[str, Any]:
    if state is None:
        state, error = _action_state_or_error("ack_observation", home)
        if error is not None:
            raise ValueError(str(error.get("error")))
    observation_id = str(observation_id or "").strip()
    payload = {"observation_id": observation_id, "actor": actor or "operator"}
    return state.acknowledge_observation(payload, idempotency_key=idempotency_key or f"ack:{observation_id}")


def act_triage(
    workspace: str,
    observation_id: str,
    *,
    home: str | os.PathLike[str] | None = None,
    state: Any | None = None,
) -> dict[str, Any]:
    if state is None:
        state, error = _action_state_or_error("kanban_triage", home)
        if error is not None:
            raise ValueError(str(error.get("error")))
    return state.create_kanban_card_from_observation(
        workspace=str(workspace or "serenade"),
        observation_id=str(observation_id or ""),
        preview_revision=None,
    )


def act(
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    idempotency_key: str | None = None,
    home: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    action_kind = str(kind or "").strip()
    state, error = _action_state_or_error(action_kind, home)
    if error is not None:
        return error
    payload = payload or {}
    try:
        if action_kind == "ack_observation":
            observation_id = str(payload.get("observation_id") or "").strip()
            action = act_ack(
                observation_id,
                actor=str(payload.get("actor") or "operator"),
                idempotency_key=idempotency_key,
                state=state,
            )
        elif action_kind == "kanban_triage":
            action = act_triage(
                str(payload.get("workspace") or "serenade"),
                str(payload.get("observation_id") or ""),
                state=state,
            )
        else:  # pragma: no cover - guarded above.
            return _failure("unknown_action_kind", detail=action_kind)
    except Exception as exc:  # noqa: BLE001 - no tracebacks from bridge entry points.
        return _action_error(exc)
    return _ok(action=action, message=_action_message(action))


def _find_observation(items: Any, observation_id: str) -> dict[str, Any] | None:
    if isinstance(items, dict):
        items = items.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "") == observation_id:
            return item
    return None


def propose_action(
    kind: str,
    observation_id: str,
    *,
    workspace: str = "serenade",
    board: str | None = None,
    actor: str = "operator",
    home: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    action_kind = str(kind or "").strip()
    state, error = _action_state_or_error(action_kind, home)
    if error is not None:
        return error
    observation_id = str(observation_id or "").strip()
    try:
        observations = state.list_observations()
    except Exception as exc:  # noqa: BLE001 - proposal must not traceback.
        return _action_error(exc)
    observation = _find_observation(observations, observation_id)
    if observation is None:
        return _failure("not_directly_actionable", detail=observation_id)

    lines = [
        f"*Observation:* {observation.get('id') or observation_id}",
        f"*Source:* {observation.get('source') or 'local'}",
        f"*Severity:* {observation.get('severity') or 'info'}",
        f"*Title:* {observation.get('title') or 'Observation'}",
        f"*Summary:* {observation.get('summary') or ''}",
        "",
    ]
    if action_kind == "ack_observation":
        lines.extend(
            [
                "*Action:* ack_observation",
                f"*Actor:* {actor or 'operator'}",
            ]
        )
    else:
        target_board = board or workspace
        lines.extend(
            [
                "*Action:* kanban_triage",
                f"*Workspace:* {workspace}",
                f"*Board:* {target_board}",
                "Talaria dedups triage on its canonical key (workspace/board/source_connector/source_ref/kind); recurrences collapse onto one card.",
                "Editable fields: workspace. Board is preview-only in this cut; the approved action uses Talaria's workspace board config.",
            ]
        )
    edit_hint = "workspace=<value>" if action_kind == "kanban_triage" else "actor=<value>"
    lines.extend(["", f"Reply: approve / approve with edit: {edit_hint} / cancel"])
    return _ok(kind=action_kind, observation=observation, mrkdwn="\n".join(lines))


def _atomic_write_preflight(directory: Path) -> dict[str, Any]:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".talaria-bridge-preflight.", suffix=".tmp", dir=directory)
        final = directory / f".talaria-bridge-preflight.{os.getpid()}.{int(time.time() * 1000)}"
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("ok\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, final)
        finally:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            with contextlib.suppress(OSError):
                final.unlink()
    except OSError as exc:
        return {"ok": False, "code": "state_dir_unavailable", "path": str(directory), "detail": str(exc)}
    return {"ok": True, "code": "write_preflight_ok", "path": str(directory)}


def _default_hermes_home() -> Path:
    env = _as_path(os.environ.get("HERMES_HOME"))
    if env is not None:
        # A profile home shares the parent Hermes root for global state.
        if env.parent.name == "profiles":
            return env.parent.parent
        return env
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData" / "Local") / "hermes"
    return Path.home() / ".hermes"


def doctor(
    home: str | os.PathLike[str] | None = None,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    ready = ensure_ready(home)
    checks.append(
        {
            "ok": bool(ready.get("state_ok")),
            "code": "state_import_ok" if ready.get("state_ok") else "state_import_failed",
            "home": ready.get("home"),
        }
    )
    checks.append(
        {
            "ok": bool(ready.get("connectors_ok")),
            "code": "connectors_import_ok" if ready.get("connectors_ok") else "connectors_import_failed",
            "home": ready.get("home"),
        }
    )
    if not ready.get("state_ok"):
        err = _first_error(ready, "state_import_failed")
        return _failure(str(err.get("code") or "state_import_failed"), detail=err.get("detail"), checks=checks, readiness=ready)

    root = Path(str(ready["home"]))
    state = _load_state(root)
    try:
        if hasattr(state, "read_state"):
            state.read_state()
        state.list_observations()
        checks.append({"ok": True, "code": "state_probe_ok"})
    except Exception as exc:  # noqa: BLE001 - corrupt state must be RED.
        code = _classify_state_exception(exc)
        checks.append({"ok": False, "code": code, "detail": str(exc)})
        return _failure(code, detail=exc, checks=checks, readiness=ready)

    base = _as_path(hermes_home) or _default_hermes_home()
    write_dirs = [
        base / "talaria",
        base / "talaria-skill" / "watches",
        base / "talaria-skill" / "wrappers",
        base / "talaria-skill" / "out",
    ]
    for directory in write_dirs:
        check = _atomic_write_preflight(directory)
        checks.append(check)
        if not check.get("ok"):
            return _failure("state_dir_unavailable", detail=check.get("detail"), checks=checks, readiness=ready)

    ok = bool(ready.get("state_ok") and ready.get("connectors_ok"))
    if not ok:
        err = _first_error(ready, "connectors_import_failed")
        return _failure("connectors_import_failed", detail=err.get("detail"), checks=checks, readiness=ready)
    return _ok(checks=checks, readiness=ready)


def _json_arg(value: str | None) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("payload must be a JSON object")
    return parsed


def _print_success(result: dict[str, Any]) -> int:
    print(json.dumps(result, sort_keys=True))
    return 0


def _print_failure(command: str, result: dict[str, Any]) -> int:
    payload = dict(result)
    payload.setdefault("command", command)
    print(json.dumps(payload, sort_keys=True))
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Talaria in-process bridge")
    parser.add_argument("--home", help="Talaria checkout root override; defaults to TALARIA_HOME/probes")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("snapshot")
    sub.add_parser("observations")
    sub.add_parser("health")
    operational = sub.add_parser("operational")
    operational.add_argument("--refresh", action="store_true")
    act_parser = sub.add_parser("act")
    act_parser.add_argument("kind")
    act_parser.add_argument("--payload", default="{}", help="JSON object payload")
    act_parser.add_argument("--idempotency-key")
    propose_parser = sub.add_parser("propose")
    propose_parser.add_argument("kind")
    propose_parser.add_argument("observation_id")
    propose_parser.add_argument("--workspace", default="serenade")
    propose_parser.add_argument("--board")
    propose_parser.add_argument("--actor", default="operator")

    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(home=args.home)
        elif args.command == "snapshot":
            result = read_snapshot(home=args.home)
        elif args.command == "observations":
            result = read_observations(home=args.home)
        elif args.command == "health":
            result = read_health(home=args.home)
        elif args.command == "operational":
            result = read_operational(home=args.home, refresh=args.refresh)
        elif args.command == "act":
            result = act(args.kind, _json_arg(args.payload), idempotency_key=args.idempotency_key, home=args.home)
        elif args.command == "propose":
            result = propose_action(
                args.kind,
                args.observation_id,
                workspace=args.workspace,
                board=args.board,
                actor=args.actor,
                home=args.home,
            )
        else:  # pragma: no cover - argparse owns this.
            result = _failure("unknown_action_kind", detail=args.command)
    except Exception as exc:  # noqa: BLE001 - CLI contract: never traceback.
        result = _failure("state_import_failed", detail=exc)

    if result.get("ok"):
        return _print_success(result)
    return _print_failure(args.command, result)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
