#!/usr/bin/env python3
"""lint.py - Vigil Skills portability lint.

Enforces the portability contract (docs/portability-contract.md):
  R1 - validates the `requires:` capability declaration (contract §3).
  R2 - flags operative harness-specific tool calls in skill bodies (contract §4).

Stdlib only - no pip install required. Cross-platform via pathlib.

Severity:
  ERROR - blocking-eligible: an operative bare harness-tool call, or a
          malformed `requires:` block.
  WARN  - advisory: a missing `requires:` block (incl. frontmatter-less/empty).

Exit behavior:
  python lint.py            -> always exits 0 (warn-only); prints findings.
  python lint.py --strict   -> exits 1 if any ERROR (WARNs never affect exit).
Both modes print a summary to stderr: `lint: <E> error(s), <W> warning(s)`.

Usage:
    python lint.py [paths...] [--strict]
    # with no paths, lints skills/*/SKILL.md relative to the repo root.

Documented v1 limitations (complemented by CodeRabbit's qualitative review):
  1. Bare-name detection deferred - only `mcp__*` identifiers are flagged, not
     ordinary tool names like Read/Edit/Bash.
  2. Operative-imperative-under-a-notes-heading not detected - the heading
     presumption is applied flat (contract §4 says such a call is still case 1).
  3. Case-2 window is +/-1 non-blank line - an operative call adjacent to an
     unrelated tagged sentence could be wrongly exempted (deliberate tradeoff
     vs false-positives on wrapped tags).
  The lint additionally rejects tab indentation in `requires:` for determinism
  (slightly stricter than contract §3's written letter).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# --- Controlled vocabulary (contract §3) ---
REQUIRES_KEYS = {"shell", "filesystem", "network", "subagents", "services"}
BOOL_KEYS = {"shell", "network", "subagents"}
FILESYSTEM_VOCAB = {"read", "write"}
SERVICES_VOCAB = {"issue-tracker", "shared-memory", "code-review-bot", "vcs-host"}

ERROR = "ERROR"
WARN = "WARN"

# A Finding is a tuple: (severity, rule, file, line, message)

_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
_MCP_RE = re.compile(r"mcp__\w+")
_NOTES_HEADING_RE = re.compile(r"^(tool-use (notes|rules)|tools available)$", re.IGNORECASE)
_HEADING_STRIP_RE = re.compile(r"^#{1,6}\s*")
_REQUIRES_LINE_RE = re.compile(r"^(\s*)requires:(.*)$")
_CASE2_TAG = "or the equivalent"


def _read_lines(path):
    """Read a file as UTF-8, strip a leading BOM, split lines (CRLF/CR/LF safe).
    Returns a list of lines, or None if the file cannot be read."""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return None
    text = raw.decode("utf-8", errors="replace")
    if text.startswith("﻿"):
        text = text[1:]
    return text.splitlines()


def _strip_comment(s):
    """Strip a trailing comment: a '#' preceded by whitespace (or at column 0)
    begins a comment. Controlled-vocabulary values never contain '#'."""
    for idx, ch in enumerate(s):
        if ch == "#" and (idx == 0 or s[idx - 1] in " \t"):
            return s[:idx]
    return s


def _find_frontmatter(lines):
    """Locate the YAML frontmatter block.

    The opening '---' must be the first non-empty line; the closing '---' is the
    next such line. Returns (content_start, content_end) as a half-open range of
    line indices for the block's *content*, or (None, None) when there is no
    well-formed frontmatter (no opening, or no closing delimiter)."""
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return (None, None)
    for j in range(i + 1, len(lines)):
        if lines[j].strip() == "---":
            return (i + 1, j)
    return (None, None)


def _validate_requires_value(key, val, fname, lineno):
    findings = []
    if key in BOOL_KEYS:
        if val.lower() not in ("true", "false"):
            findings.append((ERROR, "requires-malformed", fname, lineno,
                             f"{key} must be true/false, got: {val!r}"))
        return findings
    # filesystem / services: a single-line flow sequence
    if val.startswith("{"):
        findings.append((ERROR, "requires-malformed", fname, lineno,
                         f"{key}: nested mapping not allowed"))
        return findings
    if not (val.startswith("[") and val.endswith("]")):
        findings.append((ERROR, "requires-malformed", fname, lineno,
                         f"{key} must be a flow sequence [...]: {val!r}"))
        return findings
    inner = val[1:-1]
    trimmed = [e.strip() for e in inner.split(",")]
    non_empty = [e for e in trimmed if e]
    if not non_empty:
        return findings  # [], [ ] -> none, clean
    if len(non_empty) != len(trimmed):
        findings.append((ERROR, "requires-malformed", fname, lineno,
                         f"{key}: empty/trailing element in {val!r}"))
        return findings
    for e in non_empty:
        if '"' in e or "'" in e:
            findings.append((ERROR, "requires-malformed", fname, lineno,
                             f"{key}: quoted scalar not allowed: {e!r}"))
            continue
        if key == "filesystem":
            if e not in FILESYSTEM_VOCAB:
                findings.append((ERROR, "requires-malformed", fname, lineno,
                                 f"filesystem: invalid mode {e!r} (allowed: read, write; no '?')"))
        else:  # services
            tok = e[:-1] if e.endswith("?") else e
            if tok not in SERVICES_VOCAB:
                findings.append((ERROR, "requires-malformed", fname, lineno,
                                 f"services: invalid role {tok!r}"))
    return findings


def _lint_requires(lines, fm_start, fm_end, fname):
    """R1 - validate the `requires:` declaration within the frontmatter range."""
    req_idx = None
    req_indent = 0
    req_val = ""
    for i in range(fm_start, fm_end):
        m = _REQUIRES_LINE_RE.match(lines[i])
        if m:
            req_idx = i
            req_indent = len(m.group(1))
            req_val = _strip_comment(m.group(2)).strip()
            break
    if req_idx is None:
        return [(WARN, "missing-requires", fname, 1, "no requires: declaration")]

    # Inline value on the `requires:` line.
    if req_val:
        if req_val in ("[]", "{}", "[ ]", "{ }"):
            return []  # present but empty -> clean (no capabilities)
        if req_val.startswith("{"):
            return [(ERROR, "requires-malformed", fname, req_idx + 1,
                     "inline nested mapping not allowed")]
        return [(ERROR, "requires-malformed", fname, req_idx + 1,
                 f"inline requires value not allowed: {req_val!r}")]

    # Block form: collect contiguous more-indented child lines.
    findings = []
    for j in range(req_idx + 1, fm_end):
        raw = lines[j]
        if raw.strip() == "":
            continue  # blank line - skipped, not a terminator
        no_comment = _strip_comment(raw)
        if no_comment.strip() == "":
            continue  # comment-only line - skipped
        lead = raw[:len(raw) - len(raw.lstrip())]
        if len(lead) <= req_indent:
            break  # dedent -> block ended
        if "\t" in lead:
            findings.append((ERROR, "requires-malformed", fname, j + 1,
                             "tab indentation not allowed"))
            continue
        content = no_comment.strip()
        if ":" not in content:
            findings.append((ERROR, "requires-malformed", fname, j + 1,
                             f"expected 'key: value': {content!r}"))
            continue
        key, _, val = content.partition(":")
        key = key.strip()
        val = val.strip()
        if key not in REQUIRES_KEYS:
            findings.append((ERROR, "requires-unknown-key", fname, j + 1,
                             f"unknown key under requires: {key!r}"))
            continue
        findings.extend(_validate_requires_value(key, val, fname, j + 1))
    return findings


def _lint_intent(lines, body_start, fname):
    """R2 - flag operative harness-specific (`mcp__*`) tool calls in the body."""
    findings = []
    in_fence = False
    cur_heading = ""
    n = len(lines)
    for i in range(body_start, n):
        line = lines[i]
        stripped = line.lstrip()
        if _FENCE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            continue  # case 3: inside a fenced code block -> allowed
        if stripped.startswith("#"):
            cur_heading = _HEADING_STRIP_RE.sub("", stripped).strip().lower()
            continue
        m = _MCP_RE.search(line)
        if not m:
            continue
        # case 3: non-operative notes/reference heading -> allowed
        if _NOTES_HEADING_RE.match(cur_heading):
            continue
        # case 2: +/-1 non-blank-line window contains the "or the equivalent" tag
        window = line
        for k in range(i - 1, body_start - 1, -1):
            if lines[k].strip() != "":
                window += " " + lines[k]
                break
        for k in range(i + 1, n):
            if lines[k].strip() != "":
                window += " " + lines[k]
                break
        if _CASE2_TAG in window.lower():
            continue  # case 2: tagged illustrative example -> allowed
        # case 1: operative bare harness-tool call -> ERROR
        findings.append((ERROR, "operative-tool-call", fname, i + 1,
                         f"harness-specific tool name as operative instruction: {m.group(0)}"))
    return findings


def lint_path(path):
    """Lint one SKILL.md. Total: never raises; returns a list of Findings."""
    lines = _read_lines(path)
    fname = str(path)
    if lines is None:
        return [(WARN, "unreadable", fname, 0, "could not read file")]
    fm_start, fm_end = _find_frontmatter(lines)
    if fm_start is None:
        # No well-formed frontmatter -> missing declaration; scan whole file body.
        findings = [(WARN, "missing-requires", fname, 1,
                     "no frontmatter / no requires: declaration")]
        findings.extend(_lint_intent(lines, 0, fname))
        return findings
    findings = _lint_requires(lines, fm_start, fm_end, fname)
    findings.extend(_lint_intent(lines, fm_end + 1, fname))
    return findings


def lint_paths(paths):
    """Aggregate findings across paths. Pure aggregation: [] -> [] (no globbing)."""
    findings = []
    for p in paths:
        findings.extend(lint_path(p))
    return findings


def main(argv):
    strict = "--strict" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        skill_files = sorted((REPO_ROOT / "skills").glob("*/SKILL.md"))
        paths = [str(p) for p in skill_files]
        if not paths:
            print("lint: no skills found to lint (resolved an empty path set)",
                  file=sys.stderr)
    findings = lint_paths(paths)

    by_file = {}
    for f in findings:
        by_file.setdefault(f[2], []).append(f)
    for fname in sorted(by_file):
        print(f"{fname}:")
        for sev, rule, _, lineno, msg in by_file[fname]:
            print(f"  {sev} [{rule}] line {lineno}: {msg}")

    n_err = sum(1 for f in findings if f[0] == ERROR)
    n_warn = sum(1 for f in findings if f[0] == WARN)
    print(f"lint: {n_err} error(s), {n_warn} warning(s)", file=sys.stderr)
    return 1 if (strict and n_err > 0) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
