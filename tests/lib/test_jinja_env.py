from datetime import timedelta

import pytest

from app.lib.date_utils import utcnow
from app.lib.jinja_env import stripspecial, timeago
from app.lib.translation import translation_context


@pytest.mark.parametrize(
    ('delta', 'output'),
    [
        (timedelta(seconds=-5), 'less than 1 second ago'),
        (timedelta(seconds=35), 'half a minute ago'),
        (timedelta(days=370), '1 year ago'),
    ],
)
def test_timeago(delta, output):
    with translation_context('en'):
        assert timeago(utcnow() - delta) == output


def test_timeago_never():
    with translation_context('en'):
        assert timeago(None) == 'Never'


@pytest.mark.parametrize(
    ('input', 'output'),
    [
        ('Hello World!', 'Hello World'),
        (', Hello', 'Hello'),
    ],
)
def test_stripspecial(input, output):
    assert stripspecial(input) == output
