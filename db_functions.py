from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.engine import URL
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker
from decouple import config
from utils import logger
from sqlalchemy.exc import SQLAlchemyError
from utils import create_isotime


url = URL.create(
    drivername="postgresql",
    username=config("DB_USER"),
    password=config("DB_PASSWORD"),
    host="localhost",
    database="mydb",
    port=5432
)

engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String)
    message = Column(String)
    response = Column(String)
    time_of_inquiry = Column(DateTime)
    isotime = Column(DateTime)
    name = Column(String)
    date = Column(String)
    time = Column(String)
    status = Column(String)


Base.metadata.create_all(engine)


def get_customer_conversations(whatsapp_number):
    # Function to get conversations associated with a specific customer
    db = SessionLocal()
    try:
        # Query the database for entries related to the customer's phone number
        conversations = db.query(Conversation).filter_by(sender=whatsapp_number).all()

        # Count the number of entries
        num_entries = len(conversations)

        # Retrieve the content of messages
        message_content = [conv.message for conv in conversations]

        return num_entries, message_content

    except Exception as e:
        # Handle any exceptions, logging, or error responses as needed
        raise e

    finally:
        db.close()


def is_number_in_database(whatsapp_number):
    # Function to check if a number exists in the database
    db = SessionLocal()
    try:
        # Query the database for entries related to the customer's phone number
        conversation = db.query(Conversation).filter_by(sender=whatsapp_number).first()

        # Return True if the conversation exists (number is in the database)
        # Return False if the conversation does not exist (number is not in the database)
        return conversation is not None

    except Exception as e:
        # Handle any exceptions, logging, or error responses as needed
        raise e

    finally:
        db.close()



def check_last_entry(whatsapp_number):
    # Function to check for missing information in the last entry
    db = SessionLocal()
    try:
        # Query the database for entries related to the customer's phone number
        conversations = db.query(Conversation).filter_by(sender=whatsapp_number).all()

        # Get the last entry from the conversations list
        last_entry = conversations[-1] if conversations else None

        # Check for missing name, date, and time
        missing_info = {
            "missing_name": not last_entry.name if last_entry else False,
            "missing_date": not last_entry.date if last_entry else False,
            "missing_time": not last_entry.time if last_entry else False,
        }

        return missing_info

    except Exception as e:
        # Handle any exceptions, logging, or error responses as needed
        raise e

    finally:
        db.close()

def update_status_in_db(whatsapp_number, new_status):
    # Function to update the status of an existing conversation in the database
    db = SessionLocal()
    try:
        # Query the database for the existing conversation based on the WhatsApp number
        conversation = db.query(Conversation).filter_by(sender=whatsapp_number).first()

        # If conversation exists, update the status
        if conversation:
            conversation.status = new_status
            db.commit()
            logger.info(f"Status updated for Conversation #{conversation.id}")
        else:
            # Handle the case where the conversation does not exist (WhatsApp number not found)
            logger.error(f"Conversation with WhatsApp number {whatsapp_number} not found")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error updating status in the database: {e}")

    finally:
        db.close()


def get_booking_data_from_db(whatsapp_number):
    db = SessionLocal()
    try:
        # Query the database for the existing conversation based on the WhatsApp number
        conversation = db.query(Conversation).filter_by(sender=whatsapp_number).first()

        # Create an empty dictionary to store the field values
        booking_data = {}

        # Iterate through the fields of the conversation and add them to the dictionary
        for field in conversation.__dict__:
            # Skip internal attributes and only add user-defined fields to the dictionary
            if not field.startswith("_"):
                booking_data[field] = conversation.__dict__[field]

        print('Booking data from get_booking_data_from_db:', booking_data)
        return booking_data

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error in getting the data from the database: {e}")

    finally:
        db.close()

def update_booking_data_in_db(whatsapp_number, new_extracted_time, new_extracted_name, new_extracted_date):
    # Function to update extracted_time, extracted_name, and extracted_date in the database
    db = SessionLocal()
    try:
        # Query the database for the existing conversation based on the WhatsApp number
        conversation = db.query(Conversation).filter_by(sender=whatsapp_number).first()

        updated = []

        # If conversation exists, update the extracted_time, extracted_name, and extracted_date
        if conversation:
            # print(f"Got conv from db: {conversation.__dict__}")
            # Check if new extracted_time is available and update if so
            if conversation.time is None and new_extracted_time is not None:
                conversation.time = new_extracted_time
                updated = updated.append(new_extracted_time)
                print(f'updated time from {conversation.extracted_time} to {new_extracted_time}')

            # Check if new extracted_name is available and update if so
            if conversation.name is None and new_extracted_name is not None:
                conversation.name = new_extracted_name
                print(f'updated name from {conversation.name} to {new_extracted_name}')

            # Check if new extracted_date is available and update if so
            if conversation.date is None and new_extracted_date is not None:
                conversation.date = new_extracted_date
                updated = updated.append(new_extracted_time)
                print(f'updated date from {conversation.extracted_date} to {new_extracted_date}')


            if len(updated) > 0:
                new_isotime = create_isotime(conversation.date, conversation.time)
                conversation.isotime = new_isotime
                print(f'updated isotime from {conversation.isotime} to {new_isotime}')


            db.commit()
            logger.info(f"Updated Booking Data for Conversation #{conversation.id}")
        else:
            # Handle the case where the conversation does not exist (WhatsApp number not found)
            logger.error(f"Conversation with WhatsApp number {whatsapp_number} not found")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error updating Booking Data in the database: {e}")

    finally:
        db.close()

def store_conversation_in_db(whatsapp_number,
                             message,
                             chatgpt_response,
                             date,
                             time,
                             isotime,
                             name,
                             time_of_inquiry,
                             status,
                             db):
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=message,
            response=chatgpt_response,
            date=date,
            time=time,
            name=name,
            isotime=isotime,
            time_of_inquiry=time_of_inquiry,
            status=status
        )
        db.add(conversation)
        db.commit()
        logger.info(f"Conversation #{conversation.id} stored in database")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error storing conversation in database: {e}")
