
def download_weather_data(lat, lon, start_date, end_date, parameters):
    # check if the data file already exists
    ## get the file name from the directory
    ## get the lat, lon, start_date, end_date from the file name
    ## check if the lat, lon, start_date, end_date falls within the file name
    # if exists, return true
    #else execute the code to download the data
    ## if the date is older than 7 days, use the historical s3 bucket
    ## else use the api to get the data
    pass

async def get_Daily_S3_WTH(
        latitude=42.0,
        longitude=-93.5,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 3, 31)):

    # Fetch data from NASA POWER S3/Zarr
    df, ds_met, out = await get_power_s3_daily(
            latitude=42.0,
            longitude=-93.5,
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            include_srad=True,
            include_met=True
        )

    # fix the data values
    data_dict = _transform_values(df, out)

    # Convert to ICASA format
    icasa_format_data = convert_to_wth_format(data_dict, "NASA", 40.0)

    # Create data directory if it doesn't exist
    Path(DATA_DIR).mkdir(exist_ok=True)

    # Generate filename
    filename = f"NP{latitude}_{longitude}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.wth"
    filepath = Path(DATA_DIR) / filename

    # Save data
    save_wth_data(icasa_format_data, filepath)