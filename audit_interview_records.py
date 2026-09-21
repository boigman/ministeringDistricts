from pathlib import Path
import os
import pickle
import json
import re
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pyperclip

# This automatically finds the folder where this script lives on the flash drive
BASE_DIR = Path(__file__).resolve().parent
# --- File Path Configuration (Ubuntu Layouts) ---
TOKEN_FILE = BASE_DIR / "token.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
CONFIG_PATH = BASE_DIR / "config.json"

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def load_config():
    defaults = {"presidency_calendar_id": "primary"}
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


def get_json_from_clipboard():
    try:
        clipboard_content = pyperclip.paste()
    except Exception as e:
        raise ValueError(f"Failed to access clipboard: {e}")

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', clipboard_content)
    if match:
        return json.loads(match.group(1))

    if '{"props":{"pageProps":' in clipboard_content:
        start_idx = clipboard_content.index('{"props":{"pageProps":')
        raw_json = clipboard_content[start_idx:]
        return json.loads(raw_json[:raw_json.rfind('}') + 1])
    raise ValueError("Clipboard does not contain valid LCR page source data.")


def fetch_past_calendar_interviews(service, calendar_id, days_back):
    """Queries the Google Calendar API for past interview event structures."""
    now = datetime.now()
    start_dt = now - timedelta(days=days_back)

    time_min = start_dt.isoformat() + '-05:00'
    time_max = now.isoformat() + '-05:00'

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
        print(f"❌ Calendar API Fetch Error: {e}")
        return []

    events = events_result.get('items', [])
    calendar_interviews = []
    pattern = re.compile(r'^([A-Z]{2})-MI-(.*)$')

    for event in events:
        summary = event.get('summary', '')
        match = pattern.match(summary)
        if match:
            supervisor_initials = match.group(1)
            elder_name = match.group(2).strip()

            start_str = event['start'].get('dateTime') or event['start'].get('date')
            if start_str:
                # Safely isolate date part before 'T'
                date_part = start_str.split('T')[0]
                event_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                calendar_interviews.append({
                    "elder_name": elder_name,
                    "scheduled_date": event_date,
                    "summary": summary,
                    "initials": supervisor_initials
                })
    return calendar_interviews


def extract_lcr_recorded_interviews(lcr_data):
    recorded_map = {}
    elders_list = lcr_data['props']['pageProps']['initialState']['ministeringData']['elders']

    for dist in elders_list:
        for comps in dist['companionships']:
            for minister in comps['ministers']:
                name = minister.get('name', '').strip()
                interviews = minister.get('interviews', [])

                recorded_dates = []
                for iv in interviews:
                    d_str = iv.get('date', '')
                    if d_str:
                        try:
                            clean_date = d_str.split('T')[0]
                            recorded_dates.append(datetime.strptime(clean_date, "%Y-%m-%d").date())
                        except ValueError:
                            continue
                if name:
                    recorded_map[name] = recorded_dates
    return recorded_map


def run_audit():
    print("📊 --- Elders Quorum Ministering Interview Audit Tool ---")

    # NEW PROMPT INTERFACE: Default scan span to 30 days dynamically
    days_input = input("Enter Audit Scan Period in Days [Default: 30]: ").strip()
    days_back = int(days_input) if days_input else 30

    config = load_config()
    calendar_id = config.get("presidency_calendar_id", "primary")

    # 1. Pull LCR Data from Clipboard
    print("🔍 Inspecting system clipboard for LCR page source...")
    try:
        lcr_data = get_json_from_clipboard()
        lcr_records = extract_lcr_recorded_interviews(lcr_data)
        print(f"🎯 Success! Parsed {len(lcr_records)} elder recording histories from clipboard.")
    except Exception as e:
        print(f"⛔ Error loading clipboard data: {e}")
        print("👉 Reminder: Go to the LCR Ministering page, press Ctrl+U, Ctrl+A, Ctrl+C, then re-run.")
        return

    # 2. Pull Calendar Data from Google API
    print(f"⏳ Fetching past {days_back} days of schedule history from Google Calendar...")
    service = get_calendar_service()
    calendar_interviews = fetch_past_calendar_interviews(service, calendar_id, days_back=days_back)

    if not calendar_interviews:
        print("ℹ️ No past ministering interview events found on your Google Calendar matching the pattern.")
        return

    print(f"📋 Found {len(calendar_interviews)} calendar records to audit. Matching arrays...\n")

    completed_list = []
    flagged_list = []

    # 3. Quarter-Aware & Robust Nickname Matching Loop Engine
    for cal_item in calendar_interviews:
        elder = cal_item['elder_name']
        sched_date = cal_item['scheduled_date']

        sched_quarter = ((sched_date.month - 1) // 3) + 1
        sched_year = sched_date.year

        matched_lcr_name = None
        for lcr_name in lcr_records.keys():
            # Clean up the LCR name (e.g., "Harris, Devon Riley" -> last="harris", first="devon")
            if ',' in lcr_name:
                parts = lcr_name.lower().split(',')
                lcr_last = parts[0].strip()
                lcr_first = parts[1].strip() if len(parts) > 1 else ""
            else:
                parts = lcr_name.lower().split()
                lcr_last = parts[-1] if parts else ""
                lcr_first = parts[0] if len(parts) > 1 else ""

            lcr_first_initial = lcr_first[0] if lcr_first else ""

            # Clean up the Calendar name (e.g., "Devon Harris")
            cal_parts = elder.lower().replace(',', '').split()
            if cal_parts:
                cal_last = cal_parts[-1]
                cal_first = cal_parts[0]
                cal_first_initial = cal_first[0] if cal_first else ""

                # NICKNAME REDUCTION ENGINE: Check exact last name and first initial matches
                if cal_last == lcr_last and cal_first_initial == lcr_first_initial:
                    matched_lcr_name = lcr_name
                    break

        if matched_lcr_name:
            recorded_dates = lcr_records[matched_lcr_name]
            is_recorded = False

            for r_date in recorded_dates:
                r_quarter = ((r_date.month - 1) // 3) + 1
                r_year = r_date.year

                if (r_year == sched_year and r_quarter == sched_quarter) or abs((r_date - sched_date).days) <= 4:
                    is_recorded = True
                    break

            record_entry = {
                "name": matched_lcr_name,
                "date": sched_date.strftime("%b %d, %Y"),
                "initials": cal_item['initials']
            }

            if is_recorded:
                completed_list.append(record_entry)
            else:
                flagged_list.append(record_entry)
        else:
            flagged_list.append({
                "name": f"{elder} (Not found in EQ Roster)",
                "date": sched_date.strftime("%b %d, %Y"),
                "initials": cal_item['initials']
            })

    # 4. Display Report Summary Outputs
    print("=== ⚠️ FLAG LOGS: SCHEDULED BUT NOT RECORDED IN LCR ===")
    if flagged_list:
        for item in flagged_list:
            print(
                f"🚩 FLAG: {item['date']} - {item['original_initials'] if 'original_initials' in item else item['initials']} with {item['name']}")
    else:
        print("🎉 Perfect! Every scheduled interview matches a recorded entry in LCR.")

    print("\n=== ✅ COMPLETED & VERIFIED LOGS (RECORDED MATCHES) ===")
    if completed_list:
        for item in completed_list:
            print(f"✔ Verified: {item['date']} - {item['initials']} with {item['name']}")
    else:
        print("- No verified completed matches found in this date block range.")
    print("======================================================")


if __name__ == "__main__":
    run_audit()
