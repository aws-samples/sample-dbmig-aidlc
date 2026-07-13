"""LLM client abstraction.

The LLM is **Kiro itself**. The Python package does not call any hosted LLM API
(no Bedrock / Anthropic). Instead, the ``kiro`` provider runs in *hand-off* mode:
``convert-schema`` / ``convert-code`` write prompt bundles to the workspace and
mark each unit ``pending`` in the manifest. The Kiro ``db-migration-construction``
skill then reads each prompt, produces PostgreSQL DDL, writes it to the unit's
output ``.sql`` file, and marks it ``converted``. ``apply-schema`` applies them.

This keeps the package runnable standalone while letting Kiro be the converter.
A different backend (e.g. a hosted API) could be added by implementing another
``LLMClient`` subclass and selecting it via ``llm.provider`` in
``migration-config.yaml`` — but no such backend ships by default.
"""
from __future__ import annotations

from typing import Any, Dict


class LLMClient:
    """Base class. ``convert`` returns DDL text, or raises HandoffRequired."""

    provider = "base"

    def convert(self, prompt: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class HandoffRequired(Exception):
    """Raised by hand-off providers: conversion is performed by Kiro, not here."""


class KiroHandoffClient(LLMClient):
    """Default provider. Conversion is performed by the Kiro construction skill.

    The client itself does not generate DDL; it signals that the caller should
    persist the prompt bundle for Kiro to convert.
    """

    provider = "kiro"

    def convert(self, prompt: str) -> str:
        raise HandoffRequired(
            "provider 'kiro': conversion is performed by the Kiro "
            "db-migration-construction skill from the written prompt bundle")


def make_client(llm_cfg: Dict[str, Any]) -> LLMClient:
    provider = (llm_cfg.get("provider") or "kiro").strip().lower()
    if provider in ("kiro", "manual", "handoff"):
        return KiroHandoffClient()
    raise ValueError(
        f"unsupported llm.provider '{provider}'. This build ships the 'kiro' "
        "hand-off provider only (conversion is done by Kiro). To add a hosted "
        "backend, implement an LLMClient subclass in conversion/llm_client.py.")
