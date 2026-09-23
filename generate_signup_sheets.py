# -*- coding: utf-8 -*-
from pathlib import Path
import os
import json
import calendar
import re
from datetime import datetime, date
import pyperclip  # Crash-proof Linux clipboard management
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent
# --- File Path Configuration (Ubuntu Layouts) ---
CSV_DIRECTORY_PATH = BASE_DIR / "Elders_Phones.csv"
CONFIG_PATH = BASE_DIR / "config.json"
FALLBACK_JSON_PATH = BASE_DIR / "Ministering2026Q3.json"


class NumberedCanvas(canvas.Canvas):
    """Adds professional running headers and page numbering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        self.drawString(54, 755, "ELDERS QUORUM MINISTERING INTERVIEW SIGNUP SHEETS")

        self.setLineWidth(0.5)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.line(54, 747, 558, 747)

        self.setFont("Helvetica", 8)
        self.drawString(54, 40, f"Generated: {datetime.now().strftime('%Y-%m-%d')} | Confidential Data")
        self.drawRightString(558, 40, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def load_config(config_path):
    defaults = {
        "sender_name": "Dave Stauffer",
        "special_titles": {"Bates, Jason": "Pres"},
        "default_slots": ["11:15 AM", "11:35 AM", "11:55 AM"],
        "custom_district_slots": {
            "District 2": ["11:20 AM", "11:35 AM", "11:55 AM"],
            "District 3": ["11:20 AM", "11:35 AM", "11:55 AM"]
        },
        "stake_conference_dates": []
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return defaults


def format_supervisor_name(full_name, title_prefix):
    if not full_name or full_name == 'No District leader':
        return "Unassigned"
    if ',' in full_name:
        parts = full_name.split(',')
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ""
        return f"{title_prefix} {first} {last}".strip()
    return f"{title_prefix} {full_name.strip()}"


def get_json_data():
    print("🔍 Attempting to extract data from system clipboard...")
    try:
        clipboard_content = pyperclip.paste()
    except Exception as e:
        print(f"⚠️ Clipboard read error: {e}")
        clipboard_content = ""

    if clipboard_content and clipboard_content.strip():
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', clipboard_content)
        if match:
            print("🎯 Success! Found __NEXT_DATA__ wrapper tags.")
            return json.loads(match.group(1))

        start_marker = '{"props":{"pageProps":'
        if start_marker in clipboard_content:
            start_idx = clipboard_content.index(start_marker)
            raw_json_chunk = clipboard_content[start_idx:]
            return json.loads(raw_json_chunk[:raw_json_chunk.rfind('}') + 1])

    print(f"📂 Looking for local fallback file at: {FALLBACK_JSON_PATH}")
    if os.path.exists(FALLBACK_JSON_PATH):
        try:
            with open(FALLBACK_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def calculate_current_quarter():
    now = datetime.now()
    return now.year, ((now.month - 1) // 3) + 1


def get_easter_date(year):
    """Calculates the exact Gregorian date for Easter Sunday dynamically."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def build_pdf_signup_sheets():
    print("🗓️ --- Printed Signup Sheets Generator ---")

    default_year, default_quarter = calculate_current_quarter()
    year_input = input(f"Enter Target Year [Default Current: {default_year}]: ").strip()
    target_year = int(year_input) if year_input else default_year

    quarter_input = input(f"Enter Target Quarter (1-4) [Default Current: {default_quarter}]: ").strip()
    target_quarter = int(quarter_input) if quarter_input else default_quarter

    data = get_json_data()
    if not data:
        print("⛔ Execution halted: No valid LCR JSON data loaded.")
        return

    try:
        elders_list = data['props']['pageProps']['initialState']['ministeringData']['elders']
    except KeyError:
        print("❌ Key structure mapping error inside JSON data.")
        return

    config = load_config(CONFIG_PATH)
    stake_conf_list = config.get("stake_conference_dates", [])
    os.makedirs("generated", exist_ok=True)

    # Pre-calculate the moving calendar holidays for the chosen target year
    easter_sunday = get_easter_date(target_year)

    pdf_filename = f"generated/EQ_Signup_Sheets_{target_year}_Q{target_quarter}.pdf"
    doc = SimpleDocTemplate(
        pdf_filename, pagesize=letter,
        leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54
    )

    styles = getSampleStyleSheet()
    dist_style = ParagraphStyle('DistTitle', fontName='Helvetica-Bold', fontSize=24, leading=28,
                                textColor=colors.HexColor("#1A365D"), spaceBefore=5, spaceAfter=2)
    sup_style = ParagraphStyle('SupTitle', fontName='Helvetica', fontSize=13, leading=17,
                               textColor=colors.HexColor("#2B6CB0"), spaceAfter=15)
    date_style = ParagraphStyle('DateHdr', fontName='Helvetica-Bold', fontSize=12, leading=16,
                                textColor=colors.HexColor("#2D3748"), spaceBefore=10, spaceAfter=4)
    cell_time_style = ParagraphStyle('CellTime', fontName='Helvetica-Bold', fontSize=10, leading=14,
                                     textColor=colors.HexColor("#2D3748"))
    cell_line_style = ParagraphStyle('CellLine', fontName='Helvetica', fontSize=10, leading=14,
                                     textColor=colors.HexColor("#CBD5E0"))
    footer_text_style = ParagraphStyle('FootNotes', fontName='Helvetica-Oblique', fontSize=10, leading=14,
                                       textColor=colors.HexColor("#4A5568"), spaceBefore=15, spaceAfter=8)
    virtual_signup_style = ParagraphStyle('VirtualLines', fontName='Helvetica', fontSize=10, leading=16,
                                          textColor=colors.HexColor("#A0AEC0"), leftIndent=15)

    story = []
    start_month = (target_quarter - 1) * 3 + 1
    months = [start_month, start_month + 1, start_month + 2]

    for dist in elders_list:
        district_name = dist['districtName']
        supervisor_full = dist.get('supervisorName', 'No District leader')
        title_prefix = config.get("special_titles", {}).get(supervisor_full, "Br")
        formatted_supervisor = format_supervisor_name(supervisor_full, title_prefix)

        slots = config.get("custom_district_slots", {}).get(district_name, config.get("default_slots"))

        for m_idx in months:
            month_name = calendar.month_name[m_idx]

            story.append(Paragraph(f"{district_name}", dist_style))
            story.append(Paragraph(f"Presidency Member: {formatted_supervisor}", sup_style))
            story.append(Spacer(1, 5))

            cal = calendar.Calendar(firstweekday=6)
            m_sundays = [d for d in cal.itermonthdates(target_year, m_idx) if d.weekday() == 6 and d.month == m_idx]

            for s_idx, s_date in enumerate(m_sundays):
                lbl = s_date.strftime("%B %d")
                date_iso_str = s_date.strftime("%Y-%m-%d")
                story.append(Paragraph(f"{lbl}", date_style))

                is_excluded = False
                reason = ""

                # Rule A: General Conferences
                if m_idx == 4 and s_idx == 0:
                    is_excluded, reason = True, "General Conference"
                elif m_idx == 10 and s_idx == 0:
                    is_excluded, reason = True, "General Conference"

                # Rule B: Stake Conference list check
                elif date_iso_str in stake_conf_list:
                    is_excluded, reason = True, "Stake Conference"

                # Rule C: Christmas / New Year boundaries
                elif m_idx == 12 and s_date.day in [24, 25, 26, 31]:
                    is_excluded, reason = True, "Christmas Break"
                elif m_idx == 1 and s_date.day in [1]:
                    is_excluded, reason = True, "New Year's Break"

                # Rule D: DYNAMIC MOVING HOLIDAYS
                elif s_date == easter_sunday:
                    is_excluded, reason = True, "Easter Sunday"
                elif m_idx == 5 and s_idx == 1:  # 2nd Sunday in May
                    is_excluded, reason = True, "Mother's Day"
                elif m_idx == 6 and s_idx == 2:  # 3rd Sunday in June
                    is_excluded, reason = True, "Father's Day"

                table_data = []
                if is_excluded:
                    table_data.append(
                        [Paragraph(f"<font color='#A0AEC0'><i>*** No Interviews Scheduled ({reason}) ***</i></font>",
                                   cell_line_style), ""])
                else:
                    for i in range(0, len(slots), 2):
                        row = []
                        row.append(Paragraph(f"{slots[i]:<12} _______________________", cell_time_style))
                        if i + 1 < len(slots):
                            row.append(Paragraph(f"{slots[i + 1]:<12} _______________________", cell_time_style))
                        else:
                            row.append(Paragraph("", cell_line_style))
                        table_data.append(row)

                t = Table(table_data, colWidths=[234, 234])
                t.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LINEBELOW', (0, 0), (-1, -1), 0.2, colors.HexColor("#E2E8F0")),
                ]))
                story.append(t)
                story.append(Spacer(1, 5))

            story.append(
                Paragraph("I prefer a virtual (telephone) appointment [list preferred time (to be confirmed later)]:",
                          footer_text_style))
            story.append(Paragraph("1. Name: _______________________________  Date/Time: ___________________",
                                   virtual_signup_style))
            story.append(Spacer(1, 4))
            story.append(Paragraph("2. Name: _______________________________  Date/Time: ___________________",
                                   virtual_signup_style))
            story.append(Spacer(1, 4))
            story.append(Paragraph("3. Name: _______________________________  Date/Time: ___________________",
                                   virtual_signup_style))

            if m_idx != months[-1] or dist != elders_list[-1]:
                story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"🎉 Success! Production signup sheets generated cleanly at: {pdf_filename}")


if __name__ == "__main__":
    build_pdf_signup_sheets()
