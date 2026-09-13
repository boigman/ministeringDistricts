import json
import csv
import os
from datetime import datetime, timedelta
import re
import pyperclip  # Crash-proof Linux clipboard management

# --- File Path Configuration (Ubuntu Layouts) ---
CSV_DIRECTORY_PATH = "/home/dave/PycharmProjects/ministeringDistricts/Elders_Phones.csv"
CONFIG_PATH = "/home/dave/PycharmProjects/ministeringDistricts/config.json"


def load_config(config_path):
    defaults = {
        "sender_name": "Dave Stauffer",
        "special_titles": {},
        "default_slots": ["11:15", "11:35"],
        "custom_district_slots": {}
    }
    if not os.path.exists(config_path):
        return defaults
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return defaults


def load_phone_directory_from_csv(csv_path):
    phone_map = {}
    if not os.path.exists(csv_path):
        print(f"⚠️ Warning: CSV file not found at {csv_path}. Using blank lines.")
        return phone_map
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = row.get("Name", "").strip()
                phone_val = row.get("Phone Number", "").strip()
                if full_name:
                    if not phone_val or phone_val.lower() == "none":
                        phone_val = "___________"
                    phone_map[full_name] = phone_val
    except Exception as e:
        print(f"⚠️ Error parsing CSV file: {e}")
    return phone_map


def get_latest_interview(interviews_list):
    if not interviews_list:
        return None
    parsed_dates = []
    for interview in interviews_list:
        date_str = interview.get('date', '')
        if date_str:
            try:
                clean_date = date_str.split('T')[0]
                date_obj = datetime.strptime(clean_date, "%Y-%m-%d")
                parsed_dates.append(date_obj)
            except ValueError:
                continue
    return max(parsed_dates) if parsed_dates else None


def get_json_from_clipboard():
    try:
        clipboard_content = pyperclip.paste()
    except Exception as e:
        raise ValueError(f"Failed to access clipboard: {e}")
    if not clipboard_content.strip():
        raise ValueError("Clipboard is empty! Copy the page source first.")

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', clipboard_content)
    if match:
        return json.loads(match.group(1))

    start_marker = '{"props":{"pageProps":'
    if start_marker in clipboard_content:
        start_idx = clipboard_content.index(start_marker)
        raw_json_chunk = clipboard_content[start_idx:]
        end_idx = raw_json_chunk.rfind('}')
        if end_idx != -1:
            return json.loads(raw_json_chunk[:end_idx + 1])

    raise ValueError("Could not find data on clipboard. Make sure you used Ctrl+U and copied everything!")


def get_last_name(full_name):
    if ',' in full_name:
        return full_name.split(',')[0].strip()
    return full_name.strip()


def get_current_quarter_dates():
    now = datetime.now()
    quarter_start_month = ((now.month - 1) // 3) * 3 + 1
    return datetime(now.year, quarter_start_month, 1)


def get_months_difference(date1, date2):
    return (date1.year - date2.year) * 12 + (date1.month - date2.month)


# --- Execution Flow ---
config = load_config(CONFIG_PATH)
phone_directory = load_phone_directory_from_csv(CSV_DIRECTORY_PATH)
data = get_json_from_clipboard()

YOUR_NAME = config.get("sender_name", "Dave Stauffer")
NOW = datetime.now()
QUARTER_START = get_current_quarter_dates()

for eldata in data['props']['pageProps']['initialState']['ministeringData']['elders']:
    district_name = eldata['districtName']
    supervisor_full = eldata.get('supervisorName', 'No District leader')

    title = config.get("special_titles", {}).get(supervisor_full, "Br")
    supervisor_last = f"{title} {get_last_name(supervisor_full)}" if supervisor_full != 'No District leader' else "[Supervisor]"
    slots = config.get("custom_district_slots", {}).get(district_name, config.get("default_slots"))
    time_slots_str = " or ".join(slots[:2])

    print(f"\n==============================")
    print(f"District: {district_name} | Supervisor: {supervisor_full}")
    print(f"==============================")

    for comps in eldata['companionships']:
        print("\n  Companionship:")
        companionship_members = []
        for ministers in comps['ministers']:
            name = ministers.get('name', 'Unknown')
            last_date_obj = get_latest_interview(ministers.get('interviews', []))
            last_date_str = last_date_obj.strftime("%Y-%m-%d") if last_date_obj else "Never Interviewed"
            phone_num = phone_directory.get(name, "___________")

            companionship_members.append({
                'name': name,
                'last_name': get_last_name(name),
                'phone': phone_num,
                'last_interview_date': last_date_obj,
                'last_interview_str': last_date_str
            })
            print(f"\t- {name:<25} | Phone: {phone_num:<12} | Last Interview: {last_date_str}")

        if not companionship_members:
            continue

        # Rule 0: Skip entirely if ANYONE in the companionship was interviewed this quarter
        all_dates = [m['last_interview_date'] for m in companionship_members if m['last_interview_date'] is not None]
        if all_dates and max(all_dates) >= QUARTER_START:
            print(
                f"\t--> Status: ✅ COMPLETE. Already interviewed this quarter ({max(all_dates).strftime('%Y-%m-%d')}). Skipping.")
            continue

        # Check for individual breather metrics
        for m in companionship_members:
            m['is_breather'] = False
            if m['last_interview_date']:
                if get_months_difference(NOW, m['last_interview_date']) == 1:
                    m['is_breather'] = True

        # Check for dormant/recovery metrics (>9 months or Never)
        for m in companionship_members:
            m['is_dormant'] = False
            if m['last_interview_date'] is None:
                m['is_dormant'] = True
            else:
                if get_months_difference(NOW, m['last_interview_date']) > 9:
                    m['is_dormant'] = True

        # Count how many members are dormant
        dormant_count = sum(1 for m in companionship_members if m['is_dormant'])
        all_last_names = [m['last_name'] for m in companionship_members]
        is_shared_household = len(set(all_last_names)) == 1 and len(companionship_members) > 1

        # --- Priority Rules Mapping Engine ---

        # FALLBACK ACTION: Nominal/Dormant Partnership Check (Triggered if any companion has been missing for >9 months)
        if dormant_count > 0 and len(companionship_members) >= 2 and not is_shared_household:
            print(
                f"\t--> Strategy: ⚠️ RECOVERY PARTNERSHIP ({dormant_count} member(s) missing > 9 months). Printing texts for BOTH.")

            # Find the most critical record by comparing dates (Older date or Never)
            critical_member = companionship_members[0]
            oldest_date = critical_member['last_interview_date'] or datetime.min
            for m in companionship_members[1:]:
                curr_date = m['last_interview_date'] or datetime.min
                if curr_date < oldest_date:
                    oldest_date = curr_date
                    critical_member = m

            # Print texts for both companions individually
            for m in companionship_members:
                indicator = " [CRITICAL RECOVERY TARGET]" if m == critical_member else ""
                if m['is_breather']:
                    print(f"\t\t[Month 2 Delay]{indicator} SEND TO: {m['name']} ({m['phone']})")
                else:
                    print(f"\t\t[Month 1 Action]{indicator} SEND TO: {m['name']} ({m['phone']})")
                    print(
                        f"\t\tTEXT: \"Hi, Br {m['last_name']}. This is {YOUR_NAME}. Would you be available after church tomorrow for a ministering interview with {supervisor_last}? Right now I have times available for {time_slots_str}.\"")

        # Standard Rule 2: Shared Household Partnerships
        elif is_shared_household:
            print(f"\t--> Strategy [Rule 2]: Shared Household Partnership ({all_last_names[0]}).")
            target = companionship_members[0]
            if target['is_breather']:
                print(f"\t\t[Month 2 Delay] SEND TO: {target['name']} ({target['phone']})")
            else:
                print(f"\t\t[Month 1 Action] SEND TO: {target['name']} ({target['phone']})")
                print(
                    f"\t\tTEXT: \"Hi, Br {target['last_name']}. This is {YOUR_NAME}. Would you be available after church tomorrow for a ministering interview with {supervisor_last}? Right now I have times available for {time_slots_str}.\"")

        # Standard Rule 1: Active 2-Elder or 3-Elder Companionships (Alternating rotation)
        elif len(companionship_members) >= 2:
            print(f"\t--> Strategy [Rule 1]: Standard Multi-Elder Companionship.")
            target_companion = companionship_members[0]
            oldest_date = target_companion['last_interview_date'] or datetime.min
            for m in companionship_members[1:]:
                current_date = m['last_interview_date'] or datetime.min
                if current_date < oldest_date:
                    oldest_date = current_date
                    target_companion = m

            if target_companion['is_breather']:
                print(f"\t\t[Month 2 Delay] SEND TO: {target_companion['name']} ({target_companion['phone']})")
            else:
                print(f"\t\t[Month 1 Action] SEND TO: {target_companion['name']} ({target_companion['phone']})")
                print(f"\t\tTEXT: \"Hi, Br {target_companion['last_name']}. This is {YOUR_NAME}. Would you be available after church tomorrow for a ministering interview with {supervisor_last}? Right now I have times available for {time_slots_str}.\"")

        # Standard Single Elder Assignment
        elif len(companionship_members) == 1:
            target = companionship_members[0]
            print("\t--> Strategy: Single Elder assignment.")
            if target['is_breather']:
                print(f"\t\t[Month 2 Delay] SEND TO: {target['name']} ({target['phone']})")
            else:
                print(f"\t\t[Month 1 Action] SEND TO: {target['name']} ({target['phone']})")
                print(f"\t\tTEXT: \"Hi, Br {target['last_name']}. This is {YOUR_NAME}. Would you be available after church tomorrow for a ministering interview with {supervisor_last}? Right now I have times available for {time_slots_str}.\"")
