# -*- coding: utf-8 -*-
import json
import logging
import os
import pytest
import yaml
import couchdb

from copy import deepcopy
from StringIO import StringIO
from uuid import uuid4

from openprocurement.auction.worker.auction import Auction, SCHEDULER
from openprocurement.auction.worker.mixins import LOGGER
from openprocurement.auction.tests.functional.main import update_auctionPeriod

PWD = os.path.dirname(os.path.realpath(__file__))

tender_file_path = os.path.join(PWD, "data/tender_data.json")
worker_defaults_file_path = os.path.join(PWD, "data/auction_worker_defaults.yaml")
with open(tender_file_path) as data_file:
    tender_data = json.load(data_file)
with open(worker_defaults_file_path) as stream:
    worker_defaults = yaml.load(stream)

test_organization = {
    "name": u"Державне управління справами",
    "identifier": {
        "scheme": u"UA-EDR",
        "id": u"00037256",
        "uri": u"http://www.dus.gov.ua/"
    },
    "address": {
        "countryName": u"Україна",
        "postalCode": u"01220",
        "region": u"м. Київ",
        "locality": u"м. Київ",
        "streetAddress": u"вул. Банкова, 11, корпус 1"
    },
    "contactPoint": {
        "name": u"Державне управління справами",
        "telephone": u"0440000000"
    }
}


item_id = uuid4().hex
lot_id = '2222222222222222'
lot_tender_data = deepcopy(tender_data)

test_lot = {
        'title': 'lot title',
        'description': 'lot description',
        'value': lot_tender_data['data']['value'],
        'minimalStep': lot_tender_data['data']['minimalStep'],
}

lot_tender_data['data']['lots'] = [test_lot]
lot_tender_data['data']['items'][0]['id'] = item_id
lot_tender_data['data']['items'][0]['relatedLot'] = lot_id
lot_tender_data['data']['lots'][0]['id'] = lot_id
lot_tender_data['data']['lots'][0]['relatedItem'] = item_id

lot_tender_data['data']['bids'][0]['lotValues'] = [{
    "value": lot_tender_data['data']['bids'][0]['value'],
    "relatedLot": lot_id,
    "date": lot_tender_data['data']['bids'][0]['date']
}]
lot_tender_data['data']['bids'][1]['lotValues'] = [{
    "value": lot_tender_data['data']['bids'][1]['value'],
    "relatedLot": lot_id,
    "date": lot_tender_data['data']['bids'][1]['date']
}]
del lot_tender_data['data']['bids'][0]['value']
del lot_tender_data['data']['bids'][1]['value']
del lot_tender_data['data']['bids'][0]['date']
del lot_tender_data['data']['bids'][1]['date']


features_tender_data = deepcopy(tender_data)
test_features_item = features_tender_data['data']['items'][0].copy()
test_features_item['id'] = "1"
features_tender_data['data']['items'] = [test_features_item]
features_tender_data['data']["features"] = [
    {
        "code": "OCDS-123454-YEARS",
        "featureOf": "tenderer",
        "title": u"Років на ринку",
        "title_en": "Years trading",
        "description": u"Кількість років, які організація учасник працює на ринку",
        "enum": [
            {
                "value": 0.05,
                "title": u"До 3 років"
            },
            {
                "value": 0.1,
                "title": u"Більше 3 років, менше 5 років"
            },
            {
                "value": 0.15,
                "title": u"Більше 5 років"
            }
        ]
    }
]
features_tender_data['data']['bids'][0]['parameters'] = [
    {
        "code": "OCDS-123454-YEARS",
        "value": 0.1,
    }
]
features_tender_data['data']['bids'][1]['parameters'] = [
    {
        "code": "OCDS-123454-YEARS",
        "value": 0.15,
    }
]


@pytest.yield_fixture(scope="function")
def auction():
    update_auctionPeriod(tender_file_path)

    yield Auction(
        tender_id=tender_data['data']['tenderID'],
        worker_defaults=yaml.load(open(worker_defaults_file_path)),
        auction_data=tender_data,
        lot_id=False
    )


@pytest.yield_fixture(scope="function")
def multilot_auction():
    lot_tender_data['data']['lots'][0]['auctionPeriod'] = lot_tender_data['data']['auctionPeriod']
    
    yield Auction(
        tender_id=lot_tender_data['data']['tenderID'],
        worker_defaults=yaml.load(open(worker_defaults_file_path)),
        auction_data=lot_tender_data,
        lot_id=lot_id
    )


@pytest.yield_fixture(scope="function")
def features_auction():

    yield Auction(
        tender_id=features_tender_data['data']['tenderID'],
        worker_defaults=yaml.load(open(worker_defaults_file_path)),
        auction_data=features_tender_data,
        lot_id=False
    )


@pytest.fixture(scope='function')
def db(request):
    server = couchdb.Server("http://" + worker_defaults['COUCH_DATABASE'].split('/')[2])
    name = worker_defaults['COUCH_DATABASE'].split('/')[3]

    def delete():
        del server[name]

    if name in server:
        delete()
    server.create(name)
    request.addfinalizer(delete)


class LogInterceptor(object):
    def __init__(self, logger):
        self.log_capture_string = StringIO()
        self.test_handler = logging.StreamHandler(self.log_capture_string)
        self.test_handler.setLevel(logging.INFO)
        logger.addHandler(self.test_handler)


@pytest.fixture(scope='function')
def logger():
    return LogInterceptor(LOGGER)


@pytest.fixture(scope='function')
def scheduler():
    return SCHEDULER
