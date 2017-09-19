import pytest
from mock import MagicMock

from wtforms.validators import ValidationError
from openprocurement.auction.worker.tests.data.data import (
    test_auction_document
)
from openprocurement.auction.worker.forms import (
    validate_bid_value, BidsForm
)


def test_validate_bid_value():
    field = MagicMock()

    field.data = -0.0
    with pytest.raises(ValidationError) as e:
        validate_bid_value(None, field)
    assert e.value.message == u'Too low value'

    field.data = -0.99999999999
    with pytest.raises(ValidationError) as e:
        validate_bid_value(None, field)
    assert e.value.message == u'Too low value'

    field.data = -1.0000001
    with pytest.raises(ValidationError) as e:
        validate_bid_value(None, field)
    assert e.value.message == u'Too low value'

    field.data = 0.000001
    validate_bid_value(None, field)


def test_bids_form(auction, features_auction):
    form_errors = {
        'bid': [u'Bid amount is required'],
        'bidder_id': [u'No bidder id']
    }

    form_data = {}

    form = BidsForm().from_json({})
    assert form.validate() is False
    assert form.errors == form_errors

    form = BidsForm().from_json({'bidder_id': 'bidder_id'})
    form.document = test_auction_document
    assert form.validate() is False
    assert form.errors == {'bid': [u'Bid amount is required'],
                           'bidder_id': [u'Not valid bidder']}

    form = BidsForm().from_json({'bidder_id': 123})
    form.document = test_auction_document
    assert form.validate() is False
    assert form.errors == {'bid': [u'Bid amount is required'],
                           'bidder_id': [u'Not valid bidder']}

    form_data['bidder_id'] = u'f7c8cd1d56624477af8dc3aa9c4b3ea3'
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    assert form.validate() is False
    assert form.errors == {'bid': [u'Bid amount is required']}

    form_data['bid'] = 1
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is False
    assert form.errors == {'bid': [u'Too low value']}

    form_data['bid'] = -1
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is True
    assert form.errors == {}
    assert form.data == form_data

    form_data['bid'] = -1.0
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is True
    assert form.errors == {}
    assert form.data == form_data

    form_data['bid'] = '-1'
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is True
    assert form.errors == {}
    assert form.data['bid'] == -1.0

    form_data['bid'] = '-1.0'
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is True
    assert form.errors == {}
    assert form.data['bid'] == -1.0

    form_data['bid'] = '1'
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is False
    assert form.errors == {'bid': [u'Too low value']}

    form_data['bid'] = 'one'
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is False
    assert form.errors == {'bid': [u'Not a valid float value',
                                   u'Too low value', u'Too low value']}

    form_data['bid'] = test_auction_document['stages'][
        test_auction_document['current_stage']
    ]['amount'] + test_auction_document['minimalStep']['amount']
    form = BidsForm().from_json(form_data)
    form.document = test_auction_document
    form.auction = auction
    assert form.validate() is True
    assert form.errors == {}
    assert form.data == form_data

    # features
    form_data['bid'] = 2600000.0
    form = BidsForm().from_json(form_data)
    form.auction = features_auction
    form.document = test_auction_document
    form.document['stages'][2]['amount_features'] = \
        form.document['stages'][2]['amount']
    form.auction.features = features_auction._auction_data['data']['features']
    form.auction.bidders_coeficient = {'f7c8cd1d56624477af8dc3aa9c4b3ea3': 0.1}
    assert form.validate() is True
    assert form.errors == {}
    assert form.data == form_data

    form_data['bid'] = '2600000.0'
    form = BidsForm().from_json(form_data)
    form.auction = features_auction
    form.document = test_auction_document
    form.document['stages'][2]['amount_features'] = \
        form.document['stages'][2]['amount']
    form.auction.features = features_auction._auction_data['data']['features']
    form.auction.bidders_coeficient = {'f7c8cd1d56624477af8dc3aa9c4b3ea3': 0.1}
    assert form.validate() is True
    assert form.errors == {}
    assert form.data['bid'] == float(form_data['bid'])

    form_data['bid'] = -1
    form = BidsForm().from_json(form_data)
    form.auction = features_auction
    form.document = test_auction_document
    form.document['stages'][2]['amount_features'] = \
        form.document['stages'][2]['amount']
    form.auction.features = features_auction._auction_data['data']['features']
    form.auction.bidders_coeficient = {'f7c8cd1d56624477af8dc3aa9c4b3ea3': 0.1}
    assert form.validate() is True
    assert form.errors == {}
    assert form.data == form_data

    form_data['bid'] = 123456
    form = BidsForm().from_json(form_data)
    form.auction = features_auction
    form.document = test_auction_document
    form.document['stages'][2]['amount_features'] = \
        form.document['stages'][2]['amount']
    form.auction.features = features_auction._auction_data['data']['features']
    form.auction.bidders_coeficient = {'f7c8cd1d56624477af8dc3aa9c4b3ea3': 0.1}
    assert form.validate() is False
    assert form.errors == {'bid': [u'Too low value']}

    form_data['bid'] = 123456
    form = BidsForm().from_json(form_data)
    form.auction = features_auction
    form.document = test_auction_document
    form.document['stages'][test_auction_document['current_stage']]['type'] =\
        'not_bids'
    form.document['stages'][2]['amount_features'] = \
        form.document['stages'][2]['amount']
    form.auction.features = features_auction._auction_data['data']['features']
    form.auction.bidders_coeficient = {'f7c8cd1d56624477af8dc3aa9c4b3ea3': 0.1}
    assert form.validate() is False
    assert form.errors == {'bid': [u'Stage not for bidding']}
