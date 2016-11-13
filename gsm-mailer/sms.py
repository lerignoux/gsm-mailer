import json
import logging
from twilio.rest import TwilioRestClient

log = logging.getLogger(__name__)


class SMS(object):
    def __init__(self, account_sid, auth_token, twilio_number):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.twilio_number = twilio_number

    @classmethod
    def parse_incoming(cls, body):
        HEADERS = {
            'v': 'version',
            'r': 'recipients',
            's': 'subject',
            'h': 'hash',
            'l': 'language',
            't': 'template',
            'ts': 'timestamp',
            'e': 'encoding',
            'se': 'sender',
            'f': 'feedback',
            'rid': 'request_id'
        }

        parsed = {}
        try:
            print(body)
            headers, parsed['message'] = body.split("\n\n", 1)
        except ValueError as e:
            log.error("Failed to parse message '%s'", body)
            log.exception(e)
            return
        headers = headers.split('\n') if '\n' in headers else [headers]
        for header in headers:
            try:
                hid, hvalue = header.split(':')
                hid = hid.strip().lower()
                hvalue = hvalue.strip()
            except ValueError:
                log.warning("Incorrect header '%s'", header)
            if hid in HEADERS:
                parsed[HEADERS[hid]] = hvalue.strip()
            else:
                log.warning("Unknown header '%s'", hid)

        parsed['recipients'] = parsed['recipients'].split(' ') if ' ' in parsed['recipients'] else [parsed['recipients']]
        try:
            parsed['feedback'] = int(parsed.get('feedback', 0))
        except Exception as e:
            log.warning("Bad feedback %s", parsed['feedback'])
            parsed['feedback'] = 0
        log.debug("Parsed request %s", parsed)
        return parsed

    def send_sms(self, body, recipient):
        """
        Send a report to the sender to confirm the mail sending
        """
        log.info("Sending message %s to %s", body, recipient)

        client = TwilioRestClient(self.account_sid, self.auth_token)
        client.messages.create(
            body=json.dumps(body, ensure_ascii=False),
            to=recipient,
            from_=self.twilio_number
        )
