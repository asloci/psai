# Government of Canada Data Explorer

An [Agent Plugins 1.0](https://agent-plugins.org) package for exploring
Canadian open data portals in place with [DuckDB](https://duckdb.org) —
browse catalog metadata, then query chosen tabular resources directly over
https, with no downloads and no ingestion pipeline.

Status: work in progress. One skill is shipped and its patterns are verified
against the live catalog; more portals are coming (see Roadmap).

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

### Mistral Vibe

Current Vibe versions pin user plugins but do not yet register their skills
with the model's skill tool, so install the skills loose (the route that
works today) and optionally pin the plugin for when support lands:

```
uv run psai install-skills          # skills -> ~/.agents/skills/ (usable now)
uv run psai install-skills --project  # or .agents/skills/ inside this repo
uv run psai install-vibe           # plugin -> ~/.vibe/plugins/ (pinned)
```

Then `/reload` (or restart Vibe). The skill appears as `/open-canada-catalog`
when installed loose, or `gc_data_explorer:open-canada-catalog` once plugin
skill registration is supported.

### Other Agent Plugins 1.0 clients (Codex, Cursor, Copilot, VS Code)

Copy or point the client at the `plugin/` directory.

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

## Platform support and prerequisites

The skills run inside an agentic coding tool on a **desktop OS — macOS,
Windows, or Linux — with the DuckDB CLI installed.** They do not run on
mobile devices (iOS/Android): there is no agent runtime and no DuckDB CLI
there. A phone can read this repo, but it cannot execute the skills.

- DuckDB CLI (`duckdb --version`): `brew install duckdb` (macOS),
  `winget install DuckDB.cli` (Windows), or the single-file download from
  duckdb.org (Linux). One static binary — no server, no account.
- `httpfs` extension: recent DuckDB auto-installs and auto-loads it on the
  first https read; manual fallback is `INSTALL httpfs; LOAD httpfs;`.
- [uv](https://docs.astral.sh/uv/) — only for this repo's tooling
  (`build-claude`, `install-skills`), not for using the skills themselves.

## How a question becomes SQL, then facts

A skill is instructions, not code. When you ask a question:

1. The agent loads `SKILL.md` — a briefing on the portal's API endpoints,
   response shapes, and DuckDB idioms.
2. The agent composes SQL from those documented patterns (model-authored;
   there are no fixed query templates) and runs it locally. DuckDB with
   httpfs fetches the JSON/CSV over https; the catalog's API does the
   counting server-side.
3. The raw tables come back as tool output, and the agent writes the prose
   answer around them.

Reproducibility: the **facts are deterministic** — counts come from the
catalog API, so any correct query path converges on the same numbers for the
same point in time (the catalog itself changes daily). The **SQL text and
prose are not**: another user, agent, or model should reach the same facts
by a different route, with different queries and different wording. The
skill constrains the approach (metadata-only discovery, no downloads, query
in place with DuckDB), not the literal SQL.
