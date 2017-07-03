from openprocurement.auction.worker.tests.base import (
    auction
)


def test_generate_request_id(auction):
    # Already set up in init method
    auction.request_id = 0
    auction.generate_request_id()
    assert auction.request_id is not None
    assert "auction-req-" in auction.request_id


def test_convert_date(auction):
    converted = auction.convert_datetime('2014-01-01')
    assert converted is not None
