import mock

from openprocurement.auction.worker.auction import Auction
from openprocurement.auction.worker.tests.base import auction, db


class AuctionTest(Auction):
    lot_id = False
    def __init__(self):
        pass


@mock.patch('openprocurement.auction.worker.auctions.multilot.get_auction_info')
@mock.patch('openprocurement.auction.worker.auctions.simple.get_auction_info')
def test_mock_get_auction_auction_info(mocked_simple_get_info, mocked_multi_get_info):
    auction = AuctionTest()

    auction.get_auction_info()
    mocked_simple_get_info.assert_called_with(auction, False)

    auction.lot_id = True

    auction.get_auction_info(prepare=True)
    mocked_multi_get_info.assert_called_with(auction, True)


# DBServiceTest

def test_get_auction_info_simple(auction):
    assert auction.rounds_stages == []
    auction.get_auction_info(prepare=False)
    assert auction.rounds_stages == [1, 4, 7]


def test_prepare_auction_document(auction, db):
    assert auction.db.get(auction.auction_doc_id) is None
    auction.prepare_auction_document()
    assert auction.db.get(auction.auction_doc_id) is not None


def test_prepare_public_document(auction, db):
    auction.prepare_auction_document()
    res = auction.prepare_public_document()
    assert res is not None


def test_get_auction_document(auction, db):
    auction.prepare_auction_document()
    pub_doc = auction.db.get(auction.auction_doc_id)
    res = auction.get_auction_document()
    assert res == pub_doc

def test_save_auction_document(auction, db):
    auction.prepare_auction_document()
    response = auction.save_auction_document()
    assert len(response) == 2
    assert response[0] == auction.auction_document['_id']
    assert response[1] == auction.auction_document['_rev']
