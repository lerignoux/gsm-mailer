from datetime import datetime
import json
import logging
import os
import uuid
from django.shortcuts import render
from django.http import HttpResponse

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .models import Greeting
from django.views.decorators.csrf import csrf_exempt

import smtplib
from twilio.rest import TwilioRestClient
import urllib


log = logging.getLogger("sms_incoming")


# Create your views here.
def index(request):
    # return HttpResponse('Hello from Python!')
    return render(request, 'index.html')


def db(request):

    greeting = Greeting()
    greeting.save()

    greetings = Greeting.objects.all()

    return render(request, 'db.html', {'greetings': greetings})


@csrf_exempt
def sms_incoming(request):
    if request.method == "POST":
        log.info("Received incoming SMS")
        body = request.body.decode('utf-8')
        parameters = urllib.parse.parse_qs(body)
        query = generate_query(parameters)
        send_emails(query)

    return HttpResponse(status=200)


def parse_sms(body):
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
        'rid': 'request_id'
    }

    query = {}
    try:
        headers, query['message'] = body.split("\n\n", 1)
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
            query[HEADERS[hid]] = hvalue.strip()
        else:
            log.warning("Unknown header '%s'", hid)

    query['recipients'] = query['recipients'].split(' ') if ' ' in query['recipients'] else [query['recipients']]
    log.debug("Parsed request %s", query)
    return query


def generate_query(parameters):
    query = parse_sms(parameters['Body'][0])
    query['id'] = str(uuid.uuid4())
    query['source'] = parameters['From'][0]
    query = format_email(query)
    return query


def format_email(query):
    query['subject'] = "'{}' received from {}".format(query.get('subject', 'Mail'), query.get('sender', query.get('source')))
    return query


def send_emails(query):
    for recipient in query['recipients']:
        unit_query = query
        unit_query['recipients'] = [recipient]
        log.debug("Scheduling email to %s: '%s'", recipient, unit_query)
        process_sending(unit_query)


def process_sending(query):
    log.debug('Sending email')
    account = os.environ['GMAIL_ACCOUNT']
    password = os.environ['GMAIL_PASSWORD']

    subject = query.get('subject', "No subject")
    report = {
        'subject': subject,
        'id': query['id'],
        'timestamp': datetime.now().isoformat(),
        'recipients': query['recipients']
    }
    if 'request_id' in query:
        report['request_id'] = query['request_id']
    try:
        send_email(account, password, query['recipients'], subject, query.get('message'))
    except Exception as e:
        log.exception(e)
        log.warning("Failed to send email: %s", e)
        report['status'] = 'failure'
        report['message'] = str(e)
    else:
        report['status'] = 'success'
    send_report(report, query['source'])


def send_email(user, pwd, recipients, subject, body, force=True):
    gmail_user = user
    gmail_pwd = pwd

    msg = MIMEMultipart("alternative")
    msg.set_charset("utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ', '.join(recipients) if type(recipients) is list else recipients

    # html = message[message.find("html:") + len("html:"):message.find("text:")].strip()
    # text = message[message.find("text:") + len("text:"):].strip()

    # part1 = MIMEText(html, "html")
    part1 = MIMEText(body, "plain", "utf-8")

    # msg.attach(part1)
    msg.attach(part1)

    log.debug("Sending the following email: '%s'",  msg.as_string())

    if not force:
        log.info('Ignoring email sending until authentication is properly set')
        raise Exception("Unimplemented yet: authentication not properly set")

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(user, msg["To"], msg.as_string().encode('ascii'))
        server.close()
        log.debug('successfully sent the mail')
    except Exception as e:
        log.error("failed to send mail %s", e)
        raise


def send_report(report, recipient):
    """
    Send a report to the sender to confirm the mail sending
    """
    log.info("message sent to %s", recipient)

    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    twilio_number = os.environ['TWILIO_PHONE_NUMBER']

    client = TwilioRestClient(account_sid, auth_token)
    message = client.messages.create(
        body=json.dumps(report, ensure_ascii=False),
        to=recipient,
        from_=twilio_number
    )

    log.debug("confirmation SMS sent: '%s'", message)
