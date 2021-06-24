import psycopg2
import psycopg2.extras as extras
from retry import retry
import noaa_logger

METRIC_IMPORT_OK = "SUCCESSFUL_IMPORT"
METRIC_IMPORT_FAIL = "FAILED_IMPORT"
METRIC_VFS_SHUTDOWN = "VFS_SHUTDOWN"
METRIC_AWS_IMPORT_OK = "AWS_SUCCESSFUL_IMPORT"
METRIC_AWS_IMPORT_FAIL = "AWS_FAILED_IMPORT"


class NOOADatabaseException(Exception):
    pass


class NOAADatabase(object):
    def __init__(self, host, name, user, password):
        self.logger = noaa_logger.LOGGER
        self.host = host
        self.name = name
        self.username = user
        self.password = password
        self.connection = None

    #  Wait up to 17 mins attempting to reconnect
    @retry((Exception, psycopg2.DatabaseError), tries=10, delay=1, backoff=2)
    def connect_to_db(self):
        result = True
        conn_params = {
            "host": self.host,
            "database": self.name,
            "user": self.username,
            "password": self.password
        }

        if not self.connection:
            try:
                self.connection = psycopg2.connect(**conn_params)
        
                # create a cursor
                cur = self.connection.cursor()
        
                # execute a statement
                self.logger.debug('PostgreSQL database version:')
                cur.execute('SELECT version()')
        
                # display the PostgreSQL database server version
                db_version = cur.fetchone()
                self.logger.debug(db_version)
        
                # close communication with the PostgreSQL DB
                cur.close()
            except (Exception, psycopg2.DatabaseError) as error:
                self.logger.error("Error connecting to database:")
                self.logger.error(error)
                raise error
                
        return result

    def close(self):
        self.connection.close()

    def insert_values(self, records, sql):
        result = True
        cursor = self.connection.cursor()
        try:
            extras.execute_values(cursor, sql, records)
        except (Exception, psycopg2.Error) as error_ex:
            self.logger.error("Error executing the following sql: %s" % sql)
            self.logger.error("Error: " + str(error_ex))
            result = False
        else:
            try:
                self.connection.commit()
            except (Exception, psycopg2.Error) as error_ex:
                self.logger.error("Error on commit.")
                self.logger.error("Error: " + str(error_ex))
                self.connection.rollback()
                result = False
        finally:
            cursor.close()

        return result

    def get_values(self, sql, data=None):
        cursor = self.connection.cursor()
        try:
            if data:
                cursor.execute(sql, data)
            else:
                cursor.execute(sql)
            result = cursor.fetchall()
        except (Exception, psycopg2.Error) as error_ex:
            self.logger.error("Error executing the following sql: %s" % sql)
            self.logger.error("Error: " + str(error_ex))
            result = False
        finally:
            cursor.close()

        return result

    def get_stations(self):
        result = self.get_values('SELECT * FROM public.noaa_station')

        if result is False:
            self.logger.error("An error occurred while getting all stations.")
        else:
            self.logger.debug(
                "Returning %s stations from DB query." % len(result))

        return result

    def get_station(self, station_id):
        result = self.get_values(
            'SELECT * FROM public.noaa_station where station_id = %s',
            (station_id,))

        if result is False:
            self.logger.error("An error occurred while getting all stations.")
        else:
            self.logger.debug(
                "Got station_id: %s from DB." % station_id)

        return result

    def insert_station(self, station):
        upsert_sql = "INSERT INTO public.noaa_station( " \
                     "station_id, " \
                     "name, " \
                     "latitude, " \
                     "longitude, " \
                     "elevation, " \
                     "elevation_unit, " \
                     "mindate, " \
                     "maxdate, " \
                     "datacoverage) " \
                     "VALUES %s " \
                     "ON CONFLICT ON CONSTRAINT" \
                     "   noaa_station_pkey " \
                     "DO UPDATE " \
                     "SET (name, latitude, longitude, elevation," \
                     "elevation_unit, mindate, maxdate, datacoverage) = " \
                     "(EXCLUDED.name, EXCLUDED.latitude, EXCLUDED.longitude," \
                     "EXCLUDED.elevation, EXCLUDED.elevation_unit," \
                     "EXCLUDED.mindate, EXCLUDED.maxdate," \
                     "EXCLUDED.datacoverage);"
        return self.insert_values([station], upsert_sql)

    def insert_daily_weather_records(self, records):
        upsert_sql = "INSERT INTO public.noaa_daily( " \
                     "record_date," \
                     "station_id, " \
                     "datatype, " \
                     "attributes, " \
                     "value) " \
                     "VALUES %s " \
                     "ON CONFLICT ON CONSTRAINT" \
                     "   noaa_daily_pkey " \
                     "DO UPDATE " \
                     "SET (attributes, value) = " \
                     "(EXCLUDED.attributes, EXCLUDED.value);"

        return self.insert_values(records, upsert_sql)
