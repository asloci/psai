# 2026-2027 Public Service AI Challenge: Team 8 — Skill/Tool Development

> **Work in progress.** These skills are prompts: instructions your agent reads and may choose to follow. They work best with a coding agent in a thinking/high-reasoning mode.

Skills that let an AI agent search Government of Canada open data and query it where it lies — over the web, with DuckDB. No downloads, no data pipeline, no API keys. Formats that cannot be read this way (ZIP, XLSX, PDF, SHP) are named as such, never approximated. Every command in this README was run against the live sources on 2026-10-01. Any model that follows these skills pulls the same numbers from the source and cites the dataset. The model you choose only writes the words around them.

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
# Datasets published in the last 12 months, counted per resource format (nothing transferred)
curl -s 'https://open.canada.ca/data/en/api/3/action/package_search?q=&fq=metadata_created:%5B2025-10-01T00:00:00Z%20TO%20*%5D&facet.field=%5B%22res_format%22%5D&rows=0' | jq '.result.count, .result.facets.res_format'
```

Example ask: *"Of the datasets published in the last 12 months, how many are machine-readable CSV versus Excel, PDF, or ZIP?"* The skill counts them with one facet call over a metadata_created date range (verified 2026-10-01: 2,767 datasets published since 2025-10-01, of which 703 carry a CSV, 101 an XLSX, 99 a ZIP — and 1,013 a PDF). PDFs out-publish CSVs more than 1.4-to-1 among new datasets: most of what government releases is still not machine-readable (a dataset can carry several formats, so counts overlap).

Cite it as:

```
<Department>. "<Dataset title>" [dataset]. Government of Canada Open Data Portal / <Department>. Last modified <YYYY-MM-DD>. Accessed <YYYY-MM-DD>. https://open.canada.ca/data/en/dataset/<id>. Open Government Licence – Canada.
```

### `statcan-wds` — Statistics Canada Web Data Service

Pull official Statistics Canada data straight from the source: inflation, jobs, population, and every other released cube. The skill follows the agency's own process — find the table, read its dimensions, locate the exact series — and serves point lookups over the web, usually with no download at all. A full-table CSV export runs only when you ask.

```bash
# International migration in-flows and out-flows, Canada, quarterly, last 11 years
# (coordinates built from the cube's own metadata; both series in one batched call)
curl -s -A 'Mozilla/5.0' -X POST 'https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods' \
  -H 'Content-Type: application/json' \
  -d '[{"productId":17100040,"coordinate":"1.1.0.0.0.0.0.0.0.0","latestN":44},
       {"productId":17100040,"coordinate":"1.2.0.0.0.0.0.0.0.0","latestN":44}]'
```

Example ask: *"Show migration in-flows and out-flows from covid-era to now, and the 1-, 5-, and 10-year change."* The skill browses the cube inventory for migration cubes, reads cube 17-10-0040's dimensions to build one coordinate for Immigrants and one for Emigrants, and returns both 11-year series in a single call. At the covid border closures (Q2 2020), in-flows bottomed at 34,072 against out-flows of 7,431; by Q2 2026 in-flows stood at 99,148 (−4.2% on the year, +33.2% on five, +12.3% on ten) and out-flows at 24,926 (+1.1%, +45.8%, +79.3%) — released 2026-09-23.

Cite it as:

```
Statistics Canada. "<Cube title>" (table NN-NN-NNNN-01) [dataset]. Statistics Canada. Released <YYYY-MM-DD>. Accessed <YYYY-MM-DD>. productId <pid>; vector <vid> (where applicable). https://www150.statcan.gc.ca/t1/tbl/en/tv.action?pid=<pid>
```

### `bankofcanada-valet` — Bank of Canada Valet

Browse the Valet series and group catalogs (~18,500 entries: exchange rates, interest rates, commodity price indices, money-market statistics), fetch a series by date range or latest N, and read the JSON in place with DuckDB. GET only, no API key. Valet matches by exact series code, so the skill finds your code in the catalog first.

```sql
-- CAD vs EUR, JPY, CNY and USD, past week, all four series in one combined call
SELECT u.d AS date, u.FXCADEUR.v AS cad_to_eur, u.FXCADJPY.v AS cad_to_jpy,
       u.FXCADCNY.v AS cad_to_cny, u.FXCADUSD.v AS cad_to_usd
FROM (SELECT unnest(observations) AS u
      FROM read_json_auto('https://www.bankofcanada.ca/valet/observations/FXCADEUR,FXCADJPY,FXCADCNY,FXCADUSD/json?recent=7'));
```

Example ask: *"How did the Canadian dollar move against the euro, yen, yuan, and US dollar this past week?"* The skill resolves all four series codes from the FX group catalog, pulls them in one combined observation call, and computes the weekly change over the web: from 2026-09-21 to 2026-09-29, CAD held flat against the euro (0.6217 → 0.6217 EUR) while slipping against the US dollar (0.7132 → 0.7048, −1.2%), the yuan (4.7755 → 4.7237, −1.1%), and the yen (112.23 → 110.99, −1.1%).

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
