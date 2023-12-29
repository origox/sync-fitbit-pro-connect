from influxdb_client_3 import InfluxDBClient3, InfluxDBError, Point
import logging


class InfluxDBClient:
    def __init__(self, host: str, token: str, org: str, database: str):
        self.host = host
        self.token = token
        self.org = org
        self.database = database
        self.verify_ssl: str = False

        try:
            self.client = InfluxDBClient3(
                host=self.host,
                token=self.token,
                org=self.org,
                database=self.database,
                verify_ssl=self.verify_ssl,
                timeout=60000,
            )
            logging.info("Successfully connected to influxdb database")

        except InfluxDBError as err:
            logging.error("Unable to connect with influxdb database! Aborted")
            raise InfluxDBError("InfluxDB connection failed:" + str(err))
        except Exception as err:
            logging.error("Unable to connect with influxdb database! Aborted")
            raise Exception("InfluxDB connection failed:" + str(err))

    def write_points_to_influxdb(self, points) -> None:
        try:
            # influxdbclient.write_points(points)
            self.client.write(record=points, write_precision="s")

            # Dummy write to flush the buffer!??
            point = (
                Point("measurement").tag("location", "paris").field("temperature", 70)
            )
            #### self.client.write(point)  # write synchronously

            logging.info("Successfully updated influxdb database with new points")
        except InfluxDBError as err:
            logging.error("Unable to connect2 with influxdb database! " + str(err))

        except Exception as err:
            logging.error("Unable to connect2 with influxdb database! " + str(err))
            logging.error(f"failing points: {points}")
