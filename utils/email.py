# utils/email.py

from libs import config, MIMEText, smtplib
import logging

def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config['mail']['from_email']
    msg['To'] = to_email

    try:
        if config['mail']['smtp_protocol'] == 'ssl':
            server = smtplib.SMTP_SSL(config['mail']['smtp_host'], config['mail']['smtp_port'])
        else:
            server = smtplib.SMTP(config['mail']['smtp_host'], config['mail']['smtp_port'])
            if config['mail']['smtp_protocol'] == 'tls':
                server.starttls()
        server.login(config['mail']['smtp_username'], config['mail']['smtp_password'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logging.error(f"{failed_sending_email}: {e}")
        return False

