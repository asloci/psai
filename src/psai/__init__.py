import argparse

from .plugin_tools import build_claude, install_skills, install_vibe


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
        help="Install the plugin/ package into ~/.vibe/plugins/ (pinned, not yet usable everywhere).",
    )
    p_install = sub.add_parser(
        "install-skills",
        help="Install the plugin skills as loose skills into ~/.agents/skills/ (usable now).",
    )
    p_install.add_argument(
        "--project",
        action="store_true",
        help="Install into .agents/skills/ in this repo instead of the user directory.",
    )
    args = parser.parse_args()

    if args.command == "build-claude":
        out = build_claude()
        print(f"Claude Code plugin generated at {out}")
        print("Load it with: claude --plugin-dir " + str(out))
    elif args.command == "install-vibe":
        dest = install_vibe()
        print(f"Installed to {dest}")
        print("Plugins are pinned at session start; restart Vibe to pick it up.")
    elif args.command == "install-skills":
        installed = install_skills(project=args.project)
        for dest in installed:
            print(f"Installed {dest.name} -> {dest}")
        print("Run /reload inside Vibe (or restart) to pick them up.")
