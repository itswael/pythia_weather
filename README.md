# Pythia Weather Data Retrieval System

## Overview

The Pythia Weather Data Retrieval System is a Python-based application designed to fetch, process, and format meteorological data from NASA POWER (Prediction of Worldwide Energy Resources) databases. The system provides automated access to both real-time and historical weather data through two primary data sources: the NASA POWER API and AWS S3 Zarr archives.

## Features

- **Dual Data Sources**: Seamlessly switches between NASA POWER API and S3/Zarr archives based on data availability and age
- **ICASA Format Support**: Outputs weather data in ICASA (International Consortium for Agricultural Systems Applications) .wth format
- **Automatic Fallback**: Intelligent fallback mechanism between data sources for maximum reliability
- **Elevation Integration**: Automatic elevation lookup for precise weather station metadata
- **Asynchronous Processing**: Non-blocking data retrieval for improved performance
- **Comprehensive Error Handling**: Robust error management with informative feedback

## System Architecture

### Core Components

1. **Main Orchestrator** (`weather.py`)
   - Coordinates data retrieval workflow
   - Implements smart source selection logic
   - Manages file operations and validation

2. **API Interface** (`weather_via_API.py`)
   - Handles NASA POWER API requests
   - Optimized for recent data (last 7 days)
   - ICASA format direct output

3. **S3/Zarr Interface** (`weather_via_S3.py`)
   - Accesses historical data archives
   - Processes SYN1deg (solar) and MERRA-2 (meteorological) datasets
   - Optimized for historical data (older than 7 days)

4. **Utility Functions** (`weather_util.py`)
   - Data format conversion and processing
   - Elevation data integration
   - File I/O operations

5. **Configuration** (`config.py`)
   - System constants and parameters
   - API endpoints and variable mappings
   - File paths and naming conventions

## Data Sources

### NASA POWER API
- **Purpose**: Real-time and recent meteorological data
- **Optimal Use**: Data within the last 7 days
- **Format**: Direct ICASA output
- **Variables**: Temperature (max/min), precipitation, solar radiation

### AWS S3 Zarr Archives
- **Purpose**: Historical meteorological data
- **Optimal Use**: Data older than 7 days
- **Sources**:
  - **SYN1deg**: Solar radiation data (ALLSKY_SFC_SW_DWN)
  - **MERRA-2**: Meteorological variables (temperature, precipitation, etc.)
- **Format**: Zarr format with conversion to ICASA

## Supported Variables

### Meteorological Variables
- **T2M_MAX/TMAX**: Maximum daily temperature (°C)
- **T2M_MIN/TMIN**: Minimum daily temperature (°C)
- **PRECTOTCORR/RAIN**: Total precipitation (mm)
- **T2MDEW/TDEW**: Dew point temperature (°C)
- **WS2M/WIND**: Wind speed at 2 meters (m/s)
- **RH2M**: Relative humidity at 2 meters (%)

### Solar Variables
- **ALLSKY_SFC_SW_DWN/SRAD**: Solar radiation (converted from W/m² to MJ/m²/day)

## Installation

### Prerequisites
- Python 3.8 or higher
- Internet connection for data retrieval

### Dependencies Installation
```bash
pip install -r requirements.txt
```

### Key Dependencies
- `pandas`: Data manipulation and analysis
- `xarray`: Multi-dimensional array processing
- `httpx`: Async HTTP client for API requests
- `s3fs`: S3 filesystem interface
- `fsspec`: Filesystem specification
- `zarr`: Chunked, compressed array storage

## Usage

### Basic Usage

```python
import asyncio
from datetime import date
from weather import download_weather_data

# Download weather data for a specific location and date range
asyncio.run(download_weather_data(
    latitude=42.0,
    longitude=-93.5,
    start_date=date(2020, 1, 1),
    end_date=date(2020, 3, 31),
    include_srad=True,
    include_met=True,
    source="S3"  # or "API"
))
```

### Parameters

- **latitude** (float): Latitude coordinate (-90 to 90)
- **longitude** (float): Longitude coordinate (-180 to 180)
- **start_date** (date): Start date for data retrieval
- **end_date** (date): End date for data retrieval
- **include_srad** (bool): Include solar radiation data (default: True)
- **include_met** (bool): Include meteorological data (default: True)
- **source** (str): Preferred data source ("S3" or "API", default: "S3")

### Output Format

The system generates ICASA-formatted .wth files with the naming convention:
```
NP{latitude}_{longitude}_{start_date}_{end_date}.wth
```

Example: `NP42.0_-93.5_20200101_20200331.wth`

## Configuration

### Environment Variables
The system uses constants defined in `config.py`:

- **NASA_POWER_API_BASE**: NASA POWER API endpoint
- **NASA_POWER_S3_BASE**: AWS S3 base URL for POWER data
- **SYN1DAILY_ZARR_HINT**: Default SYN1deg Zarr location
- **MERRA2DAILY_ZARR_HINT**: Default MERRA-2 Zarr location

### Variable Mapping
The system automatically maps NASA POWER variables to ICASA standard names:
```python
variable_map = {
    'T2M': 'T2M',           # Average temperature
    'TMAX': 'TMAX',         # Maximum temperature
    'TMIN': 'TMIN',         # Minimum temperature
    'RAIN': 'RAIN',         # Precipitation
    'SRAD': 'SRAD',         # Solar radiation
    'T2MDEW': 'TDEW',       # Dew point temperature
    'WS2M': 'WIND',         # Wind speed
    'RH2M': 'RH2M'          # Relative humidity
}
```

## Data Processing Workflow

1. **Request Validation**: Validates input parameters and date ranges
2. **Source Selection**: Chooses optimal data source based on date recency
3. **Data Retrieval**: Fetches data from selected source with error handling
4. **Format Conversion**: Converts raw data to ICASA .wth format
5. **Elevation Integration**: Adds elevation data from WELEV dataset
6. **File Generation**: Saves formatted data to specified directory
7. **Fallback Handling**: Switches to alternative source if primary fails

## Error Handling

The system implements comprehensive error handling:

- **Network Errors**: Automatic retry and source switching
- **Data Availability**: Intelligent fallback between API and S3 sources
- **Format Errors**: Validation and correction of data formats
- **File System Errors**: Directory creation and permission handling

## File Structure

```
pythia_weather/
├── config.py              # Configuration constants
├── weather.py             # Main orchestrator
├── weather_via_API.py     # NASA POWER API interface
├── weather_via_S3.py      # S3/Zarr data interface
├── weather_util.py        # Utility functions
├── requirements.txt       # Python dependencies
├── welev_merra2_grid.nc   # Elevation dataset
└── data/                  # Output directory
    ├── *.wth             # Generated weather files
    └── ...
```

## Performance Considerations

- **Asynchronous Processing**: Non-blocking I/O operations for improved throughput
- **Caching**: Automatic detection of existing data files to avoid redundant downloads
- **Chunked Processing**: Efficient handling of large datasets through Zarr format
- **Connection Pooling**: Optimized HTTP connections for API requests

## Limitations

- **Geographic Coverage**: Limited to NASA POWER data coverage areas
- **Temporal Resolution**: Daily data only (no sub-daily resolution)
- **Real-time Latency**: Recent data may have 1-3 day delays
- **Variable Availability**: Some variables may not be available for all locations/dates

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check internet connectivity and firewall settings
2. **Data Unavailability**: Verify date ranges and geographic coordinates
3. **Permission Errors**: Ensure write permissions for output directory
4. **Dependency Issues**: Update packages using `pip install -r requirements.txt --upgrade`

### Debug Mode
Enable verbose logging by modifying the error handling sections in the code to include detailed exception information.

## Contributing

When contributing to this project:

1. Follow PEP 8 style guidelines
2. Add comprehensive docstrings to new functions
3. Include error handling for all external API calls
4. Test with various geographic locations and date ranges
5. Update documentation for any new features or changes

## License

This project is designed for educational and research purposes. Users should comply with NASA POWER data usage policies and terms of service.

## Support

For issues related to:
- **NASA POWER Data**: Consult NASA POWER documentation
- **Code Issues**: Review error messages and check input parameters
- **Performance**: Consider adjusting date ranges or using local caching

## Version History

- **v1.0**: Initial release with dual-source capability
- Current implementation includes automatic source selection and ICASA format output

---

*This documentation provides a comprehensive overview of the Pythia Weather Data Retrieval System. For specific implementation details, refer to the inline documentation within each module.*