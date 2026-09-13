import os
import json
import re
from datetime import datetime
import pyperclip  # Crash-proof Linux clipboard management
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# --- File Path Configuration (Ubuntu Layouts) ---
CSV_DIRECTORY_PATH = "/home/dave/PycharmProjects/ministeringDistricts/Elders_Phones.csv"
CONFIG_PATH = "/home/dave/PycharmProjects/ministeringDistricts/config.json"
FALLBACK_JSON_PATH = "/home/dave/PycharmProjects/ministeringDistricts/Ministering2026Q3.json"


class NumberedCanvas(canvas.Canvas):
    """Adds professional running headers, clean rule lines, and dynamic page counts."""

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
        self.drawString(54, 755, "MINISTERING DISTRICTS ROSTER")

        self.setLineWidth(0.5)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.line(54, 747, 558, 747)

        self.setFont("Helvetica", 8)
        self.drawString(54, 40, f"Generated: {datetime.now().strftime('%Y-%m-%d')} | Confidential Data")
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


def format_supervisor_name(full_name, title_prefix):
    """
    Safely cleans and converts 'Bates, Jason' or 'Jason Bates' with its config title
    into a natural human-driven 'Pres Jason Bates' layout format.
    """
    if not full_name or full_name == 'No District leader':
        return "Unassigned"

    # Handle 'Lastname, Firstname' format
    if ',' in full_name:
        parts = full_name.split(',')
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ""
        return f"{title_prefix} {first} {last}".strip()

    # Handle standard 'Firstname Lastname' spacing format if data format fluctuates
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
            end_idx = raw_json_chunk.rfind('}')
            if end_idx != -1:
                try:
                    return json.loads(raw_json_chunk[:end_idx + 1])
                except Exception:
                    pass

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


def build_pdf_workbook():
    print("🗓️ --- Simple List District Roster Generator ---")

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
    os.makedirs("generated", exist_ok=True)

    pdf_filename = f"generated/EQ_District_List_{target_year}_Q{target_quarter}.pdf"
    doc = SimpleDocTemplate(
        pdf_filename, pagesize=letter,
        leftMargin=54, rightMargin=54, topMargin=72, bottomMargin=72
    )

    styles = getSampleStyleSheet()

    dist_style = ParagraphStyle('DistTitle', fontName='Helvetica-Bold', fontSize=22, leading=26,
                                textColor=colors.HexColor("#1A365D"), spaceBefore=10, spaceAfter=4)
    sup_style = ParagraphStyle('SupTitle', fontName='Helvetica', fontSize=12, leading=16,
                               textColor=colors.HexColor("#2B6CB0"), spaceAfter=6)
    meta_style = ParagraphStyle('MetaYear', fontName='Helvetica-Bold', fontSize=10, leading=14,
                                textColor=colors.HexColor("#718096"), spaceAfter=15)
    comp_header = ParagraphStyle('CompHead', fontName='Helvetica-Bold', fontSize=11, leading=15,
                                 textColor=colors.HexColor("#2D3748"), spaceBefore=8, spaceAfter=2)
    name_style = ParagraphStyle('MemberName', fontName='Helvetica', fontSize=10, leading=14,
                                textColor=colors.HexColor("#4A5568"), leftIndent=15)

    story = []

    # Text lookup rules conversion array map
    suffix_map = {1: "st", 2: "nd", 3: "rd", 4: "th"}
    q_suffix = suffix_map.get(target_quarter, "th")

    for dist in elders_list:
        district_name = dist['districtName']
        supervisor_full = dist.get('supervisorName', 'No District leader')

        # 1. Determine Title Override Prefix Rule (Defaults to Br)
        title_prefix = config.get("special_titles", {}).get(supervisor_full, "Br")

        # 2. FIXED: Format Supervisor Name into '[Title] [FirstName] [LastName]'
        formatted_supervisor = format_supervisor_name(supervisor_full, title_prefix)

        # Add basic district sheet metadata headers
        story.append(Paragraph(f"{district_name}", dist_style))
        story.append(Paragraph(f"Supervisor: {formatted_supervisor}", sup_style))
        story.append(Paragraph(f"Ministering Districts - {target_year} {target_quarter}{q_suffix} Quarter", meta_style))
        story.append(Paragraph("Companionships:", comp_header))
        story.append(Spacer(1, 4))

        for comps in dist["companionships"]:
            ministers = comps.get('ministers', [])
            if not ministers:
                continue

            for m in ministers:
                story.append(Paragraph(f"{m.get('name', 'Unknown')}", name_style))

            story.append(Spacer(1, 8))

        if dist != elders_list[-1]:
            story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"🎉 Success! Simple layout roster generated cleanly at: {pdf_filename}")


if __name__ == "__main__":
    build_pdf_workbook()
