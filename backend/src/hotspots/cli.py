"""Command-line entry point.

    hotspots run --out site                     full pipeline → site/ (what CI runs)
    hotspots run --out site --firms-csv f.csv --as-of 2026-10-23T12:00Z   offline replay
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from hotspots import __version__
from hotspots.config import data_dir, firms_map_key, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hotspots", description="Volcano Watch pipeline")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="fetch, process and render the site")
    run_p.add_argument("--out", type=Path, default=Path("site"), help="output directory")
    run_p.add_argument("--config", type=Path, help="config TOML (default: config/defaults.toml)")
    run_p.add_argument("--previous-url", help="published site to reuse the catalogue from")
    run_p.add_argument("--firms-csv", type=Path, help="use a local FIRMS CSV instead of downloading")
    run_p.add_argument("--as-of", help="evaluation time, ISO 8601 (default: now)")
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    from hotspots import pipeline

    cfg = load_config(args.config)
    as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")).astimezone(timezone.utc) if args.as_of else None
    try:
        pipeline.run(cfg, args.out, data_dir(), map_key=firms_map_key(), previous_url=args.previous_url,
                     as_of=as_of, firms_csv=args.firms_csv,
                     log=lambda msg: print(msg, file=sys.stderr))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
