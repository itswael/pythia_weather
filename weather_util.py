from __future__ import annotations
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import xarray as xr
import fsspec
import s3fs
from pathlib import Path
from datetime import date, datetime
from typing import Any, Dict, Iterable
from config import ELEVATION_FILE, META, NASA_POWER_S3_BASE, variable_map
from config import ELEVATION, REFHT, WNDHT, TAV, AMP

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

def convert_to_wth_format(data_dict: Dict[str, Any], 
                         station_name: str = "S3PWR",
                         elevation: float = 0.0) -> str:
    """Convert NASA POWER data to ICASA .wth format.
    
    Args:
        data_dict: Dictionary with 'records' key containing daily data
        station_name: 4-character station identifier
        elevation: Station elevation in meters
        
    Returns:
        String in ICASA .wth format
    """
    if "error" in data_dict:
        raise ValueError(f"Cannot convert data with error: {data_dict['error']}")
    
    records = data_dict.get("records", [])
    if not records:
        raise ValueError("No data records found")
    
    # Extract metadata
    latitude = data_dict.get("latitude", 0.0)
    longitude = data_dict.get("longitude", 0.0)

    # get elevation data
    ELEVATION = get_elevation(latitude, longitude)
    
    # Build header
    wth_lines = []
    wth_lines.append(META)
    # Use consistent field widths that can handle negative values and larger numbers
    # INSI: 6 chars, WTHLAT: 8 chars, WTHLONG: 8 chars, WELEV: 7 chars, TAV: 5 chars, AMP: 5 chars, REFHT: 6 chars, WNDHT: 6 chars
    wth_lines.append(f"  {station_name:>4} {latitude:>8.1f} {longitude:>8.1f} {ELEVATION:>7.2f} {TAV:>5.1f} {AMP:>5.1f} {REFHT:>6.0f} {WNDHT:>6.0f}")
    wth_lines.append("")
    
    # Determine available variables and create header
    sample_record = records[0]

    # Find which variables are available
    available_vars = []
    header_vars = ['DATE']
    for nasa_var, icasa_var in variable_map.items():
        if nasa_var in sample_record:
            available_vars.append((nasa_var, icasa_var))
            header_vars.append(icasa_var)
    
    # Add data header
    wth_lines.append("@  DATE" + "".join(f"{var:>8}" for var in header_vars[1:]))
    
    # Add data records
    for record in records:
        date_str = record['date']
        # Format: YYYYDDD (4-digit year + day of year)
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        # Calculate day of year
        date_obj = datetime(year, month, day)
        day_of_year = date_obj.timetuple().tm_yday
        
        formatted_date = f"{year}{day_of_year:03d}"
        
        # Build data line
        data_line = f"{formatted_date:>7}"
        for nasa_var, icasa_var in available_vars:
            value = record.get(nasa_var, -99.0)
            if value is None or pd.isna(value):
                value = -99.0
            data_line += f"{value:8.1f}"
        
        wth_lines.append(data_line)
    
    return "\n".join(wth_lines)

def save_wth_data(wth_content: str, 
                  filepath: Path ) -> str:
    """Save .wth formatted data with consistent Unix-style line endings.
    
    This ensures the file is readable on any platform (Windows, Linux, macOS)
    without extra blank lines appearing.
    
    Args:
        wth_content: ICASA .wth format content
        filepath: Path where the file should be saved
        
    Returns:
        Path to the saved file
    """
    
    # Normalize line endings to Unix style (\n) for cross-platform compatibility
    # This prevents double line spacing issues when transferring between systems
    normalized_content = wth_content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Save data with newline='' to prevent Python from converting line endings
    # Use UTF-8 encoding for universal compatibility
    with open(filepath, "w", encoding="utf-8", newline='') as f:
        f.write(normalized_content)
    
    return str(filepath)

def get_elevation(lat: float, lon: float) -> float:
    """
    Get elevation for a specific latitude and longitude.

    Parameters:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.
        welev_data (xarray.Dataset): Loaded WELEV dataset.

    Returns:
        float: Elevation in meters.
    """

    welev_file=ELEVATION_FILE

    # Load the WELEV data
    ds = xr.open_dataset(welev_file)
    welev_data = ds['WELEV']

    # if direct data is to be used
    # elevation = welev_data.sel(y=lat, x=lon, method="nearest").values.item()
    
    # Interpolate to exact coordinates
    elevation = welev_data.interp(y=lat, x=lon, method='linear')
    
    return elevation.values.item()