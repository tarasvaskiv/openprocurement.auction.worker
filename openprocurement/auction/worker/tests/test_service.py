import mock

from openprocurement.auction.worker.auction import Auction
from openprocurement.auction.worker.tests.base import auction


class AuctionTest(Auction):
    lot_id = False
    def __init__(self):
        pass


def test_simple():
    assert 2 == 2


@mock.patch('openprocurement.auction.worker.auctions.multilot.get_auction_info')
@mock.patch('openprocurement.auction.worker.auctions.simple.get_auction_info')
def test_mock_get_auction_auction_info(mocked_simple_get_info, mocked_multi_get_info):
    auction = AuctionTest()

    auction.get_auction_info()
    mocked_simple_get_info.assert_called_with(auction, False)

    auction.lot_id = True

    auction.get_auction_info(prepare=True)
    mocked_multi_get_info.assert_called_with(auction, True)


def test_fixture_get_auction_info(auction):

    assert auction.rounds_stages == []

    auction.get_auction_info(prepare=False)

    assert auction.rounds_stages == [1, 4, 7]

