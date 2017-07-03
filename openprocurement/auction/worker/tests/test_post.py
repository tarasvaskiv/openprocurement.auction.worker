from copy import deepcopy
from requests import Session

from openprocurement.auction.worker.tests.base import (
    auction, db, logger, scheduler, tender_data, test_organization
)


def test_post_announce(auction, db, logger, mocker):
    test_bids = deepcopy(tender_data['data']['bids'])

    for bid in test_bids:
        bid['tenderers'] = test_organization
    mock_session_request = mocker.patch.object(Session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = {
        'data': {
            'bids': test_bids
        }
    }
    auction.prepare_auction_document()
    auction.post_announce()

    log_strings = logger.log_capture_string.getvalue().split('\n')

    """
    ['Bidders count: 2',
     'Saved auction document UA-11111 with rev 1-50b6586b0769fa09fd95039ac0a73284',
     'Get auction document UA-11111 with rev 1-50b6586b0769fa09fd95039ac0a73284',
     'Saved auction document UA-11111 with rev 2-20ae6bf47e139e274492a09dc61c204d',
     '']
    """

    assert 'Get auction document UA-11111 with rev 1-' in log_strings[2]
    assert 'Saved auction document UA-11111 with rev 2-' in log_strings[3]


def test_put_auction_data(auction, db, mocker, logger):

    test_bids = deepcopy(tender_data['data']['bids'])

    for bid in test_bids:
        bid['tenderers'] = [test_organization]

    mock_session_request = mocker.patch.object(Session, 'request', autospec=True)
    mock_session_request.return_value.json.side_effect = [
        {'data': {'id': 'UA-11111'}},
        {'data': {'bids': test_bids}},
    ]

    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages_fast_forward()
    auction.prepare_audit()

    response = auction.put_auction_data()
    assert response is True
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert "Auctions results not approved" not in log_strings

    mock_session_request.return_value.json.side_effect = [
        {'data': {'id': 'UA-11111'}},
        False,
    ]

    response = auction.put_auction_data()
    assert response is None
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert "Auctions results not approved" in log_strings
