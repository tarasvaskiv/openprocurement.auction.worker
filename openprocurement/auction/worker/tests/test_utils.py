import datetime
import pytest


def test_generate_request_id(auction):
    # Already set up in init method
    auction.request_id = 0
    auction.generate_request_id()
    assert auction.request_id is not None
    assert "auction-req-" in auction.request_id


@pytest.mark.parametrize("test_input,expected", [
    ('2014-01-01', (2014, 1, 1)),
    ('1999-10-31', (1999, 10, 31)),
    pytest.mark.xfail(('2017-25-128', (2017, 25, 128))),
])
def test_convert_date(auction, test_input, expected):
    converted = auction.convert_datetime(test_input)
    assert isinstance(converted, datetime.datetime)
    assert (converted.year, converted.month, converted.day) == expected
