import argparse

from .build_claude import build_claude


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="psai",
        description="Build tooling for the gc-data-explorer Agent Plugins 1.0 package.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "build-claude",
        help="Generate a Claude Code plugin in dist/claude/ from the Agent Plugins 1.0 source.",
    )
    args = parser.parse_args()

    if args.command == "build-claude":
        out = build_claude()
        print(f"Claude Code plugin generated at {out}")
        print("Load it with: claude --plugin-dir " + str(out))
