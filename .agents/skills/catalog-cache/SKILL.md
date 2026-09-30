---
name: catalog-cache
description: Search a unified, pre-built local cache of three Government of Canada catalogs — Open Canada (CKAN, ~48,000 datasets), StatCan WDS (~8,300 cubes), and Bank of Canada Valet (~18,500 series/groups) — as one Parquet table queryable with DuckDB. Use for "what exists about X" questions across all three sources at once, without live API calls. Rebuild the cache on demand with the bundled script. Works best in thinking/high-reasoning modes.
---

# Catalog Cache — one unified inventory, queried in place

A pre-built, on-disk index of every catalogued Government of Canada
statistical asset in three inventories. It is an index, never a corpus:
metadata rows only (source, id, title, publisher, description, formats,
url, last_modified, refreshed_at) — no dataset contents, no documents.

Built by `scripts/build_catalog_cache.py` (bundled in this skill) from the
live APIs described in the sibling skills (open-canada-catalog, statcan-wds,
bankofcanada-valet). Counts verified 2026-09-30: CKAN 47,950 datasets,
StatCan 8,271 cubes, Valet 18,493 series/groups — 74,714 rows, ~7.5 MB.

## On-load notice (show the user)

Only when the slash command arrives bare — `/catalog-cache` with nothing
after it — display this notice to the user verbatim, before any other
output:

> Catalog cache loaded. I hold a unified local index of three Government
> of Canada catalogs — Open Canada datasets, StatCan cubes, and Bank of
> Canada series — as one Parquet table, queried in place with DuckDB.
> Browsing reads cached metadata only; nothing is fetched live unless the
> cache is stale or you ask for data points, which go to the live APIs.
> Every answer ends with an offer of the query trail. What would you
> like to find?

If the command arrives with a prompt attached, skip the notice and answer
the prompt directly. If the user asks who or what this skill is ("who are
you", "what are you"), reply:

> I hold a unified local index of three Government of Canada catalogs and
> search it in place with DuckDB — instant browsing across Open Canada
> datasets, StatCan cubes, and Bank of Canada series. I answer "what
> exists" questions without any live API call, and hand off to the live
> skills for data points and downloads.

## Standing rules (read on load)

- The cache is an index, never a corpus: metadata only, no dataset
  contents. It answers "what exists" — never "what does the data say".
  For data points, series values, or table contents, hand off to the
  matching live skill (open-canada-catalog, statcan-wds,
  bankofcanada-valet) with the id/url found here.
- Cache location (conventional path): `~/.cache/psai/catalog-cache/`,
  partitioned `source=ckan|statcan|valet`. A published nightly vintage
  lives over https as a dated GitHub release asset
  (`catalog-cache-vYYYY.MM.DD`); read it the same way with DuckDB.
- Staleness rule: check `refreshed_at` before trusting the cache. If it
  is older than 7 days, say so, offer to rebuild
  (`uv run --with duckdb scripts/build_catalog_cache.py`, ~1-3 min), and
  fall back to the live APIs if the platform has no filesystem or the
  user declines a rebuild. Never present a stale cache as current.
- Queryability is unconditional: Parquet is DuckDB-readable in place, on
  any platform with DuckDB — no ingest step, no downloads.
- For ambiguous natural-language browsing (unspecified source, topic, or
  output), ask the user to pin these down before querying — use the
  client's interactive question UI (cards) where available. "Let the data
  decide" is a valid answer: report the top matches with counts and let
  the user pick.
- Every answer that returns a dataset, cube, or series from the cache
  must carry a copy/paste citation: one single-line plaintext entry per
  source, each in its own fenced code block, placed directly above the
  query-trail offer line. Cite the ORIGINAL source (publisher, title,
  id), not the cache, plus the cache vintage. Template (EU
  publications-guide order — author, title, publisher, date, date of
  extraction, persistent identifier):

  ```
  <Publisher>. "<Title>" (<id>) [dataset]. <Publisher>. Catalog record accessed <extraction date YYYY-MM-DD> via psai catalog cache vintage <refreshed_at>. <url>
  ```

  URLs must come verbatim from the cache row's `url` column — never
  invent, reconstruct, or approximate a URL. If the answer quotes more
  than five sources, cite the primary ones and offer the full list on
  request.
- After every discover → retrieve → synthesize loop, end the answer by
  offering the query trail: the SQL statements that produced the
  answer, as a code block or saved to a .sql file in the working repo.
  Generate and show the code block/file only if the user says yes.

Example prompts:
- "What exists about consumer price indexes across all three catalogs?"
- "How many datasets does each department publish, and in which formats?"
- "Is there anything about labour force for Ottawa-Gatineau anywhere?"

## Querying the cache

One table, three sources, instant search:

```sql
-- Schema
DESCRIBE SELECT * FROM read_parquet('~/.cache/psai/catalog-cache/**/*.parquet', hive_partitioning=1);

-- Everything about a topic, across all three catalogs
SELECT source, id, title, publisher, formats
FROM read_parquet('~/.cache/psai/catalog-cache/**/*.parquet', hive_partitioning=1)
WHERE title ILIKE '%consumer price index%'
ORDER BY source, title;

-- Counts by source
SELECT source, count(*) AS n
FROM read_parquet('~/.cache/psai/catalog-cache/**/*.parquet', hive_partitioning=1)
GROUP BY source;

-- Department-by-format breakdown (CKAN rows; formats is a CSV list)
SELECT publisher, formats, count(*) AS n
FROM read_parquet('~/.cache/psai/catalog-cache/**/*.parquet', hive_partitioning=1)
WHERE source = 'ckan'
GROUP BY publisher, formats ORDER BY n DESC;
```

Schema (one row per catalogued asset):

- `source` — `ckan`, `statcan`, or `valet`.
- `id` — CKAN dataset UUID, StatCan productId, or Valet series/group code.
- `title` — English title (CKAN), cube title (StatCan; French title lives
  in `description`), or series label (Valet).
- `publisher` — department name (CKAN), Statistics Canada, or Bank of Canada.
- `description` — notes (CKAN), French cube title (StatCan), or series
  description (Valet).
- `formats` — resource formats, comma-joined (e.g. `CSV,HTML,JSON,XLSX`);
  fixed `CSV,SDMX` (StatCan) or `JSON,CSV,XML` (Valet).
- `url` — the citable landing/observations URL for the asset.
- `last_modified` — CKAN metadata_modified, StatCan releaseTime, blank (Valet).
- `refreshed_at` — date the cache was built; the vintage citation key.

Trap: `hive_partitioning=1` is required when reading the local partitioned
directory — without it the `source` column comes from the folder name only
and full-glob queries may duplicate the column.

## Rebuilding

```bash
# ~1-3 min: 48 paginated CKAN calls + one WDS GET + two Valet list GETs
uv run --with duckdb scripts/build_catalog_cache.py
# -> writes ~/.cache/psai/catalog-cache/source={ckan,statcan,valet}/data_0.parquet
```

The script is pure stdlib + DuckDB (installed ephemerally by `uv`), sends a
browser User-Agent (StatCan rejects bare clients with 503), and retries
each request three times. It writes two artifacts: the partitioned
directory above, and a single-file `~/.cache/psai/catalog-cache.parquet`
(~8 MB) — the same shape published nightly as a GitHub release asset.
Overwrites in place; a partially failed rebuild leaves the previous
vintage intact until the COPY succeeds.

## Synthesize

Present cache answers as: source, title, publisher, id, formats — grouped
by source when the question spans catalogs. State the cache vintage
(`refreshed_at`) alongside the extraction date. Hand off to the live
skills for anything beyond metadata: data points (statcan-wds,
bankofcanada-valet), resource contents (open-canada-catalog). End with
the copy/paste citation block from the standing rules — one single-line
plaintext entry per source, directly above the query-trail offer.
