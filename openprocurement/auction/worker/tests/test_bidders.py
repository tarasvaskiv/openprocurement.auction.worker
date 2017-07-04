from openprocurement.auction.worker.tests.base import (
    auction, multilot_auction, features_auction, db, logger,
    tender_data
)


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

    # [{'amount': 480000.0,
    #   'bidder_id': u'5675acc9232942e8940a034994ad883e',
    #   'label': {'en': 'Bidder #2',
    #             'ru': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd1\x82\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x962',
    #             'uk': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x962'},
    #   'test': 'test',
    #   'time': '2014-11-19T08:22:24.038426+00:00'},
    #  {'amount': 475000.0,
    #   'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137',
    #   'label': {'en': 'Bidder #1',
    #             'ru': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd1\x82\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x961',
    #             'uk': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x961'},
    #   'time': '2014-11-19T08:22:21.726234+00:00'}]

    result = auction.filter_bids_keys(bids)
    assert result is not None
    bids[0]['test'] = 'test'
    result = auction.filter_bids_keys(bids)

    # [{'amount': 480000.0,
    #   'bidder_id': u'5675acc9232942e8940a034994ad883e',
    #   'bidder_name': '2',
    #   'time': '2014-11-19T08:22:24.038426+00:00'},
    #  {'amount': 475000.0,
    #   'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137',
    #   'bidder_name': '1',
    #   'time': '2014-11-19T08:22:21.726234+00:00'}]

    assert 'test' not in result[0]


def test_filter_bids_keys_features(features_auction, db):
    features_auction.prepare_auction_document()
    features_auction.get_auction_info()
    features_auction.prepare_auction_stages_fast_forward()
    bids = features_auction.auction_document['results']
    for bid in bids:
        assert 'coeficient', 'amount_features' in bid.keys()

    # [{'amount': 475000.0,
    #   'amount_features': '1454662679640670217500/3422735716801577',
    #   'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137',
    #   'coeficient': '34227357168015770/30624477466119373',
    #   'label': {'en': 'Bidder #1',
    #             'ru': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd1\x82\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x961',
    #             'uk': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x961'},
    #   'test': 'test',
    #   'time': '2014-11-19T08:22:21.726234+00:00'},
    #  {'amount': 480000.0,
    #   'amount_features': '57420895248973824375/140737488355328',
    #   'bidder_id': u'5675acc9232942e8940a034994ad883e',
    #   'coeficient': '36028797018963968/30624477466119373',
    #   'label': {'en': 'Bidder #2',
    #             'ru': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd1\x82\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x962',
    #             'uk': '\xd0\xa3\xd1\x87\xd0\xb0\xd1\x81\xd0\xbd\xd0\xb8\xd0\xba \xe2\x84\x962'},
    #   'time': '2014-11-19T08:22:24.038426+00:00'}]

    result = features_auction.filter_bids_keys(bids)
    assert result is not None
    bids[0]['test'] = 'test'
    result = features_auction.filter_bids_keys(bids)
    for item in result:
        assert 'coeficient', 'amount_features' in item.keys()

    # [{'amount': 475000.0,
    #   'amount_features': '1454662679640670217500/3422735716801577',
    #   'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137',
    #   'bidder_name': '1',
    #   'coeficient': '34227357168015770/30624477466119373',
    #   'time': '2014-11-19T08:22:21.726234+00:00'},
    #  {'amount': 480000.0,
    #   'amount_features': '57420895248973824375/140737488355328',
    #   'bidder_id': u'5675acc9232942e8940a034994ad883e',
    #   'bidder_name': '2',
    #   'coeficient': '36028797018963968/30624477466119373',
    #   'time': '2014-11-19T08:22:24.038426+00:00'}]

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


def test_set_auction_and_participation_urls_multilot(multilot_auction, mocker, logger):
    mock_session_request = mocker.patch.object(multilot_auction.session, 'request', autospec=True)
    mock_session_request.return_value.json.return_value = {
        'data': {
            'id': 'UA-11111'
        }
    }
    mock_session_request.return_value.ok.return_value = True
    multilot_auction.set_auction_and_participation_urls()
    log_strings = logger.log_capture_string.getvalue().split('\n')
    assert log_strings[0] == "Set auction and participation urls for tender {}".format(multilot_auction.tender_id)
    assert 'participationUrl' in log_strings[1]
    assert 'auctionUrl' in log_strings[1]


def test_approve_bids_information(auction, db, logger):

    test_bids = [
        {'amount': -1.0,
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

    auction.current_stage = 5
    res = auction.approve_bids_information()
    assert res is False
    assert auction.auction_document["stages"][5].get('changed') is None

    # auction.add_bid(5, test_bids[0])
    auction.add_bid(5, test_bids[1])

    res = auction.approve_bids_information()
    assert res is True
    assert auction.auction_document["stages"][5].get('changed', '') is True
    log_strings = log_strings = logger.log_capture_string.getvalue().split('\n')
    assert "Current stage bids [{'bidder_name': '1', 'amount': 475000.0, 'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137', 'time': '2014-11-19T08:22:21.726234+00:00'}]" in log_strings

    """
    ['Bidders count: 2',
     'Saved auction document UA-11111 with rev 1-a0fe042bd1320af7d456150ddc981581',
     'Bidders count: 2',
     "Current stage bids [{'bidder_name': '1', 'amount': 475000.0, 'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137', 'time': '2014-11-19T08:22:21.726234+00:00'}]",
     '']
    """

    auction.current_stage = 7
    auction.add_bid(7, test_bids[0])

    res = auction.approve_bids_information()
    assert res is False
    assert auction.auction_document["stages"][7].get('changed') is None
    log_strings = log_strings = logger.log_capture_string.getvalue().split('\n')

    assert "Current stage bids [{'bidder_name': '2', 'amount': -1.0, 'bidder_id': u'5675acc9232942e8940a034994ad883e', 'time': '2014-11-19T08:22:24.038426+00:00'}]" in log_strings
    assert "Latest bid is bid cancellation: {'bidder_name': '2', 'amount': -1.0, 'bidder_id': u'5675acc9232942e8940a034994ad883e', 'time': '2014-11-19T08:22:24.038426+00:00'}" in log_strings

    """
    ['Bidders count: 2',
     'Saved auction document UA-11111 with rev 1-5aba6a510830a744b9fc5a0fdeffd337',
     'Bidders count: 2',
     "Current stage bids [{'bidder_name': '1', 'amount': 475000.0, 'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137', 'time': '2014-11-19T08:22:21.726234+00:00'}]",
     "Current stage bids [{'bidder_name': '2', 'amount': -1.0, 'bidder_id': u'5675acc9232942e8940a034994ad883e', 'time': '2014-11-19T08:22:24.038426+00:00'}]",
     "Latest bid is bid cancellation: {'bidder_name': '2', 'amount': -1.0, 'bidder_id': u'5675acc9232942e8940a034994ad883e', 'time': '2014-11-19T08:22:24.038426+00:00'}",
     '']
    """


def test_approve_bids_information_features(features_auction, db, logger):

    test_bids = [
        {'amount': 480000.0,
         'amount_features': 0.1,
         'bidder_id': u'5675acc9232942e8940a034994ad883e',
         'bidder_name': '2',
         'time': '2014-11-19T08:22:24.038426+00:00'},
        {'amount': 475000.0,
         'amount_features': 0.15,
         'bidder_id': u'd3ba84c66c9e4f34bfb33cc3c686f137',
         'bidder_name': '1',
         'time': '2014-11-19T08:22:21.726234+00:00'}
    ]

    features_auction.prepare_auction_document()
    features_auction.get_auction_info()
    features_auction.prepare_auction_stages_fast_forward()
    features_auction.prepare_audit()

    features_auction.current_stage = 5
    res = features_auction.approve_bids_information()
    assert res is False
    assert features_auction.auction_document["stages"][5].get('changed') is None

    features_auction.add_bid(5, test_bids[1])
    features_auction.add_bid(5, test_bids[0])

    res = features_auction.approve_bids_information()
    assert res is True
    current_stage = features_auction.auction_document["stages"][features_auction.current_stage]
    assert current_stage['amount'] == 480000.0
    assert current_stage['amount_features'] == '57420895248973824375/140737488355328'
    assert current_stage['coeficient'] == '36028797018963968/30624477466119373'
    assert current_stage['bidder_id'] == '5675acc9232942e8940a034994ad883e'
    assert current_stage['label']['en'] == 'Bidder #2'
