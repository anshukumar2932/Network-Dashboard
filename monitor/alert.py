from dotenv import load_dotenv

import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

ALERT_FROM = os.getenv("ALERT_FROM")
ALERT_TO = os.getenv("ALERT_TO")

def send_email(subject: str, html_body: str):
    print(f"[ALERT] Sending email...")
    print(f"[ALERT] SMTP={SMTP_SERVER}:{SMTP_PORT}")
    print(f"[ALERT] FROM={ALERT_FROM}")
    print(f"[ALERT] TO={ALERT_TO}")
    print(f"[ALERT] USERNAME={SMTP_USERNAME}")

    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, ALERT_FROM, ALERT_TO]):
        print("[ALERT] ERROR: SMTP configuration incomplete - check .env file")
        return

    try:
        msg = MIMEMultipart()

        msg["Subject"] = subject
        msg["From"] = ALERT_FROM
        msg["To"] = ALERT_TO

        msg.attach(
            MIMEText(html_body, "html")
        )

        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT
        ) as server:

            server.starttls()

            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            server.send_message(msg)
        print("[ALERT] Email sent successfully")
    except Exception as e:
        print(f"[ALERT] Failed to send email: {e}")


def send_alert_down(devices):

    if not devices:
        print("[ALERT] No devices to alert for down")
        return

    print(f"[ALERT] Preparing down alert for {len(devices)} devices")
    rows = ""

    for device in devices:
        name = getattr(device, 'device_name', None) or getattr(device, 'ip', 'Unknown')
        ip = getattr(device, 'ip', 'Unknown')
        print(f"[ALERT]   Device: {name} ({ip})")
        rows += f"""
        <tr>
            <td>{name}</td>
            <td>{ip}</td>
        </tr>
        """

    body = f"""
    <h2>🔴 Devices Down</h2>

    <table border="1" cellpadding="5">
        <tr>
            <th>Name</th>
            <th>IP Address</th>
        </tr>

        {rows}
    </table>
    """

    send_email(
        f"[ALERT] {len(devices)} Device(s) Down",
        body
    )


def send_alert_up(devices):

    if not devices:
        print("[ALERT] No devices to alert for recovery")
        return

    print(f"[ALERT] Preparing recovery alert for {len(devices)} devices")
    rows = ""

    for device in devices:
        name = getattr(device, 'device_name', None) or getattr(device, 'ip', 'Unknown')
        ip = getattr(device, 'ip', 'Unknown')
        print(f"[ALERT]   Device: {name} ({ip})")
        rows += f"""
        <tr>
            <td>{name}</td>
            <td>{ip}</td>
        </tr>
        """

    body = f"""
    <h2>🟢 Devices Recovered</h2>

    <table border="1" cellpadding="5">
        <tr>
            <th>Name</th>
            <th>IP Address</th>
        </tr>

        {rows}
    </table>
    """

    send_email(
        f"[RECOVERY] {len(devices)} Device(s) Restored",
        body
    )