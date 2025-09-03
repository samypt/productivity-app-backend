import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv


load_dotenv()
FROM_EMAIL = os.getenv("EMAIL")
EMAIL_PASSKEY = os.getenv("EMAIL_PASSKEY")

def send_invite_email(to_email, invite_link):
    body=f"""
        <h2>Hello!</h2>
        <p>We’d love for you to join us. Click the link below to accept your invitation:</p>
        <a href="{invite_link}">Accept Invitation</a>
        <p>Thanks,<br>Your App Team</p>
    """
    subject = "You're Invited to Join Teamly!"
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(FROM_EMAIL, EMAIL_PASSKEY)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}. Error: {e}")

