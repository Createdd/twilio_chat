from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from decouple import config

from dateutil import parser
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging


# from fastapi import FastAPI, HTTPException
# from fastapi.responses import JSONResponse
# from fastapi.logger import logger as fastapi_logger

CALD_API_TOKEN = config("CALENDLY")
app = FastAPI()

# Configure the root logger
logging.basicConfig(level=logging.INFO)

# Create a logger specifically for your application
logger = logging.getLogger('app')



class Question(BaseModel):
    msg: str


@app.get("/")
async def index():
    return {"msg": "working"}

@app.get("/check_availability")
async def index():
    return {"msg": "available?"}

@app.post("/check_availability")
async def check_availability(booking_request:Question):
    # date = booking_request.date
    # time = booking_request.time

    print(booking_request)


    # if not is_valid_datetime(date, time):
    #     raise HTTPException(status_code=400, detail="Invalid date or time format")
    #
    # if not is_available(date, time):
    #     alternatives = get_alternatives(date, time)
    #     return {"available": False, "alternatives": alternatives}

    if is_available(booking_request.msg):
        return {"available": True}


    return {"available": False}

def is_available(iso_datetime: str) -> bool:
    start_time = parser.parse(iso_datetime)
    start_time = start_time + timedelta(hours=-2)
    end_time = start_time + timedelta(minutes=30)
    print(start_time, end_time, 'start and endtime')

    url = "https://api.calendly.com/scheduled_events"
    headers = {"Authorization": f"Bearer {CALD_API_TOKEN}"}

    params = {
        "min_start_time": start_time,
        "max_end_time": end_time
    }

    response = requests.get(url, headers=headers, params=params)
    # print the response
    print(response.json())

    if response.status_code == 200:
        event_data = response.json()
        return len(event_data["collection"]) == 0
    else:
        logger.error(f"Failed to check availability: {response.status_code}")
        raise HTTPException(status_code=500, detail="Failed to check availability")


# def get_alternatives(date: str, time: str) -> list:
#     # Make a request to the Calendly API to retrieve alternative slots
#     # Example: Fetch the next three available slots after the specified date and time
#     url = "https://api.calendly.com/scheduled_events"
#     headers = {"Authorization": f"Bearer {CALD_API_TOKEN}"}
#     params = {
#         "count": 3,
#         "min_start_time": f"{date}T{time}",
#         "status": "active"
#     }
#
#     response = requests.get(url, headers=headers, params=params)
#
#     if response.status_code == 200:
#         event_data = response.json()
#         alternatives = []
#         for event in event_data["collection"]:
#             alternative = {
#                 "date": event["start_time"].split("T")[0],
#                 "time": event["start_time"].split("T")[1].split(":00Z")[0]
#             }
#             alternatives.append(alternative)
#         return alternatives
#     else:
#         raise HTTPException(status_code=500, detail="Failed to retrieve alternatives")
#
# def confirm_booking() -> bool:
#     # Implement user confirmation logic, you can use a frontend framework or UI library for this
#     # Return True if the user confirms the booking, False otherwise
#     return True
#
# def create_booking(date: str, time: str) -> bool:
#     # Make a request to the Calendly API to create the booking
#     url = "https://api.calendly.com/scheduled_events"
#     headers = {"Authorization": f"Bearer {CALD_API_TOKEN}"}
#     payload = {
#         "event_type": "YOUR_EVENT_TYPE_UUID",
#         "start_time": f"{date}T{time}:00Z",
#         "end_time": f"{date}T{time}:00Z"
#     }
#
#     response = requests.post(url, headers=headers, json=payload)
#
#     if response.status_code == 201:
#         return True
#     else:
#         return False



#
#
#
#
#
# @app.exception_handler(HTTPException)
# async def http_exception_handler(request, exc):
#     # Log the error using your application logger
#     logger.error(f"HTTPException: {exc.detail}")
#
#     # Return an appropriate response to the client
#     return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
#
# @app.exception_handler(Exception)
# async def generic_exception_handler(request, exc):
#     # Log the error using your application logger
#     logger.exception("An unhandled exception occurred")
#
#     # Return an appropriate response to the client
#     return JSONResponse(status_code=500, content={"error": "Internal server error"})
#
#
# @app.on_event("startup")
# async def startup_event():
#     # You can log startup events or other application initialization tasks here
#     logger.info("Application startup")
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     # You can log shutdown events or perform cleanup tasks here
#     logger.info("Application shutdown")
