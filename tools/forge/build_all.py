#!/usr/bin/env python3
"""build_all.py - run every tools/forge/pieces/*.py builder and write contract-v1 GLBs to public/models/.

    python3 tools/forge/build_all.py                      # build every piece that has a script
    python3 tools/forge/build_all.py --only emberhold_pawn,rime_pawn
    python3 tools/forge/build_all.py --no-validate        # skip scripts/validate_glb.py

A piece script `tools/forge/pieces/{asset_id}.py` must expose
    build() -> (piece_glb_bytes, fragments_glb_bytes, stats_dict)
Assets without a script keep whatever file is already in public/models (the placeholders from
scripts/make_placeholder_glbs.py); this tool never deletes or regenerates them.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
PIECES = os.path.join(HERE, "pieces")
OUT = os.path.join(REPO, "public", "models")
VALIDATOR = os.path.join(REPO, "scripts", "validate_glb.py")


def discover():
    return sorted(f[:-3] for f in os.listdir(PIECES) if f.endswith(".py") and not f.startswith("_"))


def load(asset_id):
    spec = importlib.util.spec_from_file_location(f"forge_piece_{asset_id}", os.path.join(PIECES, asset_id + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma separated asset ids (default: all pieces with a script)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--no-validate", action="store_true")
    ap.add_argument("--stage", default="final", choices=("blockout", "final"))
    a = ap.parse_args(argv)

    available = discover()
    ids = [s.strip() for s in a.only.split(",")] if a.only else available
    bad = [i for i in ids if i not in available]
    if bad:
        print(f"no builder script for: {', '.join(bad)}  (available: {', '.join(available) or 'none'})")
        return 2
    os.makedirs(a.out, exist_ok=True)
    written, failed = [], []
    for asset_id in ids:
        t0 = time.time()
        print(f"[forge] building {asset_id} ...")
        try:
            glb, frag, stats = load(asset_id).build()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            failed.append(asset_id)
            continue
        for suffix, data in (("", glb), ("_fragments", frag)):
            path = os.path.join(a.out, f"{asset_id}{suffix}.glb")
            with open(path, "wb") as fh:
                fh.write(data)
            written.append(path)
        print(f"[forge] {asset_id}: {stats}  ({time.time() - t0:.1f}s)")
    rc = 1 if failed else 0
    if not a.no_validate and written:
        for path in written:
            r = subprocess.run([sys.executable, VALIDATOR, path, "--stage", a.stage], capture_output=True, text=True)
            lines = [l for l in r.stdout.splitlines() if l.strip() and "warning texture" not in l and "passed" not in l]
            print("\n".join(lines))
            rc = rc or r.returncode
    skipped = [f"{f}_{r}" for f in ("emberhold", "rime") for r in ("pawn", "rook", "knight", "bishop", "queen", "king") if f"{f}_{r}" not in available]
    if skipped and not a.only:
        print(f"[forge] no script yet (existing files kept): {', '.join(skipped)}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
