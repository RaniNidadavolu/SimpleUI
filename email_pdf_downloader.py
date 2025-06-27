# email_pdf_downloader
# Updated to integrate with Next.js, Prisma, and IMAP for PDF retrieval

import os
import imaplib
import email
from email.header import decode_header
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create folders
os.makedirs("./pdfs", exist_ok=True)
os.makedirs("./config", exist_ok=True)

# Database setup
conn = sqlite3.connect("./config/email_accounts.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS email_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    imap_server TEXT NOT NULL
)
""")
conn.commit()

def add_email_account(email, password, imap_server):
    """Add a new email account to the database."""
    try:
        c.execute(
            "INSERT INTO email_accounts (email, password, imap_server) VALUES (?, ?, ?)",
            (email, password, imap_server)
        )
        conn.commit()
        print(f"✅ Added account: {email}")
    except sqlite3.Error as db_error:
        print(f"❌ Database error while adding account: {db_error}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def fetch_pdfs():
    """Fetch PDFs from all configured email accounts."""
    c.execute("SELECT email, password, imap_server FROM email_accounts")
    accounts = c.fetchall()

    if not accounts:
        print("⚠️ No email accounts configured.")
        return

    for email_user, email_pass, imap_server in accounts:
        print(f"\n📧 Checking emails for: {email_user}")

        try:
            # Connect to the email server
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_user, email_pass)
            mail.select("inbox")

            # Search for all emails
            status, messages = mail.search(None, 'ALL')
            if status != "OK":
                print(f"⚠️ No messages found for {email_user}")
                continue

            for num in messages[0].split():
                try:
                    _, msg = mail.fetch(num, '(RFC822)')
                    for response_part in msg:
                        if isinstance(response_part, tuple):
                            # Parse email
                            msg = email.message_from_bytes(response_part[1])
                            subject, encoding = decode_header(msg.get("Subject"))[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else 'utf-8')

                            from_address = msg.get("From")
                            date_received = msg.get("Date")

                            # Process attachments
                            for part in msg.walk():
                                if part.get_content_maintype() == 'multipart':
                                    continue
                                if part.get('Content-Disposition') and 'attachment' in part.get('Content-Disposition'):
                                    filename = part.get_filename()
                                    if filename and filename.endswith('.pdf'):
                                        filepath = os.path.join("./pdfs", filename)
                                        if not os.path.exists(filepath):
                                            with open(filepath, "wb") as f:
                                                f.write(part.get_payload(decode=True))
                                            print(f"📥 Downloaded: {filename} from {from_address} on {date_received}")
                                        else:
                                            print(f"⚠️ Skipped existing file: {filename}")
                except Exception as msg_error:
                    print(f"❌ Error processing email {num} for {email_user}: {msg_error}")

            mail.close()
            mail.logout()

        except imaplib.IMAP4.error as imap_error:
            print(f"❌ IMAP error for {email_user}: {imap_error}")
        except Exception as e:
            print(f"❌ Unexpected error for {email_user}: {e}")

# Example usage
if __name__ == "__main__":
    # Uncomment to add a new email account
    # add_email_account("your_email@example.com", os.getenv("EMAIL_PASSWORD"), "imap.gmail.com")
    fetch_pdfs()
