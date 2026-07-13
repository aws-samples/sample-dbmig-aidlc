"""``dbmig test-connection`` — verify source/target connectivity via adapters."""
from __future__ import annotations

from .. import config, console, engines
from ..connections import load_pair


def run(args) -> int:
    try:
        pair = load_pair()
    except config.ConfigError as exc:
        console.err(str(exc))
        return 2

    sides = ["source", "target"] if args.side == "both" else [args.side]
    rc = 0
    for side in sides:
        if side not in pair:
            console.err(f"{side}: not defined in the connections file")
            rc = 1
            continue
        console.info(f"Testing {side.upper()}: {pair[side].safe()}")
        try:
            eng = (engines.get_source_engine(pair) if side == "source"
                   else engines.get_target_engine(pair))
        except config.ConfigError as exc:
            console.err(f"{side}: {exc}")
            rc = 1
            continue
        try:
            if eng.ping():
                console.ok(f"{side}: connected — {eng.server_version()}")
            else:
                console.err(f"{side}: ping query did not return expected value")
                rc = 1
        except Exception as exc:  # noqa: BLE001
            console.err(f"{side}: connection/query failed: {exc}")
            rc = 1
        finally:
            eng.close()

    if rc == 0:
        console.ok("Connectivity OK.")
    else:
        console.err("Connectivity check failed.")
    return rc
