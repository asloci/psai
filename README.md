# Public Service AI Challenge: Team 8 — Skill/Tool Development

> **Work in progress.** These are prompt-based skills — instructions your agent
> reads, and may choose to follow. Consider this repo a proof-of-concept: it
> works best with a coding agent in a thinking/high-reasoning mode.

Verified-live API skills for Government of Canada open data, plus a unified
metadata index of three catalogs, queried in place with DuckDB. Each skill
browses its source over https — no downloads, no ingestion pipeline, no API
keys — and when a resource is in a DuckDB-readable format (flat CSV/TSV/JSON
over https, Parquet on object stores), the skills do lightweight analytics
over-the-wire, querying the data where it lies. Formats that cannot be read
in place (ZIP, XLSX, PDF, SHP) are stated as such rather than approximated.

| Open Canada Catalog | StatCan WDS |
|:---:|:---:|
| ![Example prompt and response using the open-canada-catalog skill](assets/open-canada-prompt-example.png) | ![Example prompt and response using the statcan-wds skill](assets/statcan-wds-prompt-example.png) |

*Example prompts and responses from the Vibe Work desktop browser client.
Example written brief: ["What has been the biggest Labour Force change in Canada?"](assets/canada-s-biggest-labour-force-change-covid-era-2020-2026.pdf).*

## Install

Each skill is a plain folder containing a `SKILL.md` and its support files.
Download the skill folder you want, put it in your platform's skills
directory, and reload your platform. No install command, no plugin, no sync
step.

- **Vibe / any agent reading `~/.agents/skills/`** (global):
  `cp -R skills/<skill-name> ~/.agents/skills/`
- **Project-scoped**: copy the folder into your project's skills directory
  (Vibe: `.agents/skills/` inside the project) and open the project.
- Tools used by the skills: `curl` (ships with macOS) and the
  [DuckDB CLI](https://duckdb.org/) with its httpfs extension
  (`brew install duckdb`, then `INSTALL httpfs; LOAD httpfs;`).

## The data skills

### `open-canada-catalog` — Open Canada (CKAN)

Browse and search the Open Canada catalog (~48,000 datasets across 350+
departments) via the CKAN Action API, then query chosen CSV/JSON resources
in place.

Quickstart:

```bash
# How many datasets mention PSES? (count only, zero data transfer)
curl -s 'https://open.canada.ca/data/en/api/3/action/package_search?q=PSES&rows=0' | jq .result.count
```

Example session: *"Find the latest PSES dataset, then query its CSV in place
for response rate by department."* The skill searches the catalog, shows the
dataset's resources, and runs a DuckDB aggregation directly against the CSV
URL — no download, no ingest.

Citation template:

```
<Department>. "<Dataset title>" [dataset]. Government of Canada Open Data Portal / <Department>. Last modified <YYYY-MM-DD>. Accessed <YYYY-MM-DD>. https://open.canada.ca/data/en/dataset/<id>. Open Government Licence – Canada.
```

### `statcan-wds` — Statistics Canada Web Data Service

Pull official Statistics Canada data straight from the source: inflation,
jobs, population, and every other released cube. It follows the agency's own
process — find the table, read its dimensions, locate the exact series — and
serves point lookups over-the-wire, usually with no download at all.
Full-table CSV export runs only when you ask.

Quickstart:

```bash
# The all-items CPI series for Canada, latest 3 months (browser UA required)
curl -s -A 'Mozilla/5.0' -X POST 'https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods' \
  -H 'Content-Type: application/json' -d '[{"vectorId":41690973,"latestN":3}]'
```

Example session: *"How many active CPI tables are there, and which are
monthly?"* The skill filters the full cube inventory with DuckDB, then
answers with table numbers, titles, and release dates.

Citation template:

```
Statistics Canada. "<Cube title>" (table NN-NN-NNNN-01) [dataset]. Statistics Canada. Released <YYYY-MM-DD>. Accessed <YYYY-MM-DD>. productId <pid>; vector <vid> (where applicable). https://www150.statcan.gc.ca/t1/tbl/en/tv.action?pid=<pid>
```

### `bankofcanada-valet` — Bank of Canada Valet

Browse the Valet series and group catalogs (~18,500 entries: exchange rates,
interest rates, commodity price indices, money-market statistics), fetch
financial time series by date range or latest N, and read the JSON responses
in place with DuckDB. GET only, no auth, no API key. Valet is exact-match by
series code — the skill finds your series in the catalog first.

Quickstart:

```sql
-- CAD/USD noon exchange rate, latest observations, read in place
SELECT * FROM read_json_auto('https://www.bankofcanada.ca/valet/observations/IEXE0101/json?recent=5');
```

Example session: *"Plot CAD/EUR over the last two years."* The skill resolves
the series code from the group catalog, pulls the observation JSON, and
computes over-the-wire.

Citation template:

```
Bank of Canada. "<Series or group name>" (series/group <code>) [dataset]. Bank of Canada Valet API. Accessed <YYYY-MM-DD>. https://www.bankofcanada.ca/valet/observations/<code>/json
```

## The catalog cache — one searchable index of all three sources

A unified, pre-built metadata index: 74,716 rows — Open Canada / CKAN
(47,952 datasets), StatCan WDS (8,271 cubes), Bank of Canada Valet (18,493
series and groups) — as one Parquet file queryable with DuckDB. It answers
"what exists about X" across all three catalogs at once, with no live API
calls.

```sql
-- Cross-catalog search: every catalog record mentioning consumer price index
-- (verified on the 2026-09-30 vintage: CKAN 28, StatCan 23, Valet 10 hits)
SELECT source, id, title, url
FROM read_parquet('<cache location, see below>')
WHERE title ILIKE '%consumer price index%';
```

Schema: `source, id, title, publisher, description, formats, url,
last_modified, refreshed_at`. Parquet only — no embeddings, no search
infrastructure; search is query-time `ILIKE`.

Trap to know: the partitioned local cache uses hive-style partitioning, so
local reads need `hive_partitioning=1`:

```sql
SELECT * FROM read_parquet('~/.cache/psai/catalog-cache/**/*.parquet', hive_partitioning=1) LIMIT 10;
```

Honest limit: the cache answers **what exists**, never **what the data says**.
Metadata only — no documents, no dataset contents. Data points, cube
dimensions, and resource URLs always come from the live source APIs.

## How the cache is built and read

- **Built automatically (GitHub Actions).** A nightly workflow runs the build
  script on GitHub's servers and publishes the Parquet as a release asset —
  a file attached to a GitHub release. It never touches your machine. A new
  vintage is minted every night and old ones are pruned (latest 7 kept).
- **Built locally (optional).** Run
  `uv run --with duckdb scripts/build_catalog_cache.py` once on your machine
  (1–3 minutes, dominated by CKAN's paginated catalog fetch). It writes
  Parquet to `~/.cache/psai/catalog-cache/`. This is the offline /
  data-sovereignty path, and the path the skills prefer when a fresh local
  cache exists.
- **Read with no cache and no build.** Any DuckDB with the httpfs extension
  queries the release asset directly over https — no download, no build, no
  uv; the first query returns in seconds:

  ```sql
  INSTALL httpfs; LOAD httpfs;
  SELECT source, count(*) AS records
  FROM read_parquet('https://github.com/asloci/psai/releases/download/catalog-cache-v<YYYY.MM.DD>/catalog-cache-v<YYYY.MM.DD>.parquet')
  GROUP BY source;
  ```

- **How the skills read it.** A `SKILL.md` is a text file of instructions,
  not a program. For browsing questions it tells the agent to try the local
  cache first (fresh within 7 days of `refreshed_at`), then the release
  asset over https, then build locally or go live to the source APIs. The
  workflow and the skills never interact; both run the same recipe in two
  kitchens.

## Automation

The nightly build runs on GitHub's compute, free. Two ways to switch it:

- **No edit**: GitHub → this repo → Actions → *catalog-cache* → "..." menu →
  Disable workflow (Enable to turn it back on). The same page's
  *Run workflow* button mints an on-demand vintage.
- **File edit**: remove the `schedule:` lines in
  `.github/workflows/catalog-cache.yml` and keep `workflow_dispatch:`.

## Companion skill

`data-publication-assistant` — publication-quality charts and
visualizations from local files (CSV, XLSX, Parquet) or the data skills
above. Conventions are borrowed from the EU Publications Office's data
publication guidance, adapted to the Government of Canada context; it covers
chart choice, accessibility (WCAG), titles, provenance, citation, and export.
It is a companion to the data skills, not part of the core challenge framing.

## On governance

A policy instrument and governance architecture must be developed at the
same time as the AI tool itself.

> The skills and catalog cache are proofs of concept for a larger
> architecture: a federated, department-per-node model for Government of
> Canada data. The enforceable artifact would be a node contract: a
> citation standard, a no-invented-URLs rule, a hand-curated join-key
> registry, queryability disclosure, and a machine-readable inventory per
> node.

## Limits and non-goals

- Index, not corpus: the cache stores metadata and routes, never documents
  or dataset contents.
- No embeddings in v1; search is literal-text. A semantic layer (full-text
  or vector search over titles + descriptions) is a future iteration.
- Data points, cube metadata, and observations always come from the live
  source APIs, never from the cache.
- These skills are prompt-based: an agent in a low-reasoning or "fast" mode
  may ignore them and scrape web pages instead. If that happens, raise the
  reasoning level and re-ask.

## License

Code in this repo is released under the [MIT License](LICENSE). Catalog
metadata exposed through the cache originates from the Open Canada portal
(Open Government Licence – Canada), the Statistics Canada Web Data Service,
and the Bank of Canada Valet API, and remains subject to those sources'
terms.
