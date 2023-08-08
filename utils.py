# Standard library import
import logging
import datetime

# Third-party imports
from twilio.rest import Client
from decouple import config
from dateutil import parser

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
account_sid = config("TWILIO_ACCOUNT_SID")
auth_token = config("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)
twilio_number = config('TWILIO_NUMBER')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

now = datetime.datetime.now()
now = now.isoformat()

# Sending message logic through Twilio Messaging API
def send_message(to_number, body_text):
    try:
        message = client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            body=body_text,
            to=f"whatsapp:{to_number}"
            )
        logger.info(f"Message sent to {to_number}: {message.body}")
    except Exception as e:
        logger.error(f"Error sending message to {to_number} from {twilio_number}: Text was {body_text} Error was: {e}")

def convert_isotime_to_readable(iso_time):
    # Parse the ISO timestamp string to a datetime object
    time_dt = parser.parse(iso_time)

    # Extract date and time components
    date_str = time_dt.strftime('%Y-%m-%d')
    time_str = time_dt.strftime('%H:%M:%S')

    return date_str, time_str

import datetime

def create_isotime(date, time):
    date_time = datetime.datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S")
    isotime = date_time.strftime("%Y-%m-%dT%H:%M:%S")
    return isotime
