import datetime
import time
from logging import Logger
from typing import Union

global interval_end_times
global interval_lengths
global interval_limits
global counters
global loggers

interval_end_times = {}
interval_lengths = {}
interval_limits = {}
counters = {}
loggers = {}


def set_limit(resource: str, interval: int, limit: int, logger: Union[Logger, None] = None):
    global interval_lengths
    global interval_limits
    global loggers
    interval_lengths[resource] = interval
    interval_limits[resource] = limit
    loggers[resource] = logger


def reset_limit(resource: str):
    global interval_end_times
    global counters
    global loggers
    interval_end_times[resource] = datetime.datetime.now() + datetime.timedelta(seconds=interval_lengths[resource])
    if loggers[resource] is not None:
        loggers[resource].info("Set new limit for {}, on {} to {}".format(interval_end_times[resource],
                                                                          resource,
                                                                          interval_limits[resource]))
    counters[resource] = 0


def get_limit_counter(resource: str):
    if resource in counters:
        return counters[resource]
    return -1


def get_limit_interval_end(resource: str):
    if resource in interval_end_times:
        return interval_end_times[resource]
    return datetime.datetime.min


def do_with_limit(resource: str, func, args):
    global interval_end_times
    global counters
    global loggers
    if resource not in interval_end_times or interval_end_times[resource] < datetime.datetime.now():
        reset_limit(resource)
    while interval_end_times[resource] >= datetime.datetime.now() and counters[resource] >= interval_limits[resource]:
        if loggers[resource] is not None:
            loggers[resource].info("Wait to {}, because rate on {} is reached ".format(interval_end_times[resource],
                                                                                       resource))
        if interval_end_times[resource] - datetime.datetime.now() > datetime.timedelta(seconds=5):
            time.sleep(5)
        else:
            time.sleep(1)
    if interval_end_times[resource] <= datetime.datetime.now():
        reset_limit(resource)
    counters[resource] += 1
    return func(**args)
