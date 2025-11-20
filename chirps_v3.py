import os
import requests
import pandas as pd
import rioxarray
from datetime import datetime
from calendar import monthrange
from pathlib import Path

# Configuration Constants
DATA_DIR = './chirps_v3_data'
CHIRPS_V3_BASE_URL = 'https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl'

def check_existing_files(start_date, end_date, data_dir):
    """Check which CHIRPS V3 files already exist locally."""
    # start = datetime.strptime(start_date, '%Y-%m-%d')
    # end = datetime.strptime(end_date, '%Y-%m-%d')
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
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

def download_chirps_v3(missing_dates, data_dir, base_url):
    """Download missing CHIRPS V3 TIF files."""
    downloaded = []
    failed = []
    
    for date in missing_dates:
        year = date.year
        month = date.month
        day = date.day
        
        filename = f'chirps-v3.0.rnl.{year}.{month:02d}.{day:02d}.tif'
        filepath = Path(data_dir) / filename
        url = f'{base_url}/{year}/{filename}'
        
        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            downloaded.append(filepath)
            
        except Exception as e:
            failed.append((filename, str(e)))
    
    return {'downloaded': downloaded, 'failed': failed}

def load_chirps_data(file_paths, lat, lon):
    """Load CHIRPS V3 data and extract values for specific coordinates."""
    data = []
    
    for filepath in sorted(file_paths):
        filename = filepath.name
        parts = filename.split('.')
        year = int(parts[3])
        month = int(parts[4])
        day = int(parts[5])
        
        da = rioxarray.open_rasterio(filepath, masked=True)
        da = da.squeeze().drop_vars('band', errors='ignore')
        
        point_value = da.sel(x=lon, y=lat, method='nearest').values
        
        if hasattr(point_value, 'item'):
            point_value = point_value.item()
        
        if point_value < 0 or pd.isna(point_value):
            point_value = 0.0
        
        data.append({
            'year': year,
            'month': month,
            'day': day,
            'precip': float(point_value)
        })
        
        da.close()
    
    return data

def create_dataframe(data):
    """Convert data to DataFrame with DATE (yyyyddd) and CRAIN columns."""
    df = pd.DataFrame(data)
    
    df['time'] = pd.to_datetime(df[['year', 'month', 'day']])
    # df['day_of_year'] = df['date'].dt.dayofyear
    # df['DATE'] = df['year'] * 1000 + df['day_of_year']
    df['RAIN1'] = df['precip']
    
    result = df[['time', 'RAIN1']].copy()
    
    return result

def get_chirps_v3_data(latitude, longitude, start_date, end_date):
    """Main function to get CHIRPS V3 data for specified coordinates and date range."""
    file_status = check_existing_files(start_date, end_date, DATA_DIR)
    
    if file_status['missing_count'] > 0:
        download_result = download_chirps_v3(file_status['missing'], DATA_DIR, CHIRPS_V3_BASE_URL)
    else:
        print(f"All {file_status['total']} files already exist. Skipping download.")
    
    all_files = check_existing_files(start_date, end_date, DATA_DIR)['existing']
    raw_data = load_chirps_data(all_files, latitude, longitude)
    
    df = create_dataframe(raw_data)
    # print(df.head())
    
    return df

if __name__ == "__main__":
    latitude = 42.0
    longitude = -93.5
    start_date = '2020-01-01'
    end_date = '2020-01-31'
    
    get_chirps_v3_data(latitude, longitude, start_date, end_date)