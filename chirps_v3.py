import os
import requests
import pandas as pd
import rioxarray
from datetime import datetime
from calendar import monthrange
from pathlib import Path

# Configuration Constants
LATITUDE = 42.0
LONGITUDE = -93.5
START_DATE = '2020-01-01'
END_DATE = '2020-01-31'
DATA_DIR = './chirps_v3_data'
CHIRPS_V3_BASE_URL = 'https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl'

def check_existing_files(start_date, end_date, data_dir):
    """Check which CHIRPS V3 files already exist locally."""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    
    existing_files = []
    missing_dates = []
    
    current = start
    while current <= end:
        year = current.year
        month = current.month
        day = current.day
        
        filename = f'chirps-v3.0.rnl.{year}.{month:02d}.{day:02d}.tif'
        filepath = Path(data_dir) / filename
        
        if filepath.exists():
            existing_files.append(filepath)
        else:
            missing_dates.append(current)
        
        current += pd.Timedelta(days=1)
    
    total_days = (end - start).days + 1
    return {
        'existing': existing_files,
        'missing': missing_dates,
        'total': total_days,
        'existing_count': len(existing_files),
        'missing_count': len(missing_dates)
    }