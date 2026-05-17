import imaplib
import email
from email.header import decode_header


def decode_mime_header(header_value: str) -> str:

    if header_value is None:
        return ""

    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            # Decode bytes using the specified charset, or UTF-8 as fallback
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def get_email_body(msg: email.message.Message) -> str:

    body = ""

    if msg.is_multipart():
        # Walk through all parts of the multipart message
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments — we only want the email body
            if "attachment" in content_disposition:
                continue

            # Extract plain text parts
            if content_type == "text/plain":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break  # Use the first plain text part found
                except Exception:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        # Single-part message — extract payload directly
        try:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

    return body.strip()


def receive_latest_email(user_email: str, user_password: str,
                         imap_server: str = "imap.gmail.com",
                         imap_port: int = 993) -> dict | None:

    try:
        print(f"[IMAP] Connecting to {imap_server}:{imap_port}...")
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)

        print(f"[IMAP] Logging in as {user_email}...")
        mail.login(user_email, user_password)

        status, messages = mail.select("INBOX", readonly=True)

        if status != "OK":
            print("[ERROR] Could not select INBOX.")
            mail.logout()
            return None

        total_emails = int(messages[0])
        print(f"[IMAP] Total emails in INBOX: {total_emails}")

        if total_emails == 0:
            print("[IMAP] Mailbox is empty — no emails to fetch.")
            mail.logout()
            return None

        latest_email_id = str(total_emails)
        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

        if status != "OK":
            print(f"[ERROR] Could not fetch email #{latest_email_id}.")
            mail.logout()
            return None

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        sender = decode_mime_header(msg.get("From", "Unknown"))
        subject = decode_mime_header(msg.get("Subject", "No Subject"))
        date = msg.get("Date", "Unknown Date")

        body = get_email_body(msg)

        mail.close()
        mail.logout()

        result = {
            "from": sender,
            "subject": subject,
            "date": date,
            "body": body,
        }

        print("\n" + "=" * 60)
        print("  LATEST EMAIL")
        print("=" * 60)
        print(f"  From:    {result['from']}")
        print(f"  Subject: {result['subject']}")
        print(f"  Date:    {result['date']}")
        print("-" * 60)
        print(f"  Body:\n{result['body']}")
        print("=" * 60)

        return result

    except imaplib.IMAP4.error as e:
        print(f"[ERROR] IMAP error: {e}")
        print("        Check your credentials or IMAP settings.")
        return None

    except ConnectionRefusedError:
        print(f"[ERROR] Connection refused by {imap_server}:{imap_port}.")
        return None

    except TimeoutError:
        print(f"[ERROR] Connection to {imap_server}:{imap_port} timed out.")
        return None

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return None


# ── Hard-coded test cases ────────────────────────────────────────────
if __name__ == "__main__":
    # ╔═══════════════════════════════════════════════════════╗
    # ║  CONFIGURATION — Replace with your own credentials    ║
    # ╚═══════════════════════════════════════════════════════╝

    USER_EMAIL = "your_email@gmail.com"
    USER_PASSWORD = "your_app_password"       # Use App Password for Gmail
    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    # ── Test Case 1: Fetch the latest email ─────────────────────────
    print("=" * 50)
    print("TEST CASE 1: Fetch latest email")
    print("=" * 50)
    result = receive_latest_email(
        user_email=USER_EMAIL,
        user_password=USER_PASSWORD,
        imap_server=IMAP_SERVER,
        imap_port=IMAP_PORT,
    )

    if result:
        print("\n[SUCCESS] Email fetched successfully.")
    else:
        print("\n[FAILED] Could not fetch email.")

    # ── Test Case 2: Intentional error (bad credentials) ────────────
    print("\n" + "=" * 50)
    print("TEST CASE 2: Error handling — bad credentials")
    print("=" * 50)
    receive_latest_email(
        user_email="fake@gmail.com",
        user_password="wrong_password",
        imap_server=IMAP_SERVER,
        imap_port=IMAP_PORT,
    )
