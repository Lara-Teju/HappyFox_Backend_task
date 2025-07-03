#!/usr/bin/env python3
"""
fetch_and_store.py

Standalone script to:
  1) Authenticate with Gmail via OAuth2
  2) Fetch message metadata (From/To/Subject/Date/body)
  3) Store or update each message in a local SQLite database

Usage:
    cd <project_root>
    .venv/Scripts/Activate.ps1   # or `source .venv/bin/activate`
    python src/fetch_and_store.py
"""

import os
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from googleapiclient.discovery import build
from sqlalchemy import (
    create_engine, Column, String, Text, DateTime
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import base64
import quopri
from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)



# -----------------------------------------------------------------------------
# 1) CONFIGURATION
# -----------------------------------------------------------------------------
SCOPES = os.getenv("SCOPES").split(",")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_PATH = os.getenv('CRED_PATH')
DB_PATH = os.getenv('DB_PATH')
DB_URL     = f'sqlite:///{DB_PATH}'

# -----------------------------------------------------------------------------
# 2) DATABASE SETUP (SQLAlchemy ORM)
# -----------------------------------------------------------------------------
Base = declarative_base()

class Email(Base):
    __tablename__ = 'emails'
    id           = Column(String,  primary_key=True)
    thread_id    = Column(String)
    from_address = Column(String)
    to_address   = Column(String)
    subject      = Column(Text)
    snippet      = Column(Text)  
    received_at  = Column(DateTime)
    processed_at = Column(DateTime, nullable=True)

engine = create_engine(DB_URL, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# -----------------------------------------------------------------------------
# 3) GMAIL AUTH & CLIENT CREATION
# -----------------------------------------------------------------------------
def get_gmail_service():
    token_path = os.getenv("TOKEN_PATH", "token.json")
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logging.info("Refreshed expired token.")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            logging.info("New OAuth token obtained.")

        # Save credentials for next time
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
            logging.info(f"Saved token to {token_path}.")

    return build('gmail', 'v1', credentials=creds)

# -----------------------------------------------------------------------------
# Extract plain text body from Gmail message
# -----------------------------------------------------------------------------
def get_email_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            body = get_email_body(part)
            if body:
                return body
    else:
        if payload.get('mimeType') == 'text/plain':
            data = payload.get('body', {}).get('data')
            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data).decode()
                except UnicodeDecodeError:
                    decoded = quopri.decodestring(base64.urlsafe_b64decode(data)).decode()
                return decoded
    return ''

# -----------------------------------------------------------------------------
# 4) FETCH & STORE FUNCTION
# -----------------------------------------------------------------------------
def fetch_and_store(max_results=50):
    service = get_gmail_service()
    session = Session()

    response = (
        service.users()
               .messages()
               .list(userId='me', maxResults=max_results)
               .execute()
    )
    messages = response.get('messages', [])
    logging.info(f"Fetched {len(messages)} message IDs from Gmail.")

    for msg_meta in messages:
        msg_id = msg_meta['id']
        msg = (
            service.users()
                   .messages()
                   .get(
                       userId='me',
                       id=msg_id,
                       format='full'  
                   )
                   .execute()
        )

        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        full_body = get_email_body(msg['payload']) or msg.get('snippet', '')

        email_row = Email(
            id           = msg['id'],
            thread_id    = msg.get('threadId'),
            from_address = headers.get('From', ''),
            to_address   = headers.get('To', ''),
            subject      = headers.get('Subject', ''),
            snippet      = full_body,  
            received_at  = datetime.fromtimestamp(int(msg['internalDate']) / 1000)
        )

        session.merge(email_row)

    session.commit()
    logging.info(f"Stored {len(messages)} emails into {DB_PATH}.")

# -----------------------------------------------------------------------------
# 5) ENTRYPOINT
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    fetch_and_store()

