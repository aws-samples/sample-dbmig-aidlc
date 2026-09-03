"""Classify a DMS SC object as ACCEPT / VERIFY / MANUAL.

Precedence (highest first):

1. **MANUAL** — any action item that requires human rewriting: its catalog
   ``actionItem`` text matches a manual-work keyword (``manual``/``manually``/``revise
   your code``/``perform a manual``/``create a user-defined``), or it is a CRITICAL/HIGH
   severity item. These must be (re)converted.
2. **VERIFY** — otherwise, the object carries a GenAI-generated span, or an ML/
   probabilistic action item (topic mentions a language/ML model, or the ``actionItem``
   asks to *review* the converted code), or any remaining action item. Keep the DMS SC
   output but prove it with equivalence tests.
3. **ACCEPT** — no action items and no GenAI span. Keep the DMS SC output as-is.

The keyword/severity policy is centralized here so it can be tuned without touching the
parser or command.
"""
from __future__ import annotations

from typing import Iterable

from .model import ActionItem, DmsScObject

ACCEPT = "accept"
VERIFY = "verify"
MANUAL = "manual"

MANUAL_SEVERITIES = {"CRITICAL", "HIGH"}
# True "you must rewrite this by hand" instructions. Deliberately narrow: a LOW-severity
# advisory such as "review the converted code and set the time zone manually where
# necessary" is a VERIFY, not a MANUAL rewrite — so generic words like "manually" or
# "revise" are NOT in this list. MANUAL is driven primarily by severity (CRITICAL/HIGH).
_MANUAL_KEYWORDS = (
    "convert your source code manually",
    "perform a manual conversion",
    "convert your database connection manually",
    "method stub",
)
_VERIFY_KEYWORDS = ("review", "machine learning", "verify", "check", "evaluation")
_VERIFY_TOPIC_HINTS = ("LANGUAGE MODEL", "MACHINE LEARNING", "LLM", "GENAI", "GEN AI")


def _text(ai: ActionItem) -> str:
    return f"{ai.action} {ai.message}".lower()


def is_manual(ai: ActionItem) -> bool:
    if (ai.severity or "").upper() in MANUAL_SEVERITIES:
        return True
    return any(k in _text(ai) for k in _MANUAL_KEYWORDS)


def is_verify(ai: ActionItem) -> bool:
    topic = (ai.topic or "").upper()
    if any(h in topic for h in _VERIFY_TOPIC_HINTS):
        return True
    return any(k in _text(ai) for k in _VERIFY_KEYWORDS)


def classify(obj: DmsScObject) -> str:
    """Return ACCEPT / VERIFY / MANUAL and set ``obj.disposition``."""
    items: Iterable[ActionItem] = obj.action_items or ()
    disp = ACCEPT
    if any(is_manual(ai) for ai in items):
        disp = MANUAL
    elif obj.has_genai or any(is_verify(ai) for ai in items) or bool(obj.action_items):
        disp = VERIFY
    obj.disposition = disp
    return disp
