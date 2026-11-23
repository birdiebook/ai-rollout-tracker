"""Model capability from Epoch AI's benchmarking hub (`benchmark_data.zip`, CC BY 4.0).

Two capability measures, both per Epoch model (Epoch's `Model` / `model_group` name):

- ECI (`epoch_capabilities_index/eci_scores.csv`): one score per model plus its release `date`. ECI is an
  IRT fit that Epoch re-estimates when models and benchmarks are added, so every value is *today's*
  estimate. Using it for past months leaks later information (source="backfill").
- GPQA Diamond, Epoch's own runs (`gpqa_diamond.csv`): one row per run of a model version, with
  `Started at` (when Epoch started the run). known_from = Started at + RUN_DELAY_DAYS. A model's
  score at a date = the best score among its versions (reasoning-effort settings) known by then.
  `model_metadata.csv` maps each run's `Model version` to the Epoch model name.
"""

from __future__ import annotations

import io
import zipfile

import pandas as pd

from ai_tracker import http

URL = "https://epoch.ai/data/benchmark_data.zip"
SOURCE = "epoch_benchmarks"
RUN_DELAY_DAYS = 7  # conservative delay from run start to publication on the hub (phase 1 proposal)


def fetch_zip() -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(http.get(URL, SOURCE, timeout=120).content))


def _read(z: zipfile.ZipFile, name: str) -> pd.DataFrame:
    matches = [n for n in z.namelist() if n == name or n.endswith("/" + name)]
    if not matches:
        raise KeyError(f"{name} not in {URL}")
    return pd.read_csv(z.open(matches[0]))


def parse_eci(eci_scores: pd.DataFrame) -> pd.DataFrame:
    """model, organization, release (Timestamp), eci."""
    df = eci_scores.rename(columns={"Model": "model", "Organization": "organization", "date": "release"})
    df["release"] = pd.to_datetime(df["release"])
    return df[["model", "organization", "release", "eci"]].dropna(subset=["model", "eci"]).reset_index(drop=True)


def parse_gpqa(runs: pd.DataFrame, model_metadata: pd.DataFrame) -> pd.DataFrame:
    """One row per run: model, version, organization, release, score, known_from."""
    groups = (model_metadata.dropna(subset=["model_version", "model_group"])
              .drop_duplicates("model_version").set_index("model_version")["model_group"])
    df = pd.DataFrame({
        "version": runs["Model version"],
        "model": runs["Model version"].map(groups),
        "organization": runs["Organization"],
        "release": pd.to_datetime(runs["Release date"]),
        "score": runs["mean_score"],
        "started": pd.to_datetime(runs["Started at"], utc=True).dt.tz_localize(None),
    })
    df = df.dropna(subset=["model", "score", "started"])
    df["known_from"] = df["started"].dt.normalize() + pd.Timedelta(days=RUN_DELAY_DAYS)
    return df.drop(columns="started").reset_index(drop=True)


def load(z: zipfile.ZipFile | None = None) -> dict[str, pd.DataFrame]:
    z = z or fetch_zip()
    return {"eci": parse_eci(_read(z, "eci_scores.csv")),
            "gpqa": parse_gpqa(_read(z, "gpqa_diamond.csv"), _read(z, "model_metadata.csv"))}
