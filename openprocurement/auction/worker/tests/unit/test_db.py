import errno
import pytest

from copy import deepcopy

from couchdb import Database
from couchdb.http import HTTPError

from openprocurement.auction.worker.auction import Auction

from openprocurement.auction.worker.tests.data.data import (
    tender_data, test_organization, lot_tender_data
)
from openprocurement.auction.utils import filter_amount


def test_get_auction_info_universal(universal_auction, logger):
    assert universal_auction.rounds_stages == []
    assert universal_auction.mapping == {}
    assert universal_auction.bidders_data == []
    universal_auction.get_auction_info(prepare=False)
    assert universal_auction.rounds_stages == [1, 4, 7]
    assert universal_auction.bidders_count == 2
    assert universal_auction.mapping == {
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

    assert set(['date', 'id', 'value']) == set(universal_auction.bidders_data[0].keys())
    assert len(universal_auction.bidders_data) == 2

    assert universal_auction.bidders_data[0]['value']['amount'] == 475000.0
    assert universal_auction.bidders_data[0]['id'] == 'd3ba84c66c9e4f34bfb33cc3c686f137'
    assert universal_auction.bidders_data[1]['value']['amount'] == 480000.0
    assert universal_auction.bidders_data[1]['id'] == '5675acc9232942e8940a034994ad883e'

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
    auction.prepare_auction_document()  # method is calling to cover line, on which check public_document existence is passing


def test_prepare_auction_document_multilot(multilot_auction, db, mocker):
    assert multilot_auction.db.get(multilot_auction.auction_doc_id) is None
    multilot_auction.prepare_auction_document()
    auction_document = multilot_auction.db.get(multilot_auction.auction_doc_id)
    assert auction_document is not None
    assert auction_document['_id'] == 'UA-11111_2222222222222222'
    assert auction_document['_rev'] == multilot_auction.auction_document['_rev']
    assert '_rev' in auction_document
    assert set(['tenderID', 'initial_bids', 'current_stage',
            'description', 'title', 'minimalStep', 'items',
            'stages', 'procurementMethodType', 'results',
            'value', 'test_auction_data', 'auction_type', '_rev',
            'mode', 'TENDERS_API_VERSION', '_id', 'procuringEntity', 'lot']) \
            == set(auction_document.keys()) == set(multilot_auction.auction_document.keys())


def test_prepare_auction_document_smd_no_auction_universal(universal_auction, db, mocker):
    mock_session_request = mocker.patch.object(universal_auction.session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = {'data': {}}
    universal_auction._auction_data['data']['submissionMethodDetails'] = 'quick(mode:no-auction)'
    res = universal_auction.prepare_auction_document()
    assert res == 0
    del universal_auction._auction_data['data']['submissionMethodDetails']


def test_prepare_auction_document_smd_fast_forward(auction, db, mocker):
    test_bids = deepcopy(tender_data['data']['bids'])

    for bid in test_bids:
        bid['tenderers'] = [test_organization]
    mock_session_request = mocker.patch.object(auction.session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = {
        'data': {
            'bids': test_bids
        }
    }
    auction._auction_data['data']['submissionMethodDetails'] = 'quick(mode:fast-forward)'
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
                'mode', 'TENDERS_API_VERSION', '_id', 'procuringEntity', 'endDate']) \
           == set(auction_document.keys()) == set(auction.auction_document.keys())
    del auction._auction_data['data']['submissionMethodDetails']


def test_prepare_auction_document_smd_fast_forward_multilot(multilot_auction, db, mocker):
    test_bids = deepcopy(tender_data['data']['bids'])

    for bid in test_bids:
        bid['tenderers'] = [test_organization]
    mock_session_request = mocker.patch.object(multilot_auction.session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = {
        'data': {
            'bids': test_bids
        }
    }
    multilot_auction._auction_data['data']['submissionMethodDetails'] = 'quick(mode:fast-forward)'
    multilot_auction.prepare_auction_document()
    auction_document = multilot_auction.db.get(multilot_auction.auction_doc_id)
    assert auction_document is not None
    assert auction_document['_id'] == 'UA-11111_2222222222222222'
    assert auction_document['_rev'] == multilot_auction.auction_document['_rev']
    assert '_rev' in auction_document
    assert set(['tenderID', 'initial_bids', 'current_stage',
                'description', 'title', 'minimalStep', 'items',
                'stages', 'procurementMethodType', 'results',
                'value', 'test_auction_data', 'auction_type', '_rev', 'lot',
                'mode', 'TENDERS_API_VERSION', '_id', 'procuringEntity', 'endDate']) \
           == set(auction_document.keys()) == set(multilot_auction.auction_document.keys())
    del multilot_auction._auction_data['data']['submissionMethodDetails']


def test_prepare_auction_document_false_no_debug(auction, db, mocker):
    auction.debug = False
    mock_set_auction_and_participation_urls = mocker.patch.object(Auction, 'set_auction_and_participation_urls', autospec=True)
    mock_session_request = mocker.patch.object(auction.session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = auction._auction_data
    auction.prepare_auction_document()
    assert mock_set_auction_and_participation_urls.called is True
    assert mock_set_auction_and_participation_urls.call_count == 1


def test_prepare_auction_document_smd_fast_forward_no_debug(auction, db, mocker):
    auction.debug = False

    test_bids = deepcopy(tender_data['data']['bids'])
    auction_period = tender_data['data']['auctionPeriod']
    for bid in test_bids:
        bid['tenderers'] = [test_organization]
    mock_session_request = mocker.patch.object(auction.session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = {'data': {
            'bids': test_bids,
            'auctionPeriod': auction_period,
            'submissionMethodDetails': 'quick(mode:fast-forward)'
        }
    }

    mock_set_auction_and_participation_urls = mocker.patch.object(Auction, 'set_auction_and_participation_urls', autospec=True)
    auction.prepare_auction_document()
    assert mock_set_auction_and_participation_urls.called is True
    assert mock_set_auction_and_participation_urls.call_count == 1


def test_prepare_public_document(auction, db):
    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages()
    res = auction.prepare_public_document()
    assert set(['value', 'initial_bids', 'tenderID', 'description', 'title', 'minimalStep',
                'items', '_rev', 'stages', 'procurementMethodType', 'results', 'auction_type',
                'mode', 'test_auction_data', 'current_stage', 'TENDERS_API_VERSION', 'endDate',
                '_id', 'procuringEntity']) == set(res.keys())

    auction_document = auction.db.get(auction.auction_doc_id)
    assert auction_document['_id'] == 'UA-11111'
    assert auction_document['_rev'] == res['_rev']


def test_prepare_public_document_features(features_auction, db, mocker):
    features_auction.prepare_auction_document()
    features_auction.auction_document['current_stage'] = 4
    mocked_map = mocker.patch("__builtin__.map", autospec=True)
    res = features_auction.prepare_public_document()
    assert mocked_map.called is True
    assert mocked_map.call_count == 3
    assert filter_amount, 'initial_bids' in mocked_map.call_args_list[1][0]
    assert filter_amount, 'stages' in mocked_map.call_args_list[2][0]
    assert filter_amount, 'results' in mocked_map.call_args_list[3][0]


def test_get_auction_document(auction, db, mocker, logger):
    auction.prepare_auction_document()
    pub_doc = auction.db.get(auction.auction_doc_id)
    del auction.auction_document
    res = auction.get_auction_document()
    assert res == pub_doc

    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert 'Rev error' not in log_strings
    auction.auction_document['_rev'] = 'wrong_rev'
    res = auction.get_auction_document()
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert res == pub_doc
    assert 'Rev error' in log_strings

    mock_db_get = mocker.patch.object(Database, 'get', autospec=True)
    mock_db_get.side_effect = [
        HTTPError('status code is >= 400'),
        Exception('unhandled error message'),
        Exception(errno.EPIPE, 'retryable error message'),
        res
    ]
    auction.get_auction_document()
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert log_strings[5] == 'Error while get document: status code is >= 400'
    assert log_strings[6] == 'Unhandled error: unhandled error message'
    assert log_strings[7] == "Error while get document: (32, 'retryable error message')"
    assert log_strings[8] == 'Get auction document {0} with rev {1}'.format(res['_id'], res['_rev'])

    assert mock_db_get.call_count == 4


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
        Exception(errno.EPIPE, 'retryable error message'),
        (u'UA-222222', u'test-revision'),
    ]
    auction.save_auction_document()
    log_strings = logger.log_capture_string.getvalue().split('\n')

    assert 'Saved auction document UA-11111 with rev' in log_strings[1]
    assert log_strings[3] == 'Error while save document: status code is >= 400'
    assert log_strings[5] == 'Unhandled error: unhandled error message'
    assert log_strings[7] == "Error while save document: (32, 'retryable error message')"
    assert log_strings[9] == 'Saved auction document UA-222222 with rev test-revision'

    assert mock_db_save.call_count == 4
