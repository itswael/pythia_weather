## Constants

from pathlib import Path


NASA_POWER_API_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_S3_BASE = "https://nasa-power.s3.us-west-2.amazonaws.com/"

# Known daily Zarr roots (LST) for POWER ARD on AWS S3 (public/anonymous)
SYN1DAILY_ZARR_HINT = (
    "https://nasa-power.s3.us-west-2.amazonaws.com/"
    "syn1deg/temporal/power_syn1deg_daily_temporal_lst.zarr"
)
MERRA2DAILY_ZARR_HINT = (
    "https://nasa-power.s3.us-west-2.amazonaws.com/"
    "merra2/temporal/power_merra2_daily_temporal_lst.zarr"
)
# API Parameters
NASA_POWER_API_PARAMS = "T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN"

# Default variable sets
SOLAR_VARS = ["ALLSKY_SFC_SW_DWN"]  # SRAD source (W m^-2) -> convert to MJ m^-2 d^-1
MET_VARS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "T2MDEW", "WS2M", "RH2M"]

RenameMetVars = {"T2M_MAX": "TMAX", "T2M_MIN": "TMIN", "PRECTOTCORR": "RAIN"}
RenameSolarVars = {"ALLSKY_SFC_SW_DWN": "SRAD_WM2"}
variable_map = {
        'T2M': 'T2M',    # Average temperature (°C)
        'TMAX': 'TMAX',  # Maximum temperature (°C)
        'TMIN': 'TMIN',  # Minimum temperature (°C)
        'RAIN': 'RAIN',  # Precipitation (mm)
        'SRAD': 'SRAD',  # Solar radiation (MJ/m²/day)
        'T2MDEW': 'TDEW', # Dew point temperature (°C)
        'WS2M': 'WIND',   # Wind speed (m/s)
        'RH2M': 'RH2M'    # Relative humidity (%)
    }

# Output directory
DATA_DIR = Path("data")

# Elevation file
ELEVATION_FILE = Path("data/WELEV_0.1deg.nc")

#Default Values
ELEVATION = -99.0  # meters
REFHT = 2.0  # Reference height for temperature (m)
WNDHT = 2.0  # Reference height for wind speed (m)
TAV = -99.0  # Average temperature (°C)
AMP = -99.0  # Temperature amplitude (°C)