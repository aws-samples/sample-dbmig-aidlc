"""Shared conversion-manifest I/O.

A *manifest* is the YAML file that tracks each conversion unit's status
(pending/converted/applied/needs_human, prompt/output file paths, retries).
Several commands read and write it (``convert-schema``, ``convert-code``,
``apply-schema``, ``gen-tests``), so the load/write helpers live here rather than
in one command module that the others reach into — keeping the command layer free
of command->command imports.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def write_manifest(path: Path, manifest: dict) -> None:
    """Persist a manifest as YAML, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(manifest, sort_keys=False))


def load_manifest(path: Path) -> dict:
    """Load a manifest (empty dict if the file is empty)."""
    return yaml.safe_load(path.read_text()) or {}
