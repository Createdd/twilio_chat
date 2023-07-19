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


app = FastAPI()
# Set up the OpenAI API client
# openai.api_key = config("OPENAI_API_KEY")

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

# @app.post("/gpt_message")
# async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
#     # Extract the phone number from the incoming webhook request
#     form_data = await request.form()
#     whatsapp_number = form_data['From'].split("whatsapp:")[-1]
#     print(f"Sending the ChatGPT response to this number: {whatsapp_number}")
#
#     # Call the OpenAI API to generate text with ChatGPT
#     messages = [{"role": "user", "content": Body}]
#     messages.append({"role": "system", "content": "You're an investor, a serial founder and you've sold many startups. You understand nothing but business."})
#
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=messages,
#         max_tokens=200,
#         n=1,
#         stop=None,
#         temperature=0.5
#         )
#
#     # The generated text
#     chatgpt_response = response.choices[0].message.content
#     # chatgpt_response = 'this is a test response from file'
#
#     # Store the conversation in the database
#     try:
#         conversation = Conversation(
#             sender=whatsapp_number,
#             message=Body,
#             response=chatgpt_response
#             )
#         db.add(conversation)
#         db.commit()
#         logger.info(f"Conversation #{conversation.id} stored in database")
#     except SQLAlchemyError as e:
#         db.rollback()
#         logger.error(f"Error storing conversation in database: {e}")
#     send_message(whatsapp_number, chatgpt_response)
#     return ""

#-----------------------------

from pydantic import BaseModel
from nylas_integration import check_time_and_book

class BookingRequest(BaseModel):
    calendar_id: str
    time: str
    name: str
@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    form_data = await request.form()
    whatsapp_number = form_data['From'].split("whatsapp:")[-1]
    print(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    # Call the OpenAI API to generate text with ChatGPT
    messages = [{"role": "user", "content": Body}]
    booking_request = messages[0]['content']

    send_message(whatsapp_number, booking_request)


    booking_request = json.loads(booking_request)
    time = booking_request['time']
    calendar_id = booking_request['calendar_id']
    name = booking_request['name']

    # print(booking_request)
    print(time, calendar_id, name)
    booking_answer = check_time_and_book(calendar_id, time, name)
    print(booking_answer, 'booking_answer')
    send_message(whatsapp_number, booking_answer)



    print('done')
    return "done"

