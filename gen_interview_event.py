import urllib.parse
from datetime import datetime, timedelta


def get_initials(full_name):
    if ',' in full_name:
        parts = full_name.split(',')
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ""
        if first:
            return f"{first[0]}{last[0]}".upper()
        return f"{last[:2]}".upper()
    parts = full_name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return full_name[:2].upper()


def get_next_sunday():
    today = datetime.now()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday.strftime("%Y-%m-%d")


def create_testing_link():
    print("🗓️ --- Google Calendar Invitation Link Tool (TEST MODE) ---")
    default_sunday = get_next_sunday()

    elder_name = input("Enter Elder's Name (e.g., Bob Smith): ").strip()
    date_input = input(f"Enter Meeting Date [Default Next Sunday: {default_sunday}]: ").strip()
    meeting_date = date_input if date_input else default_sunday

    start_time = input("Enter Start Time (24hr HH:MM, e.g., 11:15 or 11:20): ").strip()
    supervisor = input("Enter Supervisor Name (Default: Jason Bates): ").strip() or "Jason Bates"

    initials = get_initials(supervisor)
    title = f"{initials}-MI-{elder_name}"

    try:
        start_dt = datetime.strptime(f"{meeting_date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=20)
    except ValueError as e:
        print(f"❌ Error formatting time or date fields: {e}.")
        return

    time_format = "%Y%m%dT%H%M%S"
    dates_param = f"{start_dt.strftime(time_format)}/{end_dt.strftime(time_format)}"

    location = "The Church of Jesus Christ of Latter-day Saints, 1401 S Henke Rd, Lake St Louis, MO 63367, USA"
    description = f"O'Fallon Ward Elder Quorum Presidency Calendar\nInterviewer: {supervisor}"
    testing_guests = "dstau@example.com"

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates_param,
        "details": description,
        "location": location,
        "add": testing_guests
    }

    # --- FIXED REAL ENDPOINT VALUE ---
    base_url = "https://google.com"
    final_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    print(f"\n🚀 Event Structure Generated for Sunday, {meeting_date}!")
    print("👉 Hold Ctrl and click the link below to verify on your calendar layout:")
    print(final_url)


if __name__ == "__main__":
    create_testing_link()
