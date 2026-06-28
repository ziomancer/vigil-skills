---
name: talaria
description: Read Talaria operational state, propose safe actions, and register heartbeat watches without letting an agent mutate live systems outside the approved Talaria state actions.
user_invocable: true
requires:
  shell: true
  filesystem: [read, write]
  network: true
---

# /talaria

Talaria is the local operator bridge for asking, "what needs attention?" across Vigil Harbor workspaces. It reads Talaria state and connector snapshots, renders scoped answers for humans, proposes actions for explicit approval, and can register no-agent heartbeat watches.

This skill is intentionally conservative: prefer a scoped read over a full dump, prefer a proposal over a write, and never perform customer-facing/vendor-side effects from an agent turn.

## §0 Frontmatter and runtime contract

- Required interpreter: `${HERMES_PYTHON:-python}`. Use this in every command so operators can pin the same Python that imports Talaria connector dependencies.
- Main scripts:
  - `skills/talaria/scripts/talaria_read.py` for LOOK/read/render and safe `act ack|triage` shims.
  - `skills/talaria/scripts/talaria_bridge.py` for lower-level doctor/read/propose/act calls and structured JSON errors.
  - `skills/talaria/scripts/talaria_watch.py` for watch registration, wrappers, and cron evaluator ticks.
- Talaria checkout discovery order: `--home`, then `TALARIA_HOME`, then plugin roots/cwd/ancestor probes, sibling `Talaria` checkouts, and Hermes home probes. A bad explicit `TALARIA_HOME` fails red instead of silently falling through.
- Live Talaria imports may need Hermes runtime helpers such as `hermes_constants`; the bridge temporarily probes nearby `hermes-agent*` checkouts during module import and restores `sys.path` afterward, so the repo-root doctor smoke does not require a manual `PYTHONPATH` on Devin's checkout layout.
- State/cache directories live under the Hermes root, normally `~/.hermes/talaria` and `~/.hermes/talaria-skill/`.
- On Devin's Windows/Git-Bash setup, scrub poisoned inherited Python env when commands fail to import stdlib or Talaria dependencies: `env -u PYTHONHOME -u PYTHONPATH -u UV_INTERNAL__PYTHONHOME ${HERMES_PYTHON:-python} ...`.

## §1 Read-only / proposal-only invariant

Agents may read Talaria state and propose actions. Agents must not directly perform Talaria writes except these two approved local state actions after an explicit human approval path:

1. `ack_observation`
2. `kanban_triage`

FORBIDDEN from agent turns:

- Any Talaria write/action other than `ack_observation` or `kanban_triage`.
- Any vendor/customer side effect such as refunds, emails, ticket updates, order changes, ad spend, payouts, or public/customer communications.
- Bypassing the proposal step by editing Talaria state files manually.
- Treating connector observations as directly actionable when the bridge returns `not_directly_actionable`; re-read and ask for/source a local observation instead.

If a requested action is outside the two allowed actions, stop and report the bridge's `unknown_action_kind` / proposal boundary. Do not improvise a direct API call.

## §2 NL -> intent table

Prefer the narrowest safe intent that answers the user's question.

| Natural-language ask | Intent | Preferred command | Notes |
| --- | --- | --- | --- |
| "doctor", "is Talaria wired", "check setup" | `doctor` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py doctor` | Red on corrupt state, missing connector imports, or unwritable state/cache dirs. |
| "what needs attention", "operator snapshot", "overall status" | `read_operational` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py --mrkdwn operational` | Full operational read only when no narrower owner/pane was requested. |
| "show Stripe", "how is Zendesk", "connector status" | `read_connector` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py --mrkdwn connector <connector_id>` | Scoped connector read; preserves source-confidence/timestamp footer. |
| "show money pane", "orders metric pane" | `read_pane` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py --mrkdwn pane <pane_id>` | Scoped pane read; use before dumping all panes. |
| "list observations", "open local observations" | `read_observations` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py observations` | State-side observation list; no connector aggregation needed. |
| "health", "state health" | `read_health` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py health` | State health only. |
| "refresh live snapshot" | `read_operational_refresh` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py --mrkdwn operational --refresh` | Use sparingly; respects shared cache/lease and vendor backoff. |
| "ack this observation" | `propose_ack` then `act_ack` after approval | propose: `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_bridge.py propose ack_observation <observation_id>`; approved write: `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py act ack --payload '{"observation_id":"<id>","actor":"operator"}'` | Local state write only; idempotent replays return `already applied (no-op)`. |
| "turn this into a kanban card" | `propose_triage` then `act_triage` after approval | propose: `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_bridge.py propose kanban_triage <observation_id> --workspace <workspace> --board <board>`; approved write: `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py act triage --payload '{"workspace":"<workspace>","observation_id":"<id>"}'` | Talaria dedups by canonical workspace/board/source key; duplicate/idempotent replay is success/no-op. |
| "watch this metric", "alert when X crosses Y" | `register_watch` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_watch.py register <selector> <comparator> <threshold> <schedule> <label>` | Validates selector owner and schedule freshness floor before creating a cron wrapper. |
| "remove watch" | `remove_watch` | `${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_watch.py remove-watch <watch_id>` | Removes wrapper/config/state/orphan/lock and matching cron jobs. |

## Scoped read playbook

1. Start with `doctor` when setup/import state is unknown.
2. Choose a scoped read whenever the question names a connector, pane, metric, or observation id.
3. Use `operational` only for cross-workspace/operator summaries or when selector ownership must be resolved.
4. Trust the footer: `source_confidence`, `operational_ts`, and degraded connector markers are part of the answer, not decoration.
5. If output spills, read the generated `talaria-skill/out/*.md` file only as needed; do not paste large dumps into chat.
6. If a refresh is in progress and no cache exists, report `cannot_evaluate` rather than forcing parallel connector calls.

## Connector freshness floors

Watch registration rejects schedules more frequent than the owning connector can safely refresh. Use the connector snapshot's `freshness_floor_seconds` when present; otherwise apply this seed table when designing watches and docs.

| Selector owner / connector class | Minimum freshness floor | Rationale |
| --- | ---: | --- |
| Vendor APIs (`stripe`, `suno`, `zendesk`, `agentmail`, ad platforms, other external SaaS) | >= 60s | Avoid rate-limit loops and vendor backoff churn. |
| Local Postgres connectors | >= 30s | Local but still DB-backed; avoid pointless hot polling. |
| Local JSONL/file connectors | >= 30s | Local file state can be read cheaply, but watchdogs should not spin. |
| Hermes Kanban/local state connectors | >= 30s | Local SQLite/state reads should be quiet unless explicitly debugging. |
| `metrics.<key>` selectors | Use `serenade-postgres` floor | Derived metrics are owned by the Serenade Postgres connector. |
| `connectors[website-analytics]` or `connectors[relaticle]` derived metrics | Use derived owner status, not a direct watch owner | Bridge returns `derived_metric_connector`; choose the backing metric/owner instead. |

## Schedule -> interval derivation

Talaria watch registration derives a frequency from the requested schedule before comparing it to the owner floor.

- Interval schedules: `30s`, `1m`, `every 2h`, `1d` map directly to seconds.
- Cron schedules: five-field cron is expanded over a representative calendar and the smallest gap between matching minutes becomes the effective interval.
- Invalid/ambiguous schedules return `schedule_frequency_unknown` and do not create wrappers or cron jobs.
- If derived interval is below the owner floor, registration fails with `schedule_too_frequent` and names the owner plus `freshness_floor_seconds`.

## Action approval flow

1. Read the current observation with a scoped command.
2. Generate proposal text with `talaria_bridge.py propose ...`.
3. Show the proposal to the human/operator. They may approve, approve with edit, or cancel.
4. Only after approval, execute `talaria_read.py act ack ...` or `talaria_read.py act triage ...`.
5. Treat `idempotent_replay` or `duplicate` as a no-op success; report it plainly.
6. Treat `observation_gone`, `observation_already_resolved`, `source_identifier_required`, `observation_refreshed`, `workspace_mismatch`, `unknown_workspace`, and `missing_board` as stop-and-reread conditions.

## Watch playbook

Selectors supported by the current bridge:

- `connectors[<connector_id>].<field.path>`
- `metrics.<metric_key>`

Comparators:

- Numeric: `gt`, `gte`, `lt`, `lte`, `eq`, `ne`
- Presence: `present`, `absent`

Watch behavior:

- Alerts only on transitions into breach; recovers only on transitions out of breach.
- Degraded owners produce `cannot_evaluate` instead of false healthy/false breached.
- Prior-breached degraded windows remain quiet until recovery, then recovery is annotated as possibly missed transitions.
- Missing configs emit an orphan warning once, then self-clean after repeated misses.
- Evaluators are script-only/no-agent cron wrappers and stay silent on healthy ticks.

## Test plan

Run from the vigil-skills repo root. Use stdlib unittest; no pytest/node gate is required.

1. Bridge/read/action regression suite:
   - Talaria discovery rejects predecessor trees.
   - Partial connector import still permits state reads and the two local actions.
   - State-side action gate rejects unknown writes.
   - `ack_observation` and `kanban_triage` idempotent replay/duplicate flags mirror real Talaria shapes.
   - `ValueError` and `ObservationConflict` map to stable no-traceback errors.
   - Operational merge/degrade, shared cache/lease, vendor backoff, selector owner resolution, and render/spill footer behavior stay covered.
2. Watch regression suite:
   - Registration writes config/wrapper and validates threshold, selector owner, and owner freshness floor.
   - Evaluation covers transition-only alerts/recovery, degraded scoped owners, metrics owner degradation, missing config cleanup, atomic singleflight, stalled tripwire, and prior-breached degraded/bridge-unavailable silence.
3. Strict skill lint:
   - Frontmatter uses block-form `requires:` and contains no operative harness-specific tool names.
4. Non-gating live smoke:
   - `talaria_read.py doctor` should be green against the local Talaria checkout when available.

## Test command

```console
${HERMES_PYTHON:-python} -m unittest discover -s tests -p 'test_talaria*.py' -v
${HERMES_PYTHON:-python} lint.py --strict skills/talaria/SKILL.md
${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py doctor
```

If inherited Python variables break the shell on Windows, run the same commands with env scrubbing:

```console
env -u PYTHONHOME -u PYTHONPATH -u UV_INTERNAL__PYTHONHOME ${HERMES_PYTHON:-python} -m unittest discover -s tests -p 'test_talaria*.py' -v
env -u PYTHONHOME -u PYTHONPATH -u UV_INTERNAL__PYTHONHOME ${HERMES_PYTHON:-python} lint.py --strict skills/talaria/SKILL.md
env -u PYTHONHOME -u PYTHONPATH -u UV_INTERNAL__PYTHONHOME ${HERMES_PYTHON:-python} skills/talaria/scripts/talaria_read.py doctor
```

## Done-when

- `skills/talaria/SKILL.md` passes `lint.py --strict` with zero errors and zero warnings for this file.
- `tests/test_talaria_bridge.py` lives at the vigil-skills repo root under `tests/`, not inside the skill directory, so `sync.py` does not mirror the tests into operators' skill installs.
- Unittest discovery for `test_talaria*.py` is green.
- Doctor smoke is green or, if the local Talaria checkout/dependencies are unavailable, the failure is reported as an environment blocker rather than treated as pass.
- The documented invariant remains true: agent writes are forbidden except approved `ack_observation` and `kanban_triage` proposal/action paths.
