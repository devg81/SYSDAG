"""Rebuild configs/indian_population.yaml environment.air_quality.by_state (D021).

Input: data/cpcb-aqi.parquet from github.com/Vonter/india-cpcb-aqi (ODbL-1.0,
CPCB hourly station AQI). Station mean over the year's hourly values ->
city mean -> state mean, keeping stations with >=50% of hours reporting.
States are mapped onto the Census-2011 names the generator uses.

    python ingestion/cpcb_state_aqi.py path/to/cpcb-aqi.parquet [--year 2023]
"""

from __future__ import annotations

import argparse

import pandas as pd

CENSUS_2011_NAMES = {"Telangana": "Andhra Pradesh", "Odisha": "Orissa"}
MIN_HOURLY_COVERAGE = 0.5


def state_aqi(parquet_path: str, year: int) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)
    df = df[pd.to_datetime(df["Date"]).dt.year == year]
    hours = [c for c in df.columns if c[:2].isdigit()]
    # "Station ID" is per-city in this source; "Station Name" is the station.
    long = df.melt(id_vars=["State", "City", "Station Name"], value_vars=hours, value_name="aqi")
    stations = (
        long.dropna(subset=["aqi"])
        .groupby(["State", "City", "Station Name"])["aqi"]
        .agg(["mean", "size"])
        .reset_index()
    )
    hours_in_year = 24 * (366 if pd.Timestamp(year=year, month=12, day=31).dayofyear == 366 else 365)
    stations["State"] = stations["State"].replace(CENSUS_2011_NAMES)
    kept = stations[stations["size"] / hours_in_year >= MIN_HOURLY_COVERAGE]
    cities = kept.groupby(["State", "City"])["mean"].mean().reset_index()
    out = cities.groupby("State").agg(aqi=("mean", "mean"), cities=("City", "nunique"))
    out = out.join(kept.groupby("State").size().rename("stations"))
    out = out.join(stations.groupby("State").size().rename("stations_any"), how="outer")
    return out.round({"aqi": 1})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("parquet")
    parser.add_argument("--year", type=int, default=2023)
    args = parser.parse_args()
    print(state_aqi(args.parquet, args.year).sort_values("aqi").to_string())
