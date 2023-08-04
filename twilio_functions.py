from templates import REDIRECT_TO_CS
from utils import send_message


def redirect_to_cs_if_too_many_calls(whatsapp_number, num_entries, test):
    if num_entries > 100:  # todo set to 10
        if not test:
            send_message(whatsapp_number, REDIRECT_TO_CS)
        return REDIRECT_TO_CS
