#!/usr/bin/env python3
"""
process_rules.py

Standalone script to:
  1) Load user-defined rules from a JSON file
  2) Query stored emails in SQLite (emails.db)
  3) Evaluate each email against the rule predicates (All / Any semantics)
  4) Call Gmail API to mark read/unread or move messages to a label
  5) Record which messages were processed

Usage:
    cd <project_root>
    .venv/Scripts/Activate.ps1   # or `source .venv/bin/activate`
    python src/process_rules.py --rules ../rules.json
"""

import os
import json
import argparse
from datetime import datetime, timedelta

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from sqlalchemy import (
    create_engine, Text,String,Column, DateTime as SATime, update
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# -----------------------------------------------------------------------------
# 1) CONFIGURATION & DB SETUP
# -----------------------------------------------------------------------------
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_PATH  = os.path.join(BASE_DIR, 'config', 'credentials.json')
DB_PATH    = os.path.join(BASE_DIR, 'emails.db')
DB_URL     = f'sqlite:///{DB_PATH}'

# Extend the Email model to include a processed_at column
Base = declarative_base()
class Email(Base):
    __tablename__ = 'emails'
    id           = Column(String, primary_key=True)
    thread_id    = Column(String)
    from_address = Column(String)
    to_address   = Column(String)
    subject      = Column(Text)
    snippet      = Column(Text)
    received_at  = Column(SATime)
    processed_at = Column(SATime, nullable=True)

# Create engine & session
engine = create_engine(DB_URL, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# -----------------------------------------------------------------------------
# 2) AUTHENTICATE TO GMAIL
# -----------------------------------------------------------------------------
def get_gmail_service():
    flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=creds)

# -----------------------------------------------------------------------------
# 3) PREDICATE FUNCTIONS
# -----------------------------------------------------------------------------
def predicate_contains(field_val, rule_val):
    return rule_val.lower() in (field_val or '').lower()

def predicate_not_contains(field_val, rule_val):
    return rule_val.lower() not in (field_val or '').lower()

def predicate_equals(field_val, rule_val):
    return (field_val or '').lower() == rule_val.lower()

def predicate_not_equals(field_val, rule_val):
    return (field_val or '').lower() != rule_val.lower()

def predicate_less_than_date(dt, rule_val, unit='days', now=None):
    if now is None:
        now = datetime.now()
    days = int(rule_val) * (30 if unit=='months' else 1)
    cutoff = now - timedelta(days=days)
    return dt > cutoff

def predicate_greater_than_date(dt, rule_val, unit='days', now=None):
    if now is None:
        now = datetime.now()
    days = int(rule_val) * (30 if unit=='months' else 1)
    cutoff = now - timedelta(days=days)
    return dt < cutoff

# Map textual predicates to functions
PREDICATE_FN = {
    'contains':        predicate_contains,
    'does not contain': predicate_not_contains,
    'equals':          predicate_equals,
    'does not equal':  predicate_not_equals,
    'less than':       predicate_less_than_date,
    'greater than':    predicate_greater_than_date,
}

# -----------------------------------------------------------------------------
# 4) ACTION FUNCTIONS
# -----------------------------------------------------------------------------
def mark_as_read(service, msg_id):
    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

def mark_as_unread(service, msg_id):
    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={'addLabelIds': ['UNREAD']}
    ).execute()

def move_to_label(service, msg_id, label_name, label_cache):
    """
    Move a message to a given label. For 'INBOX', it simply re-adds the INBOX label.
    For other labels, adds label and removes INBOX.
    """
    # Handle system label 'INBOX'
    if label_name.upper() == 'INBOX':
        service.users().messages().modify(
            userId='me', id=msg_id,
            body={'addLabelIds': ['INBOX']}
        ).execute()
        return

    # Fetch & cache custom label IDs
    if label_name not in label_cache:
        labels = service.users().labels().list(userId='me').execute().get('labels', [])
        label_cache.update({l['name']: l['id'] for l in labels})
    label_id = label_cache.get(label_name)
    if not label_id:
        # Optionally create label if missing:
        new = service.users().labels().create(
            userId='me', body={'name': label_name}
        ).execute()
        label_id = new['id']
        label_cache[label_name] = label_id

    # Add custom label and remove from INBOX
    service.users().messages().modify(
        userId='me', id=msg_id,
        body={'addLabelIds': [label_id], 'removeLabelIds': ['INBOX']}
    ).execute()

# -----------------------------------------------------------------------------
# 5) RULE EVALUATION
# -----------------------------------------------------------------------------
def evaluate_rule(email, rule):
    """
    rule: {
      "field": "From" | "Subject" | "snippet" | "received_at",
      "predicate": <one of PREDICATE_FN keys>,
      "value": "<string or integer>",
      "unit": "days" | "months"   # only for date predicates (optional; defaults to 'days')
    }
    """
    field = rule['field'].lower()
    pred = rule['predicate'].lower()
    val  = rule['value']
    unit = rule.get('unit', 'days')

    # Select attribute
    if field == 'from':
        target = email.from_address
    elif field == 'to':
        target = email.to_address
    elif field == 'subject':
        target = email.subject
    elif field in ('message','snippet'):
        target = email.snippet
    elif field in ('date','received','received_at'):
        target = email.received_at
    else:
        raise ValueError(f"Unsupported field in rule: {field}")

    fn = PREDICATE_FN.get(pred)
    if not fn:
        raise ValueError(f"Unsupported predicate: {pred}")

    # Date predicates expect a datetime; string ones expect text
    if 'date' in field or pred in ('less than','greater than'):
        return fn(target, val, unit)
    else:
        return fn(target, val)

# -----------------------------------------------------------------------------
# 6) MAIN PROCESSING FLOW
# -----------------------------------------------------------------------------
def process_rules(rules_path):
    # Load rule set
    with open(rules_path, 'r') as f:
        cfg = json.load(f)

    overall = cfg.get('predicate', 'All').lower()  # 'all' or 'any'
    rules   = cfg['rules']                         # list of rule dicts
    actions = cfg['actions']                       # e.g. ['mark_as_read','move_to:IMPORTANT']

    service = get_gmail_service()
    session = Session()
    label_cache = {}

    # Fetch emails that haven’t been processed yet
    emails = session.query(Email).filter(Email.processed_at.is_(None)).all()
    print(f"Loaded {len(emails)} unprocessed emails from DB.")

    for email in emails:
        # Evaluate all conditions
        results = [evaluate_rule(email, r) for r in rules]
        match = all(results) if overall == 'all' else any(results)

        if not match:
            continue

        # Apply each action in order
        for action in actions:
            if action == 'mark_as_read':
                mark_as_read(service, email.id)
            elif action == 'mark_as_unread':
                mark_as_unread(service, email.id)
            elif action.startswith('move_to:'):
                _, label = action.split(':', 1)
                move_to_label(service, email.id, label, label_cache)
            else:
                print(f"Warning: Unsupported action '{action}'")

        # Mark processed
        session.execute(
            update(Email).
            where(Email.id == email.id).
            values(processed_at=datetime.now())
        )
        session.commit()
        print(f"Applied rules to {email.id}; actions: {actions}")

# -----------------------------------------------------------------------------
# 7) CLI ENTRYPOINT
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process stored Gmail rules.")
    parser.add_argument(
        '--rules', '-r',
        required=True,
        help="Path to JSON file defining your rules and actions"
    )
    args = parser.parse_args()
    process_rules(args.rules)
