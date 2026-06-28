#!/usr/bin/env python3
"""Tests for Talaria heartbeat watches (TAL-003)."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
WATCH_PATH = REPO_ROOT / "skills" / "talaria" / "scripts" / "talaria_watch.py"


def load_script(path: Path, module_name: str):
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load script at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_watch():
    return load_script(WATCH_PATH, "talaria_watch_under_test")


def write(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


STATE_OK = r'''
def snapshot():
    return {'mode': 'fake'}

def list_observations():
    return {'items': []}

def health():
    return {'ok': True}

def workspaces():
    return {'items': []}

def connectors():
    return {'items': []}

def list_queue_events():
    return {'items': []}
'''

CONNECTORS_OK = r'''
from .aggregate import aggregate_workspace_snapshot
'''


def fake_talaria_root(base: Path, aggregate_body: str) -> Path:
    root = base / "Talaria"
    plugin = root / "plugins" / "talaria"
    write(plugin / "state.py", STATE_OK)
    write(plugin / "connectors" / "contracts.py", "SNAPSHOT_SCHEMA = 'fake'\n")
    write(plugin / "connectors" / "aggregate.py", aggregate_body)
    write(plugin / "connectors" / "__init__.py", CONNECTORS_OK)
    return root


def aggregate_from_snapshot(snapshot_file: Path) -> str:
    return f"""
    import json
    from pathlib import Path
    SNAPSHOT_FILE = Path(r'{snapshot_file.as_posix()}')
    def aggregate_workspace_snapshot(*, refresh=False):
        with SNAPSHOT_FILE.open('r', encoding='utf-8') as fh:
            return json.load(fh)
    """


def write_snapshot(path: Path, *, zendesk_status: str = "live", stripe_status: str = "live", postgres_status: str = "live", metrics: dict[str, object] | None = None, zendesk_count: object = 3) -> None:
    payload = {
        "schema": "hermes.talaria.snapshot.v1",
        "workspace": "serenade",
        "workspace_meta": {"id": "serenade", "label": "Serenade"},
        "response_generated_at": "2026-06-26T00:00:00+00:00",
        "last_successful_snapshot_at": "2026-06-26T00:00:00+00:00",
        "source_confidence": "live",
        "connectors": [
            {"id": "serenade-postgres", "status": postgres_status, "freshness_floor_seconds": 60},
            {"id": "zendesk", "status": zendesk_status, "safe_summary": {"open_tickets_count": zendesk_count}, "freshness_floor_seconds": 120},
            {"id": "stripe", "status": stripe_status, "safe_summary": {"pending": 1}, "freshness_floor_seconds": 60},
        ],
        "metrics": metrics if metrics is not None else {"orders_count": 7},
        "panes": {},
        "observations": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class TestTalariaWatch(unittest.TestCase):
    def test_watch_registration_creates_config_wrapper_and_cron(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file)
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            calls: list[list[str]] = []

            def fake_run(argv, **kwargs):
                calls.append(list(argv))
                return mock.Mock(returncode=0, stdout="created\n", stderr="")

            with mock.patch.object(watch.subprocess, "run", side_effect=fake_run):
                result = watch.register_watch(
                    selector="connectors[zendesk].safe_summary.open_tickets_count",
                    comparator="gt",
                    threshold="2",
                    schedule="every 2m",
                    label="Zendesk tickets",
                    channel=None,
                    home=root,
                    hermes_home=temp / "hermes",
                )

            self.assertTrue(result["ok"], result)
            watch_id = result["watch_id"]
            self.assertRegex(watch_id, r"^[0-9a-f]{16}$")
            self.assertTrue((temp / "hermes" / "talaria-skill" / "watches" / f"{watch_id}.json").exists())
            wrapper = temp / "hermes" / "talaria-skill" / "wrappers" / f"talaria_watch_{watch_id}.py"
            self.assertTrue(wrapper.exists())
            self.assertIn(watch_id, wrapper.read_text(encoding="utf-8"))
            self.assertEqual(calls[0][:3], ["hermes", "cron", "create"])
            self.assertIn("--no-agent", calls[0])
            self.assertIn("--script", calls[0])
            self.assertIn("slack", calls[0])

    def test_registration_rejects_bad_threshold(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file)
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))

            result = watch.register_watch(
                selector="metrics.orders_count",
                comparator="gt",
                threshold="not-a-number",
                schedule="every 1m",
                label="Orders",
                home=root,
                hermes_home=temp / "hermes",
                create_cron=False,
            )

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"], "invalid_threshold")
            self.assertFalse((temp / "hermes" / "talaria-skill" / "watches").exists())

    def test_present_absent_thresholds_are_canonicalized_for_dedupe(self):
        watch = load_watch()

        present_a = watch.build_watch_config("metrics.orders_count", "present", "ignored", "every 1m", "Orders present")
        present_b = watch.build_watch_config("metrics.orders_count", "present", "", "every 1m", "Orders present")
        absent_a = watch.build_watch_config("metrics.missing", "absent", "ignored", "every 1m", "Orders absent")
        absent_b = watch.build_watch_config("metrics.missing", "absent", None, "every 1m", "Orders absent")

        self.assertIsNone(present_a["threshold"])
        self.assertEqual(present_a["watch_id"], present_b["watch_id"])
        self.assertIsNone(absent_a["threshold"])
        self.assertEqual(absent_a["watch_id"], absent_b["watch_id"])

    def test_registration_rejects_cron_below_owner_freshness_floor(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file)
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))

            result = watch.register_watch(
                selector="connectors[zendesk].safe_summary.open_tickets_count",
                comparator="gt",
                threshold="2",
                schedule="* * * * *",
                label="Zendesk tickets",
                home=root,
                hermes_home=temp / "hermes",
                create_cron=False,
            )

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"], "schedule_too_frequent")
            self.assertEqual(result["owner"], "zendesk")
            self.assertEqual(result["freshness_floor_seconds"], 120.0)
            self.assertFalse((temp / "hermes" / "talaria-skill" / "watches").exists())

    def test_watch_transitions(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, metrics={"orders_count": 7})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)

            first = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            second = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            write_snapshot(snapshot_file, metrics={"orders_count": 4})
            recovered = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)

            self.assertIn("🔔 watch", first)
            self.assertIn("7", first)
            self.assertEqual(second, "")
            self.assertIn("✅", recovered)
            self.assertIn("recovered", recovered)

    def test_watch_selector_unresolved(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, metrics={"orders_count": 9})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.missing", "gt", 5, "every 1m", "Missing metric")
            watch.write_watch_config(config, hermes_home=hermes_home)

            line = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            state = watch.read_watch_state(config["watch_id"], hermes_home=hermes_home)

            self.assertIn("cannot_evaluate", line)
            self.assertEqual(state["status"], "cannot_evaluate")
            self.assertNotIn("breached", state)
            self.assertEqual(watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home), "")

    def test_watch_degraded_scoped(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, stripe_status="degraded", zendesk_status="live", zendesk_count=3)
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            zendesk = watch.build_watch_config("connectors[zendesk].safe_summary.open_tickets_count", "gt", 2, "every 2m", "Zendesk")
            stripe = watch.build_watch_config("connectors[stripe].safe_summary.pending", "gt", 0, "every 1m", "Stripe")
            watch.write_watch_config(zendesk, hermes_home=hermes_home)
            watch.write_watch_config(stripe, hermes_home=hermes_home)

            self.assertIn("🔔", watch.evaluate_watch(zendesk["watch_id"], home=root, hermes_home=hermes_home))
            self.assertIn("cannot_evaluate", watch.evaluate_watch(stripe["watch_id"], home=root, hermes_home=hermes_home))

    def test_metrics_owner_degraded(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, postgres_status="degraded", metrics={"orders_count": 9})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)

            line = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)

            self.assertIn("cannot_evaluate", line)
            self.assertIn("serenade-postgres", line)

    def test_prior_breached_degraded_owner_is_silent_and_recovery_notes_degraded_window(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, postgres_status="degraded", metrics={"orders_count": 9})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)
            watch.write_watch_state(config["watch_id"], {"breached": True, "status": "breached"}, hermes_home=hermes_home)

            degraded = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            degraded_state = watch.read_watch_state(config["watch_id"], hermes_home=hermes_home)
            write_snapshot(snapshot_file, postgres_status="live", metrics={"orders_count": 4})
            recovered = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)

            self.assertEqual(degraded, "")
            self.assertTrue(degraded_state["breached"])
            self.assertTrue(degraded_state["degraded_window"])
            self.assertIn("✅", recovered)
            self.assertIn("may have missed transitions while degraded", recovered)

    def test_prior_breached_bridge_unavailable_is_silent(self):
        watch = load_watch()

        class BridgeUnavailable:
            @staticmethod
            def ensure_ready(_home):
                return {"ok": False, "error": "not_ready"}

        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)
            watch.write_watch_state(config["watch_id"], {"breached": True, "status": "breached"}, hermes_home=hermes_home)

            with mock.patch.object(watch, "_load_bridge", return_value=BridgeUnavailable):
                line = watch.evaluate_watch(config["watch_id"], hermes_home=hermes_home)

            state = watch.read_watch_state(config["watch_id"], hermes_home=hermes_home)
            self.assertEqual(line, "")
            self.assertTrue(state["breached"])
            self.assertEqual(state["status"], "bridge_unavailable")

    def test_watch_state_atomic_singleflight(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, metrics={"orders_count": 9})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)
            lock = watch.acquire_watch_lock(config["watch_id"], hermes_home=hermes_home)
            self.assertIsNotNone(lock)
            try:
                skipped = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            finally:
                lock.close()

            self.assertEqual(skipped, "")
            self.assertIsNone(watch.read_watch_state(config["watch_id"], hermes_home=hermes_home))

    def test_watch_stalled_tripwire(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, metrics={"orders_count": 4})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)
            watch.write_watch_state(
                config["watch_id"],
                {"breached": False, "status": "healthy", "last_evaluated_at": time.time() - 400, "stalled_reported": False},
                hermes_home=hermes_home,
            )

            line = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            second = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)

            self.assertIn("stalled", line)
            self.assertEqual(second, "")

    def test_stalled_then_breach_emits_breach_transition(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, metrics={"orders_count": 9})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)
            watch.write_watch_state(
                config["watch_id"],
                {"breached": False, "status": "healthy", "last_evaluated_at": time.time() - 400, "stalled_reported": False},
                hermes_home=hermes_home,
            )

            line = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            state = watch.read_watch_state(config["watch_id"], hermes_home=hermes_home)

            self.assertIn("🔔 watch", line)
            self.assertNotIn("stalled", line)
            self.assertEqual(state["status"], "breached")
            self.assertTrue(state["breached"])
            self.assertFalse(state["stalled_reported"])

    def test_normal_evaluation_clears_stalled_reported(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            snapshot_file = temp / "snapshot.json"
            write_snapshot(snapshot_file, metrics={"orders_count": 4})
            root = fake_talaria_root(temp, aggregate_from_snapshot(snapshot_file))
            hermes_home = temp / "hermes"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            watch.write_watch_config(config, hermes_home=hermes_home)
            watch.write_watch_state(
                config["watch_id"],
                {"breached": False, "status": "healthy", "last_evaluated_at": time.time(), "stalled_reported": True},
                hermes_home=hermes_home,
            )

            line = watch.evaluate_watch(config["watch_id"], home=root, hermes_home=hermes_home)
            state = watch.read_watch_state(config["watch_id"], hermes_home=hermes_home)

            self.assertEqual(line, "")
            self.assertFalse(state["stalled_reported"])

    def test_watch_config_missing(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            hermes_home = Path(td) / "hermes"
            watch_id = "0123456789abcdef"

            first = watch.evaluate_watch(watch_id, hermes_home=hermes_home)
            second = watch.evaluate_watch(watch_id, hermes_home=hermes_home)

            self.assertEqual(first, "⚠ watch 0123456789abcdef: config_missing")
            self.assertEqual(second, "")
            self.assertTrue((hermes_home / "talaria-skill" / "watches" / f"{watch_id}.orphan").exists())

    def test_eval_rejects_traversal_watch_id_without_orphan_write(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            hermes_home = Path(td) / "hermes"

            line = watch.evaluate_watch("../../victim", hermes_home=hermes_home)

            self.assertEqual(line, "⚠ watch invalid: invalid_watch_id")
            self.assertFalse((hermes_home / "victim.orphan").exists())
            self.assertFalse((hermes_home / "talaria-skill" / "victim.orphan").exists())
            self.assertFalse((hermes_home / "talaria-skill" / "watches").exists())

    def test_remove_watch_rejects_traversal_watch_id_without_unlink(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            hermes_home = Path(td) / "hermes"
            victim = hermes_home / "victim.json"
            victim.parent.mkdir(parents=True, exist_ok=True)
            victim.write_text("do not delete", encoding="utf-8")

            result = watch.remove_watch("../../victim", hermes_home=hermes_home, remove_cron=False)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"], "invalid_watch_id")
            self.assertTrue(victim.exists())

    def test_remove_watch_preserves_files_when_cron_remove_fails(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            hermes_home = temp / "hermes"
            watch_id = "0123456789abcdef"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            config["watch_id"] = watch_id
            watch.write_watch_config(config, hermes_home=hermes_home)
            watch.write_watch_state(watch_id, {"status": "healthy"}, hermes_home=hermes_home)
            wrapper = hermes_home / "talaria-skill" / "wrappers" / f"talaria_watch_{watch_id}.py"
            write(wrapper, "# wrapper\n")

            def fake_run(argv, **_kwargs):
                if argv[:3] == ["hermes", "cron", "list"]:
                    return mock.Mock(returncode=0, stdout=json.dumps({"jobs": [{"name": f"talaria-watch-{watch_id}", "job_id": "job-1"}]}), stderr="")
                if argv[:3] == ["hermes", "cron", "remove"]:
                    return mock.Mock(returncode=1, stdout="", stderr="remove failed")
                raise AssertionError(argv)

            with mock.patch.object(watch.subprocess, "run", side_effect=fake_run):
                result = watch.remove_watch(watch_id, hermes_home=hermes_home)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"], "cron_remove_failed")
            self.assertTrue((hermes_home / "talaria-skill" / "watches" / f"{watch_id}.json").exists())
            self.assertTrue((hermes_home / "talaria-skill" / "watches" / f"{watch_id}.state.json").exists())
            self.assertTrue(wrapper.exists())

    def test_remove_watch_preserves_files_when_cron_list_fails(self):
        watch = load_watch()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            hermes_home = temp / "hermes"
            watch_id = "0123456789abcdef"
            config = watch.build_watch_config("metrics.orders_count", "gt", 5, "every 1m", "Orders")
            config["watch_id"] = watch_id
            watch.write_watch_config(config, hermes_home=hermes_home)

            with mock.patch.object(watch.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="list failed")):
                result = watch.remove_watch(watch_id, hermes_home=hermes_home)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"], "cron_list_failed")
            self.assertTrue((hermes_home / "talaria-skill" / "watches" / f"{watch_id}.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
