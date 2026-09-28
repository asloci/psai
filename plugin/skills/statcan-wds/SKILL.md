---
name: statcan-wds
description: Query Statistics Canada's Web Data Service (WDS) API live — browse released cubes and their metadata/dimensions, fetch time-series data points by coordinate or vector, and get full-table CSV download URLs. Use when the user wants StatCan aggregate data or table metadata (CPI, LFS, population, etc.), to check what was released on a given date, or to feed the getFullTableDownloadCSV URLs used in DuckDB ingestion.
---

# StatCan Web Data Service (WDS) — live aggregate data API

Base: `https://www150.statcan.gc.ca/t1/wds/rest/{method}`. JSON in/out; POST
methods take a JSON array body and return a JSON array of `{status, object}`
per request. All patterns below verified live (2026-09-27).

CRITICAL: requests without a browser User-Agent get 503. Always send one:

```bash
curl -s -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36' ...
```

## On-load notice (show the user)

Only when the slash command arrives bare — `/statcan-wds` with nothing
after it — display this notice to the user verbatim, before any other
output:

> StatCan Web Data Service loaded. Everything runs live over the network
> against the WDS API — browsing and cube metadata fetch inventory records
> only; nothing is downloaded or stored unless you ask, and full-table ZIP
> downloads run only on request. Without a download I can serve point
> lookups only; aggregate analysis needs an ingest step. Every answer ends
> with an offer of the query trail. What would you like to look up?

If the command arrives with a prompt attached, skip the notice and answer
the prompt directly. If the user asks who or what this skill is ("who are
you", "what are you"), reply:

> I help you connect to StatCan Web Data Service and browse the inventory
> of records without a download. I can serve point lookups, and do
> lightweight analytics over-the-wire for anything that is available for
> me to read.

## Standing rules (read on load)

- Everything runs live over the network against the WDS API. Browsing
  (getAllCubesList), cube metadata, and data-point lookups fetch metadata
  and small point payloads only — nothing is downloaded or stored unless
  the user asks. Full-table ZIP downloads run only on explicit request.
- Queryability depends on format. Without a download, WDS serves point
  lookups only (a series' latest values, latest N periods, ranges).
  Aggregate analysis requires data that is DuckDB-readable in place — flat
  CSV/TSV/JSON over https, or Parquet on object stores — and StatCan full
  tables are ZIP-only, so they always need an explicit download-and-ingest
  step first. State which case applies before answering; never approximate
  when the format forbids the query.
- Every answer that returns a cube, series, or data point must carry a
  copy/paste citation: one single-line plaintext entry per source, each in
  its own fenced code block, placed directly above the query-trail offer
  line. Template (EU publications-guide order — author, title, publisher,
  date, date of extraction, persistent identifier):

  ```
  Statistics Canada. "<Cube title>" (table NN-NN-NNNN-01) [dataset]. Statistics Canada. Released <YYYY-MM-DD>. Accessed <extraction date YYYY-MM-DD>. productId <pid>; vector <vid> (where applicable). https://www150.statcan.gc.ca/t1/tbl/en/#<pid>
  ```

  If the answer quotes more than five sources, cite the primary ones and
  offer the full list on request.
- After every discover → retrieve → synthesize loop, end the answer by
  offering the query trail: the SQL/curl statements that produced the
  numbers, as a code block or saved to a .sql file in the working repo.
  Generate and show the code block/file only if the user says yes.

Example prompts:
- "How many active CPI cubes are there, and which are monthly?"
- "Pull the latest 6 months of the CPI all-items series for Canada."

## Discovery — browse the cube inventory first

When a user browses StatCan in natural language ("what tables exist about
X", "how many CPI tables are there", "is this table still active"), always
start with `GET getAllCubesList` before any other WDS call. It is WDS's
metadata equivalent of the Open Canada catalog search: one GET returns the
entire inventory (8,271 cubes on 2026-09-27) — productId, cansimId,
bilingual titles, cube start/end dates, release time, terminated flag,
frequencyCode, subject/survey codes, and dimension names. WDS has no
full-text search endpoint, so filtering this list is the only way to browse.

```sql
-- Entire inventory, queried in place with DuckDB (httpfs required).
-- duckdb's default User-Agent is accepted; curl needs the browser UA above.
SELECT productId, cansimId, cubeTitleEn, frequencyCode, archived
FROM read_json_auto('https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesList')
WHERE cubeTitleEn ILIKE '%consumer price index%'
ORDER BY productId;
```

Codes decode via getCodeSets: `archived` 0 = active, 1 = terminated
(terminated cubes are still served, but frozen); `frequencyCode` 6 = monthly.
The catalog ↔ cube bridge: every productId here is a WDS cube, and catalog
datasets whose resource URLs carry a table number resolve to one of these;
catalog products without a table number (publications, maps) have no cube
counterpart.

## Cube metadata — dimensions and member IDs

```bash
# Cube metadata: dimensions + all member IDs + titles (POST, array body)
curl -s -A "$UA" -X POST 'https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata' \
  -H 'Content-Type: application/json' -d '[{"productId":18100004}]'
# -> object.cubeTitleEn ("Consumer Price Index, monthly, not seasonally adjusted")
# -> object.dimension[]: {dimensionNameEn, member[]: {memberId, memberNameEn}}
# -> object.frequencyCode (6 = monthly)
```

The productId is the digits of the table number: table 18-10-0004-01 → 18100004.
The dimension/member structure from this call is the map for building
coordinates (below). Cubes can have many dimensions; metadata is the only
reliable way to enumerate member IDs.

Other discovery calls:

- `GET getChangedCubeList/{YYYY-MM-DD}` → cubes released that day
  (past dates only; future dates return 409 "The product is not released yet").
- `GET getCodeSets` → scalar factors, frequencies, symbols, statuses; also
  decodes the `archived` and `frequencyCode` columns of getAllCubesList.
- Note: getAllCubesList covers tables only. For non-table StatCan products
  (publications, maps) or other departments' datasets, browse the Open Canada
  catalog (open-canada-catalog skill); its StatCan resource URLs carry the
  table number, which bridges to a productId here.

## Coordinates — how to address a data point

A coordinate is the member ID of each dimension, in cube dimension order,
dot-separated and zero-padded to 10 segments. Example for CPI
(productId 18100004, dims: Geography, Products):

- Geography member 2 = Canada; Products member 3 = Food → `2.3.0.0.0.0.0.0.0.0`
- Verify against a known vector: v41690973 (CPI Canada All-items) reports its
  own coordinate as `2.2.0.0.0.0.0.0.0.0`.

Build coordinates from getCubeMetadata's member IDs — never guess.

## Retrieval — data points

```bash
# By cube + coordinate, latest N periods (POST)
curl -s -A "$UA" -X POST 'https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods' \
  -H 'Content-Type: application/json' \
  -d '[{"productId":18100004,"coordinate":"2.3.0.0.0.0.0.0.0.0","latestN":3}]'
# -> object.vectorDataPoint[]: {refPer, value, decimals, scalarFactorCode, releaseTime}
# response also returns vectorId for the series — reuse it for later calls.

# By vector ID (POST) — CPI Canada all-items = v41690973
curl -s -A "$UA" -X POST 'https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods' \
  -H 'Content-Type: application/json' -d '[{"vectorId":41690973,"latestN":3}]'

# Vector metadata (title etc.)
curl -s -A "$UA" -X POST 'https://www150.statcan.gc.ca/t1/wds/rest/getSeriesInfoFromVector' \
  -H 'Content-Type: application/json' -d '[{"vectorId":41690973}]'
# -> object.SeriesTitleEn ("Canada;All-items")
```

Other retrieval methods (same shapes): `getBulkVectorDataByRange`,
`getDataFromVectorByReferencePeriodRange`, `getChangedSeriesDataFromVector`,
`getChangedSeriesDataFromCubePidCoord`.

## Joins and cross-cube use

WDS has no cross-table query, and CKAN has no join semantics. Joins happen
after ingestion, in DuckDB/DuckLake — never live at the API layer.

Within one cube, no join is ever needed: a coordinate is already the full
dimensional address (e.g. Geography × Product × period). Most questions stop
at one cube, one coordinate, one vector.

Across cubes, two join patterns cover nearly all StatCan cases:

1. REF_DATE + geography (DGUID). Nearly every cube has REF_DATE and a
   Geography dimension; DGUIDs are StatCan's persistent geographic
   identifiers, stable across cubes and vintages. Example: CPI Ontario joins
   LFS Ontario on (REF_DATE, DGUID).
2. Shared classification codes (NAICS, product codes, SGC). Only when both
   cubes genuinely carry the same classification dimension — verify in
   getCubeMetadata before assuming.

Rules for cross-cube work:

- Design joins at curation time, in a join-key registry
  (`{key_name, table_name, column_name, notes}` — hand-populated), never
  invent them at query time. A model that guesses a join key is guessing a
  semantic fact — the failure mode the whole architecture exists to prevent.
- Before joining two ingested tables, check both cubes' metadata for the
  geography vintage / classification vintage: Ontario DGUIDs or NAICS
  versions can differ between tables released in different years.
- When in doubt, refuse the join and report that the two cubes share no
  verified key. That is a correct answer.

## Full table download (for DuckDB ingestion)

```bash
curl -s -A "$UA" 'https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/18100004/en'
# -> {"status":"SUCCESS","object":"https://www150.statcan.gc.ca/n1/tbl/csv/18100004-eng.zip"}
```

The object is a ZIP URL. DuckDB cannot read ZIP over https directly — download,
unzip, then `read_csv` locally (the Meta.csv inside maps vector IDs to
coordinates/series titles). `getFullTableDownloadSDMX/{pid}/{lang}` is the SDMX
XML variant. This is the pattern used by the GC Data Challenge node ingestion
(Stage 1 of the build handoff): get URL → download → unzip → load into
DuckDB/DuckLake.

## Guardrails

- Always check `status == "SUCCESS"` per array element; `FAILED` with
  `responseStatusCode: 2` means the coordinate doesn't exist — go back to
  metadata, don't permute coordinates.
- 406 errors are semantic rejections with a helpful `message` (invalid
  coordinate, wrong date format); 409 on getChangedCubeList = date not yet
  released; 503 = you forgot the User-Agent.
- POST bodies must be a JSON array, even for one item.
- Prefer `latestN` and range methods over full-table download for answering
  questions; use full-table only for ingestion.
- Values carry `decimals` and `scalarFactorCode` — apply them when presenting
  numbers (getCodeSets decodes them).
- Never join across cubes on guessed keys — see Joins and cross-cube use.

## Synthesize

Cite the cube title, productId (with table number format, e.g. 18-10-0004-01),
the series title from getSeriesInfoFromVector, the reference period(s), and
StatCan release time. Include the vector ID so the user can re-query the same
series. State the extraction date. End with the copy/paste citation block
from the standing rules — one single-line plaintext entry per source,
directly above the query-trail offer.
