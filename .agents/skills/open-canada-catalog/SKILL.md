---
name: open-canada-catalog
description: Browse and search the Open Canada (CKAN) data catalog via its API without downloading datasets, then query chosen CSV/JSON resources directly with DuckDB over https. Use when the user wants to discover what Government of Canada datasets exist, inspect dataset metadata/resources, or ask questions of a catalogued tabular file live without ingesting it first.
---

# Open Canada Catalog (CKAN) — browse, then query in place

Open Canada (https://open.canada.ca) runs CKAN. Everything is exposed through a
GET-only RPC Action API. No auth, no POST, parameters in the URL. English base:
`https://open.canada.ca/data/en/api/3/action/...` (French: `/fr/`).

All patterns below were verified against the live API (2026-09-27).

## On-load notice (show the user)

Only when the slash command arrives bare — `/open-canada-catalog` with
nothing after it — display this notice to the user verbatim, before any
other output:

> Open Canada Catalog (CKAN) loaded. Discovery reads catalog metadata live
> over the network — no dataset contents are fetched unless you ask. Data
> is analyzable only when DuckDB-readable in place (flat CSV/TSV/JSON over
> https, Parquet on object stores); ZIP, XLSX, and PDF need a download
> step, which I will offer rather than approximate. Every answer ends with
> an offer of the SQL query trail. What would you like to find?

If the command arrives with a prompt attached, skip the notice and answer
the prompt directly. If the user asks who or what this skill is ("who are
you", "what are you"), reply:

> I help you connect to the Open Canada catalog and browse dataset
> metadata across 350+ departments without a download. I can do analytics
> over-the-wire for any resource in a DuckDB-readable format (CSV, JSON,
> Parquet).

## Standing rules (read on load)

- Everything runs live over the network against the CKAN API or, in Step 3, a
  resource URL — nothing is downloaded or stored unless the user asks for a
  file. Discovery (Steps 1-2) fetches catalog metadata only: no dataset
  contents, no resource URLs. Only Step 3, run on explicit request, reads a
  dataset's contents.
- Queryability depends on the resource: catalog metadata is always
  analyzable, but data contents only when DuckDB-readable in place (flat
  CSV/TSV/JSON over https, Parquet on object stores). ZIP, XLSX, and PDF
  need a download step — say so instead of approximating.
- Every answer that returns a dataset or resource must carry a copy/paste
  citation: one single-line plaintext entry per source, each in its own
  fenced code block, placed directly above the query-trail offer line.
  Template (EU publications-guide order — author, title, publisher, date,
  date of extraction, persistent identifier):

  ```
  <Department>. "<Dataset title>" [dataset]. Open Canada — Open Government Portal. Last modified <YYYY-MM-DD>. Accessed <extraction date YYYY-MM-DD>. https://open.canada.ca/data/en/dataset/<id> (<resource format>, <resource URL>)
  ```

  If the answer quotes more than five sources, cite the primary ones and
  offer the full list on request.
- After every discover → retrieve → synthesize loop, end the answer by
  offering the query trail: the SQL/curl statements that produced the
  numbers, as a code block or saved to a .sql file in the working repo.
  Generate and show the code block/file only if the user says yes.

Example prompts:
- "How many datasets are in the Open Canada catalog, by resource format and
  by department?"
- "Find the latest PSES dataset, then query its CSV in place for response
  rate by department."

## Step 1 — Discover: search the catalog (metadata only, no data download)

```bash
# Full-text search over titles/descriptions; returns count + paginated metadata
curl -s 'https://open.canada.ca/data/en/api/3/action/package_search?q=PSES&rows=20'   jq '.result.count, [.result.results[] | {title: .title_translated.en, org: .organization.title, id: .id}]'
```

Useful variants (all verified):

- `q=` free text (supports quoted phrases). `rows=` page size, `start=` offset.
- `fq=organization:<org-slug>` filters by department (e.g. `tbs-sct` → 314 datasets; StatCan's slug is `statcan`).
- `sort=metadata_modified+desc` sorts by last update.
- `package_show?id=<dataset-id>` → full metadata record for one dataset, including every resource (name, format, language, direct URL).
- `organization_list` → all ~350 department slugs.
- `package_list` → IDs of all ~48,000 datasets (rarely needed; prefer search).
- `recently_changed_packages_activity_list` → recently updated datasets.

Search tips (verified):

- The search is literal text, not semantic: "CPI Ontario" returns 0 for
  StatCan because titles spell out "Consumer Price Index". Prefer spelled-out
  terms; try synonyms if a count is 0 before concluding nothing exists.
- To answer "how many datasets are there about X" with zero data transfer, use
  `rows=0` — `result.count` returns the total match count on its own.

Response shape: `{success, result: {count, results: [...]}}`. Each result carries
`title_translated.en/fr`, `organization`, `notes_translated.en/fr`,
`metadata_modified`, and `resources[]` where each resource has
`format` (CSV/XLSX/PDF/PBIX/...), `name_translated`, and `url`.
Always check `.success == true`.

Present catalog answers as: dataset title, department, last modified, and the
resource list (format + URL). Do not fetch resource URLs during discovery.

Bridge to StatCan WDS: StatCan datasets' resource URLs contain the table number
(e.g. `.../tbl/csv/15100011-eng.zip` → productId 15100011). Use the catalog to
find what exists, then the statcan-wds skill for cube metadata and data.

## Step 2 — Retrieve: query the catalog JSON itself with DuckDB

The API response is a file DuckDB can query directly. Requires httpfs
(`duckdb -c "INSTALL httpfs; LOAD httpfs;"` first if not preloaded).

```sql
-- Query the search response in place: list matching datasets and their CSV resources
SELECT
  unnest(result.results) AS pkg,
  pkg.title_translated.en AS title,
  pkg.organization.title AS org,
  pkg.metadata_modified,
  unnest(pkg.resources) AS res,
  res.format,
  res.url
FROM read_json_auto('https://open.canada.ca/data/en/api/3/action/package_search?q=PSES&rows=20')
WHERE res.format = 'CSV';
```

Note: `read_json_auto` over https fetches the whole JSON document per query. For
repeated catalog exploration, download it once to a local file and query that.

## Step 3 — Query a chosen resource in place (no ingest)

If a resource is a flat CSV served directly over https, query it without any
download or import step (this is exactly how the PSES main dataset works —
proven pattern from the pses-analytics repo's `sql/01_raw_pses.sql`):

```sql
-- Schema sniff (cheap)
DESCRIBE SELECT * FROM read_csv_auto('https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv');

-- Sample / aggregate (avoid SELECT * on large files)
SELECT COUNT(*) FROM read_csv_auto('https://...csv');
SELECT * FROM read_csv_auto('https://...csv') LIMIT 100;
```

Guardrails for live file queries:

- Always `DESCRIBE` or `LIMIT` first — never run an unbounded `SELECT *` on an
  unprofiled remote file.
- Prefer `COUNT(*)`, aggregations, or `LIMIT` for the first touch of a big file.
- Government CSVs may be BOM-prefixed (UTF-8 with BOM) or Latin-1 encoded.
  `read_csv_auto` handles UTF-8 BOMs; for Latin-1 use
  `read_csv('...', encoding='latin-1')` or download + normalize first
  (see pses-analytics `fetch_with_bom_strip`).
- Sentinel values: PSES-family tables use `9999` for "no data" — apply
  `NULLIF(CAST(col AS INTEGER), 9999)` like the pses-analytics pipeline does.

## What DuckDB can and cannot read directly

- Direct over https: flat CSV/TSV/JSON (and Parquet on object stores).
- NOT direct: ZIP archives (StatCan CSV zips), XLSX, PDF. These need a small
  download step (`curl -L -o`), then local `read_csv` (after unzip) or the
  convert-file skill for XLSX.

## Synthesize

When answering a question about catalogued data: cite the dataset title,
department, dataset ID (or open.canada.ca URL `/data/en/dataset/<id>`), and the
exact resource URL the numbers came from in the answer body. Then end with
the copy/paste citation block from the standing rules — one single-line
plaintext entry per source, directly above the query-trail offer. If a
chosen resource is not in a directly queryable format, say so and offer the
download step instead of approximating.

End every discover → retrieve → synthesize loop by offering the query trail
(code block or .sql file) as described in the standing rules; do not dump SQL
unprompted. State the data plane only when Step 3 was used, since that is the
only step that reads dataset contents.
