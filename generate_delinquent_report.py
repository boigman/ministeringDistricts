from pathlib import Path
import os
import json
import re
import csv
from datetime import datetime
import pyperclip
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.encoders import encode_base64

# This automatically finds the folder where this script lives on the flash drive
BASE_DIR = Path(__file__).resolve().parent
# --- File Path Configuration (Ubuntu Layouts) ---
CSV_DIRECTORY_PATH = BASE_DIR / "Elders_Phones.csv"
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    defaults = {
        "sender_name": "Dave Stauffer",
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


def load_official_eq_roster_names(csv_path):
    """Loads all official elders from the CSV directory to serve as a strict validation filter."""
    official_names = set()
    if not os.path.exists(csv_path):
        print(f"⚠️ Warning: Validation CSV file not found at {csv_path}. Skipping strict roster filtering.")
        return None
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = row.get("Name", "").strip()
                if full_name:
                    official_names.add(full_name.lower())
        print(f"📂 Roster Filter Status: Loaded {len(official_names)} official names from Elders_Phones.csv.")
    except Exception as e:
        print(f"⚠️ Error parsing validation CSV file: {e}")
    return official_names


def is_name_in_official_roster(lcr_name, official_roster):
    if official_roster is None:
        return True  # Fallback if CSV is physically missing

    clean_lcr = lcr_name.lower().replace(',', '')
    lcr_tokens = set(clean_lcr.split())

    for official_name in official_roster:
        clean_off = official_name.replace(',', '')
        off_tokens = set(clean_off.split())
        if lcr_tokens == off_tokens or lcr_tokens.issubset(off_tokens) or off_tokens.issubset(lcr_tokens):
            return True

    return False


def get_json_from_clipboard():
    """Aggressively extracts text from your Linux clipboard framework layer."""
    try:
        clipboard_content = pyperclip.paste()
    except Exception as e:
        raise ValueError(f"Failed to access Ubuntu clipboard interface layers: {e}")

    if not clipboard_content or not clipboard_content.strip():
        raise ValueError("The system clipboard layer appears to be completely empty.")

    print(f"📋 Clipboard payload intercepted: {len(clipboard_content)} characters discovered.")

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', clipboard_content)
    if match:
        print("🎯 Pattern Match Success: Isolated __NEXT_DATA__ script block arrays.")
        return json.loads(match.group(1))

    if '{"props":{"pageProps":' in clipboard_content:
        print("🎯 Boundary Match Success: Bypassed HTML script tags to capture direct JSON borders.")
        start_idx = clipboard_content.index('{"props":{"pageProps":')
        raw_json = clipboard_content[start_idx:]
        return json.loads(raw_json[:raw_json.rfind('}') + 1])

    raise ValueError("Isolator Error: Clipboard text does not match LCR raw page source tracking layout patterns.")


def get_latest_interview(interviews_list):
    if not interviews_list:
        return None
    parsed_dates = []
    for interview in interviews_list:
        date_str = interview.get('date', '')
        if date_str:
            try:
                clean_date = date_str.split('T')
                parsed_dates.append(datetime.strptime(clean_date[0], "%Y-%m-%d"))
            except ValueError:
                continue
    return max(parsed_dates) if parsed_dates else None


def get_months_difference(date1, date2):
    return (date1.year - date2.year) * 12 + (date1.month - date2.month)


def email_generated_file_to_myself(text_content, subject_line, filename_on_disk):
    """Saves a local backup file copy and emails it directly to your phone's inbox."""
    os.makedirs("generated", exist_ok=True)
    full_file_path = f"generated/{filename_on_disk}"
    with open(full_file_path, "w", encoding="utf-8") as text_file:
        text_file.write(text_content)
    print(f"\n💾 Complete report backup saved locally at: {full_file_path}")

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
        print("✅ Success! Interview delinquency report successfully emailed to your phone.")
    except Exception as e:
        print(f"❌ Automated email dispatch failed: {e}")


def run_report():
    out_lines = []

    def log_print(text=""):
        print(text)
        out_lines.append(text)

    log_print("=========================================================")
    log_print(" 📈 ELDERS QUORUM INTERVIEW INACTIVITY REPORT")
    log_print("=========================================================")

    months_input = input("Enter Month Inactivity Threshold [Default: 9]: ").strip()
    months_limit = int(months_input) if months_input else 9

    # 1. Load the official local EQ verification filter
    official_roster = load_official_eq_roster_names(CSV_DIRECTORY_PATH)

    # 2. Extract Data from Clipboard
    try:
        data = get_json_from_clipboard()
        elders_list = data['props']['pageProps']['initialState']['ministeringData']['elders']
        print(f"📈 Dataset Sync Success: Found {len(elders_list)} active District datasets inside JSON structure.")
    except Exception as e:
        print(f"⛔ Error parsing data: {e}")
        print("👉 Execution Halted: Please ensure you go to LCR Ministering, press Ctrl+U, Ctrl+A, Ctrl+C, then re-run.")
        return

    now = datetime.now()
    total_months = now.year * 12 + now.month - 1 - months_limit
    cutoff_year = total_months // 12
    cutoff_month = (total_months % 12) + 1
    cutoff_date = datetime(cutoff_year, cutoff_month, 1)

    delinquent_count = 0
    never_count = 0

    log_print(
        f"\nScanning all districts for official assigned Elders with no interview since {cutoff_date.strftime('%b %Y')} (> {months_limit} months ago)...\n")

    for dist in elders_list:
        district_name = dist['districtName']
        district_lines = []

        for comps in dist['companionships']:
            for minister in comps['ministers']:
                name = minister.get('name', 'Unknown')

                # Check cross-referenced name filter rules
                if not is_name_in_official_roster(name, official_roster):
                    continue

                last_date_obj = get_latest_interview(minister.get('interviews', []))
                is_flagged = False
                status_str = ""

                if last_date_obj is None:
                    is_flagged = True
                    status_str = "NEVER INTERVIEWED"
                    never_count += 1
                else:
                    months_past = get_months_difference(now, last_date_obj)
                    if months_past >= months_limit:
                        is_flagged = True
                        status_str = f"{months_past} months ago ({last_date_obj.strftime('%Y-%m-%d')})"
                        delinquent_count += 1

                if is_flagged:
                    district_lines.append(f"  🚨 {name:<30} | Last Interview: {status_str}")

        if district_lines:
            log_print(f"=========================================================")
            log_print(f"District: {district_name}")
            log_print(f"=========================================================")
            for line in district_lines:
                log_print(line)
            log_print()

    log_print("=========================================================")
    log_print(f"📊 REPORT SUMMARY:")
    log_print(f"  - Total Overdue (> {months_limit} months): {delinquent_count}")
    log_print(f"  - Total Never Interviewed:        {never_count}")
    log_print(f"  - Total Active Action Targets:     {delinquent_count + never_count}")
    log_print("=========================================================")

    # --- TRANSMIT THE ENTIRE BUFFERED REPORT ONCE AT THE ABSOLUTE END ---
    master_text_payload = "\n".join(out_lines)
    email_generated_file_to_myself(
        text_content=master_text_payload,
        subject_line=f"EQ Interview Inactivity Report - Overdue > {months_limit} Months",
        filename_on_disk=f"delinquency_report_{now.strftime('%Y_%m_%d')}.txt"
    )

if __name__ == "__main__":
    run_report()
