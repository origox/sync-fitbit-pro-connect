import os
import secrets
import hashlib
import base64
from urllib.parse import urlencode, urlparse, parse_qs
from dotenv import load_dotenv
import requests
import json


def main():
    # load environment variables from .env
    load_dotenv(dotenv_path="../.env")

    # Generate a random PKCE code verifier (43 bytes)
    code_verifier = secrets.token_urlsafe(32)

    # Calculate the code challenge
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )

    # Generate a random OAuth state value (usually 32 characters)
    state = secrets.token_hex(16)

    print(f"PKCE Code Verifier: {code_verifier}")
    print(f"PKCE Code Challenge: {code_challenge}")
    print(f"OAuth State: {state}")

    connect_url = (
        os.getenv(key="FITBIT_API_BASE", default="https://www.fitbit.com")
        + "/oauth2/authorize?"
        + urlencode(
            {
                "state": state,
                "client_id": os.getenv(key="FITBIT_CLIENT_ID"),
                "response_type": "code",
                "scope": os.getenv(key="FITBIT_CLIENT_SCOPE"),
                "code_challenge_method": "S256",
                "code_challenge": code_challenge,
            }
        )
    )

    # Use the connect URL to open a browser window, and then copy the code from the redirect URL
    print(f"Click on Autorization URL: {connect_url}")

    # Input the code from the redirect URL
    redirect_url = input("Enter the code from the redirect URL: ")

    # parse the code from the redirect URL and get code and state
    parsed_url = urlparse(redirect_url)
    captured_state = parse_qs(parsed_url.query)["state"][0]
    captured_code = parse_qs(parsed_url.query)["code"][0]

    # Check that the state matches the state from the connect URL
    if captured_state != state:
        raise Exception("State does not match")
    else:
        print("State matches")
        print(f"State: {captured_state}")
        print(f"Code: {captured_code}")

    # Exchange the authorization code for an access token
    token_url = (
        os.getenv(key="FITBIT_API_BASE", default="https://api.fitbit.com")
        + "/oauth2/token"
    )

    headers = {
        "Authorization": "Basic "
        + base64.b64encode(
            bytes(
                os.getenv(key="FITBIT_CLIENT_ID")
                + ":"
                + os.getenv(key="FITBIT_CLIENT_SECRET"),
                encoding="utf-8",
            )
        ).decode("utf-8"),
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "code": captured_code,
        "client_id": os.getenv(key="FITBIT_CLIENT_ID"),
        "grant_type": "authorization_code",
        "code": captured_code,
        "code_verifier": code_verifier,
    }

    response = requests.post(
        url=token_url,
        headers=headers,
        data=data,
    )

    # Check that the response status code is 200 (OK)
    if response.status_code != 200:
        raise Exception("Bad response status code")
    else:
        print("Response status code is 200")

    # Get the access token and refresh token from the response
    access_token = response.json()["access_token"]
    refresh_token = response.json()["refresh_token"]

    # Print the access token and refresh token
    print(f"Access Token: {access_token}")
    print(f"Refresh Token: {refresh_token}")

    # Save the access token and refresh token
    credentials = dict(
        client_id=os.getenv(key="FITBIT_CLIENT_ID"),
        client_secret=os.getenv(key="FITBIT_CLIENT_SECRET"),
        access_token=access_token,
        refresh_token=refresh_token,
    )
    json.dump(credentials, open("auth/fitbit.json", "w"))


if __name__ == "__main__":
    main()
