from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional
import asyncio
import httpx
import os
from pathlib import Path

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

NASA_POWER_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"
async def make_nasa_request(params: Dict[str, Any]) -> str:
    """Make a request to the NASA POWER API with proper error handling."""
    async with httpx.AsyncClient() as client:
        response = await client.get(NASA_POWER_BASE, params=params, timeout=60.0)
        response.raise_for_status()
        print(len(response.text))
        with open("test.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
        return response.text


async def get_power_api_daily(latitude: float,
                              longitude: float,
                              start_date: date,
                              end_date: date,
                              parameters: str = "T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
                              community: str = "ag",
                              fmt: str = "icasa",
                              header: bool = True) -> str:
    """Fetch daily data from the NASA POWER API (AG community).

    Returns ICASA format data as text when fmt='icasa'.
    """
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


def save_icasa_data(data: str, latitude: float, longitude: float, start_date: date, end_date: date, data_dir: str = "data") -> str:
    """Save ICASA format data to a .wth file in the specified directory.
    
    Args:
        data: ICASA format data as string
        latitude: Latitude for filename
        longitude: Longitude for filename  
        start_date: Start date for filename
        end_date: End date for filename
        data_dir: Directory to save the file (default: "data")
        
    Returns:
        Path to the saved file
    """
    # Create data directory if it doesn't exist
    Path(data_dir).mkdir(exist_ok=True)
    
    # Generate filename based on coordinates and date range
    filename = f"NASA_POWER_{latitude}_{longitude}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.wth"
    filepath = Path(data_dir) / filename
    
    # Save data as-is without any modification
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(data)
    
    return str(filepath)


async def fetch_and_save_nasa_data(latitude: float,
                                   longitude: float,
                                   start_date: date,
                                   end_date: date,
                                   parameters: str = "T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
                                   data_dir: str = "data") -> str:
    """Fetch ICASA format data from NASA POWER API and save it to file.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        start_date: Start date for data
        end_date: End date for data
        parameters: NASA POWER parameters to fetch
        data_dir: Directory to save the file
        
    Returns:
        Path to the saved file
    """
    # Fetch data from NASA API in ICASA format
    icasa_data = await get_power_api_daily(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=parameters,
        fmt="icasa"
    )
    
    # Save data to file
    filepath = save_icasa_data(icasa_data, latitude, longitude, start_date, end_date, data_dir)
    
    return filepath


# Example usage
async def main():
    """Example usage of the NASA POWER API data fetching."""
    # Example coordinates (Iowa, USA)
    lat = 42.0
    lon = -93.5
    
    # Date range (last 30 days)
    start_date = date(2020, 1, 1)
    end_date = date(2020, 3, 31)
    if end_date.month == 1:
        start_date = start_date.replace(year=end_date.year - 1)
    
    try:
        # Fetch and save NASA POWER data in ICASA format
        filepath = await fetch_and_save_nasa_data(
            latitude=lat,
            longitude=lon,
            start_date=start_date,
            end_date=end_date,
            parameters="T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN"
        )
        
        print(f"Successfully saved NASA POWER data to: {filepath}")
        
    except Exception as e:
        print(f"Error fetching NASA data: {e}")


if __name__ == "__main__":
    asyncio.run(main())