"""``dbmig status`` — compact progress view of a run (built for large schemas).

On a schema with hundreds or thousands of objects the manifests are large (a
1,000-unit manifest is ~150 KB), and reading them to find "what's next" costs the
AI assistant far more tokens than the work itself. This command prints a
fixed-size summary instead: unit counts by status per phase, and the next few
prompt files still pending (deduplicated — a batch prompt covers several units).

    ./dbmig status --schema APP --project P                 # all phases
    ./dbmig status --schema APP --project P --phase code --next 5
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Dict, List

import yaml

from .. import config, console

_PHASES = {
    "schema": ("02-construction", "manifest", "status", "converted"),
    "code": ("02-construction", "code-manifest", "status", "converted"),
    "tests": ("03-validation", "test-manifest", "status", "generated"),
}
_TODO = {"pending", "failed"}
_CITATION = re.compile(r"[\w-]+-playbook/references/[\w./-]+?\.md")


def playbook_citations(log_path: Path) -> Counter:
    """Count playbook topic files cited in the conversion log (traceability check:
    the construction skill requires a citation for every detected construct)."""
    try:
        text = log_path.read_text()
    except OSError:
        return Counter()
    return Counter(_CITATION.findall(text))


def summarize(units: List[dict], status_field: str = "status") -> Dict[str, int]:
    return dict(Counter(str(u.get(status_field) or "pending") for u in units))


def next_prompts(units: List[dict], n: int) -> List[dict]:
    """First ``n`` distinct prompt files that still have a pending/failed unit."""
    out: List[dict] = []
    seen = set()
    for u in units:
        if str(u.get("status") or "pending") not in _TODO:
            continue
        pf = u.get("retry_prompt") if u.get("status") == "failed" else u.get("prompt_file")
        if not pf or pf in seen:
            continue
        seen.add(pf)
        names = [x["name"] for x in units if x.get("prompt_file") == u.get("prompt_file")
                 and str(x.get("status") or "pending") in _TODO]
        out.append({"prompt": pf, "units": names})
        if len(out) >= n:
            break
    return out


def run(args) -> int:
    wanted = [args.phase] if getattr(args, "phase", None) else list(_PHASES)
    root = config.workspace_dir(args.project)
    any_found = False
    for ph in wanted:
        sub, base, field, done = _PHASES[ph]
        ws = root / sub
        path = config.resolve_manifest(ws, base, args.schema)
        if not path.exists():
            console.info(f"{ph:<6} no manifest yet ({path.name})")
            continue
        any_found = True
        units = (yaml.safe_load(path.read_text()) or {}).get("units") or []
        counts = summarize(units, field)
        line = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        prompts = len({u.get("prompt_file") for u in units})
        console.heading(f"{ph}: {len(units)} unit(s) in {prompts} prompt(s) — {line}")
        if ph == "schema":
            post = summarize([u for u in units if u.get("status") == "applied"],
                             "post_status")
            if post:
                console.info("post-data (FK/triggers): " +
                             ", ".join(f"{k}={v}" for k, v in sorted(post.items())))
        nxt = next_prompts(units, int(getattr(args, "next", 3) or 3))
        for p in nxt:
            shown = ", ".join(p["units"][:6]) + (" …" if len(p["units"]) > 6 else "")
            print(f"  next: {sub}/{p['prompt']}  ({len(p['units'])} unit(s): {shown})")
        if not nxt:
            console.ok(f"nothing pending in {ph} (all {done} or beyond)")
    log = root / "02-construction" / "conversion-log.md"
    if log.exists():
        cited = playbook_citations(log)
        if cited:
            top = ", ".join(f"{Path(k).stem} ({v})" for k, v in cited.most_common(5))
            console.info(f"playbook topics cited in conversion-log.md: {len(cited)} "
                         f"distinct — {top}")
        else:
            console.warn("conversion-log.md cites no playbook topic file — cite the file "
                         "named in each detected-construct hint (traceability)")
    return 0 if any_found else 2
