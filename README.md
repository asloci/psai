# Government of Canada Data Explorer

An [Agent Plugins 1.0](https://agent-plugins.org) package for exploring
Canadian open data portals in place with [DuckDB](https://duckdb.org) —
browse catalog metadata, then query chosen tabular resources directly over
https, with no downloads and no ingestion pipeline.

The repository is a monorepo for the competition solution; the plugin itself
is self-contained under `plugin/`:

```
psai/
├── plugin/                  # the Agent Plugins 1.0 package (this README's subject)
│   ├── plugin.json          # manifest — the only source of truth
│   └── skills/              # one directory per portal skill
│       └── open-canada-catalog/SKILL.md
├── src/psai/                # Python tooling: build/install commands
└── dist/                    # generated output (gitignored)
```

New portal skills are added as `plugin/skills/<portal-slug>/SKILL.md`. The
layout is inspired by [duckdb-skills](https://github.com/duckdb/duckdb-skills),
re-packaged on the cross-agent plugin standard so any compatible client
(Vibe, Codex, Cursor, GitHub Copilot, VS Code, ...) loads the same folder.

## Install

### Agent Plugins 1.0 clients (Vibe, Codex, Cursor, Copilot, VS Code)

For Mistral Vibe (user scope), from this repo:

```
uv run psai install-vibe
```

This copies `plugin/` to `~/.vibe/plugins/gc-data-explorer/`; then `/reload`
inside Vibe. Skills appear as `gc-data-explorer:<skill-name>`. For other
clients, copy or point them at the `plugin/` directory.

### Claude Code

Claude Code keeps its own plugin format. Generate it from this source:

```
uv run psai build-claude
```

This writes a self-contained plugin (with its own marketplace manifest) to
`dist/claude/gc-data-explorer/`. Load it locally:

```
claude --plugin-dir dist/claude/gc-data-explorer
```

To distribute to Claude Code users, publish the generated folder (a branch,
release artifact, or separate repo) and they can add it as a marketplace.

## Skills

### `open-canada-catalog`
Browse and search the Open Canada (CKAN) catalog at
https://open.canada.ca via its GET-only Action API, then query a chosen CSV
resource in place with DuckDB.

```
/gc-data-explorer:open-canada-catalog what datasets exist about public service employee surveys?
/gc-data-explorer:open-canada-catalog list CSV resources from tbs-sct updated in the last year
```

## How the skills work together

Every skill in this package follows the same three-step flow: **discover**
(catalog/API metadata only) → **retrieve** (query the API response in place)
→ **query** (query a chosen resource in place, no ingest). Skills that need a
step beyond DuckDB's direct reach (ZIP, XLSX) say so and hand off to a small
download step or the `convert-file` skill.

## Conventions shared by all skills

- Bilingual metadata: CKAN-family portals expose `*_translated.en/fr` fields;
  present English by default, offer French.
- Encoding guardrails: government CSVs may be UTF-8 with BOM or Latin-1;
  sniff before bulk reads.
- Cheap first touch: `DESCRIBE` or `LIMIT` before any unbounded `SELECT *` on a
  remote file.
- Sentinel values (e.g. `9999` for "no data") must be nulled before analysis.
- Citations: dataset title, department, dataset ID / portal URL, and the exact
  resource URL the numbers came from.

## Roadmap

- `open-canada-catalog` — Open Canada (CKAN) — shipped
- StatCan tables and zipped CSV releases
- Provincial portals (Ontario, Quebec, BC) — also CKAN-family, same API shape
- Proactive disclosure / contracting datasets

## Prerequisites

DuckDB CLI must be installed (`duckdb --version`). Remote reads need the
`httpfs` extension (`INSTALL httpfs; LOAD httpfs;`). The build tooling
requires [uv](https://docs.astral.sh/uv/).
