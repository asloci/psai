# Government of Canada Data Explorer

Natural-language front desk for Government of Canada data. Two agent skills
let you browse catalog metadata live — what datasets, cubes, and resources
exist — and query anything DuckDB-readable in place over https: no
downloads, no ingestion pipeline, no API keys. Resources that cannot be
queried in place (ZIP, XLSX, PDF, SHP) are stated as such rather than
approximated.

- `open-canada-catalog` — the Open Canada (CKAN) catalog: search ~48,000
  datasets across 350+ departments, then query chosen CSV/JSON resources
  in place.
- `statcan-wds` — Statistics Canada's Web Data Service: browse the full
  cube inventory, fetch time-series points by coordinate or vector ID,
  and get full-table CSV download URLs for ingestion.

## Quickstart — Claude Code

Prerequisites: git, [uv](https://docs.astral.sh/uv/), and the DuckDB CLI
(it carries the httpfs extension needed for in-place queries).

    brew install uv duckdb
    git clone https://github.com/asloci/psai.git && cd psai
    uv run psai build-claude
    claude --plugin-dir dist/claude/gc-data-explorer

Then invoke the skills with `/open-canada-catalog` and `/statcan-wds`.

- Claude Code loads the plugin per-session via `--plugin-dir`; see the
  `marketplace.json` in `dist/` to install it persistently.
- Claude Work (the web client) cannot mount a local plugin directory —
  use Claude Code on your machine.
- `curl` ships with macOS. `jq` (used in some example commands) does not;
  `brew install jq` is optional.

## Quickstart — Agent-skills users (Vibe, and any agent that discovers `.agents/skills/`)

Prerequisites: git and the DuckDB CLI. No build step and no uv required.

    brew install duckdb
    git clone https://github.com/asloci/psai.git && cd psai

- Project-scoped (Vibe): open the cloned repo and accept the trust
  prompt. The committed `.agents/skills/` directory is discovered
  automatically — `/open-canada-catalog` and `/statcan-wds` work
  immediately.
- Global (any agent reading `~/.agents/skills/`): copy the skills once:

      cp -R plugin/skills/statcan-wds plugin/skills/open-canada-catalog ~/.agents/skills/

  They are then available in every project. Run `/reload` (Vibe) if a
  session is already running.

## Roadmap

- Add more per-department skills for portals with APIs (provincial CKAN
  portals, other departments).
- Create an all-encompassing front-desk skill that routes to the
  per-department skills.
- That front-desk skill will offer a catalog of what is actually
  available for over-the-wire analytics — so users never ask for PDFs,
  HTML, SHP, XLSX, or ZIP files, and get straight to what is queryable.
