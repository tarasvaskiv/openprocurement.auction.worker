import os
from pytz import timezone
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow

def parse_bpmn():
    PWD = os.path.dirname(os.path.realpath(__file__))
    parser = BpmnParser()
    files = ['{}/diagram.bpmn'.format(PWD)]
    parser.add_bpmn_files(files)
    spec = parser.get_spec('Process_1')

    wf = BpmnWorkflow(spec)
    wf.complete_all()
    tasks = wf.get_tasks()
    names = [t.get_name() for t in tasks if 'Task' in t.get_name()]
    return len(names)

ROUNDS = parse_bpmn()
TIMEZONE = timezone('Europe/Kiev')
BIDS_SECONDS = 120
FIRST_PAUSE_SECONDS = 300
PAUSE_SECONDS = 120
BIDS_KEYS_FOR_COPY = ("bidder_id", "amount", "time")
PLANNING_FULL = "full"
PLANNING_PARTIAL_DB = "partial_db"
PLANNING_PARTIAL_CRON = "partial_cron"
