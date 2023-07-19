# Third-party imports
import openai
from fastapi import FastAPI, Form, Depends, Request
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import json
# Internal imports
from models import Conversation, SessionLocal
from utils import send_message, logger

from nylas_integration import check_time_and_book

CALENDAR_ID2 = config("GOOGLE_C2_ID")

CONTEXT_FOR_GPT = """Du bist ein Servicebot für Buchungsanfragen. Wenn ein Kunde eine Buchungsanfrage stellt, extrahierst du das Datum, die Uhrzeit, den Namen und gibst es im folgenden Format aus: 
"name": "daniel", "time": "2023-07-26T15:00:00”.  Sollte kein Name vorhanden sein, nimmst du “Kunde”.
Achte darauf, dass dein Output ausschließlich diese Formatierung enthält. Verzichte auf jegliche Floskeln und Hinweise."""
app = FastAPI()
# Set up the OpenAI API client
openai.api_key = config("OPENAI_API_KEY")

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

@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    # Extract the phone number from the incoming webhook request
    form_data = await request.form()
    whatsapp_number = form_data['From'].split("whatsapp:")[-1]
    print(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    # Call the OpenAI API to generate text with ChatGPT
    messages = [{"role": "user", "content": Body}]
    messages.append({"role": "system", "content": CONTEXT_FOR_GPT})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=200,
        n=1,
        stop=None,
        temperature=0.5
        )

    chatgpt_response = response.choices[0].message.content
    # chatgpt_response = 'this is a test response from file'

    # Store the conversation in the database
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chatgpt_response
            )
        db.add(conversation)
        db.commit()
        logger.info(f"Conversation #{conversation.id} stored in database")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error storing conversation in database: {e}")

    send_message(whatsapp_number, chatgpt_response)

    try:
        booking_request = json.loads(chatgpt_response)
        time = booking_request['time']
        # calendar_id = booking_request['calendar_id']
        calendar_id = CALENDAR_ID2
        name = booking_request['name']

        booking_answer = check_time_and_book(calendar_id, time, name)


    except Exception as e:
        send_message(whatsapp_number, f'Could not extract booking info or book. {e}')

    print(booking_answer, 'booking_answer')
    send_message(whatsapp_number, booking_answer)

    # print(booking_request)
    # print(time, calendar_id, name)




    print('done')
    return "done"


    return ""

#-----------------------------

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

