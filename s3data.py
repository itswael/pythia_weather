from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional
import asyncio
from pathlib import Path

# S3/Zarr deps (install in venv: pip install xarray fsspec s3fs zarr pandas)
import xarray as xr
import fsspec
import s3fs
import pandas as pd

# =============================================================================
# GLOBAL CONFIGURATION VARIABLES
# =============================================================================

# Location coordinates (Gainesville, FL - UF campus)
LATITUDE = 42.0
LONGITUDE = -93.5
ELEVATION = 40  # meters above sea level
STATION_NAME = "GVFL"  # 4-character station code

# Time period for comparison
START_DATE = date(2020, 1, 1)
END_DATE = date(2020, 3, 31)  # 3 months for testing

# Output directory
DATA_DIR = Path("data")

# =============================================================================

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
NASA_POWER_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Known daily Zarr roots (LST) for POWER ARD on AWS S3 (public/anonymous)
SYN1DAILY_ZARR_HINT = (
    "https://nasa-power.s3.us-west-2.amazonaws.com/"
    "syn1deg/temporal/power_syn1deg_daily_temporal_lst.zarr"
)
MERRA2DAILY_ZARR_HINT = (
    "https://nasa-power.s3.us-west-2.amazonaws.com/"
    "merra2/temporal/power_merra2_daily_temporal_lst.zarr"
)

# Default variable sets
SOLAR_VARS = ["ALLSKY_SFC_SW_DWN"]  # SRAD source (W m^-2) -> convert to MJ m^-2 d^-1
MET_VARS = ["T2M_MAX", "T2M_MIN", "PRECTOTCORR", "T2MDEW", "WS2M", "RH2M"]

# ---------------------------------------------------------------------
# Helpers: POWER S3/Zarr (ARD)
# ---------------------------------------------------------------------

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
            return f"https://nasa-power.s3.us-west-2.amazonaws.com/{path}"
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


def _ds_to_records(ds: xr.Dataset) -> List[Dict[str, Any]]:
    df = ds.to_dataframe().reset_index()
    df["date"] = pd.to_datetime(df["time"]).dt.strftime("%Y%m%d")
    cols = ["date"] + [c for c in df.columns if c not in ("time", "lat", "lon", "date")]
    # round 1 decimal for numeric fields
    for c in cols:
        if c != "date":
            try:
                df[c] = df[c].astype(float).round(1)
            except Exception:
                pass
    return df[cols].to_dict(orient="records")


async def get_power_s3_daily(latitude: float,
                             longitude: float,
                             start_date: date,
                             end_date: date,
                             include_srad: bool = True,
                             include_met: bool = True,
                             syn1_url: Optional[str] = None,
                             merra2_url: Optional[str] = None) -> Dict[str, Any]:
    """Fetch daily data directly from POWER S3/Zarr (ARD), merging solar + meteorology.

    - Solar SRAD comes from SYN1deg: ALLSKY_SFC_SW_DWN (W m^-2) -> SRAD = *0.0864 (MJ m^-2 d^-1)
    - Meteorology (T2M_MAX, T2M_MIN, PRECTOTCORR, etc.) comes from MERRA-2.

    Returns a dict with `records` (list of per-day dictionaries) and metadata.
    """
    # Resolve URLs (try provided first; else discover; else fall back to hints)
    def _resolve_syn1() -> str:
        if syn1_url:
            return syn1_url
        try:
            return _discover_daily_zarr("nasa-power/syn1deg/temporal/")
        except Exception:
            return SYN1DAILY_ZARR_HINT

    def _resolve_merra2() -> str:
        if merra2_url:
            return merra2_url
        try:
            return _discover_daily_zarr("nasa-power/merra2/temporal/")
        except Exception:
            return MERRA2DAILY_ZARR_HINT

    out: Dict[str, Any] = {
        "source": "s3-zarr",
        "latitude": latitude,
        "longitude": longitude,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
    }

    try:
        # Open datasets (in threads to avoid blocking loop)
        ds_sol = None
        ds_met = None
        if include_srad:
            url_sol = _resolve_syn1()
            ds_sol = await asyncio.to_thread(_open_power_zarr, url_sol)
            out["syn1_url"] = url_sol
        if include_met:
            url_met = _resolve_merra2()
            ds_met = await asyncio.to_thread(_open_power_zarr, url_met)
            out["merra2_url"] = url_met

        # Slice
        df = None
        if ds_met is not None:
            sub_met = await asyncio.to_thread(
                _slice_point, ds_met, latitude, longitude, start_date, end_date, MET_VARS
            )
            df_met = sub_met.to_dataframe().reset_index().rename(
                columns={"T2M_MAX": "TMAX", "T2M_MIN": "TMIN", "PRECTOTCORR": "RAIN"}
            )
            df = df_met
        if ds_sol is not None:
            sub_sol = await asyncio.to_thread(
                _slice_point, ds_sol, latitude, longitude, start_date, end_date, SOLAR_VARS
            )
            df_sol = sub_sol.to_dataframe().reset_index().rename(
                columns={"ALLSKY_SFC_SW_DWN": "SRAD_WM2"}
            )
            # Convert W/m^2 (mean power) to MJ/m^2/day
            df_sol["SRAD"] = df_sol["SRAD_WM2"].astype(float) * 0.0864
            df_sol = df_sol[["time", "SRAD"]]
            if df is None:
                df = df_sol
            else:
                df = pd.merge(df, df_sol, on="time", how="inner")

        if df is None:
            return {**out, "error": "No data sources selected: set include_srad and/or include_met."}

        # Build records
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

    except Exception as e:
        out["error"] = str(e)
        return out


# =============================================================================
# ICASA .wth FORMAT CONVERSION
# =============================================================================

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
    
    # Build header
    wth_lines = []
    wth_lines.append("*WEATHER DATA : NASA POWER via S3/Zarr")
    wth_lines.append("")
    wth_lines.append("@ INSI      LAT     LONG  ELEV   TAV   AMP REFHT WNDHT")
    wth_lines.append(f"  {station_name:>4} {latitude:8.3f} {longitude:8.3f} {elevation:5.0f}  -99.0  -99.0  -99.0  -99.0")
    wth_lines.append("")
    
    # Determine available variables and create header
    sample_record = records[0]
    variable_map = {
        'TMAX': 'TMAX',  # Maximum temperature (°C)
        'TMIN': 'TMIN',  # Minimum temperature (°C)
        'RAIN': 'RAIN',  # Precipitation (mm)
        'SRAD': 'SRAD',  # Solar radiation (MJ/m²/day)
        'T2MDEW': 'TDEW', # Dew point temperature (°C)
        'WS2M': 'WIND',   # Wind speed (m/s)
        'RH2M': 'RHUM'    # Relative humidity (%)
    }
    
    # Find which variables are available
    available_vars = []
    header_vars = ['DATE']
    for nasa_var, icasa_var in variable_map.items():
        if nasa_var in sample_record:
            available_vars.append((nasa_var, icasa_var))
            header_vars.append(icasa_var)
    
    # Add data header
    wth_lines.append("@DATE  " + "".join(f"{var:>6}" for var in header_vars[1:]))
    
    # Add data records
    for record in records:
        date_str = record['date']
        # Format: YYDDD (2-digit year + day of year)
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        # Calculate day of year
        date_obj = datetime(year, month, day)
        day_of_year = date_obj.timetuple().tm_yday
        year_2digit = year % 100
        
        formatted_date = f"{year_2digit:02d}{day_of_year:03d}"
        
        # Build data line
        data_line = f"{formatted_date:>5}"
        for nasa_var, icasa_var in available_vars:
            value = record.get(nasa_var, -99.0)
            if value is None or pd.isna(value):
                value = -99.0
            data_line += f"{value:6.1f}"
        
        wth_lines.append(data_line)
    
    return "\n".join(wth_lines)


def save_wth_data(wth_content: str, 
                  latitude: float, 
                  longitude: float, 
                  start_date: date, 
                  end_date: date,
                  data_dir: str = "data") -> str:
    """Save .wth formatted data with s3** prefix in filename.
    
    Args:
        wth_content: ICASA .wth format content
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        start_date: Start date for filename
        end_date: End date for filename
        data_dir: Directory to save the file
        
    Returns:
        Path to the saved file
    """
    # Create data directory if it doesn't exist
    Path(data_dir).mkdir(exist_ok=True)
    
    # Generate filename with s3** prefix
    filename = f"s3power_{latitude}_{longitude}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.wth"
    filepath = Path(data_dir) / filename
    
    # Save data
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(wth_content)
    
    return str(filepath)


async def fetch_and_convert_nasa_s3_data(latitude: float,
                                         longitude: float,
                                         start_date: date,
                                         end_date: date,
                                         station_name: str = "S3PWR",
                                         elevation: float = 0.0,
                                         data_dir: str = "data") -> str:
    """Fetch NASA POWER data from S3 and convert to .wth format.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        start_date: Start date for data
        end_date: End date for data
        station_name: 4-character station identifier
        elevation: Station elevation in meters
        data_dir: Directory to save the file
        
    Returns:
        Path to the saved .wth file
    """
    # Fetch data from NASA POWER S3
    print(f"Fetching NASA POWER data for {latitude}, {longitude} from {start_date} to {end_date}")
    data_dict = await get_power_s3_daily(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        include_srad=True,
        include_met=True
    )
    
    if "error" in data_dict:
        raise RuntimeError(f"Failed to fetch NASA POWER data: {data_dict['error']}")
    
    print(f"Retrieved {len(data_dict['records'])} daily records")
    print(f"Available variables: {', '.join(data_dict.get('variables', []))}")
    
    # Convert to .wth format
    wth_content = convert_to_wth_format(data_dict, station_name, elevation)
    
    # Save to file with s3** prefix
    filepath = save_wth_data(wth_content, latitude, longitude, start_date, end_date, data_dir)
    
    return filepath


# Example usage
async def main():
    """Example usage of NASA POWER S3 data fetching and .wth conversion."""
    # Use coordinates from global configuration
    lat = LATITUDE
    lon = LONGITUDE
    start = START_DATE
    end = END_DATE
    
    try:
        # Fetch and convert NASA POWER data to .wth format
        filepath = await fetch_and_convert_nasa_s3_data(
            latitude=lat,
            longitude=lon,
            start_date=start,
            end_date=end,
            station_name=STATION_NAME,
            elevation=ELEVATION
        )
        
        print(f"Successfully saved NASA POWER data in .wth format to: {filepath}")
        
        # Show first few lines of the file
        with open(filepath, "r") as f:
            lines = f.readlines()[:15]
            print("\nFirst 15 lines of the .wth file:")
            for line in lines:
                print(line.rstrip())
        
    except Exception as e:
        print(f"Error processing NASA POWER data: {e}")


if __name__ == "__main__":
    asyncio.run(main())