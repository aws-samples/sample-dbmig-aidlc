# dbmig-aidlc — instructions for Claude Code

This repository's AI-assistant rules are shared with Kiro and live in one file, imported
here so there is a single source of truth:

@.kiro/steering/dbmig-aidlc.md

Notes for Claude Code:

- The framework's skills are available as Claude Code skills via `.claude/skills/` (thin
  pointers generated from the canonical `skills/` folder by `scripts/sync-claude-skills.py`).
  Invoke them by name (e.g. `db-migration-orchestrator`); each pointer tells you to load the
  full `skills/<name>/SKILL.md`.
- Wherever the skills or docs say **"Kiro"** performs a step (schema/code conversion,
  equivalence-test generation), that means **you, the AI assistant** in this session.
- Start Claude Code from this folder (the repository root). Check `/memory` (or `/context`)
  shows this `CLAUDE.md` and the imported steering file.
