from pathlib import Path
import os
import pickle
import json
import csv
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# This automatically finds the folder where this script lives on the flash drive
BASE_DIR = Path(__file__).resolve().parent
# --- File Path Configuration (Ubuntu Layouts) ---
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"
CONFIG_PATH = BASE_DIR / "config.json"
CSV_DIRECTORY_PATH = BASE_DIR / "Elders_Phones.csv"

SCOPES = ['https://googleapis.com']


def load_config():
    defaults = {
        "sender_name": "Dave Stauffer",
        "presidency_calendar_id": "primary",
        "special_titles": {"Bates, Jason": "Pres"}
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return defaults


def lookup_elder_email_from_csv(input_name, csv_path):
    if not os.path.exists(csv_path):
        print(f"⚠️ Warning: CSV file not found at {csv_path}. Proceeding without guest invitation.")
        return None, None

    input_parts = input_name.strip().lower().split()
    if not input_parts:
        return None, None

    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = row.get("Name", "").strip().lower()
                email_val = row.get("E-mail", "").strip()

                if all(part in full_name for part in input_parts):
                    if email_val and "@" in email_val:
                        return email_val, row.get("Name")
    except Exception as e:
        print(f"⚠️ Error scanning CSV registry: {e}")

    return None, None


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


def get_initials_from_lastname(last_name, config_titles):
    clean_input = last_name.strip().lower()
    for full_name, title in config_titles.items():
        if ',' in full_name:
            parts = full_name.split(',')
            extracted_last = parts[0].strip().lower()
        else:
            extracted_last = full_name.strip().lower()

        if clean_input == extracted_last:
            if ',' in full_name:
                parts = full_name.split(',')
                last = parts[0].strip()
                first = parts[1].strip() if len(parts) > 1 else ""
                initials = f"{first[0]}{last[0]}".upper() if first else f"{last[:2]}".upper()
            else:
                parts = full_name.split()
                last = parts[-1]
                first = parts[0] if len(parts) > 1 else ""
                initials = f"{first[0]}{last[0]}".upper() if first else f"{last[:2]}".upper()
            return initials, f"{title} {last}"

    fallback_last = last_name.strip().capitalize()
    return fallback_last[:2].upper(), f"Br {fallback_last}"


def get_next_sunday():
    today = datetime.now()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    return (today + timedelta(days=days_until_sunday)).strftime("%Y-%m-%d")


def insert_event():
    print("🗓️ --- Production Ward Google Calendar Inserter ---")
    config = load_config()
    special_titles = config.get("special_titles", {})

    # DYNAMIC: Read the calendar ID directly from the shared config
    presidency_calendar_id = config.get("presidency_calendar_id", "primary")

    try:
        service = get_calendar_service()
    except Exception as e:
        print(f"❌ Authentication initialization failed: {e}")
        return

    elder_name = input("Enter Elder's Name (e.g., Wil Hunt): ").strip()
    elder_email, elder_full_csv_name = lookup_elder_email_from_csv(elder_name, CSV_DIRECTORY_PATH)

    if elder_email:
        print(f"🎯 Matched Elder in CSV: {elder_full_csv_name} -> Email: {elder_email}")
    else:
        print(f"ℹ️ Could not find an email for Elder '{elder_name}' in the CSV list.")

    default_sunday = get_next_sunday()
    date_input = input(f"Enter Meeting Date [Default Next Sunday: {default_sunday}]: ").strip()
    meeting_date = date_input if date_input else default_sunday
    start_time = input("Enter Start Time (24hr HH:MM, e.g., 11:15): ").strip()

    supervisor_input = input("Enter Supervisor Last Name (Default: Bates): ").strip() or "Bates"
    initials, supervisor_display = get_initials_from_lastname(supervisor_input, special_titles)
    title = f"{initials}-MI-{elder_name}"

    try:
        start_dt = datetime.strptime(f"{meeting_date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=20)
    except ValueError as e:
        print(f"❌ Error formatting dates or times: {e}.")
        return

    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    event_body = {
        'summary': title,
        'location': "The Church of Jesus Christ of Latter-day Saints, 1401 S Henke Rd, Lake St Louis, MO 63367, USA",
        'description': f"O'Fallon Ward Elder Quorum Presidency Calendar\nInterviewer: {supervisor_display}",
        'start': {
            'dateTime': start_iso,
            'timeZone': 'America/Chicago',
        },
        'end': {
            'dateTime': end_iso,
            'timeZone': 'America/Chicago',
        },
        'attendees': [],
        'reminders': {
            'useDefault': True,
        },
    }

    if elder_email:
        event_body['attendees'].append({'email': elder_email})

    supervisor_email, supervisor_full_csv_name = lookup_elder_email_from_csv(supervisor_input, CSV_DIRECTORY_PATH)
    if supervisor_email:
        print(f"🎯 Matched Supervisor in CSV: {supervisor_full_csv_name} -> Email: {supervisor_email}")
        event_body['attendees'].append({'email': supervisor_email})

    try:
        print(f"Pushing event '{title}' to shared presidency calendar...")
        event = service.events().insert(
            calendarId=presidency_calendar_id,
            body=event_body,
            sendUpdates='all'
        ).execute()

        print(f"✅ Success! Live event created directly on the Presidency Calendar.")
        print(f"🔗 Live Event Link: {event.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Failed to insert event: {e}")


if __name__ == "__main__":
    insert_event()
