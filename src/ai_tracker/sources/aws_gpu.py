"""AWS EC2 on-demand list prices for fixed GPU instance types, from the public Price List bulk files.

`https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/index.json` lists one archived version per
month back to 2015 (`versions`: id -> versionEffectiveBeginDate/EndDate, offerVersionUrl). The version id is the
publication time (`Publication Date` in the file itself, e.g. 20230905140324 = 2023-09-05 14:03:24Z, which is the
version for August 2023). So the id date is an honest known-from date: a price list is known from its publication.

Per version: `<id>/us-east-1/index.csv` (240-300 MB, streamed and filtered; only the matching rows are kept in
data/raw/aws_gpu/<id>.csv). Price = on-demand, Linux, shared tenancy, no pre-installed software, `CapacityStatus`
Used, usage type `BoxUsage:<type>` in US East (N. Virginia), divided by the number of GPUs in the instance.

Licence: no open licence. The file's disclaimer: "This pricing list is for informational purposes only. All prices
are subject to the additional terms included in the pricing pages on http://aws.amazon.com." publish=False.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

from ai_tracker import config, http
from ai_tracker.sources import vintages

BASE = "https://pricing.us-east-1.amazonaws.com"
INDEX = f"{BASE}/offers/v1.0/aws/AmazonEC2/index.json"
REGION = "us-east-1"
SOURCE = "aws_gpu"
RAW = config.REPO / "data" / "raw" / SOURCE
# instance type -> GPUs per instance (AWS instance pages: p4d 8x A100 40GB, p5 8x H100 80GB)
TYPES = {"p4d.24xlarge": 8, "p5.48xlarge": 8}
FIRST_VERSION = pd.Timestamp("2020-11-01")  # p4d launched 2020-11-02; earlier versions cannot hold these types
LICENSE = ("no open licence: AWS Price List disclaimer 'This pricing list is for informational purposes only. All "
           "prices are subject to the additional terms included in the pricing pages on http://aws.amazon.com.'")
KEEP = {"TermType": "OnDemand", "Tenancy": "Shared", "Operating System": "Linux", "Pre Installed S/W": "NA",
        "CapacityStatus": "Used", "Unit": "Hrs", "Currency": "USD"}


def parse_index(index: dict) -> pd.DataFrame:
    """version id, published (UTC timestamp from the id), begin (effective begin date)."""
    rows = []
    for vid, v in index.get("versions", {}).items():
        rows.append((vid, pd.to_datetime(vid, format="%Y%m%d%H%M%S"),
                     pd.Timestamp(v["versionEffectiveBeginDate"]).tz_localize(None)))
    return pd.DataFrame(rows, columns=["version", "published", "begin"]).sort_values("published").reset_index(drop=True)


def filter_rows(lines, types=TYPES) -> list[dict]:
    """Matching rows from the CSV lines (5 metadata lines, then the header)."""
    reader = csv.reader(lines)
    header = None
    out = []
    for row in reader:
        if header is None:
            if row and row[0] == "SKU":
                header = {h: i for i, h in enumerate(row)}
            continue
        it = row[header["Instance Type"]] if len(row) > header["Instance Type"] else ""
        if it not in types:
            continue
        if all(row[header[k]] == v for k, v in KEEP.items()) and row[header["usageType"]] == f"BoxUsage:{it}":
            out.append({"instance_type": it, "price_per_hour": float(row[header["PricePerUnit"]]),
                        "effective": row[header["EffectiveDate"]]})
    return out


def version_rows(version: str, cache: Path = RAW) -> pd.DataFrame:
    """Filtered rows of one version (cached; versions are immutable)."""
    p = cache / f"{version}.csv"
    if p.exists():
        return pd.read_csv(p)
    url = f"{BASE}/offers/v1.0/aws/AmazonEC2/{version}/{REGION}/index.csv"
    with requests.get(url, stream=True, timeout=600, headers={"User-Agent": http.DEFAULT_UA}) as r:
        r.raise_for_status()
        r.encoding = "utf-8"
        rows = filter_rows(r.iter_lines(chunk_size=1 << 20, decode_unicode=True))
    df = pd.DataFrame(rows, columns=["instance_type", "price_per_hour", "effective"])
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return df


def events_from(versions: pd.DataFrame, rows: dict[str, pd.DataFrame], instance_type: str) -> pd.DataFrame:
    """published = evidence = publication date of the version; value = USD per GPU-hour."""
    out = []
    for vid, pub in zip(versions["version"], versions["published"]):
        r = rows.get(vid)
        if r is None or r.empty:
            continue
        price = r.loc[r["instance_type"] == instance_type, "price_per_hour"]
        if len(price) == 1:  # ambiguous or missing: skip the version
            day = pub.normalize()
            out.append((day, float(price.iloc[0]) / TYPES[instance_type], day, "release"))
    return pd.DataFrame(out, columns=["published", "value", "evidence", "source"])


@lru_cache(maxsize=1)
def _all() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    index = http.get(INDEX, SOURCE).json()
    versions = parse_index(index)
    versions = versions[versions["published"] >= FIRST_VERSION].reset_index(drop=True)
    return versions, {v: version_rows(v) for v in versions["version"]}


def price_series(instance_type: str) -> pd.DataFrame:
    versions, rows = _all()
    return vintages.monthly(events_from(versions, rows, instance_type), vintages.last_complete_month())
