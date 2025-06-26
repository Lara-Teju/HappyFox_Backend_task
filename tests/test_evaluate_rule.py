#tests/test_evaluate_rule.py
import pytest
from collections import namedtuple
from datetime import datetime, timedelta

from process_rules import evaluate_rule

# Minimal Email-like object for testing
Email = namedtuple(
    'Email',
    ['from_address', 'to_address', 'subject', 'snippet', 'received_at', 'id', 'thread_id', 'processed_at']
)

def make_email(**kwargs):
    defaults = {
        'from_address': 'alice@example.com',
        'to_address': 'bob@example.com',
        'subject': 'Interview Invitation',
        'snippet': 'Dear candidate, ...',
        'received_at': datetime.now(),
        'id': 'msg1',
        'thread_id': 'thr1',
        'processed_at': None
    }
    defaults.update(kwargs)
    return Email(**defaults)

def test_evaluate_from_contains():
    email = make_email(from_address='hr@happyfox.com')
    rule = {'field': 'From', 'predicate': 'contains', 'value': 'happyfox.com'}
    assert evaluate_rule(email, rule)

def test_evaluate_to_equals():
    email = make_email(to_address='candidate@domain.com')
    rule = {'field': 'To', 'predicate': 'equals', 'value': 'candidate@domain.com'}
    assert evaluate_rule(email, rule)

def test_evaluate_subject_not_equals():
    email = make_email(subject='Weekly Report')
    rule = {'field': 'Subject', 'predicate': 'does not equal', 'value': 'Monthly Report'}
    assert evaluate_rule(email, rule)

def test_evaluate_snippet_contains():
    email = make_email(snippet='Please review the attached document')
    rule = {'field': 'Message', 'predicate': 'contains', 'value': 'attached document'}
    assert evaluate_rule(email, rule)

def test_evaluate_received_date_predicates():
    now = datetime.now()
    two_days_ago = now - timedelta(days=2)
    email = make_email(received_at=two_days_ago)

    rule_less = {'field': 'Received', 'predicate': 'less than', 'value': 3, 'unit': 'days'}
    rule_greater = {'field': 'Received', 'predicate': 'greater than', 'value': 1, 'unit': 'days'}

    assert evaluate_rule(email, rule_less)     # older than 3 days? false for 2 days old
    assert evaluate_rule(email, rule_greater)  # newer than 1 day? true for 2 days old

def test_unsupported_field_and_predicate():
    email = make_email()
    with pytest.raises(ValueError):
        evaluate_rule(email, {'field': 'Unknown', 'predicate': 'contains', 'value': 'x'})
    with pytest.raises(ValueError):
        evaluate_rule(email, {'field': 'From', 'predicate': 'invalid', 'value': 'x'})





