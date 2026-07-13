"""``dbmig inventory`` — assess a source schema; write structured reports."""
from __future__ import annotations

import json

import yaml

from .. import config, console, engines
from ..connections import load_pair


def run(args) -> int:
    try:
        pair = load_pair()
        source = engines.get_source_engine(pair)
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    console.info(f"Inventorying schema {args.schema} ...")
    try:
        data = source.inventory(args.schema)
    except Exception as exc:  # noqa: BLE001
        console.err(f"inventory failed: {exc}")
        return 1
    finally:
        source.close()

    outdir = config.workspace_dir(args.project) / "01-assessment"
    outdir.mkdir(parents=True, exist_ok=True)
    # Schema-scope the filename so a multi-schema project doesn't overwrite an
    # earlier schema's inventory (matches the manifest-<SCHEMA>.yaml convention).
    inv_yaml = config.manifest_file("inventory", args.schema)      # inventory-<SCHEMA>.yaml
    inv_json = inv_yaml[:-5] + ".json"
    (outdir / inv_yaml).write_text(yaml.safe_dump(data, sort_keys=False))
    (outdir / inv_json).write_text(json.dumps(data, indent=2))

    counts = data.get("object_counts", {})
    tables = data.get("tables", [])
    console.heading(f"Inventory — {data.get('schema')}")
    for otype, n in counts.items():
        print(f"  {otype:<24} {n}")
    print(f"  {'TABLES (detail)':<24} {len(tables)}")
    if data.get("datatypes"):
        console.info("Datatypes in use: " +
                     ", ".join(f"{k}({v})" for k, v in data["datatypes"].items()))
    deps = data.get("cross_schema_dependencies") or []
    if deps:
        total = sum(len(d.get("edges", [])) for d in deps)
        console.info(f"Cross-schema dependencies ({total} reference(s) to "
                     f"{len(deps)} other schema(s)) — confirm these are in migration scope:")
        for d in deps:
            print(f"  -> {d['referenced_schema']:<18} {len(d['edges'])} reference(s)")
    console.ok(f"Inventory written to {outdir}/{inv_yaml} (+ .json)")
    return 0
