#!/usr/bin/env python3
"""Build the unified catalog cache: CKAN + StatCan WDS cubes + Bank of Canada Valet.

Fetches inventory metadata only (no dataset contents) and writes one unified
Parquet dataset partitioned by source to ~/.cache/psai/catalog-cache/.

Run: uv run --with duckdb scripts/build_catalog_cache.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

import duckdb

CACHE_DIR = os.path.expanduser("~/.cache/psai/catalog-cache")
SINGLE_FILE = os.path.expanduser("~/.cache/psai/catalog-cache.parquet")
REFRESHED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%d")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

CKAN_BASE = "https://open.canada.ca/data/en/api/3/action/package_search"
WDS_URL = "https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesList"
VALET_SERIES = "https://www.bankofcanada.ca/valet/lists/series/json"
VALET_GROUPS = "https://www.bankofcanada.ca/valet/lists/groups/json"


def get_json(url: str, retries: int = 3) -> object:
    last_error = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - report last error on failure
            last_error = exc
    raise RuntimeError(f"failed after {retries} attempts: {url}: {last_error}")


def fetch_ckan(limit: int | None = None) -> list[dict]:
    """Paginate package_search (no q) to every dataset's metadata."""
    rows = []
    page_size = 1000
    start = 0
    while True:
        url = f"{CKAN_BASE}?rows={page_size}&start={start}"
        payload = get_json(url)
        if not payload.get("success"):
            raise RuntimeError(f"CKAN error at start={start}: {payload}")
        results = payload["result"]["results"]
        if not results:
            break
        for pkg in results:
            formats = sorted({r.get("format", "") for r in pkg.get("resources", [])} - {""})
            rows.append(
                {
                    "source": "ckan",
                    "id": pkg.get("id", ""),
                    "title": (pkg.get("title_translated") or {}).get("en", ""),
                    "publisher": (pkg.get("organization") or {}).get("title", ""),
                    "description": (pkg.get("notes_translated") or {}).get("en", ""),
                    "formats": ",".join(formats),
                    "url": f"https://open.canada.ca/data/en/dataset/{pkg.get('id', '')}",
                    "last_modified": pkg.get("metadata_modified", ""),
                    "refreshed_at": REFRESHED_AT,
                }
            )
        start += page_size
        print(f"ckan: fetched {start} of {payload['result']['count']}", file=sys.stderr)
        if limit and start >= limit:
            break
        if start >= payload["result"]["count"]:
            break
    return rows


def fetch_statcan() -> list[dict]:
    """One GET returns the entire cube inventory."""
    cubes = get_json(WDS_URL)
    if not isinstance(cubes, list):
        raise RuntimeError(f"WDS unexpected shape: {type(cubes)}")
    rows = []
    for cube in cubes:
        rows.append(
            {
                "source": "statcan",
                "id": str(cube.get("productId", "")),
                "title": cube.get("cubeTitleEn", ""),
                "publisher": "Statistics Canada",
                "description": cube.get("cubeTitleFr", ""),
                "formats": "CSV,SDMX",
                "url": f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={cube.get('productId', '')}",
                "last_modified": cube.get("releaseTime", ""),
                "refreshed_at": REFRESHED_AT,
            }
        )
    return rows


def fetch_valet() -> list[dict]:
    """Series and group catalogs (exact-match codes, label + description)."""
    rows = []
    for kind, url in (("series", VALET_SERIES), ("groups", VALET_GROUPS)):
        payload = get_json(url)
        for name, meta in (payload.get(kind) or {}).items():
            rows.append(
                {
                    "source": "valet",
                    "id": name,
                    "title": meta.get("label", ""),
                    "publisher": "Bank of Canada",
                    "description": meta.get("description", ""),
                    "formats": "JSON,CSV,XML",
                    "url": (
                        f"https://www.bankofcanada.ca/valet/observations/{name}/json"
                        if kind == "series"
                        else f"https://www.bankofcanada.ca/valet/observations/group/{name}/json"
                    ),
                    "last_modified": "",
                    "refreshed_at": REFRESHED_AT,
                }
            )
    return rows


def main() -> None:
    all_rows: list[dict] = []
    all_rows.extend(fetch_ckan())
    print(f"ckan: {sum(1 for r in all_rows if r['source'] == 'ckan')} datasets", file=sys.stderr)
    all_rows.extend(fetch_statcan())
    print(f"statcan: {sum(1 for r in all_rows if r['source'] == 'statcan')} cubes", file=sys.stderr)
    all_rows.extend(fetch_valet())
    print(f"valet: {sum(1 for r in all_rows if r['source'] == 'valet')} series/groups", file=sys.stderr)

    os.makedirs(CACHE_DIR, exist_ok=True)
    con = duckdb.connect()
    con.execute("DROP TABLE IF EXISTS catalog")
    columns = "source VARCHAR, id VARCHAR, title VARCHAR, publisher VARCHAR, description VARCHAR, formats VARCHAR, url VARCHAR, last_modified VARCHAR, refreshed_at VARCHAR"
    con.execute(f"CREATE TABLE catalog ({columns})")
    for row in all_rows:
        con.execute(
            "INSERT INTO catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [row[c] for c in ("source", "id", "title", "publisher", "description", "formats", "url", "last_modified", "refreshed_at")],
        )
    con.execute(
        f"COPY catalog TO '{CACHE_DIR}' (FORMAT PARQUET, PARTITION_BY (source), COMPRESSION ZSTD, OVERWRITE_OR_IGNORE)"
    )
    con.execute(
        f"COPY catalog TO '{SINGLE_FILE}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    count = con.execute("SELECT count(*) FROM catalog").fetchone()[0]
    con.close()
    print(f"wrote {count} rows to {CACHE_DIR}")


if __name__ == "__main__":
    main()
