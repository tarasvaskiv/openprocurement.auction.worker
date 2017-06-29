from openprocurement.auction.worker.auction import Auction
from openprocurement.auction.worker.services import BiddersServiceMixin

from openprocurement.auction.worker.tests.base import (
    auction, db, logger
)


def test_get_round_number(auction, db):
    auction.prepare_auction_document()
    res = auction.get_round_number(auction.auction_document["current_stage"])
    assert res == 0
    res = auction.get_round_number(2)
    assert res == 1
    res = auction.get_round_number(6)
    assert res == 2
    res = auction.get_round_number(10)
    assert res == 3


def test_get_round_stages(auction):
    # auction.bidders_count == 0
    res = auction.get_round_stages(0)
    assert res == (0, 0)
    res = auction.get_round_stages(1)
    assert res == (1, 1)
    res = auction.get_round_stages(2)
    assert res == (2, 2)
    res = auction.get_round_stages(3)
    assert res == (3, 3)

    auction.get_auction_info()
    # auction.bidders_count == 2

    res = auction.get_round_stages(0)
    assert res == (-2, 0)
    res = auction.get_round_stages(1)
    assert res == (1, 3)
    res = auction.get_round_stages(2)
    assert res == (4, 6)
    res = auction.get_round_stages(3)
    assert res == (7, 9)


def test_prepare_auction_stages_fast_forward(auction, db):
    auction.prepare_auction_document()
    auction.get_auction_info()

    auction.prepare_auction_stages_fast_forward()
    assert auction.auction_document['auction_type'] == 'default'

    stages = auction.auction_document['stages']
    assert len(stages) == 11
    assert stages[0]['type'] == 'pause'
    assert stages[0]['stage'] == 'pause'
    assert stages[1]['type'] == 'bids'
    assert stages[2]['type'] == 'bids'
    assert stages[3]['type'] == 'pause'
    assert stages[3]['stage'] == 'pause'
    assert stages[4]['type'] == 'bids'
    assert stages[5]['type'] == 'bids'
    assert stages[6]['type'] == 'pause'
    assert stages[6]['stage'] == 'pause'
    assert stages[7]['type'] == 'bids'
    assert stages[8]['type'] == 'bids'
    assert stages[9]['type'] == 'pre_announcement'
    assert stages[10]['type'] == 'announcement'

    assert auction.auction_document['current_stage'] == 9
    results = auction.auction_document['results']
    assert len(results) == 2

    assert results[0]['amount'] == 480000.0
    assert results[0]['bidder_id'] == '5675acc9232942e8940a034994ad883e'

    assert results[1]['amount'] == 475000.0
    assert results[1]['bidder_id'] == 'd3ba84c66c9e4f34bfb33cc3c686f137'


def test_end_bids_stage(auction, db, mocker, logger):
    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages_fast_forward()
    auction.prepare_audit()

    auction.end_bids_stage()

    assert auction.current_stage == 9
    assert auction.current_round == 3

    mock_approve = mocker.patch.object(BiddersServiceMixin, 'approve_bids_information', autospec=True)
    mock_end_auction = mocker.patch.object(Auction, 'end_auction', autospec=True)
    mock_approve.return_value = True
    auction.end_bids_stage(9)

    assert mock_end_auction.call_count == 1
    assert mock_approve.call_count == 1


def test_update_future_bidding_orders(auction, db):

    test_bids = [
        {'amount': 480000.0,
         'bidder_id': u'5675acc9232942e8940a034994ad883e',
         'bidder_name': '2',
         'time': '2014-11-19T08:22:24.038426+00:00'},
        {'amount': 475000.0,
         'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137',
         'bidder_name': '1',
         'time': '2014-11-19T08:22:21.726234+00:00'}
    ]

    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages_fast_forward()
    auction.prepare_audit()

    auction.update_future_bidding_orders(test_bids)

    results = auction.auction_document["results"]

    assert len(results) == 2
    assert results[0]['amount'] == 480000.0
    assert results[0]['bidder_id'] == '5675acc9232942e8940a034994ad883e'
    assert results[1]['amount'] == 475000.0
    assert results[1]['bidder_id'] == 'd3ba84c66c9e4f34bfb33cc3c686f137'

    assert set(['ru', 'uk', 'en']) == set(results[0]['label'].keys())


def test_prepare_auction_stages(auction, db):
    auction.prepare_auction_document()
    auction.prepare_auction_stages()

    assert auction.auction_document['auction_type'] == 'default'
    assert auction.auction_document["initial_bids"] == []

    auction.get_auction_info()
    auction.prepare_auction_stages()
    initial_bids = auction.auction_document["initial_bids"]
    assert len(initial_bids) == 2
    assert initial_bids[0]['amount'] == '0'
    assert initial_bids[0]['bidder_id'] == 'd3ba84c66c9e4f34bfb33cc3c686f137'
    assert initial_bids[1]['amount'] == '0'
    assert initial_bids[1]['bidder_id'] == '5675acc9232942e8940a034994ad883e'

    stages = auction.auction_document['stages']
    assert len(stages) == 11
    assert stages[0]['type'] == 'pause'
    assert stages[0]['stage'] == 'pause'
    assert stages[1]['type'] == 'bids'
    assert stages[2]['type'] == 'bids'
    assert stages[3]['type'] == 'pause'
    assert stages[3]['stage'] == 'pause'
    assert stages[4]['type'] == 'bids'
    assert stages[5]['type'] == 'bids'
    assert stages[6]['type'] == 'pause'
    assert stages[6]['stage'] == 'pause'
    assert stages[7]['type'] == 'bids'
    assert stages[8]['type'] == 'bids'
    assert stages[9]['type'] == 'pre_announcement'
    assert stages[10]['type'] == 'announcement'

    assert auction.auction_document['current_stage'] == -1
    results = auction.auction_document['results']
    assert len(results) == 0


def test_next_stage(auction, db):
    auction.prepare_auction_document()
    assert auction.auction_document['current_stage'] == -1
    auction.next_stage()
    assert auction.auction_document['current_stage'] == 0
    auction.next_stage(switch_to_round=3)
    assert auction.auction_document['current_stage'] == 3
