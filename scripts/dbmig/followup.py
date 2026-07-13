"""Run modes and the follow-up log.

Run modes control what happens on a **conversion failure** or a **test comparison
failure**:

- ``silent`` (default): record the failure to the project's follow-up log and
  **continue** — never block. A human resolves the logged items later.
- ``interactive``: also prompt for input/correction (when a TTY is available),
  and surface unresolved failures via a non-zero exit so they are addressed now.

The follow-up log lives at ``migrations/<project>/follow-up.yaml`` (machine
readable) with a human-readable ``follow-up.md`` mirror.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from . import config, console

SILENT = "silent"
INTERACTIVE = "interactive"
_VALID = {SILENT, INTERACTIVE}


def resolve_mode(args=None, mig_cfg: Optional[Dict[str, Any]] = None) -> str:
    """Precedence: --mode flag > DBMIG_MODE env > config run.mode > silent."""
    if args is not None and getattr(args, "mode", None):
        m = str(args.mode).strip().lower()
        return m if m in _VALID else SILENT
    env = os.environ.get("DBMIG_MODE")
    if env:
        m = env.strip().lower()
        return m if m in _VALID else SILENT
    if mig_cfg is None:
        try:
            mig_cfg = config.load_migration_config()
        except Exception:
            mig_cfg = {}
    run = (mig_cfg.get("run") or {}) if isinstance(mig_cfg, dict) else {}
    m = str(run.get("mode") or SILENT).strip().lower()
    return m if m in _VALID else SILENT


class FollowUp:
    """Append-only log of items a human should follow up on later."""

    def __init__(self, project: str) -> None:
        self.project = project
        self.dir = config.workspace_dir(project)
        self.path = self.dir / "follow-up.yaml"
        self.md = self.dir / "follow-up.md"

    def _load(self) -> List[Dict[str, Any]]:
        if self.path.exists():
            data = yaml.safe_load(self.path.read_text()) or {}
            return data.get("items", []) if isinstance(data, dict) else []
        return []

    def record(self, phase: str, kind: str, obj: str, detail: str,
               extra: Optional[Dict[str, Any]] = None) -> None:
        items = self._load()
        entry: Dict[str, Any] = {
            "ts": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "phase": phase,
            "kind": kind,
            "object": obj,
            "detail": detail,
            "status": "open",
        }
        if extra:
            entry.update(extra)
        items.append(entry)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump({"project": self.project, "items": items}, sort_keys=False))
        self._render_md(items)

    def _render_md(self, items: List[Dict[str, Any]]) -> None:
        open_n = sum(1 for i in items if i.get("status") == "open")
        lines = [
            f"# Follow-up items — {self.project}",
            "",
            f"{open_n} open item(s). Recorded by dbmig (silent mode does not block "
            "the run); resolve these manually, then set `status: done` in "
            "`follow-up.yaml`.",
            "",
            "| When (UTC) | Phase | Kind | Object | Detail | Status |",
            "|---|---|---|---|---|---|",
        ]
        for i in items:
            detail = str(i.get("detail", "")).replace("\n", " ").replace("|", "\\|")
            if len(detail) > 200:
                detail = detail[:200] + "…"
            lines.append(
                f"| {i.get('ts')} | {i.get('phase')} | {i.get('kind')} | "
                f"{i.get('object')} | {detail} | {i.get('status')} |")
        self.md.write_text("\n".join(lines) + "\n")

    def open_count(self) -> int:
        return sum(1 for i in self._load() if i.get("status") == "open")


def handle_failure(mode: str, followup: "FollowUp", *, phase: str, kind: str,
                   obj: str, detail: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Record a failure and decide the next action.

    Always logs to the follow-up file. Returns ``"abort"`` only when the user, in
    interactive mode on a TTY, chooses to abort; otherwise ``"continue"`` (silent
    mode never blocks).
    """
    followup.record(phase, kind, obj, detail, extra)
    if mode == INTERACTIVE and sys.stdin.isatty():
        console.err(f"{kind} — {obj}: {detail}")
        try:
            ans = input("  Action — [s]kip & log for follow-up / [a]bort run? [s]: ")
        except EOFError:
            ans = "s"
        if ans.strip().lower().startswith("a"):
            return "abort"
    return "continue"
