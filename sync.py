#!/usr/bin/env python3
"""sync.py - Vigil Skills cross-machine sync.

Mirrors skills/ and agents/ between this repo and your local Claude Code config dir.

Usage:
    python sync.py install [--dry-run] [--verbose] [--prune]
    python sync.py pull    (alias for install)
    python sync.py push    [--dry-run] [--verbose]
    python sync.py status

Path resolution for the Claude config dir:
    1. --claude-dir <path> if given
    2. $CLAUDE_CONFIG_DIR if set
    3. ~/.claude (default)

Stdlib only - no pip install required. Cross-platform via pathlib.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SUBTREES = ("skills", "agents")  # dirs in repo that mirror to ~/.claude/


def resolve_claude_dir(override):
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".claude").resolve()


def iter_files(root):
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file():
            yield p.relative_to(root)


def file_state(src, dst):
    src_exists = src is not None and src.exists()
    dst_exists = dst is not None and dst.exists()
    if not src_exists and not dst_exists:
        return "missing"
    if src_exists and not dst_exists:
        return "src-only"
    if not src_exists and dst_exists:
        return "dst-only"
    return "same" if filecmp.cmp(src, dst, shallow=False) else "differ"


def cmd_install(args, claude_dir):
    """Repo -> Claude. Mirror skills/ and agents/ from this repo into the local config dir."""
    actions = []
    for subtree in SUBTREES:
        src_root = REPO_ROOT / subtree
        dst_root = claude_dir / subtree
        if not src_root.exists():
            continue
        src_files = set(iter_files(src_root))
        dst_files = set(iter_files(dst_root))
        for rel in sorted(src_files):
            src = src_root / rel
            dst = dst_root / rel
            state = file_state(src, dst)
            if state == "same":
                if args.verbose:
                    print(f"  [skip ] {subtree}/{rel}  (in sync)")
                continue
            actions.append(("write", src, dst, f"{subtree}/{rel}", state))
        if args.prune:
            for rel in sorted(dst_files - src_files):
                dst = dst_root / rel
                actions.append(("delete", None, dst, f"{subtree}/{rel}", "dst-only"))

    if not actions:
        print("No changes - repo and Claude dir are in sync.")
        return

    for verb, src, dst, label, state in actions:
        if verb == "write":
            tag = "[WRITE]" if not args.dry_run else "[WRITE/dry]"
            print(f"  {tag} {label}  ({state})")
            if not args.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        elif verb == "delete":
            tag = "[DELETE]" if not args.dry_run else "[DELETE/dry]"
            print(f"  {tag} {label}")
            if not args.dry_run:
                dst.unlink()

    print()
    if args.dry_run:
        print(f"Dry run - {len(actions)} action(s) would be applied.")
    else:
        print(f"{len(actions)} action(s) applied.")


def cmd_push(args, claude_dir):
    """Claude -> Repo. Push edits made in the local config dir back into the repo.

    Only files already tracked in the repo (i.e., present in the repo before push)
    are touched. Untracked third-party skills in your local config dir are NOT
    auto-imported into this repo.
    """
    actions = []
    for subtree in SUBTREES:
        src_root = claude_dir / subtree
        dst_root = REPO_ROOT / subtree
        if not src_root.exists() or not dst_root.exists():
            continue
        for rel in sorted(iter_files(dst_root)):
            src = src_root / rel
            dst = dst_root / rel
            state = file_state(src, dst)
            if state == "same":
                if args.verbose:
                    print(f"  [skip ] {subtree}/{rel}  (in sync)")
                continue
            if state == "src-only":
                if args.verbose:
                    print(f"  [skip ] {subtree}/{rel}  (missing locally; run install)")
                continue
            actions.append(("write", src, dst, f"{subtree}/{rel}", state))

    if not actions:
        print("No changes - Claude dir matches repo for tracked files.")
        return

    for verb, src, dst, label, state in actions:
        tag = "[PUSH]" if not args.dry_run else "[PUSH/dry]"
        print(f"  {tag} {label}  ({state})")
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    print()
    if args.dry_run:
        print(f"Dry run - {len(actions)} action(s) would be applied.")
    else:
        print(f"{len(actions)} action(s) applied. Don't forget to commit.")


def cmd_status(args, claude_dir):
    """Show diff between repo and local Claude dir for tracked subtrees."""
    any_diff = False
    for subtree in SUBTREES:
        src_root = REPO_ROOT / subtree
        dst_root = claude_dir / subtree
        src_files = set(iter_files(src_root)) if src_root.exists() else set()
        dst_files = set(iter_files(dst_root)) if dst_root.exists() else set()
        all_files = sorted(src_files | dst_files)
        for rel in all_files:
            src = src_root / rel if rel in src_files else None
            dst = dst_root / rel if rel in dst_files else None
            state = file_state(src, dst)
            if state == "same":
                continue
            any_diff = True
            print(f"  [{state:>9}] {subtree}/{rel}")
    if not any_diff:
        print("In sync.")


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--claude-dir",
        help="Override Claude config dir (default: $CLAUDE_CONFIG_DIR or ~/.claude)",
    )

    parser = argparse.ArgumentParser(
        description="Sync Vigil Skills between this repo and your Claude Code config dir.",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_install = sub.add_parser(
        "install",
        aliases=["pull"],
        help="Copy from repo into Claude dir.",
        parents=[common],
    )
    p_install.add_argument("--dry-run", action="store_true")
    p_install.add_argument("--verbose", action="store_true")
    p_install.add_argument(
        "--prune",
        action="store_true",
        help="Delete files in Claude dir that aren't in the repo. Off by default.",
    )
    p_install.set_defaults(func=cmd_install)

    p_push = sub.add_parser(
        "push",
        help="Copy tracked-file edits from Claude dir back into repo.",
        parents=[common],
    )
    p_push.add_argument("--dry-run", action="store_true")
    p_push.add_argument("--verbose", action="store_true")
    p_push.set_defaults(func=cmd_push)

    p_status = sub.add_parser(
        "status",
        help="Show diff between repo and Claude dir.",
        parents=[common],
    )
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    claude_dir = resolve_claude_dir(args.claude_dir)
    args.func(args, claude_dir)


if __name__ == "__main__":
    main()
