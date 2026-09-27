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

## Discovery — table/cube metadata

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
- `GET getCodeSets` → scalar factors, frequencies, symbols, statuses.
- Note: WDS has no dataset full-text search. To find a table number, search
  statcan.gc.ca or the Open Canada catalog (open-canada-catalog skill), then
  use its productId here.

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

## Synthesize

Cite the cube title, productId (with table number format, e.g. 18-10-0004-01),
the series title from getSeriesInfoFromVector, the reference period(s), and
StatCan release time. Include the vector ID so the user can re-query the same
series. State the extraction date.