from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import os, base64, json, time, json, pytz, logging
import requests
from datetime import datetime, timedelta
import logging
import urllib3

# Disable warnings - risky buisness
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

LOCAL_TIMEZONE = pytz.timezone(os.environ.get("FITBIT_LOCAL_TIMEZONE"))
DEVICENAME = os.environ.get("FITBIT_DEVICENAME")


RESOURCE = {
    "calories": "calories",
    "steps": "steps",
    "distance": "distance",
    "floors": "floors",
    "elevation": "elevation",
}


class FitbitOauth2Client:
    def __init__(self, client_id, client_secret, token_path):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path

        try:
            self.access_token, self.refresh_token = self.load_tokens_from_file()

        except FileNotFoundError:
            logging.exception("No token file found, refreshing tokens")

            self.access_token, self.refresh_token = self._refresh_tokens(
                client_id=self.client_id,
                client_secret=self.client_secret,
            )

    def make_request(
        self,
        url: str,
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        request_type: str = "GET",
        auth: str = "Bearer",
        accept: str = "application/json",
        language: str = "de_DE",
    ):
        headers = headers or {}
        data = data or {}

        if request_type == "GET":
            headers.update(
                {
                    "Authorization": f"{auth} {self.access_token}",
                    "Accept": accept,
                    "Accept-Language": language,
                }
            )

        try:
            resp = self._send_request(url, headers, data, request_type)
            self._log_rate_limits(resp.headers)
            self._handle_response(resp, url, headers, data, request_type)

            return resp.json()

        except ConnectionError as e:
            logging.exception(e)

    def _send_request(self, url, headers, data, request_type):
        if request_type == "GET":
            return requests.get(url, headers=headers, data=data)
        elif request_type == "POST":
            return requests.post(url, headers=headers, data=data)
        else:
            raise Exception("Invalid request type")

    def _log_rate_limits(self, headers):
        rate_limit_headers = [
            "fitbit-rate-limit-remaining",
            "fitbit-rate-limit-limit",
            "fitbit-rate-limit-reset",
        ]

        for header in rate_limit_headers:
            if header in headers:
                logging.info(f"{header}: {int(headers.get(header))}")

    def _handle_response(self, resp, url, headers, data, request_type):
        if resp.status_code == 401:
            logging.info("Refreshing tokens")
            d = json.loads(resp.content.decode("utf-8"))
            if d["errors"][0]["errorType"] == "expired_token":
                self._refresh_tokens(self.client_id, self.client_secret)
                # Update the headers with the new access token
                headers["Authorization"] = f"Bearer {self.access_token}"
                # Resend the request with the refreshed tokens
                resp = self._send_request(url, headers, data, request_type)
        return resp

    def _refresh_tokens(self, client_id: str, client_secret: str) -> Dict:
        """Refresh access and refresh tokens"""
        self.access_token, self.refresh_token = self.load_tokens_from_file()
        url: str = "https://api.fitbit.com/oauth2/token"
        headers: dict = {
            "Authorization": "Basic "
            + base64.b64encode((client_id + ":" + client_secret).encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": self.refresh_token,
        }

        json_data = self.make_request(url, headers, data, "POST")
        self.access_token = json_data["access_token"]
        self.refresh_token = json_data["refresh_token"]

        logging.info(
            f"access_token: {self.access_token} - refresh_token: {self.refresh_token}"
        )

        tokens = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }
        with open(self.token_path, "w") as file:
            json.dump(tokens, file)

        return self.access_token, self.refresh_token

    def load_tokens_from_file(self):
        with open(self.token_path, "r") as file:
            tokens = json.load(file)
            return tokens.get("access_token"), tokens.get("refresh_token")


class FitbitClient:
    def __init__(
        self, client_id: str = None, client_secret: str = None, token_path: str = None
    ):
        self.client_id = client_id or os.getenv(key="FITBIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv(key="FITBIT_CLIENT_SECRET")
        self.token_path = token_path or os.getenv(key="TOKEN_FILE_PATH")

        self.client = FitbitOauth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_path=self.token_path,
        )

    def get_intraday_activity_by_date(self, date_str, measurement_list):
        collected_records = []
        for measurement in measurement_list:
            ur = (
                "https://api.fitbit.com/1/user/-/activities/"
                + measurement[0]
                + "/date/"
                + date_str
                + "/1d/"
                + measurement[2]
                + ".json"
            )

            logging.info(f"URL to request: {ur}")

            res = self.client.make_request(ur)

            data = res["activities-" + measurement[0] + "-intraday"]["dataset"]
            if data != None:
                for value in data:
                    log_time = datetime.fromisoformat(date_str + "T" + value["time"])
                    utc_time = (
                        LOCAL_TIMEZONE.localize(log_time)
                        .astimezone(pytz.utc)
                        .isoformat()
                    )
                    collected_records.append(
                        {
                            "measurement": measurement[1],
                            "time": utc_time,
                            "tags": {"Device": DEVICENAME},
                            "fields": {"value": int(value["value"] * measurement[3])},
                        }
                    )

                logging.info(
                    "Recorded " + measurement[1] + " intraday for date " + date_str
                )
            else:
                logging.error(
                    msg="Recording failed : "
                    + measurement[1]
                    + " intraday for date "
                    + date_str
                )

        return collected_records

    def get_intraday_hrv_by_interval(self, start_date: str, end_date: str):
        collected_records = []

        hrv_data_listx = self.client.make_request(
            "https://api.fitbit.com/1/user/-/hrv/date/"
            + start_date
            + "/"
            + end_date
            + ".json"
        )

        hrv_data_list = hrv_data_listx["hrv"]

        if hrv_data_list != None:
            for data in hrv_data_list:
                log_time = datetime.fromisoformat(data["dateTime"] + "T" + "00:00:00")
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "HRV_Intraday",
                        "time": utc_time,
                        "tags": {"Device": DEVICENAME},
                        "fields": {
                            "dailyRmssd": data["value"]["dailyRmssd"],
                            "deepRmssd": data["value"]["deepRmssd"],
                        },
                    }
                )
        return collected_records

    def get_intraday_heart_rate_by_date(self, date_str: str):
        collected_records = []
        ur = (
            "https://api.fitbit.com/1/user/-/activities/heart/date/"
            + date_str
            + "/1d/1min.json"
        )

        logging.info(f"URL to request: {ur}")

        HR_zones_data_list = self.client.make_request(ur)["activities-heart"]

        if HR_zones_data_list != None:
            for data in HR_zones_data_list:
                log_time = datetime.fromisoformat(data["dateTime"] + "T" + "00:00:00")
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "HR zones",
                        "time": utc_time,
                        "tags": {"Device": DEVICENAME},
                        "fields": {
                            "Normal": data["value"]["heartRateZones"][0]["minutes"],
                            "Fat Burn": data["value"]["heartRateZones"][1]["minutes"],
                            "Cardio": data["value"]["heartRateZones"][2]["minutes"],
                            "Peak": data["value"]["heartRateZones"][3]["minutes"],
                        },
                    }
                )
                if "restingHeartRate" in data["value"]:
                    collected_records.append(
                        {
                            "measurement": "RestingHR",
                            "time": utc_time,
                            "tags": {"Device": DEVICENAME},
                            "fields": {"value": data["value"]["restingHeartRate"]},
                        }
                    )
        return collected_records

    def get_body_data_by_interval(self, start_date: str, end_date: str):
        collected_records = []

        body_list = self.client.make_request(
            "https://api.fitbit.com/1/user/-/body/log/weight/date/"
            + start_date
            + "/"
            + end_date
            + ".json"
        )["weight"]

        if body_list != None:
            for data in body_list:
                log_time = datetime.fromisoformat(data["date"] + "T" + data["time"])
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "Body",
                        "time": utc_time,
                        "tags": {"Device": data["source"]},
                        "fields": {
                            "bmi": data["bmi"],
                            # "fat": data["fat"],
                            "weight": data["weight"],
                        },
                    }
                )
        return collected_records

    def get_temperature_skin_by_interval(self, start_date: str, end_date: str):
        collected_records = []

        temperature_list = self.client.make_request(
            "https://api.fitbit.com/1/user/-/temp/skin/date/"
            + start_date
            + "/"
            + end_date
            + ".json"
        )["tempSkin"]

        if temperature_list != None:
            for data in temperature_list:
                log_time = datetime.fromisoformat(data["dateTime"] + "T" + "00:00:00")
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "TempSkin",
                        "time": utc_time,
                        "tags": {"Device": DEVICENAME},
                        "fields": {
                            "temp": data["value"]["nightlyRelative"],
                        },
                    }
                )
        return collected_records

    # Get VO2 Max Summary by Interval
    def get_vo2max_cardio_score_by_interval(self, start_date: str, end_date: str):
        collected_records = []

        vo2_list = self.client.make_request(
            "https://api.fitbit.com/1/user/-/cardioscore/date/"
            + start_date
            + "/"
            + end_date
            + ".json"
        )["cardioScore"]

        if vo2_list != None:
            for data in vo2_list:
                log_time = datetime.fromisoformat(data["dateTime"] + "T" + "00:00:00")
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "CardioScore",
                        "time": utc_time,
                        "tags": {"Device": DEVICENAME},
                        "fields": {
                            "vo2Low": list(
                                map(int, data["value"]["vo2Max"].split("-"))
                            )[0],
                            "vo2High": list(
                                map(int, data["value"]["vo2Max"].split("-"))
                            )[1],
                        },
                    }
                )
        return collected_records

    def get_sleep_log_by_interval(self, start_date: str, end_date: str):
        collected_records = []

        sleep_data = self.client.make_request(
            "https://api.fitbit.com/1.2/user/-/sleep/date/"
            + start_date
            + "/"
            + end_date
            + ".json"
        )["sleep"]

        if sleep_data != None:
            for record in sleep_data:
                log_time = datetime.fromisoformat(record["startTime"])
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                try:
                    minutesLight = record["levels"]["summary"]["light"]["minutes"]
                    minutesREM = record["levels"]["summary"]["rem"]["minutes"]
                    minutesDeep = record["levels"]["summary"]["deep"]["minutes"]
                except:
                    minutesLight = record["levels"]["summary"]["asleep"]["minutes"]
                    minutesREM = record["levels"]["summary"]["restless"]["minutes"]
                    minutesDeep = 0

                collected_records.append(
                    {
                        "measurement": "Sleep Summary",
                        "time": utc_time,
                        "tags": {
                            "Device": DEVICENAME,
                            "isMainSleep": record["isMainSleep"],
                        },
                        "fields": {
                            "efficiency": record["efficiency"],
                            "minutesAfterWakeup": record["minutesAfterWakeup"],
                            "minutesAsleep": record["minutesAsleep"],
                            "minutesToFallAsleep": record["minutesToFallAsleep"],
                            "minutesInBed": record["timeInBed"],
                            "minutesAwake": record["minutesAwake"],
                            "minutesLight": minutesLight,
                            "minutesREM": minutesREM,
                            "minutesDeep": minutesDeep,
                        },
                    }
                )

                sleep_level_mapping = {
                    "wake": 3,
                    "rem": 2,
                    "light": 1,
                    "deep": 0,
                    "asleep": 1,
                    "restless": 2,
                    "awake": 3,
                }
                for sleep_stage in record["levels"]["data"]:
                    log_time = datetime.fromisoformat(sleep_stage["dateTime"])
                    utc_time = (
                        LOCAL_TIMEZONE.localize(log_time)
                        .astimezone(pytz.utc)
                        .isoformat()
                    )
                    collected_records.append(
                        {
                            "measurement": "Sleep Levels",
                            "time": utc_time,
                            "tags": {
                                "Device": DEVICENAME,
                                "isMainSleep": record["isMainSleep"],
                            },
                            "fields": {
                                "level": sleep_level_mapping[sleep_stage["level"]],
                                "duration_seconds": sleep_stage["seconds"],
                            },
                        }
                    )
                wake_time = datetime.fromisoformat(record["endTime"])
                utc_wake_time = (
                    LOCAL_TIMEZONE.localize(wake_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "Sleep Levels",
                        "time": utc_wake_time,
                        "tags": {
                            "Device": DEVICENAME,
                            "isMainSleep": record["isMainSleep"],
                        },
                        "fields": {
                            "level": sleep_level_mapping["wake"],
                            "duration_seconds": None,
                        },
                    }
                )
            logging.info(
                "Recorded Sleep data for date " + start_date + " to " + end_date
            )
        else:
            logging.error(
                "Recording failed : Sleep data for date "
                + start_date
                + " to "
                + end_date
            )

        return collected_records

    # Get last synced battery level of the device
    def get_battery_level(self):
        collected_records = []

        device = self.client.make_request(
            "https://api.fitbit.com/1/user/-/devices.json"
        )[0]

        if device != None:
            collected_records.append(
                {
                    "measurement": "DeviceBatteryLevel",
                    "time": LOCAL_TIMEZONE.localize(
                        datetime.fromisoformat(device["lastSyncTime"])
                    )
                    .astimezone(pytz.utc)
                    .isoformat(),
                    "fields": {"value": float(device["batteryLevel"])},
                }
            )
            logging.info("Recorded battery level for " + DEVICENAME)
        else:
            logging.error("Recording battery level failed : " + DEVICENAME)

        return collected_records

    # Breathing rate
    def get_breathing_rate_by_interval(self, start_date: str, end_date: str):
        collected_records = []
        br_data_list = self.client.make_request(
            "https://api.fitbit.com/1/user/-/br/date/"
            + start_date
            + "/"
            + end_date
            + ".json"
        )["br"]
        if br_data_list != None:
            for data in br_data_list:
                log_time = datetime.fromisoformat(data["dateTime"] + "T" + "00:00:00")
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "BreathingRate",
                        "time": utc_time,
                        "tags": {"Device": DEVICENAME},
                        "fields": {"value": data["value"]["breathingRate"]},
                    }
                )
            logging.info("Recorded BR for date " + start_date + " to " + end_date)
        else:
            logging.error(
                "Recording failed : BR for date " + start_date + " to " + end_date
            )

        return collected_records

    # Get SPo2 interval
    def get_spo2_by_interval(self, start_date: str, end_date: str):
        collected_records = []

        spo2_data_list = self.client.make_request(
            "https://api.fitbit.com/1/user/-/spo2/date/"
            + start_date
            + "/"
            + end_date
            + "/all.json"
        )
        if spo2_data_list != None:
            for days in spo2_data_list:
                data = days["minutes"]
                for record in data:
                    log_time = datetime.fromisoformat(record["minute"])
                    utc_time = (
                        LOCAL_TIMEZONE.localize(log_time)
                        .astimezone(pytz.utc)
                        .isoformat()
                    )
                    collected_records.append(
                        {
                            "measurement": "SPO2_Intraday",
                            "time": utc_time,
                            "tags": {"Device": DEVICENAME},
                            "fields": {
                                "value": float(record["value"]),
                            },
                        }
                    )
            logging.info("Recorded SPO2 for date " + start_date + " to " + end_date)

        return collected_records

    # Get SPo2 Summary
    def get_spo2_summary_by_interval(self, start_date: str, end_date: str):
        collected_records = []

        data_list = self.client.make_request(
            "https://api.fitbit.com/1/user/-/spo2/date/"
            + start_date
            + "/"
            + end_date
            + ".json"
        )
        if data_list != None:
            for data in data_list:
                log_time = datetime.fromisoformat(data["dateTime"] + "T" + "00:00:00")
                utc_time = (
                    LOCAL_TIMEZONE.localize(log_time).astimezone(pytz.utc).isoformat()
                )
                collected_records.append(
                    {
                        "measurement": "SPO2",
                        "time": utc_time,
                        "tags": {"Device": DEVICENAME},
                        "fields": {
                            "avg": data["value"]["avg"],
                            "max": data["value"]["max"],
                            "min": data["value"]["min"],
                        },
                    }
                )
            logging.info("Recorded Avg SPO2 for date " + start_date + " to " + end_date)
        else:
            logging.error(
                "Recording failed : Avg SPO2 for date " + start_date + " to " + end_date
            )
        return collected_records

    ###########################################################################################################################################
    def get_daily_data_limit_365d(self, start_date_str, end_date_str):
        collected_records = []
        activity_minutes_list = [
            "minutesSedentary",
            "minutesLightlyActive",
            "minutesFairlyActive",
            "minutesVeryActive",
        ]
        for activity_type in activity_minutes_list:
            activity_minutes_data_list = self.client.make_request(
                "https://api.fitbit.com/1/user/-/activities/tracker/"
                + activity_type
                + "/date/"
                + start_date_str
                + "/"
                + end_date_str
                + ".json"
            )["activities-tracker-" + activity_type]
            if activity_minutes_data_list != None:
                for data in activity_minutes_data_list:
                    log_time = datetime.fromisoformat(
                        data["dateTime"] + "T" + "00:00:00"
                    )
                    utc_time = (
                        LOCAL_TIMEZONE.localize(log_time)
                        .astimezone(pytz.utc)
                        .isoformat()
                    )
                    collected_records.append(
                        {
                            "measurement": "Activity Minutes",
                            "time": utc_time,
                            "tags": {"Device": DEVICENAME},
                            "fields": {activity_type: int(data["value"])},
                        }
                    )
                # logging.info("Recorded " + activity_type + "for date " + start_date_str + " to " + end_date_str)
            else:
                # logging.error("Recording failed : " + activity_type + " for date " + start_date_str + " to " + end_date_str)
                apa = 1

        activity_others_list = ["distance", "calories", "steps"]
        for activity_type in activity_others_list:
            activity_others_data_list = self.client.make_request(
                "https://api.fitbit.com/1/user/-/activities/tracker/"
                + activity_type
                + "/date/"
                + start_date_str
                + "/"
                + end_date_str
                + ".json"
            )["activities-tracker-" + activity_type]
            if activity_others_data_list != None:
                for data in activity_others_data_list:
                    log_time = datetime.fromisoformat(
                        data["dateTime"] + "T" + "00:00:00"
                    )
                    utc_time = (
                        LOCAL_TIMEZONE.localize(log_time)
                        .astimezone(pytz.utc)
                        .isoformat()
                    )
                    activity_name = (
                        "Total Steps" if activity_type == "steps" else activity_type
                    )
                    collected_records.append(
                        {
                            "measurement": activity_name,
                            "time": utc_time,
                            "tags": {"Device": DEVICENAME},
                            "fields": {"value": float(data["value"])},
                        }
                    )
                logging.info(
                    "Recorded "
                    + activity_name
                    + " for date "
                    + start_date_str
                    + " to "
                    + end_date_str
                )
            else:
                logging.error(
                    "Recording failed : "
                    + activity_name
                    + " for date "
                    + start_date_str
                    + " to "
                    + end_date_str
                )
