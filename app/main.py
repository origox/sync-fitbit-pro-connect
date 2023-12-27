import os, schedule, time, logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fitbit import fitbit
from db import db
from syncronizer import syncronizer

# Load environment variables
load_dotenv()


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(os.getenv(key="FITBIT_LOG_FILE_PATH")),
            logging.StreamHandler(),
        ],
    )

    fitbitClient = fitbit.FitbitClient()

    dbClient = db.InfluxDBClient(
        host=os.getenv(key="INFLUXDB_HOST"),
        token=os.getenv(key="INFLUXDB_TOKEN"),
        org=os.getenv(key="INFLUXDB_ORG"),
        database=os.getenv(key="INFLUXDB_DATABASE"),
    )

    ### test
    date = datetime.now()
    date_str = date.strftime("%Y-%m-%d")
    resource_list = [
        ("calories", "Calories_Intraday", "1min", 1),
        ("distance", "Distance_Intraday", "1min", 1000),
        ("steps", "Steps_Intraday", "1min", 1),
        ("heart", "HeartRate_Intraday", "1min", 1),
    ]

    # Setup syncronizer
    syncHelper = syncronizer.Syncronizer(fitbitClient=fitbitClient, dbClient=dbClient)

    # only for testing
    for i in range(0, 10):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        syncHelper.SyncFitbitActivitiesToInfluxdb(date_str)
    syncHelper.SyncFitbitToInfluxdb("2023-12-20", "2023-12-27")
    print("Done")

    # Schedule syncronizer
    schedule.every(interval=1).minutes.do(
        job_func=syncHelper.SyncFitbitActivitiesToInfluxdb,
        date=datetime.now().strftime("%Y-%m-%d"),
    )

    schedule.every(interval=1).minutes.do(
        job_func=syncHelper.SyncFitbitToInfluxdb,
        start_date=datetime.now().strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"),
        # start_date="2023-12-01",
        # end_date="2023-12-10",
    )

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()