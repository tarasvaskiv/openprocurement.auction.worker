import json
import logging
import os
import pytest
import yaml
import couchdb

from StringIO import StringIO

from openprocurement.auction.worker.auction import Auction
from openprocurement.auction.worker.services import LOGGER

PWD = os.path.dirname(os.path.realpath(__file__))
# from openprocurement.auction.tests.main import update_auctionPeriod


tender_file_path = os.path.join(PWD, "data/tender_data.json")
worker_defaults_file_path = os.path.join(PWD, "data/auction_worker_defaults.yaml")
with open(tender_file_path) as data_file:
    tender_data = json.load(data_file)
with open(worker_defaults_file_path) as stream:
    worker_defaults = yaml.load(stream)


@pytest.fixture(scope="function")
def auction():
    # update_auctionPeriod(tender_file_path)

    return Auction(
        tender_id=tender_data['data']['tenderID'],
        worker_defaults=yaml.load(open(worker_defaults_file_path)),
        auction_data=tender_data,
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


class LogCapturer(object):
    def __init__(self, logger):
        self.log_capture_string = StringIO()
        self.test_handler = logging.StreamHandler(self.log_capture_string)
        self.test_handler.setLevel(logging.INFO)
        logger.addHandler(self.test_handler)


@pytest.fixture(scope='function')
def logger():
    return LogCapturer(LOGGER)
