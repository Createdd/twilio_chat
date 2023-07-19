from dateutil import parser
from datetime import datetime, timedelta
import os
from nylas import APIClient
from decouple import config
from datetime import datetime

google_account_id = config("GOOGLE_ACCOUNT_ID")
CALENDAR_ID = config("GOOGLE_C1_ID")
CALENDAR_ID2 = config("GOOGLE_C2_ID")

nylas = APIClient(
    client_id=config("NYLAS_CLIENT_ID"),
    client_secret=config("NYLAS_CLIENT_SECRET"),
    access_token=config("NYLAS_ACCESS_TOKEN"),
    api_server=config("NYLAS_API_SERVER")
)

# TIME_TO_MEET = '2023-07-19T12:30:00'

# calendars = nylas.calendars.all()
# for calendar in calendars:
#   print("Id: {} | Name: {} | Description: {} | Read Only: {}".format(
#     calendar.id, calendar.name, calendar.description, calendar.read_only))


# now = int(datetime.now().timestamp())
# # get the time for today at 0:00
# today = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
# print(today)
# events = nylas.events.where(calendar_id=CALENDAR_ID, starts_after=today).all()
# print(type(events))
# for event in events:
#     print(f'title: {event.title}, when: {event.when}, participants: {event.participants}')
#
# raise Exception('stop')




def calculate_time(time_to_meet_in_iso, unix=False):
    start_time = parser.parse(time_to_meet_in_iso)
    start_time = start_time + timedelta(hours=-0)
    end_time = start_time + timedelta(minutes=30)
    # print(start_time, end_time, 'start and endtime')
    start_time_unix, end_time_unix = int(start_time.timestamp()), int(end_time.timestamp())
    # print(start_time_unix, end_time_unix, 'start and endtime')

    if unix:
        return start_time_unix, end_time_unix
    else:
        return start_time, end_time


def get_google_calendar_availability(calendar_id, time_to_meet_in_iso):
    # start_time, end_time = calculate_time(time_to_meet_in_iso, unix=False)
    start_time_unix, end_time_unix = calculate_time(time_to_meet_in_iso, unix=True)
    # Get the calendar ID of your Google Calendar
    events = nylas.events.where(
        calendar_id=calendar_id,
        starts_before=end_time_unix,  # Specify the start time of the availability range
        ends_after=start_time_unix,
        participants=[],  # Specify any participants to include in the availability check
    ).all(limit=2)

    if not events:
        # print(f"The proposed date and time at {start_time} and ending at {end_time} ")
        print('is available')
        return True
    else:
        # print(f"The proposed date and time at {start_time} and ending at {end_time} are busy. Events:")
        for event in events:
            iso_date_start = datetime.fromtimestamp(event.when['start_time']).isoformat()
            iso_date_end = datetime.fromtimestamp(event.when['end_time']).isoformat()
            print(f"- {event.title} starting at {iso_date_start} and ending at {iso_date_end})")

        print('not available')
        return False


def book_event(title, location, description, participant, time_to_meet_in_iso, calendar_id):
    start_time_unix, end_time_unix = calculate_time(time_to_meet_in_iso, unix=True)

    event = nylas.events.create()
    event.title = title
    event.location = location
    event.description = description
    event.participants = [{"name": participant['name'], 'email': participant['email']}]
    event.when = {"start_time": start_time_unix, "end_time": end_time_unix}
    event.calendar_id = calendar_id
    # event.save(notify_participants='true')
    event.save()


# available = get_google_calendar_availability(CALENDAR_ID, TIME_TO_MEET)
# print(available)
#
# if available:
#     book_event(
#         title="lunch",
#         location="lc",
#         description="meeting lc for lunch",
#         participant={'name': "Lukas", 'email': "creativeassemblers@gmail.com"},
#         time_to_meet_in_iso=TIME_TO_MEET,
#         calendar_id=CALENDAR_ID
#     )
#     print('booking done')

def check_time_and_book(calendar_id, time_to_meet, name):
    available = get_google_calendar_availability(calendar_id, time_to_meet)
    print(available)

    if available:
        book_event(
            title=f"Booking with {name}",
            location="at office",
            description="meeting with doctor",
            participant={'name': name, 'email': "creativeassemblers@gmail.com"},
            time_to_meet_in_iso=time_to_meet,
            calendar_id=calendar_id
        )
        print('booking done')
        return('booking done')

    else:
        print('not available. suggest another time')
        return('not available. suggest another time')



# check_time_and_book(CALENDAR_ID, TIME_TO_MEET, 'daniel')