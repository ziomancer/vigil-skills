#!/usr/bin/env python3
"""Tests for the Talaria skill bridge foundation (TAL-003).

Stdlib unittest. Run directly: `python tests/test_talaria_bridge.py`.
The bridge/read scripts are loaded by file path so the skill can remain a
portable script without package boilerplate.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = REPO_ROOT / "skills" / "talaria" / "scripts" / "talaria_bridge.py"
READ_PATH = REPO_ROOT / "skills" / "talaria" / "scripts" / "talaria_read.py"


def load_script(path: Path, module_name: str):
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load script at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_bridge():
    return load_script(BRIDGE_PATH, "talaria_bridge_under_test")


def load_reader():
    return load_script(READ_PATH, "talaria_read_under_test")


def write(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


@contextlib.contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def fake_talaria_root(
    base: Path,
    *,
    connectors_init: str | None = None,
    aggregate_body: str | None = None,
    state_body: str | None = None,
) -> Path:
    root = base / "Talaria"
    plugin = root / "plugins" / "talaria"
    write(plugin / "state.py", state_body or STATE_OK)
    write(plugin / "connectors" / "contracts.py", "SNAPSHOT_SCHEMA = 'fake'\n")
    write(
        plugin / "connectors" / "aggregate.py",
        aggregate_body
        or """
        def aggregate_workspace_snapshot(*, refresh=False):
            return {
                'schema': 'hermes.talaria.snapshot.v1',
                'workspace': 'serenade',
                'workspace_meta': {'id': 'serenade', 'label': 'Serenade'},
                'response_generated_at': '2026-06-26T00:00:00+00:00',
                'snapshot_created_at': '2026-06-26T00:00:00+00:00' if refresh else None,
                'last_successful_snapshot_at': '2026-06-26T00:00:00+00:00',
                'source_confidence': 'live',
                'connectors': [{'id': 'serenade-postgres', 'status': 'live'}, {'id': 'zendesk', 'status': 'live'}],
                'metrics': {'orders_count': 7},
                'panes': {'overview': {'metrics': {'orders_count': 7}}},
                'observations': [{'id': 'obs-from-connector'}],
            }
        """,
    )
    write(plugin / "connectors" / "__init__.py", connectors_init or CONNECTORS_OK)
    return root


STATE_OK = r'''
import json
from pathlib import Path

_STATE_FILE = Path(__file__).with_name('state.json')
CALLS = []

class ObservationConflict(ValueError):
    def __init__(self, reason, observation):
        super().__init__(reason)
        self.reason = reason
        self.observation = observation
    def to_detail(self):
        return {'reason': self.reason, 'observation': self.observation}

def allowed_action_kinds():
    CALLS.append('allowed_action_kinds')
    return {'ack_observation', 'kanban_triage'}

def read_state():
    if not _STATE_FILE.exists():
        return {'observations': {}, 'acks': {}, 'actions': {}}
    with _STATE_FILE.open('r', encoding='utf-8') as fh:
        return json.load(fh)

def write_state(state):
    _STATE_FILE.write_text(json.dumps(state, sort_keys=True), encoding='utf-8')

def list_observations():
    return {'items': list(read_state().get('observations', {}).values())}

def health():
    return {'ok': True, 'state': {'path': str(_STATE_FILE)}}

def workspaces():
    return {'items': [{'id': 'serenade', 'name': 'Serenade'}]}

def connectors():
    return {'items': [{'id': 'placeholder', 'status': 'static'}]}

def list_queue_events():
    return {'items': []}

def snapshot():
    return {
        'mode': 'fake',
        'health': health(),
        'workspaces': workspaces(),
        'connectors': connectors(),
        'observations': list_observations(),
        'queue_events': list_queue_events(),
    }

def acknowledge_observation(payload, *, idempotency_key=None):
    CALLS.append('acknowledge_observation')
    observation_id = str(payload.get('observation_id') or '').strip()
    if not observation_id:
        raise ValueError('payload.observation_id is required')
    state = read_state()
    if observation_id not in state.get('observations', {}):
        raise ValueError(f'unknown observation {observation_id}')
    action_key = f'ack_observation:{idempotency_key}' if idempotency_key else ''
    if action_key and action_key in state.get('actions', {}):
        action = dict(state['actions'][action_key])
        action['idempotent_replay'] = True
        return action
    action = {
        'kind': 'ack_observation',
        'status': 'acknowledged',
        'observation_id': observation_id,
        'actor': payload.get('actor') or 'operator',
        'idempotency_key': idempotency_key,
        'idempotent_replay': False,
    }
    state.setdefault('acks', {})[observation_id] = {'actor': action['actor'], 'stage': 'acknowledged'}
    if action_key:
        state.setdefault('actions', {})[action_key] = action
    write_state(state)
    return action

def create_kanban_card_from_observation(*, workspace, observation_id, preview_revision=None):
    CALLS.append('create_kanban_card_from_observation')
    if preview_revision is not None:
        raise AssertionError('preview_revision must not be captured by this cut')
    observation_id = str(observation_id or '').strip()
    if workspace == 'unknown':
        raise ValueError("unknown workspace 'unknown'")
    if workspace == 'missing-board':
        raise ValueError("configured board 'missing-board' does not exist")
    state = read_state()
    observation = state.get('observations', {}).get(observation_id)
    if not isinstance(observation, dict):
        raise ObservationConflict('observation_missing', {'id': observation_id, 'state': 'source_missing'})
    if observation.get('workspace') and observation.get('workspace') != workspace:
        raise ValueError(f"observation {observation_id!r} does not belong to workspace {workspace!r}")
    if observation.get('state') and observation.get('state') != 'open':
        raise ObservationConflict('observation_not_open', observation)
    if observation.get('needs_source_ref'):
        raise ObservationConflict('source_identifier_required', observation)
    if observation.get('refreshed'):
        raise ObservationConflict('observation_refreshed', observation)
    action_key = f'talaria:{workspace}:{observation_id}'
    if action_key in state.get('actions', {}):
        action = dict(state['actions'][action_key])
        action['duplicate'] = True
        action['idempotent_replay'] = True
        return action
    action = {
        'kind': 'kanban_triage',
        'status': 'triage',
        'workspace': workspace,
        'observation_id': observation_id,
        'task_id': 't_fake',
        'duplicate': False,
        'idempotent_replay': False,
    }
    state.setdefault('actions', {})[action_key] = action
    write_state(state)
    return action

def sanitize_dto(value):
    return value
'''

CONNECTORS_OK = r'''
from .aggregate import aggregate_workspace_snapshot
'''


class TestTalariaBridge(unittest.TestCase):
    def test_resolve_home_rejects_predecessor(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            predecessor = base / "operator-dashboard"
            write(predecessor / "plugins" / "talaria" / "state.py", "# predecessor copied state-like file\n")
            write(predecessor / "plugins" / "talaria" / "connectors" / "aggregate.py", "# no Talaria aggregate export\n")

            actual = fake_talaria_root(base / "actual")

            with mock.patch.dict(os.environ, {"TALARIA_HOME": str(predecessor)}, clear=False):
                rejected = bridge.resolve_home()
            self.assertFalse(rejected["ok"])
            self.assertEqual(rejected["error"], "talaria_not_found")
            self.assertIn("TALARIA_HOME", rejected["hint"])

            with mock.patch.dict(os.environ, {"TALARIA_HOME": "", "TALARIA_PLUGIN_ROOTS": str(actual)}, clear=False):
                resolved = bridge.resolve_home()
            self.assertTrue(resolved["ok"], resolved)
            self.assertEqual(Path(resolved["path"]), actual)

    def test_default_discovery_finds_adjacent_talaria_and_hermes_runtime(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            workspace = base / "vigil-skills"
            workspace.mkdir()
            hermes_home = base / "hermes-home"
            write(
                base / "hermes-agent-local" / "hermes_constants.py",
                f"""
                from pathlib import Path
                def get_hermes_home():
                    return Path(r'{hermes_home.as_posix()}')
                """,
            )
            root = fake_talaria_root(
                base,
                state_body="""
                from hermes_constants import get_hermes_home

                def allowed_action_kinds():
                    return {'ack_observation', 'kanban_triage'}
                def read_state():
                    return {'home': str(get_hermes_home()), 'observations': {}}
                def list_observations():
                    return {'items': []}
                def health():
                    return {'ok': True, 'state': {'path': str(get_hermes_home() / 'talaria' / 'state.json')}}
                def workspaces():
                    return {'items': [{'id': 'serenade'}]}
                def connectors():
                    return {'items': []}
                def list_queue_events():
                    return {'items': []}
                def snapshot():
                    return {'observations': list_observations()}
                def sanitize_dto(value):
                    return value
                """,
            )

            original_sys_path = list(sys.path)
            with pushd(workspace), mock.patch.dict(
                os.environ,
                {"TALARIA_HOME": "", "TALARIA_PLUGIN_ROOTS": "", "HERMES_PLUGIN_ROOTS": ""},
                clear=False,
            ):
                result = bridge.doctor(hermes_home=hermes_home)

            self.assertTrue(result["ok"], result)
            self.assertEqual(Path(result["readiness"]["home"]), root)
            self.assertEqual(sys.path, original_sys_path)

    def test_partial_import_keeps_state_reads_and_actions_available(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            root = fake_talaria_root(Path(td), connectors_init="raise RuntimeError('connector dependency missing')\n")
            (root / "plugins" / "talaria" / "state.json").write_text(
                json.dumps({"observations": {"obs-1": {"id": "obs-1", "workspace": "serenade"}}}),
                encoding="utf-8",
            )

            ready = bridge.ensure_ready(home=root)
            self.assertTrue(ready["state_ok"], ready)
            self.assertFalse(ready["connectors_ok"], ready)
            self.assertIn("connectors_import_failed", {err["code"] for err in ready["errors"]})

            observations = bridge.read_observations(home=root)
            self.assertTrue(observations["ok"], observations)
            self.assertEqual(observations["observations"], {"items": [{"id": "obs-1", "workspace": "serenade"}]})

            ack = bridge.act(
                "ack_observation",
                {"observation_id": "obs-1"},
                idempotency_key="ack:obs-1",
                home=root,
            )
            self.assertTrue(ack["ok"], ack)
            self.assertEqual(ack["action"]["kind"], "ack_observation")

            triage = bridge.act(
                "kanban_triage",
                {"workspace": "serenade", "observation_id": "obs-1"},
                home=root,
            )
            self.assertTrue(triage["ok"], triage)
            self.assertEqual(triage["action"]["kind"], "kanban_triage")

    def test_act_gate_and_dispatch(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            root = fake_talaria_root(Path(td))
            state_file = root / "plugins" / "talaria" / "state.json"
            state_file.write_text(
                json.dumps({"observations": {"obs-1": {"id": "obs-1", "workspace": "serenade"}}}),
                encoding="utf-8",
            )

            unknown = bridge.act("send_refund", {"observation_id": "obs-1"}, home=root)
            self.assertFalse(unknown["ok"], unknown)
            self.assertEqual(unknown["error"], "unknown_action_kind")
            state = bridge._load_state(root)
            self.assertEqual(state.CALLS, ["allowed_action_kinds"])

            ack = bridge.act("ack_observation", {"observation_id": "obs-1", "actor": "operator"}, home=root)
            self.assertTrue(ack["ok"], ack)
            self.assertEqual(ack["action"]["idempotency_key"], "ack:obs-1")
            self.assertIn("acknowledge_observation", state.CALLS)

            triage = bridge.act("kanban_triage", {"workspace": "serenade", "observation_id": "obs-1"}, home=root)
            self.assertTrue(triage["ok"], triage)
            self.assertEqual(triage["action"]["kind"], "kanban_triage")
            self.assertIn("create_kanban_card_from_observation", state.CALLS)

    def test_act_idempotent_returnflags(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            root = fake_talaria_root(Path(td))
            state_file = root / "plugins" / "talaria" / "state.json"
            state_file.write_text(
                json.dumps({"observations": {"obs-1": {"id": "obs-1", "workspace": "serenade"}}}),
                encoding="utf-8",
            )

            first_ack = bridge.act("ack_observation", {"observation_id": "obs-1"}, home=root)
            second_ack = bridge.act("ack_observation", {"observation_id": "obs-1"}, home=root)
            self.assertTrue(first_ack["ok"], first_ack)
            self.assertTrue(second_ack["ok"], second_ack)
            self.assertFalse(first_ack["action"]["idempotent_replay"])
            self.assertTrue(second_ack["action"]["idempotent_replay"])
            self.assertEqual(second_ack["message"], "already applied (no-op)")

            first_triage = bridge.act("kanban_triage", {"workspace": "serenade", "observation_id": "obs-1"}, home=root)
            second_triage = bridge.act("kanban_triage", {"workspace": "serenade", "observation_id": "obs-1"}, home=root)
            self.assertTrue(first_triage["ok"], first_triage)
            self.assertTrue(second_triage["ok"], second_triage)
            self.assertFalse(first_triage["action"]["duplicate"])
            self.assertTrue(second_triage["action"]["duplicate"])
            self.assertTrue(second_triage["action"]["idempotent_replay"])
            self.assertEqual(second_triage["message"], "already applied (no-op)")

    def test_act_exception_mapping(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            root = fake_talaria_root(Path(td))
            state_file = root / "plugins" / "talaria" / "state.json"
            state_file.write_text(
                json.dumps(
                    {
                        "observations": {
                            "closed": {"id": "closed", "workspace": "serenade", "state": "closed"},
                            "needs-ref": {"id": "needs-ref", "workspace": "serenade", "needs_source_ref": True},
                            "fresh": {"id": "fresh", "workspace": "serenade", "refreshed": True},
                            "other": {"id": "other", "workspace": "other"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            cases = [
                ("ack_observation", {"observation_id": "missing"}, "observation_gone"),
                ("kanban_triage", {"workspace": "serenade", "observation_id": "missing"}, "observation_gone"),
                ("kanban_triage", {"workspace": "serenade", "observation_id": "closed"}, "observation_already_resolved"),
                ("kanban_triage", {"workspace": "serenade", "observation_id": "needs-ref"}, "source_identifier_required"),
                ("kanban_triage", {"workspace": "serenade", "observation_id": "fresh"}, "observation_refreshed"),
                ("kanban_triage", {"workspace": "serenade", "observation_id": "other"}, "workspace_mismatch"),
                ("kanban_triage", {"workspace": "unknown", "observation_id": "closed"}, "unknown_workspace"),
                ("kanban_triage", {"workspace": "missing-board", "observation_id": "closed"}, "missing_board"),
            ]
            for kind, payload, code in cases:
                with self.subTest(code=code):
                    result = bridge.act(kind, payload, home=root)
                    self.assertFalse(result["ok"], result)
                    self.assertEqual(result["error"], code)
                    self.assertNotIn("Traceback", json.dumps(result))

            with mock.patch.object(bridge._load_state(root), "write_state", side_effect=PermissionError("denied")):
                unwritable = bridge.act("ack_observation", {"observation_id": "closed"}, home=root)
            self.assertFalse(unwritable["ok"], unwritable)
            self.assertEqual(unwritable["error"], "state_not_writable")
            self.assertNotIn("Traceback", json.dumps(unwritable))

    def test_action_proposal_mrkdwn_and_local_only(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            root = fake_talaria_root(Path(td))
            state_file = root / "plugins" / "talaria" / "state.json"
            state_file.write_text(
                json.dumps(
                    {
                        "observations": {
                            "obs-1": {
                                "id": "obs-1",
                                "source": "local",
                                "severity": "warning",
                                "title": "Needs eyes",
                                "summary": "safe summary",
                                "workspace": "serenade",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            proposal = bridge.propose_action("kanban_triage", "obs-1", workspace="serenade", home=root)
            self.assertTrue(proposal["ok"], proposal)
            self.assertIn("*Observation:* obs-1", proposal["mrkdwn"])
            self.assertIn("*Source:* local", proposal["mrkdwn"])
            self.assertIn("*Severity:* warning", proposal["mrkdwn"])
            self.assertIn("*Title:* Needs eyes", proposal["mrkdwn"])
            self.assertIn("*Summary:* safe summary", proposal["mrkdwn"])
            self.assertIn("approve with edit: workspace=<value>", proposal["mrkdwn"])
            self.assertIn("dedups", proposal["mrkdwn"])

            missing = bridge.propose_action("ack_observation", "connector:obs-1", home=root)
            self.assertFalse(missing["ok"], missing)
            self.assertEqual(missing["error"], "not_directly_actionable")

    def test_doctor_corrupt_state_is_red(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            root = fake_talaria_root(temp)
            state_file = root / "plugins" / "talaria" / "state.json"
            state_file.write_text("{not-json", encoding="utf-8")

            result = bridge.doctor(home=root, hermes_home=temp / "hermes-home")
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"], "state_corrupt")
            self.assertIn("state_corrupt", {check["code"] for check in result["checks"] if not check["ok"]})

    def test_operational_merge_and_degrade(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            root = fake_talaria_root(temp / "ok")
            result = bridge.read_operational(home=root, hermes_home=temp / "hermes-ok")

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["source_confidence"], "live")
            self.assertEqual(result["metrics"], {"orders_count": 7})
            self.assertEqual(result["panes"], {"overview": {"metrics": {"orders_count": 7}}})
            self.assertEqual(result["connector_observations"], [{"id": "obs-from-connector"}])
            self.assertIsInstance(result["connectors"], list)
            self.assertEqual([item["id"] for item in result["connectors"]], ["serenade-postgres", "zendesk"])
            self.assertEqual(result["operational_snapshot"]["connectors"], result["connectors"])

            failing = fake_talaria_root(
                temp / "failing",
                aggregate_body="""
                def aggregate_workspace_snapshot(*, refresh=False):
                    raise RuntimeError('connector boom')
                """,
            )
            degraded = bridge.read_operational(home=failing, hermes_home=temp / "hermes-degraded")

            self.assertTrue(degraded["ok"], degraded)
            self.assertTrue(degraded["degraded"], degraded)
            self.assertEqual(degraded["source_confidence"], "unknown")
            self.assertEqual(degraded["connectors"], [])
            self.assertEqual(degraded["operational_snapshot"]["connectors"], [])
            self.assertEqual(degraded["last_error"]["code"], "connector_aggregation_failed")

    def test_snapshot_cache_single_refresh(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            count_file = temp / "refresh-count.txt"
            root = fake_talaria_root(
                temp,
                aggregate_body=f"""
                import time
                from pathlib import Path
                COUNT_FILE = Path(r'{count_file.as_posix()}')
                def aggregate_workspace_snapshot(*, refresh=False):
                    time.sleep(0.2)
                    count = int(COUNT_FILE.read_text(encoding='utf-8')) if COUNT_FILE.exists() else 0
                    count += 1
                    COUNT_FILE.write_text(str(count), encoding='utf-8')
                    return {{
                        'schema': 'hermes.talaria.snapshot.v1',
                        'workspace': 'serenade',
                        'workspace_meta': {{'id': 'serenade', 'label': 'Serenade'}},
                        'response_generated_at': '2026-06-26T00:00:00+00:00',
                        'last_successful_snapshot_at': '2026-06-26T00:00:00+00:00',
                        'source_confidence': 'live',
                        'connectors': [{{'id': 'serenade-postgres', 'status': 'live'}}],
                        'metrics': {{'refresh_count': count}},
                        'panes': {{}},
                        'observations': [],
                    }}
                """,
            )
            hermes_home = temp / "hermes-cache"
            results: list[dict[str, object]] = []

            def worker() -> None:
                results.append(bridge.read_operational(home=root, hermes_home=hermes_home))

            threads = [threading.Thread(target=worker) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(count_file.read_text(encoding="utf-8"), "1")
            self.assertTrue(any(item.get("ok") for item in results), results)
            self.assertTrue(any(item.get("error") == "cannot_evaluate" for item in results), results)

            cached = bridge.read_operational(home=root, hermes_home=hermes_home)
            self.assertTrue(cached["ok"], cached)
            self.assertEqual(cached["metrics"], {"refresh_count": 1})
            self.assertEqual(count_file.read_text(encoding="utf-8"), "1")

    def test_snapshot_lease_holder_heartbeats_during_refresh(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            count_file = temp / "heartbeat-count.txt"
            root = fake_talaria_root(
                temp,
                aggregate_body=f"""
                import threading
                import time
                from pathlib import Path
                COUNT_FILE = Path(r'{count_file.as_posix()}')
                COUNT_LOCK = threading.Lock()
                def aggregate_workspace_snapshot(*, refresh=False):
                    with COUNT_LOCK:
                        count = int(COUNT_FILE.read_text(encoding='utf-8')) if COUNT_FILE.exists() else 0
                        count += 1
                        COUNT_FILE.write_text(str(count), encoding='utf-8')
                    time.sleep(0.25)
                    return {{
                        'schema': 'hermes.talaria.snapshot.v1',
                        'workspace': 'serenade',
                        'workspace_meta': {{'id': 'serenade', 'label': 'Serenade'}},
                        'response_generated_at': '2026-06-26T00:00:00+00:00',
                        'last_successful_snapshot_at': '2026-06-26T00:00:00+00:00',
                        'source_confidence': 'live',
                        'connectors': [{{'id': 'serenade-postgres', 'status': 'live'}}],
                        'metrics': {{'refresh_count': count}},
                        'panes': {{}},
                        'observations': [],
                    }}
                """,
            )
            hermes_home = temp / "hermes-heartbeat"
            results: list[dict[str, object]] = []

            def worker() -> None:
                results.append(bridge.read_operational(home=root, hermes_home=hermes_home))

            with mock.patch.object(bridge, "_LEASE_STALE_SECONDS", 0.05):
                first = threading.Thread(target=worker)
                first.start()
                time.sleep(0.12)
                second = threading.Thread(target=worker)
                second.start()
                first.join()
                second.join()

            self.assertEqual(count_file.read_text(encoding="utf-8"), "1")
            self.assertTrue(any(item.get("ok") for item in results), results)
            self.assertTrue(any(item.get("error") == "cannot_evaluate" for item in results), results)

    def test_operational_connectors_resolution(self):
        bridge = load_bridge()
        payload = {
            "connectors": [
                {"id": "serenade-postgres", "status": "degraded", "last_error": {"code": "database_url_missing"}},
                {"id": "zendesk", "status": "live", "safe_summary": {"open_tickets_count": 3}},
                {"id": "stripe", "status": "degraded", "last_error": {"code": "stripe_rate_limited"}},
            ],
            "metrics": {"orders_count": 0},
        }

        zendesk = bridge.evaluate_operational_selector(payload, "connectors[zendesk].safe_summary.open_tickets_count")
        self.assertEqual(zendesk, {"ok": True, "owner": "zendesk", "value": 3})

        stripe = bridge.evaluate_operational_selector(payload, "connectors[stripe].status")
        self.assertFalse(stripe["ok"], stripe)
        self.assertEqual(stripe["error"], "cannot_evaluate")
        self.assertEqual(stripe["owner"], "stripe")

        metric = bridge.evaluate_operational_selector(payload, "metrics.orders_count")
        self.assertFalse(metric["ok"], metric)
        self.assertEqual(metric["error"], "cannot_evaluate")
        self.assertEqual(metric["owner"], "serenade-postgres")

    def test_backoff_coarse_suppression(self):
        bridge = load_bridge()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            count_file = temp / "backoff-count.txt"
            root = fake_talaria_root(
                temp,
                aggregate_body=f"""
                from pathlib import Path
                COUNT_FILE = Path(r'{count_file.as_posix()}')
                def aggregate_workspace_snapshot(*, refresh=False):
                    count = int(COUNT_FILE.read_text(encoding='utf-8')) if COUNT_FILE.exists() else 0
                    count += 1
                    COUNT_FILE.write_text(str(count), encoding='utf-8')
                    return {{
                        'schema': 'hermes.talaria.snapshot.v1',
                        'workspace': 'serenade',
                        'workspace_meta': {{'id': 'serenade', 'label': 'Serenade'}},
                        'response_generated_at': '2026-06-26T00:00:00+00:00',
                        'last_successful_snapshot_at': '2026-06-26T00:00:00+00:00',
                        'source_confidence': 'live',
                        'connectors': [{{'id': 'serenade-postgres', 'status': 'live'}}, {{'id': 'stripe', 'status': 'live'}}],
                        'metrics': {{'refresh_count': count}},
                        'panes': {{}},
                        'observations': [],
                    }}
                """,
            )
            hermes_home = temp / "hermes-backoff"
            first = bridge.read_operational(home=root, hermes_home=hermes_home)
            self.assertTrue(first["ok"], first)
            bridge.write_vendor_backoff("stripe", retry_after_seconds=120, hermes_home=hermes_home)

            suppressed = bridge.read_operational(home=root, refresh=True, hermes_home=hermes_home)
            self.assertTrue(suppressed["ok"], suppressed)
            self.assertEqual(suppressed["metrics"], {"refresh_count": 1})
            self.assertEqual(count_file.read_text(encoding="utf-8"), "1")

            cold_home = temp / "hermes-cold-backoff"
            bridge.write_vendor_backoff("stripe", retry_after_seconds=120, hermes_home=cold_home)
            cold = bridge.read_operational(home=root, refresh=True, hermes_home=cold_home)
            self.assertFalse(cold["ok"], cold)
            self.assertEqual(cold["error"], "cannot_evaluate")
            self.assertEqual(count_file.read_text(encoding="utf-8"), "1")

    def test_read_connector_selection_preserves_footer_timestamp(self):
        reader = load_reader()
        selected = reader._select_connector(
            {
                "ok": True,
                "source_confidence": "mixed",
                "response_generated_at": "2026-06-26T00:00:00+00:00",
                "last_successful_snapshot_at": "2026-06-25T00:00:00+00:00",
                "connectors": [{"id": "stripe", "status": "degraded"}],
            },
            "stripe",
        )
        rendered = reader.render_payload("connector", selected, mrkdwn=True)
        self.assertIn("operational_ts=2026-06-26T00:00:00+00:00", rendered["body"])
        self.assertNotIn("degraded — no fresh timestamp", rendered["body"])

    def test_read_render_footer_and_budget(self):
        reader = load_reader()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            payload = {
                "ok": True,
                "source_confidence": "mixed",
                "response_generated_at": "2026-06-26T00:00:00+00:00",
                "connectors": [
                    {"id": "serenade-postgres", "status": "live"},
                    {"id": "stripe", "status": "degraded", "last_error": {"code": "stripe_rate_limited"}},
                ],
                "metrics": {"very_large": "x" * 1200},
                "panes": {"money": {"very_large": "x" * 1200}},
            }

            rendered = reader.render_payload("operational", payload, mrkdwn=True, render_budget=500, hermes_home=temp)
            self.assertTrue(rendered["spilled"], rendered)
            self.assertTrue(Path(rendered["path"]).exists(), rendered)
            self.assertLessEqual(len(rendered["preview"]), 500)
            self.assertTrue(rendered["preview"].startswith("uncertain"), rendered["preview"])
            self.assertIn("source_confidence=mixed", rendered["preview"])
            self.assertIn("operational_ts=2026-06-26T00:00:00+00:00", rendered["preview"])
            self.assertIn("⚠ degraded: stripe", rendered["preview"])

    def test_read_render_spill_failure_preserves_footer(self):
        reader = load_reader()
        payload = {
            "ok": True,
            "source_confidence": "mixed",
            "response_generated_at": "2026-06-26T00:00:00+00:00",
            "connectors": [
                {"id": "serenade-postgres", "status": "live"},
                {"id": "stripe", "status": "degraded", "last_error": {"code": "stripe_rate_limited"}},
            ],
            "metrics": {"very_large": "x" * 1200},
            "panes": {"money": {"very_large": "x" * 1200}},
        }

        with mock.patch.object(reader, "_spill_text", side_effect=OSError("disk full")):
            rendered = reader.render_payload("operational", payload, mrkdwn=True, render_budget=500)

        self.assertFalse(rendered["spilled"], rendered)
        self.assertEqual(rendered["warning"], "full output unavailable")
        self.assertLessEqual(len(rendered["body"]), 500)
        self.assertIn("full output unavailable", rendered["body"])
        self.assertIn("source_confidence=mixed", rendered["body"])
        self.assertIn("operational_ts=2026-06-26T00:00:00+00:00", rendered["body"])
        self.assertIn("⚠ degraded: stripe", rendered["body"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
