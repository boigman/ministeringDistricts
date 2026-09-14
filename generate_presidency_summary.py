import os
import pickle
import json
import re
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.encoders import encode_base64
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
        "presidency_calendar_id": "primary",
        "my_email": "boigman56@gmail.com",
        "smtp_server": "74.125.142.108",
        "smtp_port": 587,
        "app_password": ""
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
    """Queries the Google API using direct string formatting blocks."""
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


def email_generated_file_to_myself(text_content, subject_line, filename_on_disk):
    """Saves a local backup file copy and emails it directly to your phone's inbox."""
    os.makedirs("generated", exist_ok=True)
    full_file_path = f"generated/{filename_on_disk}"
    with open(full_file_path, "w", encoding="utf-8") as text_file:
        text_file.write(text_content)
    print(f"\n💾 Complete summary text file backup saved locally at: {full_file_path}")

    config = load_config()
    my_email = str(config.get("my_email", "")).strip()
    app_pwd = str(config.get("app_password", "")).strip()
    smtp_srv = str(config.get("smtp_server", "74.125.142.108")).strip()
    smtp_prt = config.get("smtp_port", 587)

    if not my_email or not app_pwd or app_pwd == "YOUR_16_DIGIT_GMAIL_APP_PASSWORD_HERE" or not app_pwd.strip():
        print("ℹ️ Email configuration unconfigured or placeholder detected. Skipping email dispatch.")
        return

    print(f"📧 Initializing secure connection to dispatch logs to {my_email}...")
    try:
        msg = MIMEMultipart()
        msg['From'] = my_email
        msg['To'] = my_email
        msg['Subject'] = subject_line

        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

        with open(full_file_path, "rb") as attachment_file:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment_file.read())
            encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {filename_on_disk}")
            msg.attach(part)

        server = smtplib.SMTP(smtp_srv, smtp_prt, timeout=15)
        server.starttls()
        server.login(my_email, app_pwd)
        server.sendmail(my_email, my_email, msg.as_string())
        server.quit()
        print("✅ Success! Presidency summary log successfully emailed to your phone.")
    except Exception as e:
        print(f"❌ Automated email dispatch failed: {e}")


def generate_presidency_text():
    config = load_config()
    presidency_calendar_id = config.get("presidency_calendar_id", "primary")

    default_sunday_str = get_default_sundays()

    out_lines = []

    def log_print(text=""):
        print(text)
        out_lines.append(text)

    log_print("=========================================================")
    log_print(" 🗓️  PRESIDENCY WEEKLY SUMMARY GENERATOR")
    log_print("=========================================================")

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

    log_print("\n🚀 --- Copy/Paste Presidency Summary Text ---")
    log_print("Elder Quorum Ministering Interview Schedule:\n")

    log_print(f"This Sunday, {sunday1.strftime('%b %-d')}:")
    if list_sun1:
        for item in list_sun1:
            log_print(f"- {item['time']} {item['initials']} {item['name']}")
    else:
        log_print("- No interviews scheduled")

    log_print()

    log_print(f"Next Sunday, {sunday2.strftime('%b %-d')}:")
    if list_sun2:
        for item in list_sun2:
            log_print(f"- {item['time']} {item['initials']} {item['name']}")
    else:
        log_print("- No interviews scheduled")
    log_print("--------------------------------------------")

    # --- TRANSMIT MASTER PAYLOAD ONCE COMPILATION COMPLETES ---
    master_text_payload = "\n".join(out_lines)
    email_generated_file_to_myself(
        text_content=master_text_payload,
        subject_line=f"EQ Presidency Summary Text - Sundays {sunday1.strftime('%b %d')} & {sunday2.strftime('%b %d')}",
        filename_on_disk=f"presidency_summary_{sunday1.strftime('%Y_%m_%d')}.txt"
    )


if __name__ == "__main__":
    generate_presidency_text()
