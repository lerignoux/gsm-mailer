#!/usr/bin/env python
from datetime import datetime
import json
import logging
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib

from sms import SMS
from mail import Mail


log = logging.getLogger(__name__)


class GSMMailer(object):
    def __init__(self):
        with open('conf.json', 'r') as conf:
            self.config = json.loads(conf.read())
        self.smser = SMS(**self.config['twilio'])
        self.mailer = Mail(**self.config['gmail'])

    def handle_query(self, query):
        query['subject'] = query.get('subject', 'No subject')

        report = {
            'subject': query['subject'],
            'id': query['id'],
            'timestamp': datetime.now().isoformat(),
            'recipients': query['recipients'],
            'feedback': query['feedback']
        }

        if 'request_id' in query:
            report['request_id'] = query['request_id']

        try:
            self.mailer.send_emails(query)
        except Exception as e:
            log.exception(e)
            log.warning("Failed to send emails: %s", e)
            report['status'] = 'failure'
            report['message'] = str(e)
        else:
            report['status'] = 'success'
        if report['feedback']:
            self.smser.send_sms(report, query['source'])


# HTTPRequestHandler class
class requestsHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        post_data = urllib.parse.parse_qs(self.rfile.read(length).decode('utf-8'))
        log.critical(post_data)
        log.info("Received request %s", post_data)

        try:
            query = SMS.parse_incoming(post_data['Body'][0])
        except Exception as e:
            logging.exception(e)
            self.send_response(400)

            # Send headers
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # Write content as utf-8 data
            self.wfile.write(bytes(str(e), "utf8"))
            return

        query['id'] = str(uuid.uuid4())
        print(self.headers)
        query['source'] = self.headers['From'][0]

        try:
            GSMMailer().handle_query(query)
        except Exception as e:
            logging.exception(e)
            self.send_response(500)

            # Send headers
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # Write content as utf-8 data
            self.wfile.write(bytes(str(e), "utf8"))
            return

        # Send response status code
        self.send_response(200)
        return


if __name__ == "__main__":
    log.info('starting server...')
    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8081)
    httpd = HTTPServer(server_address, requestsHandler)
    print('running server...')
    httpd.serve_forever()
