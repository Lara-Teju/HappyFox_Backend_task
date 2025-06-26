import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from process_rules import Base, Email, evaluate_rule, predicate_less_than_date

# ----------------------
# Fixtures: DB + Session
# ----------------------
@pytest.fixture
def in_memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

@pytest.fixture
def test_emails():
    now = datetime(2025, 6, 26, 10, 0, 0)
    return [
        Email(
            id='e1',
            thread_id='t1',
            from_address='hr@happyfox.com',
            to_address='you@example.com',
            subject='Assignment',
            snippet='We enjoyed meeting you...',
            received_at=now - timedelta(days=1),
            processed_at=None,
        ),
        Email(
            id='e2',
            thread_id='t2',
            from_address='spam@market.com',
            to_address='you@example.com',
            subject='Buy now!',
            snippet='Limited time offer...',
            received_at=now - timedelta(days=7),
            processed_at=None,
        )
    ]

@pytest.fixture
def sample_rule_any():
    return {
        "predicate": "any",
        "rules": [
            {"field": "From", "predicate": "contains", "value": "happyfox.com"},
            {"field": "Subject", "predicate": "contains", "value": "Assignment"}
        ],
        "actions": {
            "mark_as_read": True,
            "move_to": "Important"
        }
    }

# ----------------------------
# Integration-style test only
# ----------------------------
def test_integration_in_memory_rule_application(in_memory_session, test_emails, sample_rule_any):
    session = in_memory_session
    session.add_all(test_emails)
    session.commit()

    ruleset = sample_rule_any
    predicate_type = ruleset['predicate']
    rules = ruleset['rules']

    emails = session.query(Email).all()

    for email in emails:
        results = [evaluate_rule(email, r) for r in rules]
        matched = all(results) if predicate_type == 'all' else any(results)

        if matched:
            # Fake "marking as processed"
            email.processed_at = datetime(2025, 6, 26, 12, 0, 0)
            email.label = ruleset['actions']['move_to']

    session.commit()
    updated = session.query(Email).order_by(Email.id).all()

    # Email 1 should match rule and be marked as processed
    assert updated[0].processed_at is not None
    assert updated[0].label == 'Important'

    # Email 2 should remain unaffected
    assert updated[1].processed_at is None
    assert not hasattr(updated[1], 'label')
