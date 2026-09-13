import os
import pickle
import json
import re
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Configuration & Paths ---
TOKEN_FILE = "/home/dave/PycharmProjects/ministeringDistricts/token.json"
CREDENTIALS_FILE = "/home/dave/PycharmProjects/ministeringDistricts/credentials.json"
CONFIG_PATH = "/home/dave/PycharmProjects/ministeringDistricts/config.json"

SCOPES = ['https://googleapis.com']


def load_config():
    defaults = {
        "presidency_calendar_id": "primary"
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return defaults


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)


def get_default_sundays():
    today = datetime.now()
    days_until_sunday = (6 - today.weekday()) % 7
    base_sunday = today + timedelta(days=days_until_sunday)
    return base_sunday.strftime("%Y-%m-%d")


def fetch_interviews_for_date(service, target_date, calendar_id):
    """Queries the Google API using the dynamically loaded calendar ID."""
    time_min = f"{target_date.strftime('%Y-%m-%d')}T00:00:00-05:00"
    time_max = f"{target_date.strftime('%Y-%m-%d')}T23:59:59-05:00"

    try:
        request = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        )
        events_result = request.execute()
    except Exception as e:
        print(f"❌ API Query Failure: {e}")
        return []

    events = events_result.get('items', [])
    interviews = []
    pattern = re.compile(r'^([A-Z]{2})-MI-(.*)$')

    for event in events:
        summary = event.get('summary', '')
        match = pattern.match(summary)
        if match:
            initials = match.group(1)
            elder_name = match.group(2)

            start_str = event['start'].get('dateTime') or event['start'].get('date')
            time_display = "11:15am"

            if start_str and 'T' in start_str:
                try:
                    time_part = start_str.split('T')[1][:5]  # Extracts exactly "11:15"
                    dt_obj = datetime.strptime(time_part, "%H:%M")
                    time_display = dt_obj.strftime("%-I:%M%p").lower()
                except Exception:
                    pass

            interviews.append({
                "time": time_display,
                "initials": initials,
                "name": elder_name
            })

    return interviews


def generate_presidency_text():
    print("🗓️ --- Presidency Weekly Summary Generator ---")
    config = load_config()
    presidency_calendar_id = config.get("presidency_calendar_id", "primary")

    default_sunday_str = get_default_sundays()
    user_date_input = input(f"Enter Base Sunday Date [Default Upcoming: {default_sunday_str}]: ").strip()
    base_date_str = user_date_input if user_date_input else default_sunday_str

    try:
        sunday1 = datetime.strptime(base_date_str, "%Y-%m-%d")
        sunday2 = sunday1 + timedelta(days=7)
    except ValueError:
        print("❌ Error formatting input date. Please use YYYY-MM-DD format.")
        return

    print("⏳ Synchronizing with Google Calendar API cloud databases...")
    service = get_calendar_service()

    list_sun1 = fetch_interviews_for_date(service, sunday1, presidency_calendar_id)
    list_sun2 = fetch_interviews_for_date(service, sunday2, presidency_calendar_id)

    print("\n🚀 --- Copy/Paste Presidency Summary Text ---")
    print("Elder Quorum Ministering Interview Schedule:\n")

    print(f"This Sunday, {sunday1.strftime('%b %-d')}:")
    if list_sun1:
        for item in list_sun1:
            print(f"- {item['time']} {item['initials']} {item['name']}")
    else:
        print("- No interviews scheduled")

    print()

    print(f"Next Sunday, {sunday2.strftime('%b %-d')}:")
    if list_sun2:
        for item in list_sun2:
            print(f"- {item['time']} {item['initials']} {item['name']}")
    else:
        print("- No interviews scheduled")
    print("--------------------------------------------")


if __name__ == "__main__":
    generate_presidency_text()
