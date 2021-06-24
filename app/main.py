import os

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import noaa_database as db
import noaa_logger

app = FastAPI()

LOGGER = noaa_logger.LOGGER

NOAA_CDO_API_URL_BASE = "https://www.ncdc.noaa.gov/cdo-web/api/v2/"

NOAA_CDO_UNITS = "standard"
NOAA_CDO_DATASET_ID = "GHCND"
NOAA_CDO_FETCH_LIMIT = 20
NOAA_CDO_DAILY_DATASET_ID = "GHCND"

# Grab the config and make sure we have everything
noaa_db_host, noaa_db_name = None, None
noaa_db_username, noaa_db_password = None, None
noaa_cdo_token = None


class StationId(BaseModel):
    station_id: str


try:
    noaa_db_host = os.environ['NOAA_DB_HOST']
    noaa_db_name = os.environ['NOAA_DB_NAME']
    noaa_db_username = os.environ['NOAA_DB_USERNAME']
    noaa_db_password = os.environ['NOAA_DB_PASSWORD']
    noaa_cdo_token = os.environ['NOAA_CDO_TOKEN']

except KeyError as ke:
    print("Key not found %s", ke)
    exit(42)

database = db.NOAADatabase(noaa_db_host,
                           noaa_db_name,
                           noaa_db_username,
                           noaa_db_password)

# noinspection PyBroadException
try:
    database.connect_to_db()
except Exception:
    LOGGER.error("Could not connect to database after 10 retries.")
    exit(42)


def get_station_data(station_id):
    result = None
    url = NOAA_CDO_API_URL_BASE + "stations/%s" % station_id.station_id

    headers = {
        'token': noaa_cdo_token
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        result = response.json()
    else:
        LOGGER.error(
            "get_station_data Failed. Error Code: %s Error: %s" % (
                response.status_code, response.content))
        result = (response.status_code, response.content)

    return result


def get_weather_data(dataset_id,
                     station_id,
                     start_date="2021-01-01",
                     end_date="2021-05-20",
                     offset=1):
    result = []
    url = NOAA_CDO_API_URL_BASE + "data"

    headers = {
        'token': noaa_cdo_token
    }

    params = {
        'datasetid': dataset_id,
        'stationid': station_id,
        'startdate': start_date,
        'enddate': end_date,
        'units': NOAA_CDO_UNITS,
        'limit': NOAA_CDO_FETCH_LIMIT,
        'offset': offset
    }

    response = requests.get(url,
                            headers=headers,
                            params=params)

    if response.status_code == 200:
        resp_dict = response.json()

        result.extend(resp_dict['results'])
        # todo error check all this
        next_offset = resp_dict['metadata']['resultset']['offset'] + \
            resp_dict['metadata']['resultset']['limit']
        count = resp_dict['metadata']['resultset']['count']

        if next_offset < count:
            result.extend(get_weather_data(dataset_id,
                                           station_id,
                                           start_date,
                                           end_date,
                                           next_offset))
    else:
        LOGGER.error(
            "Search failed. Error Code: %s Error: %s" % (
                response.status_code, response.content))

    return result


@app.get("/stations")
def get_all_stations():
    pass


@app.get("/stations/{station_id}")
def get_station(station_id):
    pass
#     elif len(result) == 0:
#     self.logger.debug(
#         "Got station_id: %s from DB." % len(result))
# else:
# self.logger.debug(
#     "Got station_id: %s from DB." % len(result))


@app.post("/stations")
def add_station(station_id: StationId):
    result = False
    station_data = get_station_data(station_id)

    if isinstance(station_data, tuple):
        raise HTTPException(
            status_code=500,
            detail="Error from NOAA API: %s - %s" % station_data)

    if isinstance(station_data, dict):
        if station_data:
            result = database.insert_station(
                (
                    station_data.get('id'),
                    station_data.get('name'),
                    station_data.get('latitude'),
                    station_data.get('longitude'),
                    station_data.get('elevation'),
                    station_data.get('elevation_unit'),
                    station_data.get('mindate'),
                    station_data.get('maxdate'),
                    station_data.get('datacoverage'),
                )
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="Station id %s not found by NOAA API." %
                       station_id/station_id)
    else:
        raise HTTPException(status_code=500, detail="Unknown error occurred.")

    if result:
        return station_data
    else:
        raise HTTPException(status_code=500,
                            detail="Error inserting station in database.")


@app.get("/daily/{station_id}")
def update_daily_weather_for_station(station_id: str):
    data = get_weather_data(NOAA_CDO_DAILY_DATASET_ID, station_id)
    row_tuples = []

    for row in data:
        row_tuples.append(
            (row['date'], row['station'], row['datatype'],
             row.get('attributes'), row['value'])
        )

    if not database.insert_daily_weather_records(row_tuples):
        raise HTTPException(
            status_code=500,
            detail="An error occurred while inserting records into the "
                   "database.\nPlease check the logs for more details.")

    return {'Records inserted': len(row_tuples)}


# This is for debugging, for more info read:
# https://fastapi.tiangolo.com/tutorial/debugging/#about-__name__-__main__
if __name__ == "__main__":
    uvicorn.run(app)
    # What else do I need?
    # add/remove station
    # method to get all data for a station based on min/max
    # method to get latest data based on last station data date
    # method to update all stations at once
    # method to refresh/ update/overwrite existing data
