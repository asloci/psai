import argparse

from .build_claude import build_claude, install_vibe


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="psai",
        description="Build tooling for the gc-data-explorer Agent Plugins 1.0 package.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "build-claude",
        help="Generate a Claude Code plugin in dist/claude/ from the plugin/ source.",
    )
    sub.add_parser(
        "install-vibe",
        help="Install the plugin/ package into ~/.vibe/plugins/ for Mistral Vibe.",
    )
    args = parser.parse_args()

    if args.command == "build-claude":
        out = build_claude()
        print(f"Claude Code plugin generated at {out}")
        print("Load it with: claude --plugin-dir " + str(out))
    elif args.command == "install-vibe":
        dest = install_vibe()
        print(f"Installed to {dest}")
        print("Run /reload inside Vibe to pick it up.")
