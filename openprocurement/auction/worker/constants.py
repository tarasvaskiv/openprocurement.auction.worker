from pytz import timezone


ROUNDS = 3
TIMEZONE = timezone('Europe/Kiev')
BIDS_SECONDS = 120
FIRST_PAUSE_SECONDS = 300
PAUSE_SECONDS = 120
BIDS_KEYS_FOR_COPY = ("bidder_id", "amount", "time")
PLANNING_FULL = "full"
PLANNING_PARTIAL_DB = "partial_db"
PLANNING_PARTIAL_CRON = "partial_cron"


