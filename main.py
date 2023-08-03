# Third-party imports
import openai
from fastapi import FastAPI, Form, Depends, Request
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import json
# Internal imports
from models import Conversation, SessionLocal, get_customer_conversations, check_last_entry, is_number_in_database, \
    update_status, update_booking_data_in_db, get_booking_data
from utils import send_message, logger, convert_isotime_to_readable
import datetime

from nylas_integration import check_time_and_book, get_google_calendar_availability, book_event, get_next_available_slots

#-----------------Test-----------------
TEST=True
# -----------------Test-----------------


CALENDAR_ID2 = config("GOOGLE_C2_ID")

now = datetime.datetime.now()
now = now.isoformat()

NOW_PHRASE = f"The point of questioning is {now}."

CONTEXT_FOR_GPT = """
Du bist ein Servicebot für Buchungsanfragen.
Extrahiere das Datum, die Uhrzeit und den Namen aus der Anfrage und gib die Informationen im folgenden JSON-Format aus:
{"name": "NAME", "time": "HH:MM:SS”, "date":"YYYY-MM-DD", isotime:"YYYY-MM-DDTHH:MM:SS"}.
Von dem Zeitpunkt der Anfrage sollen die Zeiten berechnet werden. wie zum beispiel "Übermorgen", "Morgen", etc.
Überprüfe ob in der Anfrage sowohl ein Datum als auch eine Uhrzeit vorhanden ist. Wenn nicht dann frage jeweils nach dem fehlenden Teil.
Nimm nicht irgendwelche Werte an.
Wenn der Kunde nach "Morgen" fragt, evaluiere das Datum ausgehend von heute.
Sollte kein Name in der Buchungsanfrage vorhanden sein, verwende None.
Sollte kein Datum in der Buchungsanfrage vorhanden sein, verwende None. Datum ist hier als "date zu verstehen" und damit ist nur der kalender tag gemeint.
Sollte keine Uhrzeit in der Buchungsanfrage vorhanden sein, verwende None.
Achte darauf, dass die Ausgabe ausschließlich dieses JSON-Format enthält und verzichte auf jegliche Hinweise und Floskeln.
Jede deiner Antworten darf nur im Schema: "name": "XXX", "time": "HH:MM:SS”, "date":"YYYY-MM-DD, isotime:"YYYY-MM-DDTHH:MM:SS" sein.
"""
# CONTEXT_FOR_GPT = """
# This is the context. Do not repeat this or summarize it to the user.
# You are a service bot that handles booking requests. You guide the customer to the point where he or she provides 3 pieces of information.
# 1 Name, 2 Date, 3 Time.
# Make sure that the customers gives these 3 pieces of information and if the conversion tends to go somewhere else bring it back to the booking.
# If you have all the booking information, prompt the customer: "Lassen Sie mich überprüfen ob der Termin verfügbar ist. Datum: {date} Zeit: {time}."
# This prompt is always necessary, because I use it to query my database. Make sure that the format of date is YYYY-MM-DD and the format of time is HH:MM:SS.
# If the the schedule is available, ask the customer to confirm the booking, with the prompt 'Datum und Uhrzeit sind verfügbar. Wollen Sie den Termin buchen?'.
# If the customer confirms the booking, send the prompt "Ich habe den Termin gebucht. Vielen Dank für Ihre Buchung."
# """

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

    def __str__(self):
        return f"Name: {self.name}, Date: {self.date}, Time: {self.time}, ISO Time: {self.isotime}, Available: {self.available}, Status: {self.status}"


booking_data = BookingData()


@app.get("/")
async def index():
    return {"msg": "working"}

@app.get("/message")
async def index():
    return {"msg": "Send a POST req"}


# def identify_booking_fields(chatgpt_response):
#     try:
#         booking_request = json.loads(chatgpt_response)
#         # calendar_id = booking_request['calendar_id']
#         # calendar_id = CALENDAR_ID2
#         booking_data.name = booking_request['name']
#         booking_data.date = booking_request['date']
#         booking_data.time = booking_request['time']
#         booking_data.isotime = booking_request['isotime']
#         # print('-----------------------PRINT worked ', available, date, time, name)
#     except Exception as e:
#         # if not TEST:
#           send_message(whatsapp_number,
#         #              f'Kannst du mir nochmal sagen, wann du du genau einen Termin möchtest und für welchen Namen ich diesen buchen darf? {e}')
#         booking_data.status = 'NO_TIME_OR_DATE'
#         print('NO_TIME_OR_DATE', e)
#
#     return booking_data.status


def identify_booking_fields(chatgpt_response):
    print('RESPONSE for identifying fields', chatgpt_response)
    booking_request = None

    # Define the list of required fields and their corresponding error messages
    required_fields = {
        'name': 'MISSING_NAME',
        'date': 'MISSING_DATE',
        'time': 'MISSING_TIME',
        'isotime': 'MISSING_ISOTIME',
    }
    try:
        booking_request = json.loads(chatgpt_response)
    except Exception as e:
        print('Cannot JSON load response', e)

    for field in required_fields:
        if booking_request[field] is None:
            continue
        required_fields[field] = booking_request[field]

    extracted_fields = required_fields
    print('extracted_fields', extracted_fields)
    return extracted_fields
def identify_fields_to_update(whatsapp_number):
    existing_fields = get_booking_data(whatsapp_number)

    fields_to_update = []
    for field in existing_fields:
        # print('field', field, existing_fields[field] )
        if existing_fields[field] is None:
            fields_to_update.append(field)

    #todo: add logic to update outdated fields
    print('identify_fields_to_update', fields_to_update)
    return fields_to_update




def update_customer_data(fields_to_update):
    # print('BOOKINGREQUEST', booking_request)
    for field in fields_to_update:
        try:
            # print('fields', field, booking_request[field])
            setattr(booking_data, field, fields_to_update[field])
            # if booking_data[field] is None:
            #     # print('triggered')
            #     booking_data.status = required_fields[field]
            #     booking_data[field] = extracted_fields[field]

        except Exception as e:
            # Handle any exceptions, logging, or error responses as needed
            # booking_data.status = required_fields[field]
            print('Error', fields_to_update[field], e)


    # for field in booking_data.__dict__:
    #     if field is None:
    #         booking_data.status = required_fields[field]
    booking_data.status = 'UPDATED_DATA'
    print('FIELDS TO UPDATE', fields_to_update)
    print('UPDATED BOOKING DATA: ', booking_data)
    return booking_data.status


def store_conversation_in_db(whatsapp_number, Body, chatgpt_response, date, time, isotime, name, now, status,
                             db):
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chatgpt_response,
            date=date,
            time=time,
            name=name,
            isotime=isotime,
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
        if not TEST:
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

    if not TEST:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.5
        )

        chatgpt_response = response.choices[0].message.content
    else:
        chatgpt_response = Body
#     chatgpt_response = '''{  "name": null,
#   "time": "23:00:00",
#   "date": "2023-07-27",
#   "isotime": "2023-07-27T23:00:00"
# }'''

    # chatgpt_response = Body
    # if not TEST:
    #   send_message(whatsapp_number, chatgpt_response)  # for logging

    if is_number_in_database(whatsapp_number):
        print('number is in database')
        extracted_fields = identify_booking_fields(chatgpt_response)
        fields_to_update = identify_fields_to_update(whatsapp_number)
        print('FIELDS TO UPDATE', fields_to_update)
        new_fields = {}
        for field in fields_to_update:
            new_fields[field] = extracted_fields[field]
        update_customer_data(new_fields)

        # print('extracted_fields', extracted_fields)
        # todo only idetify above and do not change status
        update_booking_data_in_db(whatsapp_number, booking_data.time, booking_data.name, booking_data.date)

        missing_info = check_last_entry(whatsapp_number)
        print(f'=========PPPPRINT {missing_info}')
        if missing_info['missing_name']:
            if not TEST:
                send_message(whatsapp_number, 'Wie ist dein Name?')
            return 'Wie ist dein Name?'
        if missing_info['missing_date']:
            if not TEST:
                send_message(whatsapp_number, 'An welchem Datum möchtest du einen Termin?')
            return 'An welchem Datum möchtest du einen Termin?'
        if missing_info['missing_time']:
            if not TEST:
                send_message(whatsapp_number, 'Um welche Uhrzeit möchtest du einen Termin?')
            return 'Um welche Uhrzeit möchtest du einen Termin?'
    else:
        extracted_fields = identify_booking_fields(chatgpt_response)
        fields_to_update = identify_fields_to_update(whatsapp_number)
        print('FIELDS TO UPDATE', fields_to_update)
        new_fields = {}
        for field in fields_to_update:
            new_fields[field] = extracted_fields[field]
        update_customer_data(new_fields)

        store_conversation_in_db(whatsapp_number, Body,
                                 chatgpt_response,
                                 booking_data.date,
                                 booking_data.time,
                                 booking_data.isotime,
                                 booking_data.name,
                                 now,
                                 booking_data.status,
                                 db)

    print('ok1')
    print('booking status', booking_data.status)
    if booking_data.status == 'AVAILABLE':
        print('AVAILABLE: ',chatgpt_response.lower())
        if 'ja' in chatgpt_response.lower():
            booking_data.status = 'READY_TO_BOOK'
            update_status(whatsapp_number, booking_data.status)

        elif 'nein' in chatgpt_response.lower():
            booking_data.status = 'NO_INFO_ON_BOOKING'
            update_status(whatsapp_number, booking_data.status)

            return 'Ok, wir suchen einen anderen Termin.'
        else:
            booking_data.status = 'NO_INFO_ON_BOOKING'
            update_status(whatsapp_number, booking_data.status)

            return 'Ich habe Sie nicht verstanden. Welchen Termin wollen Sie buchen?'

    print('ok2')

    if booking_data.status == 'NO_TIME_OR_DATE':
        return 'Kannst du mir nochmal sagen, wann du du genau einen Termin möchtest und für welchen Namen ich diesen buchen darf?'
    else:
        if booking_data.isotime is not None:
            booking_data.available = get_google_calendar_availability(calendar_id, booking_data.isotime)
            print("??????????",booking_data.available, 'booking_data.available')


    if booking_data.available is None:
        # if not TEST:
        #   send_message(whatsapp_number, 'Wir leiten dich an einen Mitarbeiter weiter.')
        booking_data.status = 'NO_INFO_ON_AVAILABILITY'
        update_status(whatsapp_number, booking_data.status)

        return booking_data.status

    if booking_data.available:
        booking_data.status = 'AVAILABLE'
        update_status(whatsapp_number, booking_data.status)

        # print(booking_answer, 'booking_answer')
        if not TEST:
            send_message(whatsapp_number, 'Datum und Uhrzeit sind verfügbar. Wollen Sie den Termin buchen?')
    else:
        booking_data.status = 'NOT_AVAILABLE'
        update_status(whatsapp_number, booking_data.status)

        date_suggestions = get_next_available_slots("creativeassemblers@gmail.com", booking_data.isotime)
        response = f'Der Termin ist nicht mehr frei. würde einer dieser passen?'

        for isodate in date_suggestions:
            suggested_date, suggested_time = convert_isotime_to_readable(isodate)
            response += f' \nDatum: {suggested_date}, Zeit: {suggested_time}'

        response += '\nFalls nicht, dann bitte geben Sie uns einen neuen Wunschtermin mit Datum und Uhrzeit an.'
        if not TEST:
            send_message(whatsapp_number, response)

        return response



    if booking_data.status == 'READY_TO_BOOK':
        booking_answer = book_event(
            title=f"Booking with {booking_data.name}",
            location="at office",
            description="meeting with doctor",
            participant={'name': booking_data.name, 'email': "creativeassemblers@gmail.com"},
            time_to_meet_in_iso=booking_data.isotime,
            calendar_id=CALENDAR_ID2
        )
        booking_data.status = 'BOOKED'
        update_status(whatsapp_number, booking_data.status)
        response = f'Der Termin wurde gebucht. Zeit: {booking_data.time}, Datum: {booking_data.date}, Name: {booking_data.name}'
        if not TEST:
            send_message(whatsapp_number, response)
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
#     # if not TEST:
#       send_message(whatsapp_number, booking_request)
#
#     try:
#         booking_request = json.loads(booking_request)
#         time = booking_request['time']
#         calendar_id = booking_request['calendar_id']
#         name = booking_request['name']
#     except Exception as e:
#         if not TEST:
#           send_message(whatsapp_number, f'Could not extract booking info. {e}')
#
#     # print(booking_request)
#     print(time, calendar_id, name)
#     booking_answer = check_time_and_book(calendar_id, time, name)
#     print(booking_answer, 'booking_answer')
#     if not TEST:
#       send_message(whatsapp_number, booking_answer)
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
#     if not TEST:
#       send_message(whatsapp_number,
#                  f'Kannst du mir nochmal sagen, wann du du genau einen Termin möchtest und für welchen Namen ich diesen buchen darf? {e}')
#     status = 'NO_TIME_OR_DATE'


# return status
