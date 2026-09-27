"""Build and install tooling for the gc-data-explorer Agent Plugins 1.0 package."""

import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugin"
VIBE_PLUGINS_DIR = Path.home() / ".vibe" / "plugins"


def _load_manifest() -> dict:
    return json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))


def build_claude() -> Path:
    """Translate the Agent Plugins 1.0 package into a Claude Code plugin
    under dist/claude/<name>/ and copy the skills tree.

    The output is a self-contained plugin: .claude-plugin/plugin.json,
    .claude-plugin/marketplace.json, and skills/.
    """
    src_manifest = _load_manifest()
    name = src_manifest["name"]
    author = src_manifest.get("author", {})

    out = REPO_ROOT / "dist" / "claude" / name
    if out.exists():
        shutil.rmtree(out)
    (out / ".claude-plugin").mkdir(parents=True)

    # Claude's manifest is the same document minus the $schema key.
    claude_plugin = {k: v for k, v in src_manifest.items() if k != "$schema"}
    (out / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(claude_plugin, indent=2) + "\n", encoding="utf-8"
    )

    marketplace = {
        "name": name,
        "owner": {"name": author.get("name", name), "url": author.get("url", "")},
        "plugins": [
            {
                "name": name,
                "source": "./",
                "description": src_manifest.get("description", ""),
                "version": src_manifest.get("version", "0.0.0"),
                "license": src_manifest.get("license", "MIT"),
                "keywords": src_manifest.get("keywords", []),
            }
        ],
    }
    (out / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(marketplace, indent=2) + "\n", encoding="utf-8"
    )

    shutil.copytree(PLUGIN_ROOT / "skills", out / "skills")
    return out


def install_vibe() -> Path:
    """Copy the plugin package into ~/.vibe/plugins/<name>/ for Mistral Vibe.

    Vibe pins user plugins at session start; plugin skill registration is not
    served by all runtime versions yet — use install_skills() for immediate
    usability.
    """
    name = _load_manifest()["name"]
    dest = VIBE_PLUGINS_DIR / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(PLUGIN_ROOT, dest)
    return dest


def install_skills(project: bool = False) -> list[Path]:
    """Copy each skill from plugin/skills/ into a loose skills directory.

    User scope: ~/.agents/skills/ (available everywhere).
    Project scope: .agents/skills/ in this repo (available when the repo is
    opened in a trusted folder).
    """
    skills_src = PLUGIN_ROOT / "skills"
    dest_root = (REPO_ROOT / ".agents" / "skills") if project else (Path.home() / ".agents" / "skills")
    installed = []
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        dest = dest_root / skill_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)
        installed.append(dest)
    return installed
