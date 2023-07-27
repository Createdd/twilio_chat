from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.engine import URL
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker
from decouple import config


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
    extracted_date = Column(DateTime)
    extracted_time = Column(String)


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