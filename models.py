from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.engine import URL
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker
from decouple import config
from utils import logger
from sqlalchemy.exc import SQLAlchemyError


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
    extracted_name = Column(String)
    extracted_date = Column(String)
    extracted_time = Column(String)
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
            "missing_name": not last_entry.extracted_name if last_entry else False,
            "missing_date": not last_entry.extracted_date if last_entry else False,
            "missing_time": not last_entry.extracted_time if last_entry else False,
        }

        return missing_info

    except Exception as e:
        # Handle any exceptions, logging, or error responses as needed
        raise e

    finally:
        db.close()

def update_status(whatsapp_number, new_status):
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