from datetime import date
from typing import Any, Dict, Optional
import asyncio
import pandas as pd
import xarray as xr
from config import MERRA2DAILY_ZARR_HINT, SYN1DAILY_ZARR_HINT, MET_VARS, SOLAR_VARS, RenameMetVars, RenameSolarVars
from weather_util import _discover_daily_zarr, _open_power_zarr, _slice_point, _transform_values, convert_to_wth_format

async def get_power_s3_daily(latitude: float,
                             longitude: float,
                             start_date: date,
                             end_date: date,
                             include_srad: bool = True,
                             include_met: bool = True,
                             syn1_url: Optional[str] = None,
                             merra2_url: Optional[str] = None) -> tuple[pd.DataFrame, Dict[str, Any]]:
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
    df = None
    ds_sol = None
    ds_met = None
    try:
        # Open datasets (in threads to avoid blocking loop)
        
        if include_srad:
            url_sol = _resolve_syn1()
            ds_sol = await asyncio.to_thread(_open_power_zarr, url_sol)
            out["syn1_url"] = url_sol
        if include_met:
            url_met = _resolve_merra2()
            ds_met = await asyncio.to_thread(_open_power_zarr, url_met)
            out["merra2_url"] = url_met

        # Slice
        
        if ds_met is not None:
            sub_met = await asyncio.to_thread(
                _slice_point, ds_met, latitude, longitude, start_date, end_date, MET_VARS
            )
            df_met = sub_met.to_dataframe().reset_index().rename(
                columns=RenameMetVars
            )
            df = df_met
        if ds_sol is not None:
            sub_sol = await asyncio.to_thread(
                _slice_point, ds_sol, latitude, longitude, start_date, end_date, SOLAR_VARS
            )
            df_sol = sub_sol.to_dataframe().reset_index().rename(
                columns=RenameSolarVars
            )
            # Convert W/m^2 (mean power) to MJ/m^2/day
            df_sol["SRAD"] = df_sol["SRAD_WM2"].astype(float) * 0.0864
            df_sol = df_sol[["time", "SRAD"]]
            if df is None:
                df = df_sol
            else:
                df = pd.merge(df, df_sol, on="time", how="inner")

        if df is None:
            df = pd.DataFrame()
            out["error"] = "No data sources selected: set include_srad and/or include_met."
        
    except Exception as e:
        if df is None:
            df = pd.DataFrame()
            out["error"] = str(e)
    return (df, out)

async def get_Daily_S3_WTH(
        chirpsdata: pd.DataFrame,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        include_srad: bool,
        include_met: bool):

    # Fetch data from NASA POWER S3/Zarr
    df, out = await get_power_s3_daily(
            latitude,
            longitude,
            start_date,
            end_date,
            include_srad,
            include_met
        )
    df = df.merge(chirpsdata, on="time", how="left")
    # fix the data values
    data_dict = _transform_values(df, out)

    # Convert to ICASA format
    icasa_format_data = convert_to_wth_format(data_dict, "NASA", 40.0)

    return icasa_format_data
