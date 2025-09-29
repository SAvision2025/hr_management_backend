import smtplib
from email.mime.text import MIMEText

def send_reminder_email(to_email, subject, body):
    from_email = "timesheetsystem2025@gmail.com"         # Your Gmail
    password = "mhuv nxdf ciqz igws"         # Gmail App Password (not your real password)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, password)
        server.send_message(msg)
