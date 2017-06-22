import json
import os
import pytest
import yaml

from openprocurement.auction.worker.auction import Auction

PWD = os.path.dirname(os.path.realpath(__file__ ))
# from openprocurement.auction.tests.main import update_auctionPeriod


@pytest.fixture(scope="module")
def auction():
    tender_file_path = os.path.join(PWD, "data/tender_data.json")
    worker_defaults_file_path = os.path.join(PWD, "data/auction_worker_defaults.yaml")
    # update_auctionPeriod(tender_file_path)

    with open(tender_file_path) as data_file:
        tender_data = json.load(data_file)

    return Auction(
        tender_id=tender_data['data']['tenderID'],
        worker_defaults=yaml.load(open(worker_defaults_file_path)),
        auction_data=tender_data,
        lot_id=False
    )
