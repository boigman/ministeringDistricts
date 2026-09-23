# 🛠️ Elders Quorum Ministering Automation Suite

A complete, production-ready automation toolkit for an Elders Quorum Presidency. This suite simplifies the administrative burden of ministering interviews by providing automated text invitation systems, secure Google Calendar synchronization tools, professional PDF booklet/signup sheet layouts, past event data auditing, and delinquency reporting.

---


## 🎯 Core Project Goals

The overarching objective of this toolkit is to provide a **lightweight, terminal-based automation suite** that minimizes the administrative burden of running an Elders Quorum presidency, specifically targeting **Ministering Interviews**. The suite fulfills four core pillars:

1. **Text Invitation Automation:** Eliminate the manual work of checking who is due for an interview and writing out text invitations one by one.
2. **Calendar Integration:** Provide a fast, error-proof way to log confirmed appointments onto a shared Google Calendar without manually typing names, times, or custom titles.
3. **Presidency Coordination:** Automatically generate copy-and-paste schedule updates for the weekly presidency text thread and real-time reminders for scheduled elders on Sunday morning.
4. **Data Reconciliation & Auditing:** Cross-examine what was actually scheduled on the calendar against what LCR shows as officially recorded to ensure no interviews slip through the cracks.

---

## 📋 Logical Assumptions & Business Rules

We codified specific presidency logic, Church directory constraints, and behavioral rules into the codebase to keep the automation intelligent:

### 1. The Interview Priority & Breather Engine (`main.py`)
To prevent over-texting or contacting elders out of order, the selection engine operates under a strict hierarchy based on the elapsed time since their last interview:
* **Rule 0 (Quarterly Complete):** If *any single member* of a companionship has had an interview recorded in the active calendar quarter, the entire companionship is marked as **Complete** and skipped entirely for that quarter.
* **The "Breather" Rule (Month 2 Delay):** If a companionship was interviewed exactly one month ago, they are in a "breather" month. The script skips texting them this week to avoid spamming them, allowing them to shift to an alternating two-month rotation.
* **The "Action" Rule (Month 1 Action):** If their last interview was 2+ months ago, they are due. The script targets the companion who has gone the longest without an interview and prints a custom text invitation.
* **The "Recovery" Action (Dormant > 9 Months):** If an active elder has gone 9+ months without an interview or is marked as *Never Interviewed*, they are flagged as a high-priority recovery target. The script overrides standard rotation rules and generates a customized text invitation to **both** companions to maximize contact success.
* **Shared Household Rule:** If companions live in the same house (e.g., family members sharing a last name), the system skips complex individual rotations and coordinates their timeslot under a single invitation.

### 2. Name Matching & Nickname Reconciliation
* **First-Initial/Last-Name Matching:** Because humans use short names or nicknames on calendars (e.g., *"Devon Harris"*, *"Dave Stauffer"*) while LCR lists formal names (*"Harris, Devon Riley"*, *"Stauffer, David"*), the audit and reminder tools strip out commas and middle names. They validate matches by enforcing that the **last name** and the **first initial** match exactly.
* **Quorum Integrity Filtering:** The raw LCR page source includes all assigned ministers—including spouses or Relief Society sisters assigned to companion blocks. To prevent non-quorum members from appearing on Elders Quorum delinquency logs, the tools pass all names through a strict cross-reference filter against `Elders_Phones.csv`. Anyone not on that official quorum phone roster is silently filtered out.

### 3. Date & Quarter Synchronization
* **LCR Static Quarter Matching:** When an interview checkbox is clicked in LCR, the database records the date as the **first day of that quarter** (e.g., July 1st for Q3) rather than the actual Sunday the meeting occurred. The audit tool is "quarter-aware"; it calculates which calendar quarter an event belongs to and successfully matches a July 19th calendar event to a July 1st LCR record without triggering a false positive flag.
* **Dynamic Calendar Defaults:** Summary and reminder tools inspect the system clock. If executed on a Sunday, they default to evaluating *today's date*. If run on a weekday, they automatically step forward to calculate the *upcoming Sunday* as the target baseline.

---

## 💻 Technical Assumptions & Environment Constraints

The system was progressively hardened to guarantee total cross-platform stability across **Ubuntu Linux** (local development space) and **Windows/macOS** (successor environments):

* **Zero-Input Clipboard Parsing:** Rather than scraping LCR behind a password wall (which violates Church safety policies), the tools safely read live member data instantly via the system clipboard (`pyperclip`) using raw HTML source code chunks (`__NEXT_DATA__`).
* **Universal Interpreter Pathing (`sys.executable`):** To stop Windows from accidentally routing background script executions through old, native Python 2.7 installations, the menu launcher explicitly tracks the active path of the running Python 3 interpreter to open all sub-scripts cleanly.
* **Platform-Independent String Formatters:** Windows crashes when processing Linux zero-padding day/hour text commands (`%-d` or `%-I`). The system includes local OS detection hooks to seamlessly swap out hyphen modifiers for native Windows hash symbols (`%#d` and `%#I`) on the fly.
* **Dynamic Directory Anchoring (`pathlib.Path`):** All hardcoded Ubuntu path tracking arrays were completely removed. The toolkit automatically anchors all data files (`config.json`, keys, databases) relative to the root directory where `menu.py` is sitting.
* **Network & Security Bypasses:** 
  * Ubuntu's local DNS caching layers can block standard mail address lookups. The configuration file routes automated message delivery traffic using Google’s **direct, permanent global server IP block (`74.125.142.108`)**, bypassing local routing bottlenecks entirely.
  * Google’s cloud servers require explicit full-access calendar permissions (`.../auth/calendar.events`) to allow event insertion while cleanly reading records.


## 📁 Recommended Directory Structure
To run successfully, the compiled executable or Python files must live in the same directory alongside their respective data registries and access keys:

```text
📁 OF Ward EQ Ministering Tools/
│
├── 🚀 Run_EQ_Suite.exe         # The master console menu dashboard app
├── ⚙️ config.json              # Central settings (names, timeslots, calendar ID, emails)
├── 📋 Elders_Phones.csv        # The official LCR member roster directory
├── 🔑 credentials.json         # Google Cloud API Project Access Key
└── 🎟️ token.json               # Secure Google Calendar login handshake token
```

---

## 📋 1. How to Generate `Elders_Phones.csv`
The automation suite relies on a local member directory spreadsheet to look up phone numbers, emails, and resolve name variations or nicknames automatically. You must regenerate this file once every quarter.

1. **Log in to LCR:** Go to [lcr.churchofjesuschrist.org](https://churchofjesuschrist.org) and log in with your Church Account credentials.
2. **Navigate to the Directory:** In the main top navigation menu, click on **Reports** and select **Directory**.
3. **Filter by Quorum:** On the left-hand sidebar menu, change the target dropdown filter selection from *Ward* to **Elders Quorum**.
4. **Export the Data:** Look toward the upper-right corner of the member grid list and click the **Export** button. This downloads a spreadsheet file onto your computer.
5. **Verify Columns:** Open the file in Excel, LibreOffice, or Google Sheets. Ensure it contains the following three column headers exactly (do not alter spelling or capitalization):
   * `Name` (Formatted by the Church as *Lastname, Firstname*)
   * `Phone Number` (or `Phone`)
   * `E-mail`
6. **Save as CSV:** Click **File > Save As**. Choose **CSV (Comma Delimited) (`.csv`)** as the file type. 
7. **Rename & Place:** Name the file exactly **`Elders_Phones.csv`** and drop it directly into the same folder as your master dashboard program.

---

## 📋 2. How to Copy the LCR Ministering Page to Your Clipboard
To pull live companion histories and calculate interview priority intervals without saving your password inside the code, the suite reads your active data instantly from your system clipboard cache.

1. **Navigate to Ministering:** Inside LCR, click on **Organizations** in the top menu and select **Elders Quorum**. Click on the **Ministering** tab.
2. **Open Raw Page Source:** 
   * On **Windows or Linux** keyboards: Press **`Ctrl + U`**
   * On **macOS (Safari/Chrome)** keyboards: Press **`Option + Command + U`** (or right-click the page background and select *View Page Source*).
3. *A new browser tab will open displaying columns of raw HTML text.*
4. **Select All Data:**
   * On **Windows/Linux**: Press **`Ctrl + A`**
   * On **macOS**: Press **`Command + A`**
5. **Copy Everything:**
   * On **Windows/Linux**: Press **`Ctrl + C`**
   * On **macOS**: Press **`Command + C`**
6. **Execute:** Minimize your browser, open the master suite dashboard, and choose an action (like Option 1 or Option 8). The script will automatically intercept your copied payload text block instantly!

---

## ⚙️ 3. Central Configuration (`config.json`)
Before launching the tools, open `config.json` in Notepad or any text editor to initialize your presidency setup parameters:

* **`sender_name`**: Your name (used to sign text messages automatically).
* **`presidency_calendar_id`**: The target shared Google Calendar string address.
* **`special_titles`**: Map leadership last names to formal callings (e.g., `"Bates, Jason": "Pres"`).
* **`default_slots`**: Your standard Sunday interview availability windows (e.g., `["11:15 AM", "11:35 AM"]`).
* **`stake_conference_dates`**: Add blockout dates in `YYYY-MM-DD` layout format to automatically skip texting or printing sheets for those weekends.
* **`my_email` & `app_password`**: Set up a 16-digit Google App Password to securely email generated logs directly to your mobile device's notification panel.

---

## 🚀 4. How to Run the App Suite

This suite runs natively using the modern Python 3 platform engine. Ensure you have installed the required background libraries (`pip install pyperclip reportlab google-api-python-client google-auth-oauthlib`) before launching.

### 🏁 On Windows:
1. Open Windows File Explorer and navigate into your project folder: `OF Ward EQ Ministering Tools`.
2. Click directly onto any empty white space inside the **folder address path bar** at the very top of the window (where it lists *This PC > USB Drive...*).
3. Type the letters **`cmd`** directly into that top bar and press **Enter**. A black Command Prompt window will open, targeted inside your directory.
4. Type this command and press **Enter** to launch the master dashboard:
   ```cmd
   python menu.py
   ```
   *(Note: If your system environment variables default to an older version of Python, launch using `py -3 menu.py` or `python3 menu.py` instead.)*

### 🐧 On Ubuntu Linux:
1. Open a terminal window directly inside your toolkit directory.
2. Launch the master dashboard suite using your virtual environment Python interpreter path to ensure all background dependencies map seamlessly:
   ```bash
   .venv/bin/python menu.py
   ```
