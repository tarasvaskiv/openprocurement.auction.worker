import pytest
import gevent
import gc
from pytz import timezone
from datetime import datetime, timedelta
from gevent.subprocess import Popen
from contextlib import contextmanager
from gevent import Greenlet, sleep

from openprocurement.auction.utils import calculate_hash

INIT_WORKER_MESSAGES = [
    'Bidders count: 2',
    'Saved auction document UA-11111 with rev',
    'Scheduler started',
    'Get auction document UA-11111 with rev',
    'Get _auction_data from auction_document',
    'Bidders count: 2',
    'Saved auction document UA-11111 with rev',
    'Added job "Start of Auction" to job store "default"',
    'Added job "End of Pause Stage: [0 -> 1]" to job store "default"',
    'Added job "End of Bids Stage: [1 -> 2]" to job store "default"',
    'Added job "End of Bids Stage: [2 -> 3]" to job store "default"',
    'Added job "End of Pause Stage: [3 -> 4]" to job store "default"',
    'Added job "End of Bids Stage: [4 -> 5]" to job store "default"',
    'Added job "End of Bids Stage: [5 -> 6]" to job store "default"',
    'Added job "End of Pause Stage: [6 -> 7]" to job store "default"',
    'Added job "End of Bids Stage: [7 -> 8]" to job store "default"',
    'Added job "End of Bids Stage: [8 -> 9]" to job store "default"',
    'Prepare server ...',
    'Start server',
    'Server mapping: UA-11111 ->',
]

START_AUCTION_MESSAGES = [
     'Removed job Start of Auction',
     'Running job "Start of Auction',
     '---------------- Start auction ----------------',
     'Bidders count: 2',
     'Get auction document UA-11111 with rev ',
     'Saved auction document UA-11111 with rev',
     'Job "Start of Auction',
]

FIRST_PAUSE_MESSAGES = [
     'Removed job End of Pause Stage: [0 -> 1]',
     'Running job "End of Pause Stage: [0 -> 1] (trigger:',
     '---------------- End First Pause ----------------',
     'Get auction document UA-11111 with rev',
     'Saved auction document UA-11111 with rev',
     'Job "End of Pause Stage: [0 -> 1] (trigger: date',
]

BIDS_STAGES_MESSAGES = [
    'Removed job End of Bids Stage: [1 -> 2]',
    'Running job "End of Bids Stage: [1 -> 2] (trigger: date',
    'Get auction document UA-11111 with rev',
    '---------------- End Bids Stage ----------------',
    '---------------- Start stage 2 ----------------',
    'Saved auction document UA-11111 with rev',
    'Job "End of Bids Stage: [1 -> 2] (trigger: date',
    'Removed job End of Bids Stage: [2 -> 3]',
    'Running job "End of Bids Stage: [2 -> 3] (trigger: date',
    'Get auction document UA-11111 with rev',
    '---------------- End Bids Stage ----------------',
    '---------------- Start stage 3 ----------------',
    'Saved auction document UA-11111 with rev',
    'Job "End of Bids Stage: [2 -> 3] (trigger: date',
    'Removed job End of Pause Stage: [3 -> 4]',
    'Running job "End of Pause Stage: [3 -> 4] (trigger: date',
    'Get auction document UA-11111 with rev',
    'Saved auction document UA-11111 with rev',
    '---------------- Start stage 4 ----------------',
    'Job "End of Pause Stage: [3 -> 4] (trigger: date',
    'Removed job End of Bids Stage: [4 -> 5]',
    'Running job "End of Bids Stage: [4 -> 5] (trigger: date',
    'Get auction document UA-11111 with rev',
    '---------------- End Bids Stage ----------------',
    '---------------- Start stage 5 ----------------',
    'Saved auction document UA-11111 with rev',
    'Job "End of Bids Stage: [4 -> 5] (trigger: date',
    'Removed job End of Bids Stage: [5 -> 6]',
    'Running job "End of Bids Stage: [5 -> 6] (trigger: date',
    'Get auction document UA-11111 with rev ',
    '---------------- End Bids Stage ----------------',
    '---------------- Start stage 6 ----------------',
    'Saved auction document UA-11111 with rev ',
    'Job "End of Bids Stage: [5 -> 6] (trigger: date',
    'Removed job End of Pause Stage: [6 -> 7]',
    'Running job "End of Pause Stage: [6 -> 7] (trigger: date',
    'Get auction document UA-11111 with rev 9-',
    'Saved auction document UA-11111 with rev ',
    '---------------- Start stage 7 ----------------',
    'Job "End of Pause Stage: [6 -> 7] (trigger: date',
    'Removed job End of Bids Stage: [7 -> 8]',
    'Running job "End of Bids Stage: [7 -> 8] (trigger: date',
    'Get auction document UA-11111 with rev 10-',
    '---------------- End Bids Stage ----------------',
    '---------------- Start stage 8 ----------------',
    'Saved auction document UA-11111 with rev ',
    'Job "End of Bids Stage: [7 -> 8] (trigger: date',
    'Removed job End of Bids Stage: [8 -> 9]',
    'Running job "End of Bids Stage: [8 -> 9] (trigger: date',
    'Get auction document UA-11111 with rev',
    '---------------- End Bids Stage ----------------',
]


def _kill():
    gevent.killall([obj for obj in gc.get_objects() if isinstance(obj, Greenlet)])


def wait_untill(date):
    now = datetime.now(timezone('Europe/Kiev'))
    sleep((date - now).seconds + 2)


def check_logs(logs, params,  patterns):
    for msg in params:
        if any([i for i in patterns if i in msg]):
            assert any([s for s in logs if msg in s])
        else:
            assert msg in logs


def test_worker_init(auction, db, scheduler, logger):
    auction.prepare_auction_document()
    scheduler.start()
    auction.schedule_auction()
    log_strings = logger.log_capture_string.getvalue().split('\n')
    check_logs(log_strings, INIT_WORKER_MESSAGES, ['auction', 'server', 'Server'])
    doc = auction._auction_data['data']
    assert auction.audit['items'] == doc['items']
    assert auction.audit['auction_id'] == auction.tender_id
    assert auction.audit['auctionId'] == doc['auctionID']
    scheduler.shutdown(wait=False)
    _kill()


def test_auction_start(auction, db, scheduler, logger):
    auction.prepare_auction_document()
    scheduler.start()
    auction.schedule_auction()
    wait_untill(auction.convert_datetime(
        auction.auction_document['stages'][0]['start']
        )
    )

    log_strings = logger.log_capture_string.getvalue().split('\n')
    check_logs(log_strings, START_AUCTION_MESSAGES, ['document', 'job', 'Job'])
    assert auction.bidders_count == len(auction._auction_data['data']['bids'])
    for bid in auction.auction_document['initial_bids']:
        assert 'label' in bid
        assert "Bidder #{}".format(auction.mapping[bid['bidder_id']]) == bid['label']['en']
        for bidder in auction._auction_data['data']['bids']:
            if bidder['id'] == bid['bidder_id']:
                assert bidder['value']['amount'] == bid['amount']
    # TODO: check time
    assert auction.audit['timeline']['auction_start']['time']
    assert auction.auction_document['current_stage'] == 0
    assert auction.auction_document['initial_bids'] == auction.auction_document['results']
    for stage in filter(lambda s: s['type'] == 'bids', auction.auction_document['stages']):
        # TODO: check bids order
        assert all([field in stage for field in ['bidder_id', 'label', 'start', 'type']])
        for bid in auction._auction_data['data']['bids']:
            if bid['id'] == stage['bidder_id']:
                assert bid['value']['amount'] == stage['amount']

    client = auction.server.application.test_client()
    for bid in auction.bidders_data:
        url = '/login?bidder_id={}&hash={}'.format(bid['id'], calculate_hash(bid['id'], auction.worker_defaults['HASH_SECRET']))
        resp = client.get(url)
        assert resp.status_code == 302
        assert resp.status == '302 FOUND'

    scheduler.shutdown(wait=False)
    _kill()


def test_first_pause(auction, db, scheduler, logger):
    auction.prepare_auction_document()
    scheduler.start()
    auction.schedule_auction()
    next_run = datetime.now(timezone('Europe/Kiev')) + timedelta(seconds=2)
    job = scheduler.get_job("End of Pause Stage: [0 -> 1]")
    job.modify(next_run_time=next_run)

    wait_untill(next_run)

    log_strings = logger.log_capture_string.getvalue().split('\n')
    check_logs(log_strings, FIRST_PAUSE_MESSAGES, ['document', 'job', 'Job'])
    scheduler.shutdown(wait=False)
    _kill()


def test_bids_stages(auction, db, scheduler, logger):
    auction.prepare_auction_document()
    scheduler.start()
    auction.schedule_auction()
    next_run = datetime.now(timezone('Europe/Kiev')) + timedelta(seconds=2)
    job = scheduler.get_job("End of Pause Stage: [0 -> 1]")
    job.modify(next_run_time=next_run)

    wait_untill(next_run)

    next_run = datetime.now(timezone('Europe/Kiev')) + timedelta(seconds=2)
    for job in scheduler.get_jobs():
        job.modify(next_run_time=next_run)
        wait_untill(next_run)
        next_run = datetime.now(timezone('Europe/Kiev')) + timedelta(seconds=2)
    log_strings = logger.log_capture_string.getvalue().split('\n')
    check_logs(log_strings, BIDS_STAGES_MESSAGES, ['document', 'date'])
    scheduler.shutdown(wait=False)
    _kill()
