"""``dbmig app-backup`` — back up the application before the first edit.

    ./dbmig app-backup --project P --app DIR [--mode auto|git|file-copy] [--scope src,pom.xml]
    ./dbmig app-backup --project P            # show the recorded backup

``auto`` uses git when the app is in a git repository with a commit and no
uncommitted in-scope changes, else a file copy. ``git`` falls back to a file copy
when git cannot be used, so no file is edited without a backup. The record is
``05-application/00-intake/backup.yaml``; copies go to ``05-application/backup/<ts>/``.
"""
from __future__ import annotations

import json

from .. import appmod, config, console, gates
from ..project import exists, load, resolve_dir, whoami


def _show(rec: dict) -> None:
    console.info(f"mode: {rec.get('mode')} — {rec.get('reason')}")
    console.info(f"app: {rec.get('app_dir')}  scope: {', '.join(rec.get('scope') or []) or 'all'}")
    if rec.get("mode") == "git":
        g = rec.get("git") or {}
        console.info(f"base commit: {g.get('commit')} ({g.get('branch')}); git-ignored files "
                     f"copied: {g.get('ignored_copied', 0)}")
    console.info(f"backup folder: {rec.get('backup_dir')} ({rec.get('files_copied', 0)} file(s))")


def _precheck(ws) -> int:
    try:
        enforce = bool((config.load_migration_config().get("run") or {}).get("enforce_gates", False))
    except config.ConfigError:
        enforce = False
    if not exists(ws):
        msg = "gate 'app-inception' has no record yet (no project.yaml)"
    else:
        st = gates.status(load(ws, create=False), "app-inception")
        msg = None if st == "approved" else \
            f"gate 'app-inception' is {st}; application files are edited only after the change " \
            "plan is approved"
    if not msg:
        return 0
    if enforce:
        console.err(f"refused: {msg} (run.enforce_gates is true). See ./dbmig gate status")
        return 2
    console.warn(f"{msg} — see ./dbmig gate status")
    return 0


def run(args) -> int:
    ws = resolve_dir(args)
    rec = appmod.read_record(ws)
    if rec and not args.force:
        if args.json:
            print(json.dumps(rec, indent=2))
            return 0
        console.heading(f"Application backup — {ws.name} (already recorded; --force for a new one)")
        _show(rec)
        return 0
    if not args.app:
        if rec is None:
            console.err("no backup recorded yet: give --app <application directory>")
            return 2
    rc = _precheck(ws)
    if rc:
        return rc
    app = args.app or rec["app_dir"]
    scope = [s for s in (args.scope or "").split(",") if s.strip()] or (rec or {}).get("scope") or []
    try:
        new = appmod.make_backup(ws, app, requested=args.mode, scope=scope, by=whoami())
    except appmod.BackupError as exc:
        console.err(str(exc))
        return 1
    if args.json:
        print(json.dumps(new, indent=2))
        return 0
    if new["mode"] == "file-copy" and args.mode == "git":
        console.warn(new["reason"])
    console.ok(f"application backup recorded in {appmod.BACKUP_RECORD}")
    _show(new)
    return 0
