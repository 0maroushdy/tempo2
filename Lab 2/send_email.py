import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(sender_email: str, sender_password: str,
            recipient_email: str, subject: str, body: str,
            smtp_server: str = "smtp.gmail.com", smtp_port: int = 587) -> bool:

    try:
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject

        # Attach the body as plain text
        message.attach(MIMEText(body, "plain"))

        print(f"[SMTP] Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)

        server.ehlo()
        server.starttls()
        server.ehlo()

        print(f"[SMTP] Logging in as {sender_email}...")
        server.login(sender_email, sender_password)

        server.send_message(message)

        server.quit()

        print(f"[SMTP] Email sent successfully to {recipient_email}!")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[ERROR] Authentication failed. Check your email/password.")
        print("        For Gmail, use an App Password (not your regular password).")
        return False

    except smtplib.SMTPConnectError:
        print(f"[ERROR] Could not connect to {smtp_server}:{smtp_port}.")
        return False

    except smtplib.SMTPRecipientsRefused:
        print(f"[ERROR] Recipient address {recipient_email} was refused by the server.")
        return False

    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP error occurred: {e}")
        return False

    except ConnectionRefusedError:
        print(f"[ERROR] Connection refused by {smtp_server}:{smtp_port}.")
        return False

    except TimeoutError:
        print(f"[ERROR] Connection to {smtp_server}:{smtp_port} timed out.")
        return False

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


# ── Hard-coded test cases ────────────────────────────────────────────
if __name__ == "__main__":
    # ╔═══════════════════════════════════════════════════════════════╗
    # ║  CONFIGURATION — Replace with your own credentials            ║
    # ╚═══════════════════════════════════════════════════════════════╝

    SENDER_EMAIL = "your_email@gmail.com"
    SENDER_PASSWORD = "your_app_password"       # Use App Password for Gmail
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    # ── Test Case 1: Basic email ────────────────────────────────────
    print("=" * 50)
    print("TEST CASE 1: Basic email")
    print("=" * 50)
    send_email(
        sender_email=SENDER_EMAIL,
        sender_password=SENDER_PASSWORD,
        recipient_email="recipient@example.com",
        subject="Test Email - Lab 2",
        body="Hello! This is a test email sent from my Python email client.",
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
    )

    # ── Test Case 2: Email with longer body ─────────────────────────
    print("\n" + "=" * 50)
    print("TEST CASE 2: Longer body")
    print("=" * 50)
    send_email(
        sender_email=SENDER_EMAIL,
        sender_password=SENDER_PASSWORD,
        recipient_email="recipient@example.com",
        subject="Detailed Test - Lab 2",
        body=(
            "Dear Recipient,\n\n"
            "This is a more detailed test email from the CC451 Lab 2 project.\n"
            "The email client uses SMTP protocol with TLS encryption.\n\n"
            "Best regards,\n"
            "Email Client Application"
        ),
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
    )

    # ── Test Case 3: Intentional error (bad credentials) ────────────
    print("\n" + "=" * 50)
    print("TEST CASE 3: Error handling — bad credentials")
    print("=" * 50)
    send_email(
        sender_email="fake@gmail.com",
        sender_password="wrong_password",
        recipient_email="anyone@example.com",
        subject="This should fail",
        body="Testing error handling.",
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
    )
