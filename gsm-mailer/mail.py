import logging
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


class Mail(object):

    def __init__(self, login, password):
        self.login = login
        self.password = password

    @classmethod
    def parse_incoming(parameters):
        pass

    @classmethod
    def get_html_email(cls, subject, body, source, template="default"):
        with open("templates/{}.html".format(template), 'r') as tpl:
            html = tpl.read()
            return html.format(subject=subject, body=body, source=source)

    def build_email(self, query):
        msg = MIMEMultipart("alternative")
        msg.set_charset("utf-8")
        msg["Subject"] = query['subject']
        msg["From"] = self.login
        msg["To"] = ', '.join(query['recipients']) if type(query['recipients']) is list else query['recipients']

        msg.attach(MIMEText(query['message'], "plain", "utf-8"))
        msg.attach(MIMEText(self.get_html_email(query['subject'], query['message'], query['source']), "html"))

        return msg

    def send_emails(self, query):
        """
        process a multiple recipients query to send emails
        """
        for recipient in query['recipients']:
            unit_query = query
            unit_query['recipients'] = [recipient]
            log.debug("Scheduling email to %s: '%s'", recipient, unit_query)
            self.send_email(unit_query['recipients'], self.build_email(query))

    def send_email(self, recipients, msg, force=True):

        log.debug("Sending the following email: '%s'",  msg.as_string())

        if not force:
            log.info('Ignoring email sending until authentication is properly set')
            raise Exception("Unimplemented yet: authentication not properly set")

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self.login, self.password)
            server.sendmail(self.login, msg["To"], msg.as_string().encode('ascii'))
            server.close()
            log.debug('Email successfully sent.')
        except Exception as e:
            log.error("failed to send mail %s", e)
            raise
