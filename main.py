# Third-party imports
import uvicorn
import openai
from fastapi import FastAPI, Form, Depends, Request
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from gpt_functions import get_gpt_response
from templates import *
from db_functions import *
from booking import *
from twilio_functions import redirect_to_cs_if_too_many_calls

from utils import send_message, logger, convert_isotime_to_readable, now
import datetime

from nylas_integration import check_time_and_book, get_google_calendar_availability, book_event, get_next_available_slots

#-----------------Test-----------------
TEST=True
# -----------------Test-----------------


CALENDAR_ID2 = config("GOOGLE_C2_ID")



app = FastAPI()

calendar_id = CALENDAR_ID2


# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()



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


@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    # Extract the phone number from the incoming webhook request
    form_data = await request.form()
    # print('***********', request, form_data)
    whatsapp_number = form_data['From'].split("whatsapp:")[-1]
    # print(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    num_entries, _message_content = get_customer_conversations(whatsapp_number)
    redirect_to_cs_if_too_many_calls(whatsapp_number, num_entries, TEST)

    chatgpt_response = get_gpt_response(Body, TEST)

#     chatgpt_response = '''{  "name": null,
#   "time": "23:00:00",
#   "date": "2023-07-27",
#   "isotime": "2023-07-27T23:00:00"
# }'''

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
                send_message(whatsapp_number, ASK_NAME)
            return ASK_NAME
        if missing_info['missing_date']:
            if not TEST:
                send_message(whatsapp_number, ASK_DATE)
            return ASK_DATE
        if missing_info['missing_time']:
            if not TEST:
                send_message(whatsapp_number, ASK_TIME)
            return ASK_TIME
    else:
        extracted_fields = identify_booking_fields(chatgpt_response)
        fields_to_update = identify_fields_to_update(whatsapp_number)
        print('FIELDS TO UPDATE', fields_to_update)
        new_fields = {}
        for field in fields_to_update:
            new_fields[field] = extracted_fields[field]
        update_customer_data(new_fields)

        store_conversation_in_db(whatsapp_number=whatsapp_number,
                                 message=Body,
                                 chatgpt_response=chatgpt_response,
                                 date=booking_data.date,
                                 time=booking_data.time,
                                 isotime=booking_data.isotime,
                                 name=booking_data.name,
                                 time_of_inquiry=now,
                                 status=booking_data.status,
                                 db=db)

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

            return NOT_UNDERSTOOD

    print('ok2')

    if booking_data.status == 'NO_TIME_OR_DATE':
        return ASK_DATE_AGAIN
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
            send_message(whatsapp_number, ASK_CONFIRMATION)
    else:
        booking_data.status = 'NOT_AVAILABLE'
        update_status(whatsapp_number, booking_data.status)

        date_suggestions = get_next_available_slots("creativeassemblers@gmail.com", booking_data.isotime)
        response = SUGGEST_ALTERNATIVES_INTRO

        for isodate in date_suggestions:
            suggested_date, suggested_time = convert_isotime_to_readable(isodate)
            response += f' \nDatum: {suggested_date}, Zeit: {suggested_time}'

        response += SUGGEST_ALTERNATIVES_OUTRO
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
        response = BOOKING_CONFIRMATION + f'Zeit: {booking_data.time}, Datum: {booking_data.date}, Name: {booking_data.name}'
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")