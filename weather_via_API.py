from __future__ import annotations
from datetime import date
from typing import Any, Dict
import httpx
from config import NASA_POWER_API_BASE, NASA_POWER_API_PARAMS

async def make_nasa_request(params: Dict[str, Any]) -> str:
    """Make a request to the NASA POWER API with proper error handling."""
    async with httpx.AsyncClient() as client:
        response = await client.get(NASA_POWER_API_BASE, params=params, timeout=60.0)
        response.raise_for_status()
        return response.text


async def get_Daily_API_WTH(latitude: float,
                              longitude: float,
                              start_date: date,
                              end_date: date,
                              include_srad: bool = True,
                              include_met: bool = True,
                              community: str = "ag",
                              fmt: str = "icasa",
                              header: bool = True) -> str:
    """Fetch daily data from the NASA POWER API (AG community).

    Returns ICASA format data as text when fmt='icasa'.
    """
    if not include_srad and not include_met:
        raise ValueError("At least one of include_srad or include_met must be True.")
    
    # Start with all parameters
    parameters = NASA_POWER_API_PARAMS
    
    # Filter out SRAD parameter if not requested
    if not include_srad:
        parameters = ",".join([p for p in parameters.split(",") if p != "ALLSKY_SFC_SW_DWN"])
    
    # Filter out meteorological parameters if not requested
    if not include_met:
        parameters = ",".join([p for p in parameters.split(",") if p not in ["T2M_MAX", "T2M_MIN", "PRECTOTCORR"]])

    params = {
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "latitude": latitude,
        "longitude": longitude,
        "community": community,
        "parameters": parameters,
        "format": fmt,
        "header": header,
    }

    return await make_nasa_request(params)

