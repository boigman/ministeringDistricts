import os
import pickle
import json
import csv
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# --- File Path Configuration (Ubuntu Layouts) ---
TOKEN_FILE = "/home/dave/PycharmProjects/ministeringDistricts/token.json"
CREDENTIALS_FILE = "/home/dave/PycharmProjects/ministeringDistricts/credentials.json"
CONFIG_PATH = "/home/dave/PycharmProjects/ministeringDistricts/config.json"
CSV_DIRECTORY_PATH = "/home/dave/PycharmProjects/ministeringDistricts/Elders_Phones.csv"

SCOPES = ['https://googleapis.com']


def load_config():
    defaults = {
        "presidency_calendar_id": "primary",
        "special_titles": {"Bates, Jason": "Pres"},
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


def load_phone_directory(csv_path):
    phone_map = {}
    if not os.path.exists(csv_path):
        print(f"⚠️ Warning: CSV file not found at {csv_path}. Using blank placeholders.")
        return phone_map
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = row.get("Name", "").strip()
                phone_val = row.get("Phone Number", "").strip() or row.get("Phone", "").strip()
                if full_name:
                    if not phone_val or phone_val.lower() == "none":
                        phone_val = "___________"
                    phone_map[full_name] = phone_val
    except Exception as e:
        print(f"⚠️ Error parsing CSV file: {e}")
    return phone_map


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


def get_last_name_from_lcr(full_name):
    if ',' in full_name:
        return full_name.split(',')[0].strip()
    return full_name.strip()


def find_elder_metadata(cal_elder_name, phone_directory):
    """Matches calendar name variations to the official CSV directory."""
    cal_parts = cal_elder_name.lower().replace(',', '').split()
    if not cal_parts:
        return cal_elder_name, "___________"

    cal_last = cal_parts[-1]
    cal_first_init = cal_parts[0][0] if cal_parts[0] else ""

    for csv_name, phone in phone_directory.items():
        if ',' in csv_name:
            parts = csv_name.lower().split(',')
            csv_last = parts[0].strip()
            csv_first = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = csv_name.lower().split()
            csv_last = parts[-1] if parts else ""
            csv_first = parts[0] if len(parts) > 1 else ""

        csv_first_init = csv_first[0] if csv_first else ""

        if cal_last == csv_last and cal_first_init == csv_first_init:
            return get_last_name_from_lcr(csv_name), phone

    return cal_elder_name.split()[-1] if ' ' in cal_elder_name else cal_elder_name, "___________"


def get_supervisor_display(initials, config_titles):
    """Maps initials back to full names and custom titles (Pres vs Br)."""
    for full_name, title in config_titles.items():
        if ',' in full_name:
            parts = full_name.split(',')
            last = parts[0].strip()
            first = parts[1].strip() if len(parts) > 1 else ""
            calc_initials = (first[0] + last[0]).upper() if first and last else ""
        else:
            parts = full_name.split()
            last = parts[-1] if parts else ""
            calc_initials = (parts[0][0] + last[0]).upper() if len(parts) > 1 else ""

        if calc_initials == initials.upper():
            return f"{title} {last}"

    return f"Br {initials}"


def email_generated_file_to_myself(text_content, subject_line, filename_on_disk):
    """Saves a local backup file copy and emails it directly to your phone's inbox."""
    os.makedirs("generated", exist_ok=True)
    full_file_path = f"generated/{filename_on_disk}"
    with open(full_file_path, "w", encoding="utf-8") as text_file:
        text_file.write(text_content)
    print(f"\n💾 Complete reminder text file backup saved locally at: {full_file_path}")

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
        print("✅ Success! Sunday reminder text logs successfully emailed to your phone.")
    except Exception as e:
        print(f"❌ Automated email dispatch failed: {e}")


def generate_today_reminders():
    config = load_config()
    calendar_id = config.get("presidency_calendar_id", "primary")
    special_titles = config.get("special_titles", {})

    phone_directory = load_phone_directory(CSV_DIRECTORY_PATH)
    service = get_calendar_service()

    today = datetime.now()
    time_min = f"{today.strftime('%Y-%m-%d')}T00:00:00-05:00"
    time_max = f"{today.strftime('%Y-%m-%d')}T23:59:59-05:00"

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
        print(f"❌ Failed to reach Google Calendar API: {e}")
        return

    events = events_result.get('items', [])
    pattern = re.compile(r'^([A-Z]{2})-MI-(.*)$')
    count = 0

    out_lines = []

    def log_print(text=""):
        print(text)
        out_lines.append(text)

    log_print("=========================================================")
    log_print(" 📱 SUNDAY INTERVIEW TEXT REMINDER GENERATOR")
    log_print(f" Scanning schedules for today: {today.strftime('%A, %b %-d, %Y')}")
    log_print("=========================================================")
    log_print("\n🚀 --- Copy/Paste Text Reminders ---")

    for event in events:
        summary = event.get('summary', '')
        match = pattern.match(summary)
        if match:
            initials = match.group(1)
            elder_name = match.group(2).strip()

            start_str = event['start'].get('dateTime') or event['start'].get('date')
            time_display = "11:15 AM"
            if start_str and 'T' in start_str:
                try:
                    time_part = start_str.split('T')[1][:5]
                    dt_obj = datetime.strptime(time_part, "%H:%M")
                    time_display = dt_obj.strftime("%-I:%M %p")
                except Exception:
                    pass

            clean_lastname, phone = find_elder_metadata(elder_name, phone_directory)
            supervisor_display = get_supervisor_display(initials, special_titles)

            log_print(f"\n📱 SEND TO: {elder_name} ({phone})")
            log_print(
                f"TEXT: \"Hi, Br {clean_lastname}. As a reminder, you have a ministering interview scheduled today at {time_display} with {supervisor_display}.\"")
            count += 1

    log_print("\n---------------------------------------------------------")
    log_print(f"🎉 Complete! Processed {count} active text reminder(s) for today.")

    # --- TRANSMIT THEMaster PAYLOAD ONCE ALL EVENTS ARE PARSED ---
    master_text_payload = "\n".join(out_lines)
    email_generated_file_to_myself(
        text_content=master_text_payload,
        subject_line=f"EQ Today's Sunday Reminders - {today.strftime('%b %d, %Y')}",
        filename_on_disk=f"sunday_reminders_{today.strftime('%Y_%m_%d')}.txt"
    )


if __name__ == "__main__":
    generate_today_reminders()
