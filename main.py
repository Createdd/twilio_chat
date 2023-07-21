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
import datetime

from nylas_integration import check_time_and_book, get_google_calendar_availability, book_event

CALENDAR_ID2 = config("GOOGLE_C2_ID")

now = datetime.datetime.now()
now = now.isoformat()

NOW_PHRASE = f"Der zeitpunkt der anfrage ist {now}."

CONTEXT_FOR_GPT = """
Du bist ein Servicebot für Buchungsanfragen. 
Extrahiere das Datum, die Uhrzeit und den Namen aus der Anfrage und gib die Informationen im folgenden JSON-Format aus: 
{"name": "Daniel", "time": "YYYY-MM-DDTHH:MM:SS"}. 
Von dem Zeitpunkt der Anfrage sollen die Zeiten berechnet werden. wie zum beispiel "Übermorgen", "Morgen", etc.
Überprüfe ob in der Anfrage sowohl ein Datum als auch eine Uhrzeit vorhanden ist. Wenn nicht dann frage jeweils nach dem fehlenden Teil. 
Nimm nicht irgendwelche Werte an.
Wenn der Kunde nach "Morgen" fragt, evaluiere das Datum ausgehend von heute. 
Falls kein Name angegeben ist, verwende "Kunde" als Standardname. 
Sollte kein Datum in der Buchungsanfrage vorhanden sein, verwende “fehlt”. 
Sollte keine Uhrzeit in der Buchungsanfrage vorhanden sein, verwende “fehlt”. 
Achte darauf, dass die Ausgabe ausschließlich dieses JSON-Format enthält und verzichte auf jegliche Hinweise und Floskeln. 
Jede deiner Antworten darf nur im Schema: "name": "XXX", "time": "YYYY-MM-DDTHH:MM:SS” sein.
"""

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

    # Get or create the user session for the specific route
    # user_session = db.query(UserSession).filter_by(user_id=whatsapp_number, route_name="message").first()
    # if not user_session:
    #     user_session = UserSession(user_id=whatsapp_number, route_name="message")
    #     db.add(user_session)

    # Call the OpenAI API to generate text with ChatGPT
    messages = [{"role": "user", "content": Body}]
    messages.append({"role": "system", "content": NOW_PHRASE})
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
    send_message(whatsapp_number, chatgpt_response)  # fo rlogging

    # chatgpt_response = 'this is a test response from file'

    # # Store the conversation in the database
    # try:
    #     conversation = Conversation(
    #         sender=whatsapp_number,
    #         message=Body,
    #         response=chatgpt_response
    #         )
    #     db.add(conversation)
    #     db.commit()
    #     logger.info(f"Conversation #{conversation.id} stored in database")
    # except SQLAlchemyError as e:
    #     db.rollback()
    #     logger.error(f"Error storing conversation in database: {e}")

    name, time, available = None, None, None

    try:
        booking_request = json.loads(chatgpt_response)
        time = booking_request['time']
        # calendar_id = booking_request['calendar_id']
        calendar_id = CALENDAR_ID2
        name = booking_request['name']

        available = get_google_calendar_availability(calendar_id, time)
        print('worked', available, time, name)

    except Exception as e:
        send_message(whatsapp_number,
                     f'Kannst du mir nochmal sagen, wann du du genau einen Termin möchtest und für welchen Namen ich diesen buchen darf?')
        return 'no time or date'

    if available is None:
        send_message(whatsapp_number, 'Wir leiten dich an einen Mitarbeiter weiter.')
        return 'done'

    if available:
        booking_answer = book_event(
            title=f"Booking with {name}",
            location="at office",
            description="meeting with doctor",
            participant={'name': name, 'email': "creativeassemblers@gmail.com"},
            time_to_meet_in_iso=time,
            calendar_id=CALENDAR_ID2
        )
        print(booking_answer, 'booking_answer')
        send_message(whatsapp_number, booking_answer)

    else:
        send_message(whatsapp_number, 'Der Termin ist nicht mehr frei. Nenne einen anderen')

    # print(booking_request)
    # print(time, calendar_id, name)

    print('done')
    return "done"

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
