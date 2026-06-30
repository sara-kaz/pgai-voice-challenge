"""
Trigger one outbound test call.

Usage:
    python place_call.py simple_scheduling
    python place_call.py --list

The server (app/server.py, exposed via ngrok) must already be running and
PUBLIC_BASE_URL in .env must point at it, since Twilio will call back into
our /twiml endpoint as soon as the line picks up.
"""

import argparse
import os
import sys
import time

from dotenv import load_dotenv
from twilio.rest import Client

from scenarios.scenarios import SCENARIOS

load_dotenv()

ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
FROM_NUMBER = os.environ["TWILIO_FROM_NUMBER"]
TARGET_NUMBER = os.environ["TARGET_NUMBER"]
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")


def place_call(scenario_key: str) -> str:
    if scenario_key not in SCENARIOS:
        sys.exit(f"Unknown scenario '{scenario_key}'. Use --list to see options.")

    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    call = client.calls.create(
        to=TARGET_NUMBER,
        from_=FROM_NUMBER,
        url=f"{PUBLIC_BASE_URL}/twiml?scenario={scenario_key}",
        record=True,
        recording_channels="dual",
        recording_status_callback=f"{PUBLIC_BASE_URL}/recording-callback",
        recording_status_callback_event=["completed"],
    )
    print(f"Placed call. CallSid={call.sid}, scenario={scenario_key}")
    return call.sid


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", nargs="?", help="Scenario key from scenarios/scenarios.py")
    parser.add_argument("--list", action="store_true", help="List available scenarios and exit")
    args = parser.parse_args()

    if args.list or not args.scenario:
        for key, info in SCENARIOS.items():
            print(f"{key:30s} {info['description']}")
        sys.exit(0)

    place_call(args.scenario)
