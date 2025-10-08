from __future__ import annotations
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import xarray as xr
import fsspec
import s3fs
from datetime import date, datetime
from typing import Any, Dict, Iterable
from config import NASA_POWER_S3_BASE

#find the daily LST zarr under a given prefix
def _discover_daily_zarr(prefix: str) -> str:
    """Discover a DAILY temporal LST Zarr under a given POWER product prefix.
    prefix examples: "nasa-power/syn1deg/temporal/" or "nasa-power/merra2/temporal/"
    Returns an HTTPS URL.
    """
    fs = s3fs.S3FileSystem(anon=True)
    keys = [p for p in fs.ls(prefix) if p.endswith(".zarr")]
    # Prefer names containing daily + temporal + lst
    for k in keys:
        low = k.lower()
        if ("daily" in low) and ("temporal" in low) and ("lst" in low):
            # Strip leading bucket name when forming HTTPS URL
            path = k.split("nasa-power/", 1)[1]
            return f"{NASA_POWER_S3_BASE}{path}"
    # Fallback: if nothing matches, raise
    raise RuntimeError(f"No DAILY LST Zarr found under {prefix}")

def _open_power_zarr(zarr_url: str) -> xr.Dataset:
    store = fsspec.get_mapper(zarr_url)
    return xr.open_zarr(store, consolidated=True)

def _slice_point(ds: xr.Dataset,
                 latitude: float,
                 longitude: float,
                 start_date: date,
                 end_date: date,
                 variables: Iterable[str]) -> xr.Dataset:
    avail = [v for v in variables if v in ds.data_vars]
    if not avail:
        raise KeyError("None of the requested variables are present. Available examples: "
                       + ", ".join(list(ds.data_vars)[:25]))
    sub = ds[avail].sel(lat=latitude, lon=longitude, method="nearest").sel(
        time=slice(datetime.combine(start_date, datetime.min.time()),
                   datetime.combine(end_date, datetime.min.time()))
    )
    return sub

def _transform_values(df: pd.DataFrame, out: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a dataframe to a WTH-like dictionary."""
    df["date"] = pd.to_datetime(df["time"]).dt.strftime("%Y%m%d")
    cols = ["date"] + [c for c in df.columns if c not in ("time", "lat", "lon", "date")]
    for c in cols:
        if c != "date":
            try:
                df[c] = df[c].astype(float).round(1)
            except Exception:
                pass
    records = df[cols].to_dict(orient="records")
    out["records"] = records
    out["variables"] = [c for c in cols if c != "date"]
    return out