# Third-party imports
import openai
from fastapi import FastAPI, Form, Depends, Request
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import json
# Internal imports
from models import Conversation, SessionLocal, get_customer_conversations, check_last_entry, is_number_in_database, \
    update_status
from utils import send_message, logger
import datetime

from nylas_integration import check_time_and_book, get_google_calendar_availability, book_event

CALENDAR_ID2 = config("GOOGLE_C2_ID")

now = datetime.datetime.now()
now = now.isoformat()

NOW_PHRASE = f"Der zeitpunkt der anfrage ist {now}."

CONTEXT_FOR_GPT = """
Du bist ein Servicebot für Buchungsanfragen. 
Extrahiere das Datum, die Uhrzeit und den Namen aus der Anfrage und gib die Informationen im folgenden JSON-Format aus: 
{"name": "NAME", "time": "HH:MM:SS”, "date":"YYYY-MM-DD", isotime:"YYYY-MM-DDTHH:MM:SS"}. 
Von dem Zeitpunkt der Anfrage sollen die Zeiten berechnet werden. wie zum beispiel "Übermorgen", "Morgen", etc.
Überprüfe ob in der Anfrage sowohl ein Datum als auch eine Uhrzeit vorhanden ist. Wenn nicht dann frage jeweils nach dem fehlenden Teil. 
Nimm nicht irgendwelche Werte an.
Wenn der Kunde nach "Morgen" fragt, evaluiere das Datum ausgehend von heute. 
Falls kein Name angegeben ist, verwende "Kunde" als Standardname. 
Sollte kein Datum in der Buchungsanfrage vorhanden sein, verwende “fehlt”. Datum ist hier als "date zu verstehen" und damit ist nur der kalender tag gemeint. 
Sollte keine Uhrzeit in der Buchungsanfrage vorhanden sein, verwende “fehlt”. 
Achte darauf, dass die Ausgabe ausschließlich dieses JSON-Format enthält und verzichte auf jegliche Hinweise und Floskeln. 
Jede deiner Antworten darf nur im Schema: "name": "XXX", "time": "HH:MM:SS”, "date":"YYYY-MM-DD, isotime:"YYYY-MM-DDTHH:MM:SS" sein.
"""

app = FastAPI()
# Set up the OpenAI API client
openai.api_key = config("OPENAI_API_KEY")

calendar_id = CALENDAR_ID2


# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


class BookingData:
    def __init__(self):
        self.name = None
        self.time = None
        self.date = None
        self.isotime = None
        self.available = None
        self.status = None


booking_data = BookingData()


@app.get("/")
async def index():
    return {"msg": "working"}

@app.get("/message")
async def index():
    return {"msg": "Send a POST req"}


def identify_booking_fields(chatgpt_response):
    try:
        booking_request = json.loads(chatgpt_response)
        # calendar_id = booking_request['calendar_id']
        calendar_id = CALENDAR_ID2
        booking_data.name = booking_request['name']
        booking_data.date = booking_request['date']
        booking_data.time = booking_request['time']
        booking_data.isotime = booking_request['isotime']
        # print('-----------------------PRINT worked ', available, date, time, name)
    except Exception as e:
        # send_message(whatsapp_number,
        #              f'Kannst du mir nochmal sagen, wann du du genau einen Termin möchtest und für welchen Namen ich diesen buchen darf? {e}')
        booking_data.status = 'NO_TIME_OR_DATE'
        print('NO_TIME_OR_DATE', e)

    return booking_data.status


def store_conversation_in_db(whatsapp_number, Body, chatgpt_response, date, time, isotime, name, now, status,
                             db):
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chatgpt_response,
            extracted_date=date,
            extracted_time=time,
            extracted_name=name,
            extracted_isotime=isotime,
            time_of_inquiry=now,
            status=status
        )
        db.add(conversation)
        db.commit()
        logger.info(f"Conversation #{conversation.id} stored in database")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error storing conversation in database: {e}")


@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    # Extract the phone number from the incoming webhook request
    form_data = await request.form()
    # print('***********', request, form_data)
    whatsapp_number = form_data['From'].split("whatsapp:")[-1]
    # print(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    num_entries, message_content = get_customer_conversations(whatsapp_number)
    # print(num_entries)

    if num_entries > 100:  # todo set to 10
        send_message(whatsapp_number, '''
        Das Thema scheint kompliziert zu sein. Es gibt viele Fragen. 
Wir leiten dich an einen Mitarbeiter weiter.''')
        return 'done'

    # Get or create the user session for the specific route
    # user_session = db.query(UserSession).filter_by(user_id=whatsapp_number, route_name="message").first()
    # if not user_session:
    #     user_session = UserSession(user_id=whatsapp_number, route_name="message")
    #     db.add(user_session)

    # Call the OpenAI API to generate text with ChatGPT
    messages = [{"role": "user", "content": Body}]
    messages.append({"role": "system", "content": NOW_PHRASE})
    messages.append({"role": "system", "content": CONTEXT_FOR_GPT})

    # response = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=messages,
    #     max_tokens=200,
    #     n=1,
    #     stop=None,
    #     temperature=0.5
    # )
    #
    # chatgpt_response = response.choices[0].message.content
    chatgpt_response = '''{  "name": "ZZZZZ",
  "time": "23:00:00",
  "date": "2023-07-27",
  "isotime": "2023-07-27T23:00:00"
}'''
    # send_message(whatsapp_number, chatgpt_response)  # for logging

    if is_number_in_database(whatsapp_number):
        print('number is in database')
        missing_info = check_last_entry(whatsapp_number)
        print(f'=========PPPPRINT {missing_info}')
        if missing_info['missing_name']:
            # send_message(whatsapp_number, 'Wie ist dein Name?')
            return 'Wie ist dein Name?'
        if missing_info['missing_date']:
            # send_message(whatsapp_number, 'An welchem Datum möchtest du einen Termin?')
            return 'An welchem Datum möchtest du einen Termin?'
        if missing_info['missing_time']:
            # send_message(whatsapp_number, 'Um welche Uhrzeit möchtest du einen Termin?')
            return 'Um welche Uhrzeit möchtest du einen Termin?'
    else:
        identify_booking_fields(chatgpt_response)
        store_conversation_in_db(whatsapp_number, Body,
                                 chatgpt_response,
                                 booking_data.date,
                                 booking_data.time,
                                 booking_data.isotime,
                                 booking_data.name,
                                 now,
                                 booking_data.status,
                                 db)

    print('BOOOOKING DATA ISO TIME', booking_data.isotime)
    if booking_data.status == 'NO_TIME_OR_DATE':
        return 'Kannst du mir nochmal sagen, wann du du genau einen Termin möchtest und für welchen Namen ich diesen buchen darf?'
    else:
        if booking_data.isotime is not None:
            booking_data.available = get_google_calendar_availability(calendar_id, booking_data.isotime)
            print("??????????",booking_data.available, 'booking_data.available')


    if booking_data.available is None:
        # send_message(whatsapp_number, 'Wir leiten dich an einen Mitarbeiter weiter.')
        booking_data.status = 'NO_INFO_ON_AVAILABILITY'
        update_status(whatsapp_number, booking_data.status)

        return booking_data.status

    if booking_data.available:
        booking_data.status = 'AVAILABLE'
        update_status(whatsapp_number, booking_data.status)
        booking_answer = book_event(
            title=f"Booking with {booking_data.name}",
            location="at office",
            description="meeting with doctor",
            participant={'name': booking_data.name, 'email': "creativeassemblers@gmail.com"},
            time_to_meet_in_iso=booking_data.isotime,
            calendar_id=CALENDAR_ID2
        )
        # print(booking_answer, 'booking_answer')
        # send_message(whatsapp_number, booking_answer)
        booking_data.status = 'BOOKED'
        update_status(whatsapp_number, booking_data.status)
        response = f'Der Termin wurde gebucht. Zeit: {booking_data.time}, Datum: {booking_data.date}, Name: {booking_data.name}'
        return response
    else:
        status = 'NOT_AVAILABLE'
        update_status(whatsapp_number, status)
        response = f'Der Termin ist nicht mehr frei. Nenne einen anderen'
        # send_message(whatsapp_number, 'Der Termin ist nicht mehr frei. Nenne einen anderen')

        return response

# -----------------------------

# from pydantic import BaseModel
# from nylas_integration import check_time_and_book
#
# class BookingRequest(BaseModel):
#     calendar_id: str
#     time: str
#     name: str
# @app.post("/message")
# async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
#     form_data = await request.form()
#     whatsapp_number = form_data['From'].split("whatsapp:")[-1]
#     print(f"Sending the ChatGPT response to this number: {whatsapp_number}")
#
#     # Call the OpenAI API to generate text with ChatGPT
#     messages = [{"role": "user", "content": Body}]
#     booking_request = messages[0]['content']
#
#     # send_message(whatsapp_number, booking_request)
#
#     try:
#         booking_request = json.loads(booking_request)
#         time = booking_request['time']
#         calendar_id = booking_request['calendar_id']
#         name = booking_request['name']
#     except Exception as e:
#         send_message(whatsapp_number, f'Could not extract booking info. {e}')
#
#     # print(booking_request)
#     print(time, calendar_id, name)
#     booking_answer = check_time_and_book(calendar_id, time, name)
#     print(booking_answer, 'booking_answer')
#     send_message(whatsapp_number, booking_answer)
#
#
#
#     print('done')
#     return "done"


# try:
#     booking_request = json.loads(chatgpt_response)
#     isotime = booking_request['isotime']
#     # calendar_id = booking_request['calendar_id']
#     calendar_id = CALENDAR_ID2
#     name = booking_request['name']
#
#     # available = get_google_calendar_availability(calendar_id, isotime)
#
#     date = booking_request['date']
#     time = booking_request['time']
#     print('-----------------------PRINT worked ', available, date, time, name)
#
# except Exception as e:
#     send_message(whatsapp_number,
#                  f'Kannst du mir nochmal sagen, wann du du genau einen Termin möchtest und für welchen Namen ich diesen buchen darf? {e}')
#     status = 'NO_TIME_OR_DATE'


# return status
