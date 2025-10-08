
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