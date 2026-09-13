import os
import json
import calendar
import re
from datetime import datetime
import pyperclip  # Crash-proof Linux clipboard management
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# --- File Path Configuration (Ubuntu Layouts) ---
CSV_DIRECTORY_PATH = "/home/dave/PycharmProjects/ministeringDistricts/Elders_Phones.csv"
CONFIG_PATH = "/home/dave/PycharmProjects/ministeringDistricts/config.json"
FALLBACK_JSON_PATH = "/home/dave/PycharmProjects/ministeringDistricts/Ministering2026Q3.json"


class NumberedCanvas(canvas.Canvas):
    """
    A professional dynamic two-pass canvas layout engine to render running
    headers, lines, and true 'Page X of Y' counts on your workbook.
    """

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
        self.drawString(54, 755, "O'FALLON WARD ELDERS QUORUM — QUARTERLY WORKBOOK")

        self.setLineWidth(0.5)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.line(54, 747, 558, 747)

        self.setFont("Helvetica", 8)
        self.drawString(54, 40,
                        f"Generated on: {datetime.now().strftime('%Y-%m-%d')} | Confidential LDS Leadership Data")
        self.drawRightString(558, 40, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def load_config(config_path):
    defaults = {"sender_name": "Dave Stauffer", "special_titles": {"Bates, Jason": "Pres"}}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return defaults


def get_json_data():
    print("🔍 Attempting to extract data from system clipboard...")
    try:
        clipboard_content = pyperclip.paste()
    except Exception as e:
        print(f"⚠️ Clipboard read error: {e}")
        clipboard_content = ""

    if clipboard_content and clipboard_content.strip():
        print(f"📋 Clipboard detected payload size: {len(clipboard_content)} characters.")

        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', clipboard_content)
        if match:
            print("🎯 Success! Found __NEXT_DATA__ script wrapper tags on clipboard.")
            return json.loads(match.group(1))

        start_marker = '{"props":{"pageProps":'
        if start_marker in clipboard_content:
            print("🎯 Success! Found raw JSON object boundaries on clipboard layout.")
            start_idx = clipboard_content.index(start_marker)
            raw_json_chunk = clipboard_content[start_idx:]
            end_idx = raw_json_chunk.rfind('}')
            if end_idx != -1:
                try:
                    return json.loads(raw_json_chunk[:end_idx + 1])
                except Exception as e:
                    print(f"⚠️ Failed parsing raw JSON boundary chunk: {e}")
        print("❌ Could not isolate the LCR data block patterns on your clipboard.")
    else:
        print("⚠️ Clipboard appears to be completely empty.")

    print(f"📂 Looking for local fallback file at: {FALLBACK_JSON_PATH}")
    if os.path.exists(FALLBACK_JSON_PATH):
        try:
            with open(FALLBACK_JSON_PATH, 'r', encoding='utf-8') as f:
                print("🎯 Success! Loaded data directly from local file backup.")
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to parse local fallback file: {e}")
    else:
        print("❌ Local fallback file not found either.")

    return None


def get_last_name(full_name):
    """Safely extracts and cleans the last name from 'Lastname, Firstname'."""
    if ',' in full_name:
        return full_name.split(',')[0].strip()
    return full_name.strip()


def calculate_current_quarter():
    """Dynamically calculates the current calendar year and quarter based on today's date."""
    now = datetime.now()
    current_year = now.year
    current_quarter = ((now.month - 1) // 3) + 1
    return current_year, current_quarter


def build_pdf_workbook():
    print("🗓️ --- Dynamic District Signup Sheet Generator ---")

    # 1. Calculate dynamic fallbacks based on today's date
    default_year, default_quarter = calculate_current_quarter()

    # 2. Prompt user for Year and Quarter overrides
    year_input = input(f"Enter Target Year [Default Current: {default_year}]: ").strip()
    target_year = int(year_input) if year_input else default_year

    quarter_input = input(f"Enter Target Quarter (1-4) [Default Current: {default_quarter}]: ").strip()
    target_quarter = int(quarter_input) if quarter_input else default_quarter

    if target_quarter < 1 or target_quarter > 4:
        print("❌ Invalid quarter selected. Must be a number between 1 and 4.")
        return

    data = get_json_data()
    if not data:
        print("⛔ Execution halted: No valid LCR JSON data could be loaded via clipboard or file.")
        return

    try:
        elders_list = data['props']['pageProps']['initialState']['ministeringData']['elders']
        print(f"📈 Found {len(elders_list)} Districts in the dataset. Compiling PDF columns...")
    except KeyError as e:
        print(f"❌ Structural key mapping error inside JSON: {e}")
        return

    config = load_config(CONFIG_PATH)
    os.makedirs("generated", exist_ok=True)

    pdf_filename = f"generated/EQ_Ministering_Workbook_{target_year}_Q{target_quarter}.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54, rightMargin=54, topMargin=72, bottomMargin=72,
        title=f"EQ Ministering Interview Sheets Q{target_quarter}"
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=24,
                                 leading=28, textColor=colors.HexColor("#1A365D"), spaceAfter=6)
    subtitle_style = ParagraphStyle('DocSub', fontName='Helvetica-Bold', fontSize=12, leading=15,
                                    textColor=colors.HexColor("#2B6CB0"), spaceAfter=18)
    month_hdr_style = ParagraphStyle('MonthHdr', fontName='Helvetica-Bold', fontSize=14, leading=18,
                                     textColor=colors.HexColor("#2C5282"), spaceBefore=10, spaceAfter=10)
    cell_name_style = ParagraphStyle('CellName', fontName='Helvetica', fontSize=9, leading=13,
                                     textColor=colors.HexColor("#2D3748"))
    cell_header_style = ParagraphStyle('CellHeader', fontName='Helvetica-Bold', fontSize=9, leading=11,
                                       textColor=colors.white, alignment=1)

    story = []
    start_month = (target_quarter - 1) * 3 + 1
    months = [start_month, start_month + 1, start_month + 2]

    for dist in elders_list:
        district_name = dist['districtName']
        supervisor_full = dist.get('supervisorName', 'No District leader')

        title_prefix = config.get("special_titles", {}).get(supervisor_full, "Br")
        supervisor_last = f"{title_prefix} {get_last_name(supervisor_full)}" if supervisor_full != 'No District leader' else "Unassigned"

        for idx, m_idx in enumerate(months):
            month_name = calendar.month_name[m_idx]

            story.append(Paragraph(f"{district_name}", title_style))
            story.append(Paragraph(f"District Supervisor: <b>{supervisor_last}</b>", subtitle_style))
            story.append(Paragraph(f"Ministering Interview Signups — {month_name} {target_year}", month_hdr_style))

            cal = calendar.Calendar(firstweekday=6)
            m_sundays = [d for d in cal.itermonthdates(target_year, m_idx) if d.weekday() == 6 and d.month == m_idx]

            avail_sundays = []
            for s_idx, s_date in enumerate(m_sundays):
                lbl = s_date.strftime("%b %d")
                is_excluded = False
                reason = ""

                if m_idx == 4 and s_idx == 0:
                    is_excluded, reason = True, "General Conf"
                elif m_idx == 10 and s_idx == 0:
                    is_excluded, reason = True, "General Conf"
                elif m_idx == 5 and s_idx == 1:
                    is_excluded, reason = True, "Mother's Day"
                elif m_idx == 6 and s_idx == 2:
                    is_excluded, reason = True, "Father's Day"
                elif m_idx == 12 and s_date.day in [24,25,31]:
                    is_excluded, reason = True, "Holiday"

                avail_sundays.append({"label": lbl, "excluded": is_excluded, "reason": reason})

            headers = ["Current Companionships Assigned"] + [s["label"] for s in avail_sundays]
            table_data = [[Paragraph(h, cell_header_style) for h in headers]]

            for comps in dist["companionships"]:
                names_list = [m.get('name', 'Unknown') for m in comps['ministers']]
                if not names_list:
                    continue

                comp_text = "<br/>".join([f"• {name}" for name in names_list])
                comp_p = Paragraph(comp_text, cell_name_style)

                row = [comp_p]
                for s in avail_sundays:
                    if s["excluded"]:
                        row.append(Paragraph(f"<font color='#A0AEC0'><i>{s['reason']}</i></font>", cell_name_style))
                    else:
                        row.append(Paragraph("Time: _________", cell_name_style))
                table_data.append(row)

            num_cols = len(headers)
            col_widths = [180] + [(324 / (num_cols - 1))] * (num_cols - 1)

            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ]

            for r_idx in range(1, len(table_data)):
                if r_idx % 2 == 0:
                    t_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor("#F7FAFC")))

            t.setStyle(TableStyle(t_style))
            story.append(t)

            if idx < len(months) - 1 or dist != elders_list[-1]:
                story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"🎉 Success! Production workbook generated cleanly at: {pdf_filename}")


if __name__ == "__main__":
    build_pdf_workbook()
