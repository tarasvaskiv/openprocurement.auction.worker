# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()

import os.path
import json
from gevent.subprocess import check_output, sleep
from openprocurement.auction.tests.utils import update_auctionPeriod
from openprocurement.auction.worker.tests.data.data import SIMPLE_TENDER_ID, \
    MULTILOT_TENDER_ID


PWD = os.path.dirname(os.path.realpath(__file__))
CWD = os.getcwd()


def run_simple(worker_cmd, tender_file_path, auction_id):
    with update_auctionPeriod(tender_file_path, auction_type='simple') as auction_file:
        check_output(worker_cmd.format(CWD, auction_id, auction_file).split())
    sleep(2)


def run_multilot(worker_cmd, tender_file_path, auction_id):
    with open(tender_file_path) as _file:
        data = json.load(_file).get('data', {})
        lot_id = data.get('lots', [])[0].get('id')
    with update_auctionPeriod(tender_file_path, auction_type='multilot') as auction_file:
        command_line = worker_cmd.format(
            CWD, auction_id, auction_file, lot_id
        )
        check_output(command_line.split())
    sleep(2)


def includeme():
    return {
        'simple': {
            'worker_cmd': '{0}/bin/auction_worker planning {1}'
                          ' {0}/etc/auction_worker_defaults.yaml'
                          ' --planning_procerude partial_db --auction_info {2}',
            'runner': run_simple,
            'tender_file_path': '{0}/data/tender_simple.json'.format(PWD),
            'auction_id': SIMPLE_TENDER_ID,
            'auction_worker_defaults': 'auction_worker_defaults:{0}/etc/auction_worker_defaults.yaml',
            'suite': PWD
        },
        'multilot': {
            'worker_cmd': '{0}/bin/auction_worker planning {1}'
                          ' {0}/etc/auction_worker_defaults.yaml'
                          ' --planning_procerude partial_db --auction_info {2} --lot {3}',
            'runner': run_multilot,
            'tender_file_path': '{0}/data/tender_multilot.json'.format(PWD),
            'auction_id': MULTILOT_TENDER_ID,
            'auction_worker_defaults': 'auction_worker_defaults:{0}/etc/auction_worker_defaults.yaml',
            'suite': PWD
        }
    }
