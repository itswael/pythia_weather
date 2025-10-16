import asyncio
from datetime import date
from pathlib import Path
from weather_util import save_wth_data
from weather_via_S3 import get_Daily_S3_WTH
from weather_via_API import get_Daily_API_WTH
from config import DATA_DIR

async def download_weather_data(
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        include_srad: bool = True,
        include_met: bool = True,
        source: str = "S3") -> None:
    
    # check if the data file already exists
    if validate_existing_data(latitude, longitude, start_date, end_date, DATA_DIR):
        print("Data file already exists. Skipping download.")
        return
    #else execute the code to download the data
    if source == "API":
        try:
            if (date.today() - end_date).days < 7:
                raise ValueError("Data older than 7 days not available in API.")
            icasa_format_data = await get_Daily_API_WTH(latitude, longitude, start_date, end_date, include_srad, include_met)
        except Exception as e:
            print(f"Error occurred while fetching data from API: {e}")
            print("Warning: Data might not be available in API for dates older than 7 days. Falling back to S3.")
            try:
                icasa_format_data = await get_Daily_S3_WTH(latitude, longitude, start_date, end_date, include_srad, include_met)
            except Exception as e:
                print(f"Error occurred while fetching data from S3: {e}")
            return

    ## if the date is older than 7 days, use the historical s3 bucket
    elif (date.today() - end_date).days > 7 and source == "S3":
        try:
            icasa_format_data = await get_Daily_S3_WTH(latitude, longitude, start_date, end_date, include_srad, include_met)
        except Exception as e:
            print(f"Error occurred while fetching data from S3: {e}")
            print("Warning: Data might not be available in S3 for the last 7 days. Falling back to API.")
            try:
                icasa_format_data = await get_Daily_API_WTH(latitude, longitude, start_date, end_date, include_srad, include_met)
            except Exception as e:
                print(f"Error occurred while fetching data from API: {e}")
                return

    # if the stated method fails, fallback to the other method
    
    # Create data directory if it doesn't exist
    Path(DATA_DIR).mkdir(exist_ok=True)

    # Generate filename
    filename = f"NP{latitude}_{longitude}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.WTH"
    filepath = Path(DATA_DIR) / filename

    # Save data
    try:
        save_wth_data(icasa_format_data, filepath)
    except Exception as e:
        print(f"Error occurred while saving data: {e}")

def validate_existing_data(
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        data_dir: Path = DATA_DIR) -> bool:
    """Check if data file already exists for given parameters."""

    ## get the file names from the directory
    ## get the lat, lon, start_date, end_date from the file name
    ## if the lat, lon, start_date, end_date falls within the file name, return true
    ## else return false
    return False
    

if __name__ == "__main__":
    asyncio.run(download_weather_data(42.0, -93.5, date(1996, 5, 16), date(1997, 3, 25)))