# sync-fitbit-pro-connect
[![CI/CD Workflow](https://github.com/origox/sync-fitbit-pro-connect/actions/workflows/main.yaml/badge.svg)](https://github.com/origox/sync-fitbit-pro-connect/actions/workflows/main.yaml)

# Prereqs
These steps need to be performed if there are no access and refresh tokens.

## 1. Register APP
- Go to https://dev.fitbit.com/apps and register app. Get Client ID and Client Secret, store those in environment variables

## 2. Get Access Token
- Run get_authorization_code.py script in two steps
1. First run until Authorization url is created then click that link and then you get a redirict url back.
2. Copy redirect url from browser bar and paste to script input(will solve/automate this step later on). Then you get access and refresh tokens.

Note, Same process can be follow here: https://dev.fitbit.com/build/reference/web-api/troubleshooting-guide/oauth2-tutorial/ 

# Environment Variables

This project uses the following environment variables:

- `FITBIT_CLIENT_ID`: Your Fitbit client ID.
- `FITBIT_CLIENT_SECRET`: Your Fitbit client secret.
- `FITBIT_CLIENT_SCOPE`: The scopes your Fitbit app needs access to.
- `FITBIT_DEVICE_NAME`: The name of your Fitbit device.
- `FITBIT_LOCAL_TIMEZONE`: Your local timezone.
- `FITBIT_LOG_FILE_PATH`: The path where Fitbit logs will be stored.
- `FITBIT_TOKEN_FILE_PATH`: The path where Fitbit tokens will be stored.
- `FITBIT_INITIAL_ACCESS_TOKEN`: Initial access token, used when no file avail. 
- `FITBIT_INITIAL_REFRESH_TOKEN`: Initial refresh token, used when no file avail.
- `OVERWRITE_LOG_FILE`: Whether to overwrite the log file or not. Set this to `True` or `False`.
- `FITBIT_LANGUAGE`: The language used by Fitbit.
- `INFLUXDB_HOST`: The host of your InfluxDB.
- `INFLUXDB_ORG`: The organization of your InfluxDB.
- `INFLUXDB_PORT`: The port of your InfluxDB. (currently not used, included in host, TODO refact.)
- `INFLUXDB_USERNAME`: The username of your InfluxDB.
- `INFLUXDB_TOKEN`: The token of your InfluxDB.
- `INFLUXDB_DATABASE`: The database of your InfluxDB.





# API - Intraday

| Resource | External API | Internal API | Scope | Limit | InfluxDB - bucket | Grafana |
|---|---|---|---|---|---|---|
|Get Activity Intraday by Date|/1/user/[user-id]/activities/[resource]/date/[start-date]/[detail-level].json|*get_intraday_activity_by_date|activity|24 hours|[Calories/Distance/Steps]_Intraday||
|Get Breathing Rate Intraday by Interval|/1/user/[user-id]/br/date/[start-date]/[end-date]/all.json|*get_breathing_rate_by_interval|respiratory_rate|30 days|BreathingRate||
|Get Heart Rate Intraday by Date|/1/user/[user-id]/activities/heart/date/[start-date]/[detail-level].json|*get_intraday_heart_rate_by_date|heartrate|24 hours|HR zones/RestingHR||
|Get HRV Intraday by Interval|/1/user/[user-id]/hrv/date/[startDate]/[endDate]/all.json|*get_intraday_hrv_by_interval|heartrate|30 days|HRV_Intraday||  
|Get SpO2 Intraday by Interval|/1/user/[user-id]/spo2/date/[start-date]/[end-date]/all.json|*get_spo2_by_interval|oxygen_saturation|30 days|SPO2_Intraday||


# API - Time series

| Resource | API | Internal API | Scope | Limit | InfluxDB - bucket | Grafana |
|---|---|---|---|---|---|---|
|Get Weight Time Series by Date Range|/1/user/[user-id]/body/log/weight/date/[start-date]/[end-date].json|*get_body_data_by_interval|weight|31 days|Body||
|Get VO2 Max Summary by Interval|/1/user/[user-id]/cardioscore/date/[start-date]/[end-date].json|*get_vo2max_cardio_score_by_interval|cardio_fitness|30 days|CardioScore||
|Get Sleep Log by Date Range|/1.2/user/[user-id]/sleep/date/[startDate]/[endDate].json|*get_sleep_log_by_interval|sleep|100 days|Sleep Summary/Sleep Levels||
|Get Temperature (Skin) Summary by Interval|/1/user/[user-id]/temp/skin/date/[start-date]/[end-date].json|*get_temperature_skin_by_interval|temperature|30 days|TempSkin||
|Get SpO2 Summary by Interval|/1/user/[user-id]/spo2/date/[start-date]/[end-date].json|*get_spo2_summary_by_interval|oxygen_saturation|None|SPO2|
|Get Activity Time Series by Date Range|/1/user/[user-id]/activities/[resource-path]/date/[start-date]/[end-date].json|*get_activity_summary_by_interval|activity|1095|[distance/calories/steps/Activity Minutes]|


# API - Device
| Resource | API | Internal API | Scope | Limit | InfluxDB - bucket | Grafana |
|---|---|---|---|---|---|---|
|Get Devices|/1/user/[user-id]/devices.json|*get_battery_level|settings|None|DeviceBatteryLevel||

# Docker
- Build of Docker image is part of CI/CD flow
- [Images stored on Docker Hub ](https://hub.docker.com/r/origox/sync-fitbit-pro-connect)

## Dev stuff
```sh
# Build docker image from Dockerfile
docker build -t sync-fitbit-pro-connect:2.0.0 .

# Run docker container
docker run --rm  --env-file=.env -v ./app/auth:/app/app/auth -v ./logs:/app/logs input:10.0.0   
docker run --rm --env-file=.env -v ./app/auth:/app/app/auth -v ./logs:/app/logs origox/sync-fitbit-pro-connect:sha-c9ffd6b

# Test auth script
~/dev/sync-fitbit-pro-connect# python3 app/auth/get_authorization_code.py

# Test run from cmdline
~/dev/sync-fitbit-pro-connect# python3 app/main.py 
```
# DEVSECOPS
- DevSecOps is part of CI/CD flow
- [Insiration: DevSecOps - Github Actions](https://www.youtube.com/watch?v=gLJdrXPn0ns)

# Kubernetes
- test of deployment, /tmp/fitbit/deployment.yaml, is working
- todo: add proper sops encrypted secrets, include into my gitops repo

### Inspiration
- [ex. 1](https://github.com/pkpio/fitbit-googlefit)
- [ex. 2](https://github.com/arpanghosh8453/public-fitbit-projects)