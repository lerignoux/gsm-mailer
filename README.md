# gsm-mailer
Send emails using GSM network

# Start the server:
in gsm-mailer folder:
```
pip install -r requirements.py
python server.py
```

# Example twilio query:
```
curl -i -XPOST localhost:8081 -d'Body=v:1,%0Af:0%0Ar:<my_email>@gmail.com%0A%0A here is my message%0A' -H'From: +3312345678'
```
