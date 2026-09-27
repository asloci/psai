"""Generate a Claude Code plugin from the Agent Plugins 1.0 source."""

import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_claude() -> Path:
    """Translate the root Agent Plugins 1.0 manifest into a Claude Code
    plugin under dist/claude/<name>/ and copy the skills tree.

    The output is a self-contained plugin: .claude-plugin/plugin.json,
    .claude-plugin/marketplace.json, and skills/.
    """
    src_manifest = json.loads((REPO_ROOT / "plugin.json").read_text(encoding="utf-8"))
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

    shutil.copytree(REPO_ROOT / "skills", out / "skills")
    return out
