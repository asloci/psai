---
name: bankofcanada-valet
description: Query the Bank of Canada Valet API live — browse the series and group catalogs, fetch financial time series (exchange rates, interest rates, commodity price indices, money-market statistics) by date range or latest N, and read the JSON in place with DuckDB over https. For Bank of Canada data without downloading files. Works best in thinking/high-reasoning modes; fast modes tend to scrape web pages instead of using the API.
---

# Bank of Canada Valet — live financial time-series API

Base: `https://www.bankofcanada.ca/valet/{method}` (French host:
`https://www.banqueducanada.ca/valet/...`). GET only, no auth, no API key,
no User-Agent requirement — plain curl works. Formats: `json` (preferred —
DuckDB-readable in place), `csv` (carries a preamble), and `xml` (clean
shape, newest-first order, but not DuckDB-readable — no XML extension in
current DuckDB builds). `html` is rejected by every endpoint ("Bad output
format (html) requested."). Human docs:
`https://www.bankofcanada.ca/valet/docs` (Swagger UI; no machine-readable
spec is exposed — the patterns below were verified live, 2026-09-30).

## On-load notice (show the user)

Only when the slash command arrives bare — `/bankofcanada-valet` with nothing
after it — display this notice to the user verbatim, before any other output:

> Bank of Canada Valet loaded. Everything runs live over the network against
> the Valet API — catalog browsing and series lookups fetch metadata and
> point payloads only; nothing is downloaded or stored unless you ask.
> The JSON responses are DuckDB-readable in place, so lightweight analytics
> over-the-wire work without any ingest step. Every answer ends with an
> offer of the query trail. Tip: Valet is exact-match by series code —
> find your series in the catalog first. What would you like to look up?

If the command arrives with a prompt attached, skip the notice and answer
the prompt directly. If the user asks who or what this skill is ("who are
you", "what are you"), reply:

> I help you connect to the Bank of Canada Valet API and browse the
> inventory of financial series without a download. I can serve point
> lookups, and do lightweight analytics over-the-wire for anything that is
> available for me to read.

## Standing rules (read on load)

- Everything runs live over the network against the Valet API. Catalog
  browsing and series lookups fetch metadata and point payloads only —
  nothing is downloaded or stored unless the user asks.
- Cache-first browsing: before fetching the series/group lists live, check
  the unified local cache at `~/.cache/psai/catalog-cache/` (Parquet,
  `source = 'valet'`; see the catalog-cache skill) — one DuckDB query
  covers all ~18,500 series and groups instantly. Trust it only if its
  `refreshed_at` vintage is 7 days old or less; if stale or absent, fall
  back to the live lists. Observations (data points) always go live.
- Queryability depends on format, and for Valet the news is good: the JSON
  responses are flat and DuckDB-readable in place, so lightweight analytics
  (aggregations, window functions, change calculations) run over-the-wire
  with no ingest step. The CSV variant carries a preamble and needs
  skip-tuning — prefer JSON. State which case applies before answering;
  never approximate when the format forbids the query.
- For ambiguous natural-language questions (unspecified series, date range,
  or output), ask the user to pin these down before querying — use the
  client's interactive question UI (cards) where available. The choices are
  real series or groups from the catalog lists. "Let the data decide" is a
  valid answer — fetch the candidate series and report the largest change.
  Match the chosen output format (table, brief, chart) in the final answer.
- Every answer that returns a series, group, or data point must carry a
  copy/paste citation: one single-line plaintext entry per source, each in
  its own fenced code block, placed directly above the query-trail offer
  line. Template (EU publications-guide order — author, title, publisher,
  date, date of extraction, persistent identifier):

  ```
  Bank of Canada. "<Series label>" (series NAME) [dataset]. Bank of Canada Valet API. Accessed <extraction date YYYY-MM-DD>. series NAME; group <GROUP> (where applicable); observations <first date> to <last date>. https://www.bankofcanada.ca/valet/observations/NAME/json
  ```

  The only URL patterns allowed in citations are the Valet endpoint patterns
  documented in this skill (verified live 2026-09-30):
  `https://www.bankofcanada.ca/valet/observations/{NAME}/json`,
  `https://www.bankofcanada.ca/valet/observations/group/{GROUP}/json`, and
  `https://www.bankofcanada.ca/valet/series/{NAME}/json`. Any other URL
  cited must come verbatim from an API response (e.g. a `link` field, the
  `terms.url` embedded in every response). Never invent, reconstruct, or
  approximate a URL — if no verified URL exists, cite the series name
  without a link rather than fabricate one.

  If the answer quotes more than five sources, cite the primary ones and
  offer the full list on request.
- After every discover → retrieve → synthesize loop, end the answer by
  offering the query trail: the SQL/curl statements that produced the
  numbers, as a code block or saved to a .sql file in the working repo.
  Generate and show the code block/file only if the user says yes.

Example prompts:
- "What is the USD/CAD exchange rate trend over the last month?"
- "Which Bank of Canada series exist about mortgage rates, and what is the
  latest value of each?"

## Discovery — browse the catalogs first

Valet is exact-match by series code: there is no full-text search endpoint,
so natural-language browsing ("what series exist about X", "which groups
cover bond yields") always starts with the two catalog lists:

```bash
# Series catalog: 15,948 series with label + description (verified 2026-09-30)
curl -s 'https://www.bankofcanada.ca/valet/lists/series/json'

# Group catalog: 2,545 groups with label + description (verified 2026-09-30)
curl -s 'https://www.bankofcanada.ca/valet/lists/groups/json'
```

Trap: the lists type is `series` (singular) but `groups` (plural) —
`/valet/lists/group/json` returns 404 with a misleading error message that
says "use series or group". The working pair is `series` and `groups`.

Cache both lists once per session, then browse locally — every
natural-language query against the local files is instant:

```bash
curl -s 'https://www.bankofcanada.ca/valet/lists/series/json' -o /tmp/valet_series.json
curl -s 'https://www.bankofcanada.ca/valet/lists/groups/json' -o /tmp/valet_groups.json
```

```sql
-- Find candidate series by keyword (map_entries + unnest, verified live)
SELECT e.key AS series_name, e.value.label, e.value.description
FROM read_json_auto('/tmp/valet_series.json') v, UNNEST(map_entries(v.series)) AS t(e)
WHERE e.value.label ILIKE '%mortgage%' OR e.value.description ILIKE '%mortgage%';
```

Common series codes worth knowing: `FXUSDCAD`, `FXEURCAD` (daily FX);
`AVG_1M_CORRA`, `AVG_3M_CORRA` (CORRA term averages); `WOCR` (policy rate);
`A.AGRI`, `A.BCPI` (commodity price indices). Series codes are the address —
never guess one; find it in the catalog first.

The catalog ↔ other-skills bridge: Valet covers Bank of Canada financial
series only. For CPI, LFS, population, and other aggregate official
statistics use the statcan-wds skill; for other departments' datasets or
non-table products use the open-canada-catalog skill.

## Series and group metadata

```bash
# One series: label, description, and (in observations calls) dimension key
curl -s 'https://www.bankofcanada.ca/valet/series/FXUSDCAD/json'
# -> {terms, seriesDetails: {name, label, description}}

# One group: label, description, and its member series
curl -s 'https://www.bankofcanada.ca/valet/groups/goccaddep_weekly/json'
# -> {terms, groupDetails: {name, label, description, groupSeries}}
```

Use group metadata when the user asks about a topic block (e.g. "Government
of Canada deposits"): the group fetches all its member series in one call
during retrieval, rather than enumerating series one by one.

## Retrieval — observations

```bash
# One or more series, comma-joined, by date range
curl -s 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD,FXEURCAD/json?start_date=2026-09-01&end_date=2026-09-30'

# Latest N points only
curl -s 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=10'

# A whole group in one call
curl -s 'https://www.bankofcanada.ca/valet/observations/group/goccaddep_weekly/json?start_date=2026-01-01'
```

JSON shape: `{terms, seriesDetail: {NAME: {label, description, dimension}},
observations: [{d: "YYYY-MM-DD", NAME: {v: "1.4145"}}]}`. Values arrive as
strings — cast before arithmetic. `recent=N` returns exactly the last N
points (verified). `order_dir=desc` is accepted but was observed to still
return ascending dates — never rely on server-side ordering; sort
client-side.

The DuckDB pattern (httpfs required) — JSON reads in place, observations is
a nested array, unnest it:

```sql
SELECT o.d AS date, o.FXUSDCAD.v::DOUBLE AS usdcad
FROM read_json_auto('https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=30'),
unnest(observations) AS t(o)
ORDER BY o.d;
```

Multi-series calls put every requested series in each observation row —
one fetch, all columns, no per-series looping. Group observations are the
same shape with one column per member series. This is what makes
over-the-wire analytics (monthly averages, min/max, period-over-period
change) a single query.

## CSV variant (only when the user asks for a file)

```bash
curl -s 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/csv?start_date=2026-09-01' -o fxusdcad.csv
```

The CSV carries a preamble: a terms-and-conditions block, a SERIES section
with one row per series, then the OBSERVATIONS header and data. It is
BOM-prefixed and CRLF-terminated. DuckDB's `read_csv` handles the UTF-8 BOM
and CRLF fine — only the preamble needs skipping, and the skip count varies
with series count (`skip=8` works for a single series; one more line per
additional series), which is why JSON is the default path. For a
user-facing CSV, deliver the API's own CSV rather than hand-building one.

## Guardrails

- Series codes are exact-match. A wrong or misspelled code returns
  `{"message": "The page you are looking for is unavailable.", ...}` with
  HTTP 404 — go back to the catalog lists, don't permute codes.
- Valet has no User-Agent requirement, no rate limit documented, and no
  auth — plain curl and DuckDB's default UA both work. Do not add
  complexity that the API does not require.
- Values are strings; dates are ISO `YYYY-MM-DD`. Cast values before
  arithmetic; a missing observation for a series simply omits that key in
  the row — join or filter accordingly rather than assuming a dense grid.
- Always bound queries with `start_date`/`end_date` or `recent=N`; an
  unbounded series query returns the full history (decades for daily FX —
  thousands of rows when you wanted a month).
- Date coverage varies per series (FXUSDCAD starts 2017-01-03; others go
  back further): check the first observation returned, and say so when the
  user's requested range predates the series.
- Never fabricate URLs — see the citation rule in the standing rules.
- Joins across series happen naturally in DuckDB (multi-series fetch or a
  join on `d`) — that is the intended pattern; there is no cross-series
  query at the API layer beyond comma-joining codes in one call.

## Synthesize

Cite the series label and series code (and group name where applicable),
the observation date range actually returned, and the extraction date.
State the frequency when it is not obvious from context (daily, weekly
Wednesday, monthly — the group description carries it). Note the date
coverage of the series when it bounds the answer. End with the copy/paste
citation block from the standing rules — one single-line plaintext entry
per source, directly above the query-trail offer. Valet responses embed
`terms.url` (https://www.bankofcanada.ca/terms/) — Bank of Canada terms
apply to redistributed data; the citation carries the attribution.

Bridge to data-publication-assistant: when the user wants a chart,
publication visual, or formatted brief of fetched data, the
data-publication-assistant skill governs chart choice, design, provenance,
and export.
