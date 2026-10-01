# 2026-2027 Public Service AI Challenge: Team 8 — Skill/Tool Development

> **Work in progress.** These skills are prompts: instructions your agent reads and may choose to follow. They work best with a coding agent in a thinking/high-reasoning mode.

Skills that let an AI agent search Government of Canada open data and query it where it lies — over the web, with DuckDB. No downloads, no data pipeline, no API keys. Formats that cannot be read this way (ZIP, XLSX, PDF, SHP) are named as such, never approximated. Every command in this README was run against the live sources on 2026-10-01.

| Skill | What it does |
|---|---|
| `open-canada-catalog` | Search ~48,000 Open Canada datasets (CKAN), query flat CSV/JSON resources in place |
| `statcan-wds` | Find StatCan tables, pull exact series values (CPI, jobs, population) over the web |
| `bankofcanada-valet` | Find Bank of Canada series (exchange, interest, commodity prices), read their JSON in place |
| `catalog-cache` | One searchable index of all three catalogs: ~74,700 rows in a single Parquet file |
| `data-publication-assistant` | Companion: publication-ready charts — choice, accessibility, citation, export |

| Open Canada Catalog | StatCan WDS |
|:---:|:---:|
| ![Example prompt and response using the open-canada-catalog skill](assets/open-canada-prompt-example.png) | ![Example prompt and response using the statcan-wds skill](assets/statcan-wds-prompt-example.png) |

*Example prompts and responses from the Vibe Work desktop browser client.
Example written brief: ["What has been the biggest Labour Force change in Canada?"](assets/canada-s-biggest-labour-force-change-covid-era-2020-2026.pdf).*

## Install

Each skill is a plain folder with a `SKILL.md` inside. Copy the folder you want into your agent's skills directory and reload your platform. There is no install command, no plugin, and no sync step.

- Global (Vibe, and any agent that reads `~/.agents/skills/`): `cp -R skills/<skill-name> ~/.agents/skills/`
- Project-scoped: copy the folder into `.agents/skills/` inside your project, then open the project.
- Tools the skills use: `curl` (ships with macOS) and the [DuckDB CLI](https://duckdb.org/) with its httpfs extension (`brew install duckdb`, then `INSTALL httpfs; LOAD httpfs;`).

## The data skills

### `open-canada-catalog` — Open Canada (CKAN)

Search the Open Canada catalog (~48,000 datasets from 352 departments) with the CKAN Action API, then query a chosen CSV or JSON resource in place.

```bash
# Datasets with at least one HTML resource, counted per department (nothing transferred)
curl -s 'https://open.canada.ca/data/en/api/3/action/package_search?q=&fq=res_format:HTML&facet.field=%5B%22organization%22%5D&rows=0' | jq '.result.count, .result.facets.organization'
```

Example ask: *"Which departments publish the most HTML, compared to CSV or JSON?"* The skill counts each format with one call (verified 2026-10-01: 32,367 datasets carry an HTML resource, 15,792 a CSV, 401 a JSON), then reads the organization facet for the ranking: Statistics Canada tops HTML and CSV (8,981 and 8,450), while Yukon (2,919), Alberta (2,893), and Health Canada (2,822) publish almost exclusively HTML.

Cite it as:

```
<Department>. "<Dataset title>" [dataset]. Government of Canada Open Data Portal / <Department>. Last modified <YYYY-MM-DD>. Accessed <YYYY-MM-DD>. https://open.canada.ca/data/en/dataset/<id>. Open Government Licence – Canada.
```

### `statcan-wds` — Statistics Canada Web Data Service

Pull official Statistics Canada data straight from the source: inflation, jobs, population, and every other released cube. The skill follows the agency's own process — find the table, read its dimensions, locate the exact series — and serves point lookups over the web, usually with no download at all. A full-table CSV export runs only when you ask.

```bash
# LFS employment in information, culture and recreation, by gender, latest 3 months
# (coordinates built from the cube's own metadata; both series in one batched call)
curl -s -A 'Mozilla/5.0' -X POST 'https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods' \
  -H 'Content-Type: application/json' \
  -d '[{"productId":14100022,"coordinate":"1.2.25.2.1.0.0.0.0.0","latestN":3},
       {"productId":14100022,"coordinate":"1.2.25.3.1.0.0.0.0.0","latestN":3}]'
```

Example ask: *"How many men and women work in Canada's information, culture and recreation sector?"* The skill browses the cube inventory for Labour Force Survey cubes, reads the cube's dimensions to build one coordinate per gender, and returns both series in a single call: August 2026, 512,500 men and 468,300 women (released 2026-09-04).

Cite it as:

```
Statistics Canada. "<Cube title>" (table NN-NN-NNNN-01) [dataset]. Statistics Canada. Released <YYYY-MM-DD>. Accessed <YYYY-MM-DD>. productId <pid>; vector <vid> (where applicable). https://www150.statcan.gc.ca/t1/tbl/en/tv.action?pid=<pid>
```

### `bankofcanada-valet` — Bank of Canada Valet

Browse the Valet series and group catalogs (~18,500 entries: exchange rates, interest rates, commodity price indices, money-market statistics), fetch a series by date range or latest N, and read the JSON in place with DuckDB. GET only, no API key. Valet matches by exact series code, so the skill finds your code in the catalog first.

```sql
-- CAD/EUR daily exchange rate, last 5 business days, read in place
SELECT u.d AS date, u.FXCADEUR.v AS cad_to_eur
FROM (SELECT unnest(observations) AS u
      FROM read_json_auto('https://www.bankofcanada.ca/valet/observations/FXCADEUR/json?recent=5'));
```

Example ask: *"Plot CAD/EUR over the last two years."* The skill resolves the series code from the group catalog, pulls the observation JSON, and computes over the web — 1 CAD bought 0.6217 EUR on 2026-09-29.

Cite it as:

```
Bank of Canada. "<Series or group name>" (series/group <code>) [dataset]. Bank of Canada Valet API. Accessed <YYYY-MM-DD>. https://www.bankofcanada.ca/valet/observations/<code>/json
```

## The catalog cache — one index of all three sources

A pre-built Parquet file: ~74,700 rows (as of 2026-10-01: 47,953 Open Canada datasets, 8,240 StatCan cubes, 18,493 Bank of Canada series and groups — the counts move daily). It answers "what exists about X?" across all three catalogs at once, with no live API calls.

```sql
INSTALL httpfs; LOAD httpfs;
-- Cross-catalog search: every record whose title mentions consumer price index
-- (verified 2026-10-01: CKAN 28, StatCan 23, Valet 10 hits)
SELECT source, id, title, url
FROM read_parquet('https://github.com/asloci/psai/releases/download/catalog-cache-v<YYYY.MM.DD>/catalog-cache-v<YYYY.MM.DD>.parquet')
WHERE title ILIKE '%consumer price index%';
```

Replace `<YYYY.MM.DD>` with the latest date on the [Releases](https://github.com/asloci/psai/releases) page — a new vintage is published every night, and the last 7 are kept.

Schema: `source, id, title, publisher, description, formats, url, last_modified, refreshed_at`. Search is plain text (`ILIKE`) — no embeddings, no search service.

Three ways to read it:

1. **Straight from the release asset over https** — the query above. No download, no build; the first result returns in seconds.
2. **Build it locally** (the offline, data-sovereignty path; the skills prefer it when a fresh copy exists): run `uv run --with duckdb scripts/build_catalog_cache.py` once (1–3 minutes, dominated by CKAN's paginated fetch). It writes to `~/.cache/psai/catalog-cache/`:

   ```sql
   -- hive_partitioning=1 is optional on current DuckDB (auto-detected); it keeps older versions working
   SELECT * FROM read_parquet('~/.cache/psai/catalog-cache/**/*.parquet', hive_partitioning=1) LIMIT 10;
   ```

3. **No cache, no build** — the skills go straight to the live source APIs.

The skills try a fresh local cache first, then the release asset, then the live APIs. A `SKILL.md` is a text file of instructions, not a program; the nightly workflow and the skills never interact — they follow the same recipe independently.

Honest limit: the cache answers what exists, never what the data says. Metadata only — no documents, no dataset contents. Data points, cube dimensions, and resource URLs always come from the live source APIs.

## Automation

A GitHub Actions workflow builds a fresh vintage every night at 08:30 UTC on GitHub's servers, free, and attaches it to a release. It never touches your machine. Old vintages are deleted; the last 7 are kept.

- No edit needed: GitHub → this repo → Actions → *catalog-cache* → "..." menu → Disable workflow (Enable turns it back on). The same page's *Run workflow* button builds one on demand.
- File edit: remove the `schedule:` lines in `.github/workflows/catalog-cache.yml` and keep `workflow_dispatch:`.

## Companion skill

`data-publication-assistant` — publication-quality charts and visualizations from local files (CSV, XLSX, Parquet) or the data skills above. Conventions are borrowed from the [EU Publications Office's data publication guidance](https://data.europa.eu/apps/data-in-publications-guide/). Adapted to the Government of Canada context: chart choice, accessibility (WCAG), titles, provenance, citation, and export.

## On governance

A policy instrument and governance architecture must be developed at the same time as the AI tool itself.

> The skills and catalog cache are proofs of concept for a larger architecture: a federated, department-per-node model for Government of Canada data. The enforceable artifact would be a node contract: a citation standard, a no-invented-URLs rule, a hand-curated join-key registry, queryability disclosure, and a machine-readable inventory per node.

## Limits

- Index, not corpus: the cache stores metadata and routes, never documents or dataset contents.
- Search is literal text, not semantic. A semantic layer is a future iteration.
- Data points, cube metadata, and observations always come from the live source APIs, never from the cache.
- These skills are prompt-based. An agent in a fast or low-reasoning mode may ignore them and scrape web pages instead. If that happens, raise the reasoning level and ask again.

## License

Code in this repo is released under the [MIT License](LICENSE). Catalog metadata exposed through the cache originates from the Open Canada portal (Open Government Licence – Canada), the Statistics Canada Web Data Service, and the Bank of Canada Valet API, and remains subject to those sources' terms.
