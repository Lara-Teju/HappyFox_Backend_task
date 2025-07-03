import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime as SATime
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
load_dotenv()
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

# ----------------------------------------------------------------
# SETUP (adjust paths as needed)
# ----------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv('DB_PATH')
DB_URL = f'sqlite:///{DB_PATH}'

# Define the Email model (must match your original schema)
Base = declarative_base()

class Email(Base):
    __tablename__ = 'emails'
    id = Column(String, primary_key=True)
    thread_id = Column(String)
    from_address = Column(String)
    to_address = Column(String)
    subject = Column(Text)
    snippet = Column(Text)
    received_at = Column(SATime)
    processed_at = Column(SATime, nullable=True)

# ----------------------------------------------------------------
# DB CONNECTION
# ----------------------------------------------------------------
engine = create_engine(DB_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# ----------------------------------------------------------------
# FETCH & DISPLAY
# ----------------------------------------------------------------
def show_emails():
    emails = session.query(Email).all()
    if not emails:
        print("No emails found in the database.")
        return

    print(f"{'ID':<30} {'From':<40} {'Subject':<40} {'Processed':<20}")
    print("=" * 140)
    for email in emails:
        processed = email.processed_at.strftime("%Y-%m-%d %H:%M") if email.processed_at else "❌ Not yet"
        print(f"{email.id[:8]}...  {email.from_address[:38]:<40} {email.subject[:38]:<40} {processed:<20}")

if __name__ == '__main__':
    show_emails()
