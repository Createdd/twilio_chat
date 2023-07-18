from dateutil import parser
from datetime import datetime, timedelta
import os
from nylas import APIClient
from decouple import config

google_account_id = config("GOOGLE_ACCOUNT_ID")
CALENDAR_ID = config("GOOGLE_C1_ID")



nylas = APIClient(
    client_id=config("NYLAS_CLIENT_ID"),
    client_secret=config("NYLAS_CLIENT_SECRET"),
    access_token=config("NYLAS_ACCESS_TOKEN"),
    api_server=config("NYLAS_API_SERVER")
)
from datetime import datetime




start_time = parser.parse('2023-07-19T17:00:00')
start_time = start_time + timedelta(hours=-0)
end_time = start_time + timedelta(minutes=30)
print(start_time, end_time, 'start and endtime')
start_time_unix, end_time_unix = int(start_time.timestamp()), int(end_time.timestamp())
print(start_time_unix, end_time_unix, 'start and endtime')

# calendars = nylas.calendars.all()
# for calendar in calendars:
#   print("Id: {} | Name: {} | Description: {} | Read Only: {}".format(
#     calendar.id, calendar.name, calendar.description, calendar.read_only))


# now = int(datetime.now().timestamp())
# events = nylas.events.where(calendar_id=CALENDAR_ID, starts_after=start_time).all()
# print(type(events))
# for event in events:
#     print(f'title: {event.title}, when: {event.when}, participants: {event.participants}')


# event = nylas.events.create()
# event.title = "New Years Party!"
# event.location = "My House!"
# event.description = "We'll ring in the new year in style!"
# event.participants = [{"name": "dan ", 'email': 'deudan1010@gmail.com'}]
# event.when = {"start_time": start_time, "end_time": end_time}
#
# event.calendar_id = CALENDAR_ID
# event.save(notify_participants='true')

def get_google_calendar_availability():
    # Get the calendar ID of your Google Calendar
    events = nylas.events.where(
        calendar_id=CALENDAR_ID,
        starts_before=end_time_unix,  # Specify the start time of the availability range
        ends_after=start_time_unix,
        # starts_after=start_time_unix,  # Specify the start time of the availability range
        # ends_after=start_time_unix,  # Specify the end time of the availability range
        participants=[],  # Specify any participants to include in the availability check
    ).all(limit=2)

    if not events:
        # If no events are found within the time range, the proposed date and time is available
        print(f"The proposed date and time at {start_time} and ending at {end_time} ")
        return 'is available'
    else:
        # If events are found within the time range, the proposed date and time is busy
        print(f"The proposed date and time at {start_time} and ending at {end_time} are busy. Events:")
        for event in events:
            iso_date_start = datetime.fromtimestamp(event.when['start_time']).isoformat()
            iso_date_end = datetime.fromtimestamp(event.when['end_time']).isoformat()
            print(f"- {event.title} starting at {iso_date_start} and ending at {iso_date_end})")
        return 'not available'


# # Call the function to get the availability of your Google Calendar
print(get_google_calendar_availability())



# print(f'is available: {availability}')
