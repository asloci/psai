---
name: open-canada-catalog
description: Browse and search the Open Canada (CKAN) catalog via its API without downloads, then query chosen CSV/JSON resources directly with DuckDB over https. For discovering what Government of Canada datasets exist, inspecting metadata/resources, or querying a catalogued tabular file live without ingesting it first. Unreadable resources (HTML, PDF, XLSX) are fetched, cited, and table-extracted. Works best in thinking/high-reasoning modes; fast modes tend to web-scrape instead of using the API.
---

# Open Canada Catalog (CKAN) — browse, then query in place

Open Canada (https://open.canada.ca) runs CKAN. Everything is exposed through a
GET-only RPC Action API. No auth, no POST, parameters in the URL. English base:
`https://open.canada.ca/data/en/api/3/action/...` (French: `/fr/`).

All patterns below were verified against the live API (2026-09-27; the
Step 2 pattern on 2026-09-30).

## On-load notice (show the user)

Only when the slash command arrives bare — `/open-canada-catalog` with
nothing after it — display this notice to the user verbatim, before any
other output:

> Open Canada Catalog (CKAN) loaded. Discovery reads catalog metadata live
> over the network — no dataset contents are fetched unless you ask. Data
> is analyzable only when DuckDB-readable in place (flat CSV/TSV/JSON over
> https); other formats need a download step, and unstructured documents
> (HTML, PDF, XLSX) I fetch and extract tables from first, handing the rest
> to your platform's reader. Every answer ends with an offer of the SQL
> query trail. Tip: multi-step catalog lookups work best in a
> thinking/high-reasoning mode — fast modes may shortcut to web scraping
> instead of this API. What would you like to find?

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
  file. Discovery (Steps 1-2) fetches catalog metadata only: resource URLs
  are listed, never fetched. Only Step 3, run on explicit request, reads a
  dataset's contents.
- Queryability depends on the resource: catalog metadata is always
  analyzable, but data contents only when DuckDB-readable in place (flat
  CSV/TSV/JSON over https, Parquet on object stores). Classify every
  resource by its `format` at metadata time — never by fetching — into
  Tier A (readable in place → Step 3), Tier B (download + transform → curl
  then unzip/excel/spatial), or Tier C (unstructured document → Step 4).
  Say which tier applies; never approximate when the format forbids the
  query.
- For ambiguous natural-language questions (unspecified dataset, department,
  resource format, or output), ask the user to pin these down before
  querying — use the client's interactive question UI (cards) where
  available. The choices are real catalog facets from the search results:
  candidate datasets (with department and last-modified date), department
  (`fq=organization:<slug>`), resource format, and output format (table,
  brief, chart). "Let the data decide" is a valid answer — inspect the
  candidate datasets' metadata and report the best match. Match the chosen
  output format in the final answer.
- Every answer that returns a dataset or resource must carry a copy/paste
  citation: one single-line plaintext entry per source, each in its own
  fenced code block, placed directly above the query-trail offer line.
  Template (EU publications-guide order — author, title, publisher, date,
  date of extraction, persistent identifier):

  ```
  <Department>. "<Dataset title>" [dataset]. Open Canada — Open Government Portal. Last modified <YYYY-MM-DD>. Accessed <extraction date YYYY-MM-DD>. https://open.canada.ca/data/en/dataset/<id> (<resource format>, <resource URL>)
  ```

  Never invent, reconstruct, or approximate a URL in a citation. The
  dataset link comes from the result's `id`; the resource URL must be
  copied verbatim from the API's `resources[].url`. If the API did not
  return a URL for a source, cite the dataset ID without a link rather
  than fabricate one.

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
curl -s 'https://open.canada.ca/data/en/api/3/action/package_search?q=PSES&rows=20' | jq '.result.count, [.result.results[] | {title: .title_translated.en, org: .organization.title, id: .id}]'
```

Useful variants (all verified):

- `q=` free text (supports quoted phrases). `rows=` page size, `start=` offset.
- `fq=organization:<org-slug>` filters by department (e.g. `tbs-sct` → 314 datasets; StatCan's slug is `statcan`).
- `sort=metadata_modified+desc` sorts by last update.
- `package_show?id=<dataset-id>` → full metadata record for one dataset, including every resource (name, format, language, direct URL).
- `organization_list` → all ~350 department slugs.
- `package_list` → IDs of all ~48,000 datasets (rarely needed; prefer search).
- `recently_changed_packages_activity_list` → recently updated datasets.
- `rows=0&facet.field=["res_format"]` → counts of every resource format
  matching a query, zero data transfer (URL-encode the brackets:
  `facet.field=%5B%22res_format%22%5D`; same works for `"organization"`).
  Catalog-wide on 2026-09-30: HTML 32,335; CSV 15,790; XML 12,934; PDF
  8,322 — unstructured documents are the majority of the catalog, which is
  why Step 4 exists.

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

Bridge to data-publication-assistant: when the user wants a chart or
publication visual of catalogued data, the data-publication-assistant skill
governs chart choice, design, provenance, and export.

Bridge to Bank of Canada Valet: for Bank of Canada financial time series
(exchange rates, interest rates, commodity price indices), the
bankofcanada-valet skill queries the Valet API directly — the freshest path
even where a catalog entry also exists.

## Step 2 — Retrieve: query the catalog JSON itself with DuckDB

The API response is a file DuckDB can query directly. Requires httpfs
(`duckdb -c "INSTALL httpfs; LOAD httpfs;"` first if not preloaded).

```sql
-- Query the search response in place: list matching datasets and their CSV resources
-- maximum_depth=2 keeps each result as raw JSON — CKAN's mixed-precision
-- timestamps (some with, some without fractional seconds) break plain
-- read_json_auto's timestamp parsing.
SELECT
  pkg->>'$.title_translated.en' AS title,
  pkg->>'$.organization.title' AS org,
  res->>'$.format' AS fmt,
  res->>'$.url' AS url
FROM read_json_auto('https://open.canada.ca/data/en/api/3/action/package_search?q=PSES&rows=20', maximum_depth=2),
     UNNEST(json_extract(result, '$.results[*]')) AS t(pkg),
     UNNEST(json_extract(pkg, '$.resources[*]')) AS u(res)
WHERE res->>'$.format' = 'CSV';
```

Note: `read_json_auto` over https fetches the whole JSON document per query.
For repeated catalog exploration of the same search, cache it once per
session and browse locally — same pattern as the cube/series lists in the
sibling skills:

```bash
curl -s 'https://open.canada.ca/data/en/api/3/action/package_search?q=PSES&rows=100' -o /tmp/ckan_search.json
```

```sql
-- Same query as above, against the local cached file — instant to iterate on
SELECT
  pkg->>'$.title_translated.en' AS title,
  pkg->>'$.organization.title' AS org,
  res->>'$.format' AS fmt,
  res->>'$.url' AS url
FROM read_json_auto('/tmp/ckan_search.json', maximum_depth=2),
     UNNEST(json_extract(result, '$.results[*]')) AS t(pkg),
     UNNEST(json_extract(pkg, '$.resources[*]')) AS u(res)
WHERE res->>'$.format' = 'CSV';
```

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

## Resource tiers — classify by `format`, never by fetching

Every resource carries `format` in `resources[]`; route on it at metadata
time (counts from the catalog-wide facet query, verified 2026-09-30):

| Tier | Formats | Path |
|---|---|---|
| A — readable in place | CSV, TSV, JSON, TXT, ESRI REST (returns JSON) | Step 3 |
| B — download + transform | ZIP (unzip → CSV), XLSX/XLS (DuckDB `excel` extension `read_xlsx`, or the convert-file skill), SHP/KML/FGDB/GEOJSON (spatial skill; GeoJSON also reads as JSON) | `curl -L -o`, then transform locally |
| C — unstructured document | HTML, PDF, DOCX, PBIX, JP2/JPG | Step 4 |

XML (12,934 resources) has no reader in current DuckDB builds — parse
platform-side or via a transform; do not claim it is directly readable.

## Step 4 — Unstructured documents: fetch, cite, then delegate

Tier C is the majority of the catalog (32,335 HTML + 8,322 PDF resources
alone). The pattern: fetch the real file, cite it, extract tables first,
and let the platform decide the reader.

1. Size and content-type check first — never blind-download a large file:
   `curl -sI '<resource URL>'` (Content-Length, Content-Type).
2. Fetch to a local file: `curl -sL '<resource URL>' -o /tmp/<name>`.
3. Cite the fetched file per the standing citation rule — before opening it.
4. Extract in priority order — tables first:
   a. embedded tables (HTML `<table>`, PDF text-layer tables, XLSX sheets);
   b. full text layer;
   c. machine vision on rendered pages — fallback for scanned PDFs and
      images.
   Which of these runs is the platform's call: a CLI agent uses Python
   libraries (`pandas.read_html`, `pdfplumber`); a GUI client uses its
   document/vision models; mobile does what it can. The skill fixes the
   priority order, not the tool.
5. The fetched file is the source — never answer a question about a
   document's contents from memory or from the dataset title alone.
6. If the file is too large for the platform to handle, say so and fall
   back to the catalog metadata (title, department, description) instead
   of guessing.

## Synthesize

When answering a question about catalogued data: cite the dataset title,
department, dataset ID (or open.canada.ca URL `/data/en/dataset/<id>`), and the
exact resource URL the numbers came from in the answer body. Then end with
the copy/paste citation block from the standing rules — one single-line
plaintext entry per source, directly above the query-trail offer. If a
chosen resource is Tier B or C, say which tier applies and offer the
download path or table-first extraction instead of approximating.

End every discover → retrieve → synthesize loop by offering the query trail
(code block or .sql file) as described in the standing rules; do not dump SQL
unprompted. State the data plane only when Step 3 was used, since that is the
only step that reads dataset contents.
