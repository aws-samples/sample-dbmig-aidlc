"""``migrations/<project>/project.yaml`` — gate records, decisions and policies.

- Load as a plain dict and update keys in place; never rebuild the file from a fixed
  schema, so keys added by hand or by a newer version survive a save.
- Timestamps stay strings. PyYAML would turn an unquoted ISO timestamp into a
  ``datetime``; :class:`_Loader` disables that resolver.
- ``migration-config.yaml`` stays the only settings source. This file records only
  what the gates need: entry path, pair, schemas in scope, strategy mode.

Recording who approved a gate is bookkeeping, not authentication: ``by`` comes from
``--approved-by``, else ``git config user.name``, else ``$USER``.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess  # nosec B404 - fixed argv, no shell
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from . import config

FILE = "project.yaml"
PHASES = ("intake", "inception", "construction", "validation", "operations", "cutover",
          "app-intake", "app-inception", "app-construction", "app-validation", "app-operations")
GATED_PHASES = ("inception", "construction", "validation", "operations")
# Optional application modernization module (05-application/): its own four gates,
# recorded only once the module has started (05-application/00-intake/app-intake.md).
APP_GATED_PHASES = ("app-inception", "app-construction", "app-validation", "app-operations")
ALL_GATED_PHASES = GATED_PHASES + APP_GATED_PHASES
APP_DIR = "05-application"
APP_INTAKE = "05-application/00-intake/app-intake.md"
VIA = ("cli", "chat", "questionnaire")

PHASE_TITLES = {
    "intake": "Intake",
    "inception": "Inception — Assessment & Planning",
    "construction": "Construction — Conversion",
    "validation": "Validation & Testing",
    "operations": "Operations & Cutover Planning",
    "cutover": "Cutover",
    "app-intake": "Application — Intake",
    "app-inception": "Application — Assessment & Change Plan",
    "app-construction": "Application — Conversion",
    "app-validation": "Application — Build & Test",
    "app-operations": "Application — Cutover Plan",
}
GATE_QUESTIONS = {
    "inception": "Approve the assessment & migration plan?",
    "construction": "Approve the converted schema + code?",
    "validation": "Approve the equivalence test results?",
    "operations": "Approve the cutover & rollback plan?",
    "app-inception": "Approve the application assessment & change plan?",
    "app-construction": "Approve the converted application?",
    "app-validation": "Approve the application validation results?",
    "app-operations": "Approve the application cutover plan?",
}


def gate_group(phase: str) -> tuple:
    """The ordered gates ``phase`` belongs to (database or application)."""
    return APP_GATED_PHASES if phase in APP_GATED_PHASES else GATED_PHASES

_HEADER = ("# dbmig project file. Gate records and decisions are written by `./dbmig gate`\n"
           "# and `./dbmig decision`; do not approve by hand-editing. Settings live in\n"
           "# migration-config.yaml.\n")


class ProjectError(Exception):
    pass


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps timestamps as strings (YAML 1.2 behaviour, as Studio)."""


_Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path) -> Any:
    """Load YAML with timestamps kept as strings."""
    return yaml.load(path.read_text(), Loader=_Loader)  # nosec B506 - SafeLoader subclass


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def whoami(explicit: Optional[str] = None) -> str:
    """Name recorded on a gate or decision (not authentication)."""
    if explicit and explicit.strip():
        return explicit.strip()
    try:
        out = subprocess.run(["git", "config", "user.name"], capture_output=True,  # nosec B603 B607
                             text=True, timeout=5, check=False).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.SubprocessError):
        pass
    return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def resolve_dir(args) -> Path:
    """Project folder: ``--dir`` (any folder, e.g. a sample run) else
    ``migrations/<--project>``."""
    d = getattr(args, "dir", None)
    if d:
        return Path(d).expanduser().resolve()
    return config.workspace_dir(getattr(args, "project", None) or "default")


def _blank_gate() -> Dict[str, Any]:
    return {"status": "open", "history": []}


def _discover_schemas(ws: Path) -> List[str]:
    out: List[str] = []
    for sub, rx in (("01-assessment", r"^inventory-(.+)\.yaml$"),
                    ("01-assessment", r"^dms-sc-map-(.+)\.json$"),
                    ("02-construction", r"^(?:code-)?manifest-(.+)\.yaml$")):
        d = ws / sub
        if d.is_dir():
            for f in sorted(d.iterdir()):
                m = re.match(rx, f.name)
                if m and m.group(1) not in out:
                    out.append(m.group(1))
    return out


def _local_config(ws: Path) -> Dict[str, Any]:
    """migration-config for this folder: the sample's ``sample_migration-config.yaml``
    when present, else the active ``migration-config.yaml``."""
    for c in (ws / "sample_migration-config.yaml", ws / "migration-config.yaml"):
        if c.exists():
            data = load_yaml(c) or {}
            return data if isinstance(data, dict) else {}
    try:
        return config.load_migration_config()
    except config.ConfigError:
        return {}


def _local_pair(ws: Path) -> str:
    c = ws / "sample_connections.yaml"
    if c.exists():
        raw = load_yaml(c) or {}
        src = config.normalize_engine((raw.get("source") or {}).get("engine")) or "oracle"
        tgt = config.normalize_engine((raw.get("target") or {}).get("engine")) or "postgresql"
        return f"{src}-to-{tgt}"
    return config.active_pair()


def propose(ws: Path, name: str) -> Dict[str, Any]:
    """A new project.yaml for folder ``ws`` (new or with existing artifacts)."""
    cfg = _local_config(ws)
    scope = cfg.get("scope") or {}
    schemas = [str(s).upper() for s in (scope.get("schemas") or [])]
    for s in _discover_schemas(ws):
        if s not in schemas:
            schemas.append(s)
    dms = any((ws / "01-assessment").glob("dms-sc-map-*.json")) \
        if (ws / "01-assessment").is_dir() else False
    # Settings (scope details, strategy, data load, llm) stay in migration-config.yaml;
    # only what the gate logic needs is recorded here.
    return {
        "version": 1,
        "project": name,
        "createdAt": now(),
        "entryPath": "dms-sc" if dms else "fresh",
        "pair": _local_pair(ws),
        "schemas": schemas,
        "strategy": str((cfg.get("strategy") or {}).get("mode") or "full"),
        "gates": {p: _blank_gate() for p in GATED_PHASES},
        "decisions": [],
    }


class Project:
    """A loaded project.yaml. ``data`` is a plain dict; unknown keys are kept."""

    def __init__(self, ws: Path, data: Dict[str, Any]) -> None:
        self.dir = Path(ws)
        self.data = data
        self._normalize()

    # ---- paths ---------------------------------------------------------
    @property
    def file(self) -> Path:
        return self.dir / FILE

    @property
    def name(self) -> str:
        return str(self.data.get("project") or self.dir.name)

    def path(self, *rel: str) -> Path:
        return self.dir.joinpath(*rel)

    # ---- accessors -----------------------------------------------------
    @property
    def schemas(self) -> List[str]:
        return [str(s) for s in (self.data.get("schemas") or [])]

    @property
    def entry_path(self) -> str:
        return str(self.data.get("entryPath") or "fresh")

    @property
    def strategy_mode(self) -> str:
        return str(self.data.get("strategy") or "full")

    @property
    def app_active(self) -> bool:
        """The application module has started: its intake exists or a gate was recorded."""
        gates = self.data.get("gates") or {}
        return (self.dir / APP_INTAKE).exists() or any(
            isinstance(gates.get(p), dict) and gates[p].get("history") for p in APP_GATED_PHASES)

    @property
    def gated_phases(self) -> tuple:
        """Database gates, plus the application gates once that module has started."""
        return ALL_GATED_PHASES if self.app_active else GATED_PHASES

    def gate(self, phase: str) -> Dict[str, Any]:
        if phase not in ALL_GATED_PHASES:
            raise ProjectError(f"not a gated phase: {phase} (one of {', '.join(ALL_GATED_PHASES)})")
        g = self.data["gates"].get(phase)
        if not isinstance(g, dict):
            g = self.data["gates"][phase] = _blank_gate()
        g.setdefault("status", "open")
        if not isinstance(g.get("history"), list):
            g["history"] = []
        return g

    @property
    def app(self) -> Dict[str, Any]:
        """Application module answers: ``intake`` and ``policies`` (app questionnaire)."""
        a = self.data.get("app")
        if not isinstance(a, dict):
            a = self.data["app"] = {}
        return a

    @property
    def decisions(self) -> List[Dict[str, Any]]:
        return self.data["decisions"]

    @property
    def policies(self) -> Dict[str, Any]:
        return self.data.setdefault("policies", {})

    def _normalize(self) -> None:
        d = self.data
        d.setdefault("version", 1)
        d.setdefault("project", self.dir.name)
        gates = d.setdefault("gates", {})
        if not isinstance(gates, dict):
            gates = d["gates"] = {}
        for p in GATED_PHASES + (APP_GATED_PHASES if (self.dir / APP_INTAKE).exists() else ()):
            g = gates.setdefault(p, _blank_gate())
            if not isinstance(g, dict):
                g = gates[p] = _blank_gate()
            g.setdefault("status", "open")
            if not isinstance(g.get("history"), list):
                g["history"] = []
        if not isinstance(d.get("decisions"), list):
            d["decisions"] = []

    # ---- io ------------------------------------------------------------
    def reload(self) -> None:
        self.data = load_yaml(self.file) or {}
        self._normalize()

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        body = _HEADER + yaml.safe_dump(self.data, sort_keys=False, allow_unicode=True,
                                        width=100)
        fd, tmp = tempfile.mkstemp(prefix=".project.", suffix=".yaml", dir=self.dir)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(body)
            os.replace(tmp, self.file)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise


def exists(ws: Path) -> bool:
    return (Path(ws) / FILE).exists()


def load(ws: Path, *, create: bool = True, name: Optional[str] = None) -> Project:
    """Load ``ws/project.yaml``; create it (lazily) from the folder's artifacts and
    migration-config when missing and ``create`` is set."""
    ws = Path(ws)
    f = ws / FILE
    if f.exists():
        data = load_yaml(f) or {}
        if not isinstance(data, dict):
            raise ProjectError(f"{f}: expected a YAML mapping")
        return Project(ws, data)
    if not create:
        raise ProjectError(f"no {FILE} in {ws} (run ./dbmig project init)")
    p = Project(ws, propose(ws, name or ws.name))
    p.save()
    return p
