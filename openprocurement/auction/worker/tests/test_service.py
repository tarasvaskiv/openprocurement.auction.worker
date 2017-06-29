import pytest

from copy import deepcopy
from couchdb import Database
from couchdb.http import HTTPError
from requests import Session

from openprocurement.auction.worker.auction import Auction
from openprocurement.auction.worker.services import BiddersServiceMixin
from openprocurement.auction.worker.tests.base import (
    auction, db, logger, scheduler, tender_data, test_organization
)

# DBServiceTest


def test_get_auction_info_simple(auction, logger):
    assert auction.rounds_stages == []
    assert auction.mapping == {}
    assert auction.bidders_data == []
    auction.get_auction_info(prepare=False)
    assert auction.rounds_stages == [1, 4, 7]
    assert auction.bidders_count == 2
    assert auction.mapping == {
        u'5675acc9232942e8940a034994ad883e': '2',
        u'd3ba84c66c9e4f34bfb33cc3c686f137': '1'
    }

    # auction.bidders_data == [
    #     {'date': u'2014-11-19T08:22:21.726234+00:00',
    #      'id': u'd3ba84c66c9e4f34bfb33cc3c686f137',
    #      'value': {u'amount': 475000.0,
    #                u'currency': None,
    #                u'valueAddedTaxIncluded': True}},
    #     {'date': u'2014-11-19T08:22:24.038426+00:00',
    #      'id': u'5675acc9232942e8940a034994ad883e',
    #      'value': {u'amount': 480000.0,
    #                u'currency': None,
    #                u'valueAddedTaxIncluded': True}}
    # ]

    assert set(['date', 'id', 'value']) == set(auction.bidders_data[0].keys())
    assert len(auction.bidders_data) == 2

    assert auction.bidders_data[0]['value']['amount'] == 475000.0
    assert auction.bidders_data[0]['id'] == 'd3ba84c66c9e4f34bfb33cc3c686f137'
    assert auction.bidders_data[1]['value']['amount'] == 480000.0
    assert auction.bidders_data[1]['id'] == '5675acc9232942e8940a034994ad883e'

    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert log_strings[0] == 'Bidders count: 2'


def test_prepare_auction_document(auction, db, mocker):
    assert auction.db.get(auction.auction_doc_id) is None
    auction.prepare_auction_document()
    auction_document = auction.db.get(auction.auction_doc_id)
    assert auction_document is not None
    assert auction_document['_id'] == 'UA-11111'
    assert auction_document['_rev'] == auction.auction_document['_rev']
    assert '_rev' in auction_document
    assert set(['tenderID', 'initial_bids', 'current_stage',
            'description', 'title', 'minimalStep', 'items',
            'stages', 'procurementMethodType', 'results',
            'value', 'test_auction_data', 'auction_type', '_rev',
            'mode', 'TENDERS_API_VERSION', '_id', 'procuringEntity']) \
            == set(auction_document.keys()) == set(auction.auction_document.keys())


def test_prepare_public_document(auction, db):
    auction.prepare_auction_document()
    res = auction.prepare_public_document()
    assert res is not None


def test_get_auction_document(auction, db, mocker, logger):
    auction.prepare_auction_document()
    pub_doc = auction.db.get(auction.auction_doc_id)
    res = auction.get_auction_document()
    assert res == pub_doc

    mock_db_get = mocker.patch.object(Database, 'get', autospec=True)
    mock_db_get.side_effect = [
        HTTPError('status code is >= 400'),
        Exception('unhandled error message'),
        res
    ]
    auction.get_auction_document()
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert log_strings[3] == 'Error while get document: status code is >= 400'
    assert log_strings[4] == 'Unhandled error: unhandled error message'
    assert log_strings[5] == 'Get auction document {0} with rev {1}'.format(res['_id'], res['_rev'])


def test_save_auction_document(auction, db, mocker, logger):
    auction.prepare_auction_document()
    response = auction.save_auction_document()
    assert len(response) == 2
    assert response[0] == auction.auction_document['_id']
    assert response[1] == auction.auction_document['_rev']

    mock_db_save = mocker.patch.object(Database, 'save', autospec=True)
    mock_db_save.side_effect = [
        HTTPError('status code is >= 400'),
        Exception('unhandled error message'),
        (u'UA-222222', u'test-revision'),
    ]
    auction.save_auction_document()
    log_strings = logger.log_capture_string.getvalue().split('\n')

    assert 'Saved auction document UA-11111 with rev' in log_strings[1]
    assert log_strings[3] == 'Error while save document: status code is >= 400'
    assert log_strings[5] == 'Unhandled error: unhandled error message'
    assert log_strings[7] == 'Saved auction document UA-222222 with rev test-revision'

    assert mock_db_save.call_count == 3

# StagesServiceTest


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

# AuditServiceTest


def test_prepare_audit(auction, db):
    auction.prepare_audit()

    # auction.audit == {'id': u'UA-11111',
    #                   'tenderId': u'UA-11111',
    #                   'tender_id': u'UA-11111',
    #                   'timeline': {'auction_start': {'initial_bids': []},
    #                                'round_1': {},
    #                                'round_2': {},
    #                                'round_3': {}}}

    assert set(['id', 'tenderId', 'tender_id', 'timeline']) == set(auction.audit.keys())
    assert auction.audit['id'] == 'UA-11111'
    assert auction.audit['tenderId'] == 'UA-11111'
    assert auction.audit['tender_id'] == 'UA-11111'
    assert len(auction.audit['timeline']) == 4
    assert 'auction_start' in auction.audit['timeline']
    for i in range(1, len(auction.audit['timeline'])):
        assert 'round_{0}'.format(i) in auction.audit['timeline'].keys()


def test_approve_audit_info_on_bid_stage(auction, db):
    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages_fast_forward()

    auction.current_stage = 7
    auction.current_round = auction.get_round_number(
        auction.auction_document["current_stage"]
    )
    auction.prepare_audit()
    auction.auction_document["stages"][auction.current_stage]['changed'] = True

    auction.approve_audit_info_on_bid_stage()

    # auction.audit == {'id': u'UA-11111',
    #                   'tenderId': u'UA-11111',
    #                   'tender_id': u'UA-11111',
    #                   'timeline': {'auction_start': {'initial_bids': []},
    #                                'round_1': {},
    #                                'round_2': {},
    #                                'round_3': {'turn_1': {'bidder': u'5675acc9232942e8940a034994ad883e',
    #                                                       'time': '2017-06-23T13:18:49.764132+03:00'}}}}

    assert set(['id', 'tenderId', 'tender_id', 'timeline']) == set(auction.audit.keys())
    assert auction.audit['id'] == 'UA-11111'
    assert auction.audit['tenderId'] == 'UA-11111'
    assert auction.audit['tender_id'] == 'UA-11111'
    assert len(auction.audit['timeline']) == 4
    assert 'auction_start' in auction.audit['timeline']
    for i in range(1, len(auction.audit['timeline'])):
        assert 'round_{0}'.format(i) in auction.audit['timeline'].keys()
    assert 'turn_1' in auction.audit['timeline']['round_3']
    assert auction.audit['timeline']['round_3']['turn_1']['bidder'] == '5675acc9232942e8940a034994ad883e'


def test_approve_audit_info_on_announcement(auction, db):
    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages_fast_forward()

    auction.prepare_audit()

    auction.approve_audit_info_on_announcement()

    # {'id': u'UA-11111',
    #  'tenderId': u'UA-11111',
    #  'tender_id': u'UA-11111',
    #  'timeline': {'auction_start': {'initial_bids': []},
    #               'results': {'bids': [{'amount': 480000.0,
    #                                     'bidder': u'5675acc9232942e8940a034994ad883e',
    #                                     'time': '2014-11-19T08:22:24.038426+00:00'},
    #                                    {'amount': 475000.0,
    #                                     'bidder': u'd3ba84c66c9e4f34bfb33cc3c686f137',
    #                                     'time': '2014-11-19T08:22:21.726234+00:00'}],
    #                           'time': '2017-06-23T13:28:24.676818+03:00'},
    #               'round_1': {},
    #               'round_2': {},
    #               'round_3': {}}}

    assert set(['id', 'tenderId', 'tender_id', 'timeline']) == set(auction.audit.keys())
    assert auction.audit['id'] == 'UA-11111'
    assert auction.audit['tenderId'] == 'UA-11111'
    assert auction.audit['tender_id'] == 'UA-11111'
    assert len(auction.audit['timeline']) == 5
    assert 'auction_start' in auction.audit['timeline']
    assert 'results' in auction.audit['timeline']
    for i in range(2, len(auction.audit['timeline'])):
        assert 'round_{0}'.format(i-1) in auction.audit['timeline'].keys()
    results = auction.audit['timeline']['results']
    assert len(results['bids']) == 2

    assert results['bids'][0]['amount'] == 480000.0
    assert results['bids'][0]['bidder'] == '5675acc9232942e8940a034994ad883e'

    assert results['bids'][1]['amount'] == 475000.0
    assert results['bids'][1]['bidder'] == 'd3ba84c66c9e4f34bfb33cc3c686f137'


def test_upload_audit_file_without_document_service(auction, db, logger, mocker):
    from requests import Session as RequestsSession
    auction.session_ds = RequestsSession()
    auction.prepare_auction_document()
    auction.get_auction_info()

    res = auction.upload_audit_file_with_document_service()
    assert res is None

    mock_session_request = mocker.patch.object(Session, 'request', autospec=True)

    mock_session_request.return_value.json.return_value = {
        'data': {
            'id': 'UA-11111'
        }
    }

    res = auction.upload_audit_file_with_document_service('UA-11111')
    assert res == 'UA-11111'

    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert log_strings[3] == 'Audit log not approved.'


def test_upload_audit_file_with_document_service(auction, db, logger):
    auction.prepare_auction_document()
    auction.get_auction_info()

    res = auction.upload_audit_file_without_document_service()
    assert res is None
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert log_strings[3] == 'Audit log not approved.'


# RequestIDService


def test_generate_request_id(auction):
    # Already set up in init method
    auction.request_id = 0
    auction.generate_request_id()
    assert auction.request_id is not None
    assert "auction-req-" in auction.request_id


# DateTimeServiceMixin


def test_convert_date(auction):
    converted = auction.convert_datetime('2014-01-01')
    assert converted is not None

# BiddersServiceMixin


def test_add_bid(auction, db):
    test_bid = tender_data['data']['bids'][0]
    auction.prepare_auction_document()
    auction.get_auction_info()
    assert auction._bids_data == {}
    auction.add_bid(1, test_bid)
    assert auction._bids_data is not None
    assert auction._bids_data.keys() == [1]
    round_num = 101
    auction.add_bid(round_num, test_bid)
    assert auction._bids_data.keys() == [1, 101]


def test_filter_bids_keys(auction, db):
    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages_fast_forward()
    bids = auction.auction_document['results']
    result = auction.filter_bids_keys(bids)
    assert result is not None
    bids[0]['test'] = 'test'
    result = auction.filter_bids_keys(bids)
    assert 'test' not in result[0]


def test_set_auction_and_participation_urls(auction, mocker, logger):
    mock_session_request = mocker.patch.object(auction.session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = {
        'data': {
            'id': 'UA-11111'
        }
    }
    mock_session_request.return_value.ok.return_value = True
    auction.set_auction_and_participation_urls()
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert log_strings[0] == "Set auction and participation urls for tender {}".format(auction.tender_id)
    assert 'participationUrl' in log_strings[1]
    assert 'auctionUrl' in log_strings[1]


# TODO
def test_approve_bids_information():
    pass


# PostAuctionServiceMixin: TODO

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


# WorkerTest

@pytest.mark.worker
def test_worker(auction, db, scheduler, logger):

    auction.prepare_auction_document()

    scheduler.start()
    auction.schedule_auction()
    auction.wait_to_end()
    scheduler.shutdown()

    log_strings = logger.log_capture_string.getvalue().split('\n')

    """
    ['Bidders count: 2',
     'Saved auction document UA-11111 with rev 1-e505e42c3fc2b1e5259fde558d74a351',
     'Scheduler started',
     'Get auction document UA-11111 with rev 1-e505e42c3fc2b1e5259fde558d74a351',
     'Get _auction_data from auction_document',
     'Bidders count: 2',
     'Saved auction document UA-11111 with rev 2-fade9aa2875aace5b38d4d8b29d3b147',
     'Added job "Start of Auction" to job store "default"',
     'Added job "End of Pause Stage: [0 -> 1]" to job store "default"',
     'Added job "End of Bids Stage: [1 -> 2]" to job store "default"',
     'Added job "End of Bids Stage: [2 -> 3]" to job store "default"',
     'Added job "End of Pause Stage: [3 -> 4]" to job store "default"',
     'Added job "End of Bids Stage: [4 -> 5]" to job store "default"',
     'Added job "End of Bids Stage: [5 -> 6]" to job store "default"',
     'Added job "End of Pause Stage: [6 -> 7]" to job store "default"',
     'Added job "End of Bids Stage: [7 -> 8]" to job store "default"',
     'Added job "End of Bids Stage: [8 -> 9]" to job store "default"',
     'Prepare server ...',
     'Start server on 127.0.0.1:9010',
     'Server mapping: UA-11111 -> http://127.0.0.1:9010/',
     'Removed job Start of Auction',
     'Running job "Start of Auction (trigger: date[2017-06-26 17:30:06 EEST], next run at: 2017-06-26 17:30:06 EEST)" (scheduled at 2017-06-26 17:30:06.894373+03:00)',
     '---------------- Start auction ----------------',
     'Bidders count: 2',
     'Get auction document UA-11111 with rev 2-fade9aa2875aace5b38d4d8b29d3b147',
     'Saved auction document UA-11111 with rev 3-7912a4424a3f360a88d6f2a9b432a4bc',
     'Job "Start of Auction (trigger: date[2017-06-26 17:30:06 EEST], next run at: 2017-06-26 17:30:06 EEST)" executed successfully',
     'Removed job End of Pause Stage: [0 -> 1]',
     'Running job "End of Pause Stage: [0 -> 1] (trigger: date[2017-06-26 17:35:06 EEST], next run at: 2017-06-26 17:35:06 EEST)" (scheduled at 2017-06-26 17:35:06.894373+03:00)',
     '---------------- End First Pause ----------------',
     'Get auction document UA-11111 with rev 3-7912a4424a3f360a88d6f2a9b432a4bc',
     'Saved auction document UA-11111 with rev 4-d06402c4a9fb382d031d59b71bb69dc0',
     'Job "End of Pause Stage: [0 -> 1] (trigger: date[2017-06-26 17:35:06 EEST], next run at: 2017-06-26 17:35:06 EEST)" executed successfully',
     'Removed job End of Bids Stage: [1 -> 2]',
     'Running job "End of Bids Stage: [1 -> 2] (trigger: date[2017-06-26 17:37:06 EEST], next run at: 2017-06-26 17:37:06 EEST)" (scheduled at 2017-06-26 17:37:06.894373+03:00)',
     'Get auction document UA-11111 with rev 4-d06402c4a9fb382d031d59b71bb69dc0',
     '---------------- End Bids Stage ----------------',
     '---------------- Start stage 2 ----------------',
     'Saved auction document UA-11111 with rev 5-2ae211f857991f66a69ccd1fc031c890',
     'Job "End of Bids Stage: [1 -> 2] (trigger: date[2017-06-26 17:37:06 EEST], next run at: 2017-06-26 17:37:06 EEST)" executed successfully',
     'Removed job End of Bids Stage: [2 -> 3]',
     'Running job "End of Bids Stage: [2 -> 3] (trigger: date[2017-06-26 17:39:06 EEST], next run at: 2017-06-26 17:39:06 EEST)" (scheduled at 2017-06-26 17:39:06.894373+03:00)',
     'Get auction document UA-11111 with rev 5-2ae211f857991f66a69ccd1fc031c890',
     '---------------- End Bids Stage ----------------',
     '---------------- Start stage 3 ----------------',
     'Saved auction document UA-11111 with rev 6-37b1f136a422b103ac2d7702b6e26033',
     'Job "End of Bids Stage: [2 -> 3] (trigger: date[2017-06-26 17:39:06 EEST], next run at: 2017-06-26 17:39:06 EEST)" executed successfully',
     'Removed job End of Pause Stage: [3 -> 4]',
     'Running job "End of Pause Stage: [3 -> 4] (trigger: date[2017-06-26 17:41:06 EEST], next run at: 2017-06-26 17:41:06 EEST)" (scheduled at 2017-06-26 17:41:06.894373+03:00)',
     'Get auction document UA-11111 with rev 6-37b1f136a422b103ac2d7702b6e26033',
     'Saved auction document UA-11111 with rev 7-58a0796ed6aa5d950f8d38315ba44b5e',
     '---------------- Start stage 4 ----------------',
     'Job "End of Pause Stage: [3 -> 4] (trigger: date[2017-06-26 17:41:06 EEST], next run at: 2017-06-26 17:41:06 EEST)" executed successfully',
     'Removed job End of Bids Stage: [4 -> 5]',
     'Running job "End of Bids Stage: [4 -> 5] (trigger: date[2017-06-26 17:43:06 EEST], next run at: 2017-06-26 17:43:06 EEST)" (scheduled at 2017-06-26 17:43:06.894373+03:00)',
     'Get auction document UA-11111 with rev 7-58a0796ed6aa5d950f8d38315ba44b5e',
     '---------------- End Bids Stage ----------------',
     '---------------- Start stage 5 ----------------',
     'Saved auction document UA-11111 with rev 8-c61c7e71a3b2d9a0ecc4b1b3720d855a',
     'Job "End of Bids Stage: [4 -> 5] (trigger: date[2017-06-26 17:43:06 EEST], next run at: 2017-06-26 17:43:06 EEST)" executed successfully',
     'Removed job End of Bids Stage: [5 -> 6]',
     'Running job "End of Bids Stage: [5 -> 6] (trigger: date[2017-06-26 17:45:06 EEST], next run at: 2017-06-26 17:45:06 EEST)" (scheduled at 2017-06-26 17:45:06.894373+03:00)',
     'Get auction document UA-11111 with rev 8-c61c7e71a3b2d9a0ecc4b1b3720d855a',
     '---------------- End Bids Stage ----------------',
     '---------------- Start stage 6 ----------------',
     'Saved auction document UA-11111 with rev 9-fb48f13ccc2d53b9575344a7d2bb9ab0',
     'Job "End of Bids Stage: [5 -> 6] (trigger: date[2017-06-26 17:45:06 EEST], next run at: 2017-06-26 17:45:06 EEST)" executed successfully',
     'Removed job End of Pause Stage: [6 -> 7]',
     'Running job "End of Pause Stage: [6 -> 7] (trigger: date[2017-06-26 17:47:06 EEST], next run at: 2017-06-26 17:47:06 EEST)" (scheduled at 2017-06-26 17:47:06.894373+03:00)',
     'Get auction document UA-11111 with rev 9-fb48f13ccc2d53b9575344a7d2bb9ab0',
     'Saved auction document UA-11111 with rev 10-2ecec75a5bed9af33fe8890ffee7b467',
     '---------------- Start stage 7 ----------------',
     'Job "End of Pause Stage: [6 -> 7] (trigger: date[2017-06-26 17:47:06 EEST], next run at: 2017-06-26 17:47:06 EEST)" executed successfully',
     'Removed job End of Bids Stage: [7 -> 8]',
     'Running job "End of Bids Stage: [7 -> 8] (trigger: date[2017-06-26 17:49:06 EEST], next run at: 2017-06-26 17:49:06 EEST)" (scheduled at 2017-06-26 17:49:06.894373+03:00)',
     'Get auction document UA-11111 with rev 10-2ecec75a5bed9af33fe8890ffee7b467',
     '---------------- End Bids Stage ----------------',
     '---------------- Start stage 8 ----------------',
     'Saved auction document UA-11111 with rev 11-ebeeacc65d7a10c376d0213bfad05ea1',
     'Job "End of Bids Stage: [7 -> 8] (trigger: date[2017-06-26 17:49:06 EEST], next run at: 2017-06-26 17:49:06 EEST)" executed successfully',
     'Removed job End of Bids Stage: [8 -> 9]',
     'Running job "End of Bids Stage: [8 -> 9] (trigger: date[2017-06-26 17:51:06 EEST], next run at: 2017-06-26 17:51:06 EEST)" (scheduled at 2017-06-26 17:51:06.894373+03:00)',
     'Get auction document UA-11111 with rev 11-ebeeacc65d7a10c376d0213bfad05ea1',
     '---------------- End Bids Stage ----------------',
     '---------------- Start stage 9 ----------------',
     'Saved auction document UA-11111 with rev 12-d6e1adc65450d9963d71a2479be72248',
     '---------------- End auction ----------------',
     'Audit data: ',
     ' id: UA-11111',
     'tenderId: UA-11111',
     'tender_id: UA-11111',
     'timeline:',
     '  auction_start:',
     '    initial_bids:',
     "    - {amount: 475000.0, bidder: d3ba84c66c9e4f34bfb33cc3c686f137, date: '2014-11-19T08:22:21.726234+00:00'}",
     "    - {amount: 480000.0, bidder: 5675acc9232942e8940a034994ad883e, date: '2014-11-19T08:22:24.038426+00:00'}",
     "    time: '2017-06-26T17:30:06.899074+03:00'",
     '  results:',
     '    bids:',
     "    - {amount: 480000.0, bidder: 5675acc9232942e8940a034994ad883e, time: '2014-11-19T08:22:24.038426+00:00'}",
     "    - {amount: 475000.0, bidder: d3ba84c66c9e4f34bfb33cc3c686f137, time: '2014-11-19T08:22:21.726234+00:00'}",
     "    time: '2017-06-26T17:51:07.034734+03:00'",
     '  round_1:',
     "    turn_1: {bidder: 5675acc9232942e8940a034994ad883e, time: '2017-06-26T17:37:06.910031+03:00'}",
     "    turn_2: {bidder: d3ba84c66c9e4f34bfb33cc3c686f137, time: '2017-06-26T17:39:06.909795+03:00'}",
     '  round_2:',
     "    turn_1: {bidder: 5675acc9232942e8940a034994ad883e, time: '2017-06-26T17:43:06.913207+03:00'}",
     "    turn_2: {bidder: d3ba84c66c9e4f34bfb33cc3c686f137, time: '2017-06-26T17:45:06.910214+03:00'}",
     '  round_3:',
     "    turn_1: {bidder: 5675acc9232942e8940a034994ad883e, time: '2017-06-26T17:49:06.916444+03:00'}",
     "    turn_2: {bidder: d3ba84c66c9e4f34bfb33cc3c686f137, time: '2017-06-26T17:51:06.906981+03:00'}",
     '',
     'Saved auction document UA-11111 with rev 13-4fc9e12e34d848faebfbf39ed37ae65e',
     'Job "End of Bids Stage: [8 -> 9] (trigger: date[2017-06-26 17:51:06 EEST], next run at: 2017-06-26 17:51:06 EEST)" executed successfully',
     'Stop auction worker',
     'Scheduler has been shut down',
     '']
    """
