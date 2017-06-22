import json
import os
import pytest
import yaml

from openprocurement.auction.worker.auction import Auction
from openprocurement.auction.tests.main import PWD, CWD
# from openprocurement.auction.tests.main import update_auctionPeriod


@pytest.fixture(scope="module")
def auction():
    tender_file_path = os.path.join(PWD, "data/tender_data.json")
    # update_auctionPeriod(tender_file_path)

    with open(tender_file_path) as data_file:
        tender_data = json.load(data_file)

    return Auction(
        tender_id=tender_data['data']['tenderID'],
        worker_defaults=yaml.load(open('{0}/etc/auction_worker_defaults.yaml'.format(CWD))),
        auction_data=tender_data,
        lot_id=False
    )
