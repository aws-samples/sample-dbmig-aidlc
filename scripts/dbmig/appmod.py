"""Application modernization module: backup before the first edit.

Two backup modes, recorded in ``05-application/00-intake/backup.yaml``:

- ``git``: the application's own git history is the backup. Used only when it is
  safe: git is installed, the app is in a repository with a commit, and the
  in-scope files have no uncommitted changes. The base commit is recorded;
  rollback is ``git restore --source <commit>``. In-scope files that git ignores
  (local config, for example) cannot be restored from git, so they are copied.
- ``file-copy``: the in-scope tree is copied once into
  ``05-application/backup/<timestamp>/`` (mirrored paths, timestamps and modes kept).

``auto`` (the default) picks ``git`` when possible. When ``git`` is asked for but is
not possible, the backup falls back to ``file-copy`` so no file is ever edited
without a backup. Backups are never written inside the application directory.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
import shutil
import subprocess  # nosec B404 - fixed argv lists, no shell
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .project import APP_DIR, load_yaml, now

BACKUP_RECORD = f"{APP_DIR}/00-intake/backup.yaml"
MODES = ("auto", "git", "file-copy")
# build output, dependencies, tool state: never part of a backup
EXCLUDE_DIRS = {".git", "target", "build", "bin", "obj", "node_modules", "dist", "out",
                ".gradle", ".idea", ".vs", ".vscode", "__pycache__", ".venv", "venv",
                ".mvn", ".next", ".nuxt", "coverage", ".pytest_cache", ".tox"}


class BackupError(Exception):
    pass


def _git(app: Path, *args: str, binary: bool = False) -> Tuple[int, Any]:
    try:
        p = subprocess.run(["git", "-C", str(app), *args], capture_output=True,  # nosec B603 B607
                           timeout=120, check=False, text=not binary)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return p.returncode, p.stdout


def _pathspec(scope: List[str]) -> List[str]:
    return ["--", *scope] if scope else ["--", "."]


def _excluded(rel: str) -> bool:
    return any(part in EXCLUDE_DIRS for part in Path(rel).parts[:-1])


def detect_git(app: Path, scope: List[str]) -> Dict[str, Any]:
    """Whether git can be the backup for ``scope`` of ``app``.
    Returns ``{"possible": bool, "reason": str, ...commit/branch/toplevel/ignored}``."""
    if not shutil.which("git"):
        return {"possible": False, "reason": "git is not installed"}
    rc, top = _git(app, "rev-parse", "--show-toplevel")
    if rc != 0:
        return {"possible": False, "reason": "the application is not in a git repository"}
    rc, commit = _git(app, "rev-parse", "--verify", "HEAD")
    if rc != 0:
        return {"possible": False, "reason": "the git repository has no commit yet"}
    rc, dirty = _git(app, "status", "--porcelain", "--untracked-files=all", *_pathspec(scope))
    if rc != 0:
        return {"possible": False, "reason": "git status failed"}
    changed = [ln for ln in dirty.splitlines() if ln.strip()]
    if changed:
        return {"possible": False,
                "reason": f"{len(changed)} in-scope file(s) have uncommitted changes "
                          "(commit or stash them to use git as the backup)",
                "uncommitted": [ln[3:] for ln in changed[:20]]}
    _, branch = _git(app, "rev-parse", "--abbrev-ref", "HEAD")
    rc, ign = _git(app, "ls-files", "--others", "--ignored", "--exclude-standard",
                   *_pathspec(scope))
    ignored = [f for f in (ign.splitlines() if rc == 0 else []) if f and not _excluded(f)]
    return {"possible": True, "reason": "clean git working tree", "commit": commit.strip(),
            "branch": branch.strip(), "toplevel": top.strip(), "ignored": ignored}


def choose_mode(requested: str, git: Dict[str, Any]) -> Tuple[str, str]:
    """(mode, reason). Never returns ``git`` when git is not possible."""
    if requested not in MODES:
        raise BackupError(f"--mode must be one of {', '.join(MODES)}")
    if requested == "file-copy":
        return "file-copy", "file copy requested"
    if git.get("possible"):
        return "git", ("git requested" if requested == "git" else "the application is in git") \
            + f"; base commit {git['commit'][:12]}"
    why = git.get("reason") or "git is not available"
    if requested == "git":
        return "file-copy", f"git was requested but cannot be used ({why}); falling back to a " \
                            "file copy so no file is edited without a backup"
    return "file-copy", f"git cannot be used ({why})"


def _files(app: Path, scope: List[str]) -> List[str]:
    roots = [app / s for s in scope] if scope else [app]
    out: List[str] = []
    for r in roots:
        if r.is_file():
            out.append(str(r.relative_to(app)))
            continue
        if not r.is_dir():
            raise BackupError(f"scope entry not found: {r}")
        for dirpath, dirnames, filenames in os.walk(r):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
            for f in sorted(filenames):
                p = Path(dirpath) / f
                if p.is_file() and not p.is_symlink():
                    out.append(str(p.relative_to(app)))
    return out


def copy_files(app: Path, dest: Path, rels: List[str]) -> int:
    n = 0
    for rel in rels:
        src = app / rel
        if not src.is_file():
            continue
        tgt = dest / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)
        n += 1
    return n


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def read_record(ws: Path) -> Optional[Dict[str, Any]]:
    f = Path(ws) / BACKUP_RECORD
    if not f.exists():
        return None
    try:
        d = load_yaml(f) or {}
    except Exception:  # noqa: BLE001
        return None
    return d if isinstance(d, dict) else None


def _manifest(rec: Dict[str, Any], copied: int) -> str:
    app = rec["app_dir"]
    lines = [f"# Application backup — {rec['created_at']}", "",
             "<!-- written by ./dbmig app-backup; append each edited file to the table below -->", "",
             f"- Mode: **{rec['mode']}** ({rec['reason']})", f"- Application: `{app}`",
             f"- Scope: {', '.join(f'`{s}`' for s in rec.get('scope') or []) or 'whole application'}"]
    if rec["mode"] == "git":
        g = rec["git"]
        lines += [f"- Base commit: `{g['commit']}` on `{g.get('branch')}`",
                  f"- Files copied (git-ignored in-scope files git cannot restore): {copied}", "",
                  "Restore one file: `git -C <app> restore --source <commit> -- <path>`. "
                  "See every change: `git -C <app> diff <commit>`.",
                  "New files added by the conversion are not removed by restore; delete them "
                  "by hand if you roll back."]
    else:
        lines += [f"- Files copied: {copied}", "",
                  "Restore everything: `cp -Rp <this folder>/. <app>/` (remove MANIFEST.md "
                  "afterwards). Compare: `diff -r <this folder> <app>`."]
    lines += ["", "## Edited files", "", "| File | Bytes | Why it changed |", "|---|---|---|", ""]
    return "\n".join(lines)


def make_backup(ws: Path, app: Path, *, requested: str = "auto",
                scope: Optional[List[str]] = None, by: str = "") -> Dict[str, Any]:
    """Create the backup and its record. Returns the record."""
    ws, app = Path(ws).resolve(), Path(app).expanduser().resolve()
    scope = [s.strip().strip("/") for s in (scope or []) if s.strip()]
    if not app.is_dir():
        raise BackupError(f"application directory not found: {app}")
    if _inside(ws, app):
        raise BackupError("the migration workspace is inside the application directory; "
                          "backups must not be written inside the application")
    git = detect_git(app, scope)
    mode, reason = choose_mode(requested, git)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = ws / APP_DIR / "backup" / stamp
    if dest.exists():
        raise BackupError(f"{dest} already exists; wait a second and retry")
    dest.mkdir(parents=True)
    rels = git.get("ignored", []) if mode == "git" else _files(app, scope)
    copied = copy_files(app, dest, rels)
    rec: Dict[str, Any] = {
        "mode": mode, "requested": requested, "reason": reason, "app_dir": str(app),
        "scope": scope, "backup_dir": str(dest.relative_to(ws)), "files_copied": copied,
        "created_at": now(), "by": by,
    }
    if mode == "git":
        rec["git"] = {k: git[k] for k in ("commit", "branch", "toplevel")}
        rec["git"]["ignored_copied"] = copied
    elif git.get("reason"):
        rec["git_unavailable"] = git["reason"]
    (dest / "MANIFEST.md").write_text(_manifest(rec, copied))
    f = ws / BACKUP_RECORD
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("# written by ./dbmig app-backup; the backup of the application before the "
                 "first edit\n" + yaml.safe_dump(rec, sort_keys=False))
    return rec


def git_change_digest(rec: Dict[str, Any]) -> Optional[str]:
    """sha256 of the application's changes since the base commit (tracked diff plus
    untracked in-scope files), for the app-construction gate fingerprint."""
    if (rec or {}).get("mode") != "git":
        return None
    app, commit = Path(rec["app_dir"]), (rec.get("git") or {}).get("commit")
    if not commit or not app.is_dir():
        return None
    spec = _pathspec(list(rec.get("scope") or []))
    rc, diff = _git(app, "diff", "--binary", commit, *spec, binary=True)
    if rc != 0:
        return None
    h = hashlib.sha256(diff if isinstance(diff, bytes) else b"")
    rc, new = _git(app, "ls-files", "--others", "--exclude-standard", *spec)
    for rel in sorted(new.splitlines() if rc == 0 else []):
        p = app / rel
        if p.is_file() and not _excluded(rel):
            h.update(rel.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()
