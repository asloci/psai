---
name: data-publication-assistant
description: Create publication-quality charts and visualizations from datasets or insights pulled from the open-canada-catalog and statcan-wds skills — one-off charts for reports, briefs, slides, and social media. Covers chart choice, design, accessibility (WCAG), titles, provenance, citation, and export. Load when asked to visualize, chart, or plot data for publication, or to review a chart for publication readiness. Works best in thinking/high-reasoning modes; fast modes tend to skip the process.
---

# Data Publication Assistant — charts fit for publication

Use when the user wants a one-off visual (chart, map, small multiples) of a
dataset or a StatCan / Open Canada insight, destined for a report, brief,
slide, or social post. Companion to open-canada-catalog and statcan-wds:
they fetch the data, this skill governs how the visual is designed,
labelled, cited, and exported.

Conventions are borrowed from the Publications Office of the European
Union's open guides: the Data Visualisation Guide
(https://data.europa.eu/apps/data-visualisation-guide) and "A practical
guide to user-friendly data in publications"
(https://data.europa.eu/apps/data-in-publications-guide). The
chart-selection tree below is adapted from the MIT-licensed dataviz skill
in github.com/mehd-io/agent-skills.

## On-load notice (show the user)

Only when the slash command arrives bare — `/data-publication-assistant`
with nothing after it — display this notice verbatim, before any other
output:

> Publication Data Visualization loaded. Give me data (a file, a query
> result, or a StatCan/Open Canada dataset) and the message you want the
> chart to convey, and I will pick the chart type, design it to
> publication and accessibility standards, cite the source, and export it
> in the formats you need.

If the command arrives with a prompt attached, skip the notice and act.

## Standing rules (read on load)

- One chart, one message. Before plotting, write the message in one
  sentence ("The gender gap in cultural employment is at an all-time
  low"). If you cannot state it, you are not ready to chart.
- Never visualize when text is better. Small samples, heavy caveats, or
  qualitative findings get prose, an infographic, or a table — not a chart
  that implies precision the data does not have.
- Verify the message against the data before publishing. The chart, the
  title, and the surrounding text must say the same thing in the same
  units.
- Every published chart carries a provenance block: author/creator,
  data source, retrieval or reference date, and licence.
- Prefer accessible defaults over post-hoc fixes: colour-blind-safe
  palette, direct labels, alt text, values shown.
- If audience, destination (PDF, web, slide, social), or message is
  unstated and the choice materially changes the design, ask via the
  client's interactive question UI where available — with the real
  options as choices and "let the data decide" as a valid answer. Do not
  gate otherwise; act on the prompt.

## Workflow

1. **Frame.** Identify the insight worth showing, the audience, and the
   destination (PDF, web, slide 16:9, social 1:1). Ask only if the
   destination changes the design materially.
2. **Choose the chart type** by walking the tree below top-down: state
   the path you took and justify the leaf you land on.
3. **Design to the checklist below.**
4. **Provenance and accessibility** (citation, alt text, metadata).
5. **Render** via the host-agnostic path (below), **export** in the
   requested formats, and deliver.

## Chart selection tree (walk top-down, justify the leaf)

```
What kind of data?
│
├── NUMERIC only
│   ├── 1 variable                → Histogram
│   ├── 2 variables, one ordered (time/sequence)
│   │                              → Line (Area only when totals are meaningful)
│   └── 2 variables, unordered    → Scatter
│
├── CATEGORIC only
│   ├── 1 variable                → Bar (horizontal bars when labels are long)
│   ├── parts of a whole summing to 100%
│   │                              → Stacked bar — not pie; if a pie at all,
│   │                                never more than 5 slices
│   └── hierarchy (e.g. region > city)
│                                  → Treemap
│
├── NUMERIC + CATEGORIC (mixed)
│   ├── 1 numeric per group       → Bar, Lollipop
│   ├── several numerics, one ordered
│   │                              → Multi-line, Stacked bar
│   └── distributions per group    → Box plot, Violin
│
├── TIME SERIES
│   ├── 1 series                  → Line
│   ├── few series (<7)           → Multi-line
│   └── many series               → Small multiples, Heatmap
│
└── GEOGRAPHIC
    ├── regions (boundaries)       → Choropleth
    └── points (lat/lon)           → Bubble map
```

Anti-patterns (always avoid, from the tree and the guides): pie charts
with more than 5 slices; 3D charts of any kind; dual axes with unrelated
metrics; line charts with more than 7 series; truncated y-axes on bar
charts; rainbow palettes with no semantic meaning.

## Rendering path (host-agnostic, zero added dependencies)

This skill mandates no library, runtime, or dashboard framework. Never
install npm/Node stacks, Vite/React apps, or cloud services to produce a
one-off publication chart. Render in this order:

1. The host client's native charting or visual-output capability, if one
   exists.
2. The environment's already-available static-image path (an installed
   plotting tool or charting skill).
3. If neither exists, deliver the chart specification (type, series,
   axes, annotations, palette) plus the tidy data table, and say plainly
   that the environment cannot render the image.

Whatever the path, the deliverable must still satisfy the design rules,
provenance block, and export section below.

## Design rules — the hard don'ts

- No 3D charts. 2D only.
- No dual x-axes. Put two stacked charts below each other instead.
- No decoration, drop shadows, gradients, or chart junk. Declutter: remove
  gridline noise, borders, unnecessary legends.
- Y-axis starts at zero and is evenly spaced. Inconsistent axes mislead.
- No rotated or vertical text. If labels do not fit, flip the chart so
  labels run horizontally along a horizontal axis.
- No overused guide lines; lighten or thin them so data stays high in the
  visual hierarchy and axes recede.
- Don't rely on colour alone: pair colour with direct labels, patterns,
  or ordering.

## Design rules — the dos

- Label series directly on the data where possible; a legend that can be
  replaced by direct labelling should be. If a legend remains, keep
  entries short and consistent ("EU residents, aged 18–40" not three
  near-identical long phrases).
- Show data values when there are few points; when too many, annotate the
  minimum, maximum, latest value, and any point the message rests on.
  Offer a data table beneath or beside the chart for verification.
- Annotate salient features in a few short sentences with pointer lines:
  surprising developments, outliers, the point that proves the message.
- Provide context inside the chart: missing data explicitly marked,
  uncertainty ranges or confidence bands, trendlines, benchmarks.
- Consistency across a set: same colour = same variable, same fonts,
  same layout in every chart of the publication.
- Use a standard layout, top to bottom: figure number → title → subtitle
  → legend → chart body → annotations → footnote → source/licence line.
- Fonts legible on screen, 12pt/px and larger; no cursive or novelty
  fonts; never distort fonts.

## Accessibility (WCAG-AA oriented)

- Roughly 1 in 12 men and 1 in 200 women have a colour vision deficiency.
  Pick a palette that survives colour-blindness simulation.
- Forbidden colour combinations: red/green/brown; pink/turquoise/grey;
  purple/blue.
- Contrast at least 4.5:1 for normal text, 3:1 for large text and graphic
  elements, against background and between data colours.
- Never encode meaning in colour alone — add labels, patterns, or
  position.

## Titles, subtitles, legends

- Title = the message, not the description. Fewer than 10 words:
  "'A' is the most popular letter" beats "Letters by popularity".
- Subtitle = the data description: geography, period, units ("Letters by
  popularity in the EU, 2022, in per cent").
- Spell out acronyms on first occurrence in titles, legends, and text.
- Legends explain every visual element; test on someone outside the
  field if possible.

## Writing around the chart

- The paragraph before the chart introduces concepts and highlights the
  finding; the paragraph after adds context and summarizes the takeaway.
- Match units between text and chart. Use exact dates, not "last year"
  or "recently".
- Make numbers human: rates, ratios, proportions ("1 in 7"), whole
  numbers, rounded approximations ("roughly", "about half"), a relatable
  scale when it helps.
- Plain language: short sentences (≈20–25 words max), short paragraphs
  (1–4 sentences), define terms on first use.
- For recurring/updated visuals, keep text generic: state values and let
  them update, or describe only stable methodology, so rewrites stay
  small.

## Provenance, licensing, GC specifics

- Under each chart, bottom corners, small/light text: author, data
  source, licence. Link the source name to the dataset.
- Statistics Canada: cite "Statistics Canada, table/tableau XX-XX-XX-XX"
  (or product number and name) plus the retrieval date. StatCan data is
  under the Statistics Canada Open Licence / Open Government Licence –
  Canada; reproduce licence symbols or link with the chart and credit
  "Adapted from Statistics Canada..." when you transform.
- Open Canada datasets: cite the title, the department, the record or
  resource URL, and the licence stated in the dataset metadata (often
  Open Government Licence – Canada 2.0). Respect what the metadata says;
  a resource with no open licence is treated as third-party and needs
  permission before publication.
- Third-party (non-Crown) data or visuals: obtain permission, keep proof,
  and credit per the licence — possibly differing from the publication's
  general notice.
- In the accompanying text or data section, introduce the data: coverage,
  dimensions, units, methodology, limitations, and a link to the source.
- Never invent or reconstruct a URL for the source. Cite the resource URL
  verbatim from the API response or dataset metadata, or cite the dataset
  ID without a link.

## Alt text and metadata (always attach)

- Alt text formula: "[Chart type] of [type of data] where [reason the
  chart is included]." Example: "Line chart of hectares burnt in Europe
  in 2020–2022, where 2022 clearly has the highest rates even though the
  year is not over."
- Also record: title, subtitle, description, date, author, source,
  copyright/licence, keywords.

## Export

- Default: PNG (fixed, portable) and SVG (editable, scalable) if the
  rendering path supports it.
- Offer aspect variants on request: 16:9 for slides, 1:1 for social,
  portrait for print.
- The exported file must carry the provenance block; a bare chart image
  loses its source the moment it travels.
- Also offer the underlying data as a tidy CSV/JSON (see next section)
  whenever the chart is published, not just shown in chat.

## Data hygiene for the chart's data table

- One header row starting at A1, no merged cells, one variable per
  column, one observation per row.
- Explicit nulls ("null", not 0 or blank), units in the column header,
  ISO 8601 dates (YYYY-MM-DD), no colour coding in cells.
- Name files after their content; one table per file.

## Pre-delivery checklist (run through silently, report gaps)

1. Message stated in one sentence; chart type matches it and the data.
2. No 3D, no dual axes, y-axis from zero, no rotated text, decluttered.
3. Colour-blind-safe palette; contrast ≥ 4.5:1 text / 3:1 graphics;
   meaning never in colour alone.
4. Message title, descriptive subtitle, units stated.
5. Values shown or key points annotated; missing data marked.
6. Provenance block: author, source, date, licence.
7. Alt text written; metadata recorded.
8. Text around the chart matches units and claims.
9. Rendered PNG (+SVG) via an available path — or the specification plus
   data delivered with the limitation stated.
10. Tidy data file offered.

Report the checklist result in one line with the deliverables. Every
delivery ends with an offer of the data query trail (the SQL/API calls
behind the numbers) so the user can verify or reproduce.
