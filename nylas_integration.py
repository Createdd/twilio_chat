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


now = int(datetime.now().timestamp())
# get the time for today at 0:00
today = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
print(today)
# events = nylas.events.where(calendar_id=CALENDAR_ID, starts_after=today).all()
# print(type(events))
# for event in events:
#     print(f'title: {event.title}, when: {event.when}, participants: {event.participants}')
#
# raise Exception('stop')




def calculate_time(time_to_meet_in_iso, unix=False):
    print(time_to_meet_in_iso, type(time_to_meet_in_iso))
    if type(time_to_meet_in_iso) != str:
        time_to_meet_in_iso = time_to_meet_in_iso.isoformat()
    print(time_to_meet_in_iso, type(time_to_meet_in_iso))

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
    try:
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
        return 'BOOKED'
    except Exception as e:
        print('from book_event: ', e)
        return e




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

def check_if_time_is_busy(email, requested_time):
    # start_time = parser.parse(requested_time)
    start_time = requested_time
    start_time = start_time + timedelta(hours=-0)
    end_time = start_time + timedelta(minutes=30)
    start_time_unix, end_time_unix = int(start_time.timestamp()), int(end_time.timestamp())
    time_list=[[start_time_unix, end_time_unix]]

    print(time_list)
    is_busy = is_time_slot_busy(email, start_time_unix, end_time_unix)
    print('is busy???', is_busy)
    if is_busy:
        response = 'busy'
    else:
        response = 'free'



    # free_busy_week = []
    # for time_pair in time_list:
    #     free_busy = nylas.free_busy(email, time_pair[0], time_pair[1])
    #     free_busy_week.append(free_busy)

    print(response)
    return is_busy

def is_time_slot_busy(email, start_time, end_time):
    # Use the Nylas API to get the free busy time slots for the specified calendar
    busy_slots = nylas.free_busy(email, start_time, end_time)
    print(busy_slots[0]['time_slots'], ' busy time slots')

    # If there are no  busy time slots within the specified time range, the time slot is not busy
    is_busy = len(busy_slots[0]['time_slots']) > 0

    return is_busy

test_time = str(datetime.now())


# def get_next_available_slots(email, suggested_time):
#     # Convert the suggested time to a datetime object
#     suggested_time_dt = parser.parse(suggested_time)
#
#     # Create a list of weekdays (Monday to Friday)
#     weekdays = [0, 1, 2, 3, 4]  # Monday=0, Tuesday=1, ..., Friday=4
#
#     # Create a list to store the next available time slots
#     next_available_slots = []
#
#     # Iterate through each weekday
#     for weekday in weekdays:
#         # Get the start time and end time for the specified weekday (e.g., Monday 9:00 to 18:00)
#         start_time = datetime(suggested_time_dt.year, suggested_time_dt.month, suggested_time_dt.day, 9, 0)
#         end_time = datetime(suggested_time_dt.year, suggested_time_dt.month, suggested_time_dt.day, 18, 0)
#
#         # Add the weekday offset to the start time and end time
#         start_time += timedelta(days=weekday)
#         end_time += timedelta(days=weekday)
#
#         print(start_time, end_time)
#
#         # Get the free busy time slots for the specified weekday
#         # free_busy = get_free_busy(email, suggested_time)
#
#         # # Get the available time slots for the specified weekday
#         # available_slots = get_available_slots_from_free_busy(start_time, end_time, free_busy)
#         #
#         # # Find the closest available time slot to the suggested time
#         # closest_slot = find_closest_time_slot(suggested_time_dt, available_slots)
#
#         # if closest_slot:
#         #     next_available_slots.append(closest_slot)
#
#     return next_available_slots

def get_next_available_slots(email, suggested_time):
    # Convert the suggested time to a datetime object
    # print(suggested_time)

    if type(suggested_time) != str:
        suggested_time = suggested_time.isoformat()

    suggested_time_dt = datetime.fromisoformat(suggested_time)
    # print(suggested_time_dt)
    # Create a list of available time slots
    available_slots = []

    # Define the alternating time increments (30, -30, 60, -60, 90, -90, ...)
    time_increments = [30 * i * (-1) ** i for i in range(1, 13)]

    # Iterate through time increments and check for available time slots
    for increment in time_increments:
        # Add the time increment to the suggested time and check if the time slot is available
        new_time = suggested_time_dt + timedelta(minutes=increment)
        # print(len(available_slots))
        # print('new time', new_time)
        is_busy = check_if_time_is_busy(email, new_time)
        # print('is available?', not is_busy)
        if not is_busy:
            available_slots.append(new_time.strftime('%Y-%m-%dT%H:%M:%S'))

        if len(available_slots) == 3:
            break

    print(available_slots)
    return available_slots


# get_next_available_slots("creativeassemblers@gmail.com", test_time)



# check_time_and_book(CALENDAR_ID, TIME_TO_MEET, 'daniel')