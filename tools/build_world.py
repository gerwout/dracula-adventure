"""Regenerate engine/data/world.json from an original DRACULA.TXT.

The original 1982 data file is NOT shipped in this repository. Point --txt at your own
copy of DRACULA.TXT to (re)produce the committed world data. At runtime the engine reads
ONLY engine/data/world.json (UTF-8); it never touches the original file.

Usage:
    python tools/build_world.py --txt path/to/DRACULA.TXT
    python tools/build_world.py                 # tries ../original/DRACULA.TXT
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.data.loader import load   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TXT = ROOT / "original" / "DRACULA.TXT"
DEFAULT_OUT = ROOT / "engine" / "data" / "world.json"


def build(txt: Path, out: Path) -> dict:
    data = txt.read_bytes()
    world = load(data)                       # load() never applies corrections
    payload = {
        "meta": {
            "schema": 1,
            "source": "DRACULA.TXT",
            "source_length": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
        **world.to_dict(),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build engine/data/world.json from DRACULA.TXT")
    ap.add_argument("--txt", type=Path, default=DEFAULT_TXT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    if not args.txt.exists():
        ap.error(f"DRACULA.TXT not found at {args.txt} — pass --txt <path to your copy>")
    p = build(args.txt, args.out)
    print(f"wrote {args.out} — {p['meta']['source_length']} source bytes, "
          f"{len(p['rooms'])} rooms, {len(p['messages'])} messages, "
          f"{len(p['objects'])} objects")


if __name__ == "__main__":
    main()
