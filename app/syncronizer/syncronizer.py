from fitbit import fitbit
from db import db
import logging

resource_list = [
    ("calories", "Calories_Intraday", "1min", 1),
    ("distance", "Distance_Intraday", "1min", 1000),
    ("steps", "Steps_Intraday", "1min", 1),
    ("heart", "HeartRate_Intraday", "1min", 1),
]


class Syncronizer:
    """Methods to syncronize data between Fitbit and InfluxDB"""

    def __init__(self, fitbitClient: fitbit.FitbitClient, dbClient: db.InfluxDBClient):
        """Initialize Syncronizer object

        fitbitClient: authenticated fitbit client
        dbClient: authenticated influxdb client
        """
        self.fitbitClient = fitbitClient
        self.dbClient = dbClient

        logging.info("Syncronizer initialized")

    def SyncFitbitActivitiesToInfluxdb(self, date: str) -> None:
        """Syncronize intradata for all resources/activities with 24 hours limit from Fitbit to InfluxDB

        date: date to syncronize
        resource_list: list of measurements to syncronize
        """
        logging.info(f"Syncing Fitbit activities for date: {date}")

        fitbit_data = self.fitbitClient.get_intraday_activity_by_date(
            date, resource_list
        )
        self.dbClient.write_points_to_influxdb(points=fitbit_data)

        fitbit_data = self.fitbitClient.get_intraday_heart_rate_by_date(date)
        self.dbClient.write_points_to_influxdb(points=fitbit_data)

        # Battery level
        fitbit_data = self.fitbitClient.get_battery_level()
        self.dbClient.write_points_to_influxdb(points=fitbit_data)

    def SyncFitbitToInfluxdb(
        self, start_date: str, end_date: str, start_time=None, end_time=None
    ) -> None:
        """Syncronize data from Fitbit to InfluxDB with 30 days or more limit

        start_date: from date to syncronize
        end_date: to date to syncronize
        start_time: not used at the moment
        end_time: not used at the moment
        """
        logging.info(f"Syncing Fitbit data from {start_date} to {end_date}")

        # HRV
        results = self.fitbitClient.get_intraday_hrv_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # Body data
        results = self.fitbitClient.get_body_data_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # Temperature - Skin
        results = self.fitbitClient.get_temperature_skin_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # CardioScore - VO2Max
        results = self.fitbitClient.get_vo2max_cardio_score_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # Sleep
        results = self.fitbitClient.get_sleep_log_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # Breathing
        results = self.fitbitClient.get_breathing_rate_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # SP02 Intraday
        results = self.fitbitClient.get_spo2_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # SP02 Summary
        results = self.fitbitClient.get_spo2_summary_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)

        # Activity Summary
        results = self.fitbitClient.get_activity_summary_by_interval(
            start_date=start_date, end_date=end_date
        )
        self.dbClient.write_points_to_influxdb(points=results)
