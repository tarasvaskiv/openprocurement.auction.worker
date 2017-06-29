from couchdb import Database
from couchdb.http import HTTPError

from openprocurement.auction.worker.tests.base import (
    auction, logger, db
)


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
