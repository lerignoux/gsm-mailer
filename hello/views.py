import logging
import os
from django.shortcuts import render
from django.http import HttpResponse

from .models import Greeting
from django.views.decorators.csrf import csrf_exempt

import smtplib
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
        log.debug(request.body)
        body = request.body.decode('utf-8')
        parameters = urllib.parse.parse_qs(body)
        log.debug(parameters)
        query = parse_sms(parameters['Body'][0])
        query['source'] = parameters['From'][0]
        query = format_email(query)

        password = os.environ['GMAIL_PASSWORD']
        account = os.environ['GMAIL_ACCOUNT']
        send_email(
            account, password,
            query.get('recipients'),
            query.get('subject', "No subject"), query.get('message'))

    return HttpResponse(status=200)


def parse_sms(body):
    HEADERS = {
        'v': 'version',
        'r': 'recipients',
        's': 'subject',
        'h': 'hash',
        'l': 'language',
        't': 'template',
        'e': 'encoding',
        'se': 'sender'
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


def format_email(query):
    query['subject'] = "'{}' received from {}".format(query.get('subject', 'Mail'), query.get('sender', query.get('source')))
    return query


def send_email(user, pwd, recipients, subject, body, force=True):

    gmail_user = user
    gmail_pwd = pwd
    FROM = user
    TO = recipients if type(recipients) is list else [recipients]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)

    log.debug('Sending the following email:')
    log.debug(message)

    if not force:
        log.info('Ignoring email sending until authentication is properly set')
        return

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        log.debug('successfully sent the mail')
    except:
        log.debug("failed to send mail")
