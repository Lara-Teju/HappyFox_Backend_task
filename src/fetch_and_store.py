#!/usr/bin/env python3
"""
fetch_and_store.py

Standalone script to:
  1) Authenticate with Gmail via OAuth2
  2) Fetch message metadata (From/To/Subject/Date/snippet)
  3) Store or update each message in a local SQLite database

Usage:
    cd <project_root>
    .venv/Scripts/Activate.ps1   # or `source .venv/bin/activate`
    python src/fetch_and_store.py
"""

import os
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sqlalchemy import (
    create_engine, Column, String, Text, DateTime
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# -----------------------------------------------------------------------------
# 1) CONFIGURATION
# -----------------------------------------------------------------------------
# We need both read-only (to list & get messages) and modify (to mark/read or move later)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Compute BASE_DIR = project root (one level above src/)
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_PATH  = os.path.join(BASE_DIR, 'config', 'credentials.json')
DB_PATH    = os.path.join(BASE_DIR, 'emails.db')
DB_URL     = f'sqlite:///{DB_PATH}'

# -----------------------------------------------------------------------------
# 2) DATABASE SETUP (SQLAlchemy ORM)
# -----------------------------------------------------------------------------
Base = declarative_base()

class Email(Base):
    """ORM model for storing Gmail message metadata."""
    __tablename__ = 'emails'
    id           = Column(String,  primary_key=True)  # Gmail message ID
    thread_id    = Column(String)
    from_address = Column(String)
    to_address   = Column(String)
    subject      = Column(Text)
    snippet      = Column(Text)
    received_at  = Column(DateTime)
    processed_at = Column(DateTime, nullable=True)

# Create engine and tables if they don’t exist
engine = create_engine(DB_URL, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# -----------------------------------------------------------------------------
# 3) GMAIL AUTH & CLIENT CREATION
# -----------------------------------------------------------------------------
def get_gmail_service():
    """
    Perform OAuth2 desktop flow and return an authorized Gmail service object.
    """
    flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=creds)

# -----------------------------------------------------------------------------
# 4) FETCH & STORE FUNCTION
# -----------------------------------------------------------------------------
def fetch_and_store(max_results=50):
    """
    1) List up to `max_results` message IDs from the user's inbox.
    2) For each message ID, fetch the specified headers + snippet.
    3) Upsert into the local SQLite `emails` table.
    """
    service = get_gmail_service()
    session = Session()

    # --- 1) List message IDs ---
    response = (
        service.users()
               .messages()
               .list(userId='me', maxResults=max_results)
               .execute()
    )
    messages = response.get('messages', [])
    print(f"Fetched {len(messages)} message IDs from Gmail.")

    # --- 2) Iterate & fetch metadata ---
    for msg_meta in messages:
        msg_id = msg_meta['id']
        msg = (
            service.users()
                   .messages()
                   .get(
                       userId='me',
                       id=msg_id,
                       format='metadata',
                       metadataHeaders=['From', 'To', 'Subject', 'Date']
                   )
                   .execute()
        )

        # --- 3) Parse headers into a dict ---
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}

        # --- 4) Build ORM object ---
        email_row = Email(
            id           = msg['id'],
            thread_id    = msg.get('threadId'),
            from_address = headers.get('From', ''),
            to_address   = headers.get('To', ''),
            subject      = headers.get('Subject', ''),
            snippet      = msg.get('snippet', ''),
            received_at  = datetime.fromtimestamp(int(msg['internalDate']) / 1000)
        )

        # --- 5) Upsert into DB ---
        session.merge(email_row)

    # --- 6) Commit all changes ---
    session.commit()
    print(f"Stored {len(messages)} emails into {DB_PATH}.")

# -----------------------------------------------------------------------------
# 5) ENTRYPOINT
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    fetch_and_store()
