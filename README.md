# 🛠️ Elders Quorum Ministering Automation Suite

A complete, production-ready automation toolkit for an Elders Quorum Presidency. This suite simplifies the administrative burden of ministering interviews by providing automated text invitation systems, secure Google Calendar synchronization tools, professional PDF booklet/signup sheet layouts, past event data auditing, and delinquency reporting.

---

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
### 🏁 On Windows:
Simply double-click the **`Run_EQ_Suite.exe`** icon file inside the folder workspace. A standard console menu option screen will initialize immediately.

### 🐧 On Ubuntu Linux:
1. Open a terminal inside your folder directory block.
2. Grant execution privileges to the program once:  
   `chmod +x menu`
3. Launch the dashboard suite natively:  
   `./menu`
