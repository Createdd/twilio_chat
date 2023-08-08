from db_functions import get_booking_data
import json
from utils import create_isotime


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

def identify_booking_fields(chatgpt_response):
    print('RESPONSE for identifying fields', chatgpt_response)
    booking_request = None

    # Define the list of required fields and their corresponding error messages
    required_fields = {
        'name': 'MISSING_NAME',
        'date': 'MISSING_DATE',
        'time': 'MISSING_TIME',
    }
    try:
        booking_request = json.loads(chatgpt_response)
    except Exception as e:
        print('Cannot JSON load response', e)

    for field in required_fields:
        if booking_request[field] is None:
            continue
        required_fields[field] = booking_request[field]

    if required_fields['date'] and required_fields['time'] is not None:
        required_fields['isotime'] = create_isotime(
            required_fields['date'], required_fields['time'])


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

    # todo: add logic to update outdated fields
    print('identify_fields_to_update', fields_to_update)
    return fields_to_update
