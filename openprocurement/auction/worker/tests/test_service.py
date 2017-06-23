from openprocurement.auction.worker.tests.base import auction, db

# DBServiceTest


def test_get_auction_info_simple(auction):
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


def test_prepare_auction_document(auction, db):
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


def test_end_bids_stage(auction, db):
    auction.prepare_auction_document()
    auction.get_auction_info()
    auction.prepare_auction_stages_fast_forward()
    auction.prepare_audit()

    auction.end_bids_stage()

    assert auction.current_stage == 9
    assert auction.current_round == 3


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


def test_upload_audit_file_with_document_service(auction, db):
    from requests import Session as RequestsSession
    auction.session_ds = RequestsSession()
    auction.prepare_auction_document()
    auction.get_auction_info()

    res = auction.upload_audit_file_with_document_service()


def test_upload_audit_file_without_document_service(auction, db):
    auction.prepare_auction_document()
    auction.get_auction_info()

    res = auction.upload_audit_file_without_document_service()
