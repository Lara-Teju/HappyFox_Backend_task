#tests/test_predicates.py
import pytest
from datetime import datetime, timedelta

from process_rules import (
    predicate_contains,
    predicate_not_contains,
    predicate_equals,
    predicate_not_equals,
    predicate_less_than_date,
    predicate_greater_than_date,
)

def test_contains_true_and_false():
    # Positive matches
    assert predicate_contains("Hello World", "world")
    assert predicate_contains("ABC123", "bc1")
    # Negative match
    assert not predicate_contains("Hello", "bye")

def test_not_contains_true_and_false():
    assert predicate_not_contains("Hello", "bye")
    assert not predicate_not_contains("Hello World", "world")

def test_equals_and_not_equals():
    assert predicate_equals("Test", "test")
    assert not predicate_equals("Foo", "Bar")
    assert predicate_not_equals("Foo", "Bar")
    assert not predicate_not_equals("Same", "same")

def test_date_less_than_and_greater_than_days():
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    # less than: arrives within last 2 days
    assert predicate_less_than_date(yesterday, 2, unit='days', now=now)
    assert not predicate_less_than_date(two_days_ago, 2, unit='days', now=now)

    # greater than: arrives more than 1 day ago
    assert predicate_greater_than_date(two_days_ago, 1, unit='days', now=now)
    assert not predicate_greater_than_date(yesterday, 1, unit='days', now=now)


def test_date_less_and_greater_than_months_with_fixed_now():
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago  = now - timedelta(days=60)

    # “less than 2 months old” → arrived within the last ~60 days
    assert predicate_less_than_date(thirty_days_ago, 2, unit='months', now=now)
    assert not predicate_less_than_date(sixty_days_ago, 2, unit='months', now=now)

    # “greater than 1 month old” → arrived more than ~30 days ago
    assert predicate_greater_than_date(sixty_days_ago, 1, unit='months', now=now)
    assert not predicate_greater_than_date(thirty_days_ago, 1, unit='months', now=now)


def test_edge_cases_none_and_empty():
    # None input should be treated as empty string
    assert not predicate_contains(None, "any")
    assert predicate_not_contains(None, "any")
    # Empty string equals empty
    assert predicate_equals("", "")
    assert not predicate_not_equals("", "")
