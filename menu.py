import os
import sys


def clear_screen():
    """Prints whitespace lines to cleanly clear the PyCharm internal run console views."""
    print("\n" * 40)



def display_menu():
    clear_screen()
    print("=========================================================")
    print(" 🛠️  ELDERS QUORUM MINISTERING AUTOMATION SUITE DASHBOARD")
    print("=========================================================")
    print(" 1) [Text Tool] Run Priority Text Invitation Generator (main.py)")
    print(" 2) [Calendar]  Sync/Insert a Confirmed Appointment (insert_interview_event.py)")
    print(" 3) [Calendar]  Generate 2-Week Summary Text for Presidency (generate_presidency_summary.py)")
    print(" 4) [Calendar]  Generate Today's Sunday Text Reminders (generate_today_reminders.py)")
    print(" 5) [PDF Sheet] Print Clean District List Rosters (generate_district_sheets.py)")
    print(" 6) [PDF Sheet] Print Clean Monthly Signup Sheets Table (generate_signup_sheets.py)")
    print(" 7) [Auditor]   Reconcile Google Calendar vs Recorded LCR History (audit_interview_records.py)")
    print(" 8) [Git Save]  Backup/Push Code Updates to Private GitHub Repository")
    print(" 9) Exit Suite")
    print("=========================================================")


def main_loop():
    while True:
        display_menu()
        choice = input("Enter your choice (1-9): ").strip()

        if choice == '1':
            print("\nExecuting Priority Text Invitation Generator...\n")
            os.system("python main.py")
        elif choice == '2':
            print("\nExecuting Google Calendar Event Sync/Inserter...\n")
            os.system("python insert_interview_event.py")
        elif choice == '3':
            print("\nExecuting 2-Week Summary Text Compiler...\n")
            os.system("python generate_presidency_summary.py")
        elif choice == '4':
            print("\nExecuting Today's Text Reminder Generator...\n")
            os.system("python generate_today_reminders.py")
        elif choice == '5':
            print("\nCompiling PDF Roster Lists...\n")
            os.system("python generate_district_sheets.py")
        elif choice == '6':
            print("\nCompiling PDF Monthly Signup Tables...\n")
            os.system("python generate_signup_sheets.py")
        elif choice == '7':
            print("\nRunning Google Calendar vs LCR Audit Reconciliation Engine...\n")
            os.system("python audit_interview_records.py")
        elif choice == '8':
            print("\nBacking up files to private cloud GitHub registry...\n")
            os.system(
                "git add . && git commit -m 'Dashboard Update: Full tool alignment completed' && git push origin main")
        elif choice == '9':
            print("\nExiting Suite. Have a fantastic Sunday!")
            sys.exit(0)
        else:
            input("\n❌ Invalid Selection. Press Enter to return to menu...")
            continue

        print("\n=========================================================")
        input("Execution completed. Press Enter to return to dashboard...")


if __name__ == "__main__":
    main_loop()
