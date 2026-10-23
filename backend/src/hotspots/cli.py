"""Command-line entry point."""

from __future__ import annotations

import argparse

from hotspots import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hotspots", description="Volcano Watch pipeline")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("fetch", help="fetch upstream data into the cache")
    sub.add_parser("process", help="associate, score and build markers")
    sub.add_parser("render", help="render the world map")
    sub.add_parser("run", help="full pipeline")
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0
    raise NotImplementedError(f"'{args.command}' is not implemented yet")


if __name__ == "__main__":
    raise SystemExit(main())
