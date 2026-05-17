import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

from send_email import send_email
from receive_email import receive_latest_email

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("[WARNING] plyer not installed. Push notifications disabled.")
    print("          Install with: pip install plyer")


class EmailClientGUI:

    def __init__(self, root: tk.Tk):
        """Initialize the GUI layout and widgets."""
        self.root = root
        self.root.title("CC451 Email Client — Lab 2")
        self.root.geometry("700x720")
        self.root.resizable(False, False)

        # chosing a theme ─────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")

        # ── Build the interface ─────────────────────────────────────
        self._build_credentials_frame()
        self._build_server_frame()
        self._build_compose_frame()
        self._build_buttons_frame()
        self._build_output_frame()
        self._build_status_bar()

    # ── Credentials Section ──────────────────────────────────────────
    def _build_credentials_frame(self):
        """Create the login credentials input section."""
        frame = ttk.LabelFrame(self.root, text="  Login Credentials  ", padding=10)
        frame.pack(fill="x", padx=15, pady=(15, 5))

        ttk.Label(frame, text="Your Email:").grid(row=0, column=0, sticky="w", pady=3)
        self.email_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.email_var, width=50).grid(
            row=0, column=1, padx=(10, 0), pady=3
        )

        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky="w", pady=3)
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, width=50, show="*").grid(
            row=1, column=1, padx=(10, 0), pady=3
        )

    # ── Server Configuration ─────────────────────────────────────────
    def _build_server_frame(self):
        """Create the server settings section."""
        frame = ttk.LabelFrame(self.root, text="  Server Settings  ", padding=10)
        frame.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame, text="SMTP Server:").grid(row=0, column=0, sticky="w", pady=3)
        self.smtp_server_var = tk.StringVar(value="smtp.gmail.com")
        ttk.Entry(frame, textvariable=self.smtp_server_var, width=25).grid(
            row=0, column=1, padx=(10, 15), pady=3
        )

        ttk.Label(frame, text="Port:").grid(row=0, column=2, sticky="w", pady=3)
        self.smtp_port_var = tk.StringVar(value="587")
        ttk.Entry(frame, textvariable=self.smtp_port_var, width=8).grid(
            row=0, column=3, padx=(5, 0), pady=3
        )

        ttk.Label(frame, text="IMAP Server:").grid(row=1, column=0, sticky="w", pady=3)
        self.imap_server_var = tk.StringVar(value="imap.gmail.com")
        ttk.Entry(frame, textvariable=self.imap_server_var, width=25).grid(
            row=1, column=1, padx=(10, 15), pady=3
        )

        ttk.Label(frame, text="Port:").grid(row=1, column=2, sticky="w", pady=3)
        self.imap_port_var = tk.StringVar(value="993")
        ttk.Entry(frame, textvariable=self.imap_port_var, width=8).grid(
            row=1, column=3, padx=(5, 0), pady=3
        )

    # ── Compose Section ──────────────────────────────────────────────
    def _build_compose_frame(self):
        """Create the email composition section."""
        frame = ttk.LabelFrame(self.root, text="  Compose Email  ", padding=10)
        frame.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame, text="To:").grid(row=0, column=0, sticky="w", pady=3)
        self.recipient_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.recipient_var, width=50).grid(
            row=0, column=1, padx=(10, 0), pady=3
        )

        ttk.Label(frame, text="Subject:").grid(row=1, column=0, sticky="w", pady=3)
        self.subject_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.subject_var, width=50).grid(
            row=1, column=1, padx=(10, 0), pady=3
        )

        ttk.Label(frame, text="Body:").grid(row=2, column=0, sticky="nw", pady=3)
        self.body_text = tk.Text(frame, height=5, width=50, wrap="word")
        self.body_text.grid(row=2, column=1, padx=(10, 0), pady=3)

    # ── Action Buttons ───────────────────────────────────────────────
    def _build_buttons_frame(self):
        """Create the Send and Receive buttons."""
        frame = ttk.Frame(self.root, padding=5)
        frame.pack(fill="x", padx=15, pady=5)

        self.send_btn = ttk.Button(
            frame, text="Send Email", command=self._on_send, width=20
        )
        self.send_btn.pack(side="left", padx=(0, 10))

        self.receive_btn = ttk.Button(
            frame, text="Receive Latest Email", command=self._on_receive, width=25
        )
        self.receive_btn.pack(side="left")

    # ── Output / Log Section ─────────────────────────────────────────
    def _build_output_frame(self):
        """Create the output display area."""
        frame = ttk.LabelFrame(self.root, text="  Output  ", padding=10)
        frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.output_text = scrolledtext.ScrolledText(
            frame, height=10, wrap="word", state="disabled"
        )
        self.output_text.pack(fill="both", expand=True)

    # ── Status Bar ───────────────────────────────────────────────────
    def _build_status_bar(self):
        """Create a status bar at the bottom."""
        self.status_var = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief="sunken", anchor="w"
        )
        status_bar.pack(fill="x", side="bottom", padx=0, pady=0)

    # ── Helper Methods ───────────────────────────────────────────────
    def _log(self, text: str):
        """Append text to the output area."""
        self.output_text.config(state="normal")
        self.output_text.insert("end", text + "\n")
        self.output_text.see("end")
        self.output_text.config(state="disabled")

    def _set_status(self, text: str):
        """Update the status bar."""
        self.status_var.set(text)
        self.root.update_idletasks()

    def _validate_credentials(self) -> bool:
        """Check that email and password are filled in."""
        if not self.email_var.get().strip():
            messagebox.showwarning("Missing Info", "Please enter your email address.")
            return False
        if not self.password_var.get().strip():
            messagebox.showwarning("Missing Info", "Please enter your password.")
            return False
        return True

    # ── Send Handler ─────────────────────────────────────────────────
    def _on_send(self):
        """Handle the Send button click — runs in a separate thread."""
        if not self._validate_credentials():
            return
        if not self.recipient_var.get().strip():
            messagebox.showwarning("Missing Info", "Please enter a recipient email.")
            return

        # Disable button to prevent double-click
        self.send_btn.config(state="disabled")
        self._set_status("Sending email...")

        # Run in background thread to keep GUI responsive
        thread = threading.Thread(target=self._send_worker, daemon=True)
        thread.start()

    def _send_worker(self):
        """Background worker that sends the email."""
        success = send_email(
            sender_email=self.email_var.get().strip(),
            sender_password=self.password_var.get().strip(),
            recipient_email=self.recipient_var.get().strip(),
            subject=self.subject_var.get().strip(),
            body=self.body_text.get("1.0", "end").strip(),
            smtp_server=self.smtp_server_var.get().strip(),
            smtp_port=int(self.smtp_port_var.get().strip()),
        )

        # Schedule GUI updates on the main thread
        self.root.after(0, self._send_complete, success)

    def _send_complete(self, success: bool):
        """Called on the main thread after sending completes."""
        self.send_btn.config(state="normal")
        if success:
            self._log("[SUCCESS] Email sent successfully!")
            self._set_status("Email sent successfully.")
            messagebox.showinfo("Success", "Email sent successfully!")
        else:
            self._log("[FAILED] Email sending failed. Check output for details.")
            self._set_status("Email sending failed.")
            messagebox.showerror("Error", "Failed to send email. Check your credentials.")

    # ── Receive Handler ──────────────────────────────────────────────
    def _on_receive(self):
        """Handle the Receive button click — runs in a separate thread."""
        if not self._validate_credentials():
            return

        self.receive_btn.config(state="disabled")
        self._set_status("Fetching latest email...")

        thread = threading.Thread(target=self._receive_worker, daemon=True)
        thread.start()

    def _receive_worker(self):
        """Background worker that fetches the latest email."""
        result = receive_latest_email(
            user_email=self.email_var.get().strip(),
            user_password=self.password_var.get().strip(),
            imap_server=self.imap_server_var.get().strip(),
            imap_port=int(self.imap_port_var.get().strip()),
        )

        self.root.after(0, self._receive_complete, result)

    def _receive_complete(self, result: dict | None):
        """Called on the main thread after receiving completes."""
        self.receive_btn.config(state="normal")
        if result:
            self._log("=" * 50)
            self._log(f"From:    {result['from']}")
            self._log(f"Subject: {result['subject']}")
            self._log(f"Date:    {result['date']}")
            self._log("-" * 50)
            self._log(f"{result['body']}")
            self._log("=" * 50)
            self._set_status("Latest email fetched successfully.")

            # ── Push notification (bonus) ────────────────────────────
            if PLYER_AVAILABLE:
                try:
                    notification.notify(
                        title=f"New Email: {result['subject']}",
                        message=f"From: {result['from']}\n{result['body'][:100]}...",
                        app_name="CC451 Email Client",
                        timeout=10,
                    )
                except Exception as e:
                    print(f"[WARNING] Push notification failed: {e}")
        else:
            self._log("[FAILED] Could not fetch email.")
            self._set_status("Email fetch failed.")
            messagebox.showerror("Error", "Failed to fetch email. Check credentials.")


# ── Main Entry Point ─────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = EmailClientGUI(root)
    root.mainloop()
