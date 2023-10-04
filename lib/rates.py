import datetime
import time

global interval_end_times
global interval_lengths
global interval_limits
global counters

interval_end_times = {}
interval_lengths = {}
interval_limits = {}
counters = {}


def set_limit(resource: str, interval: int, limit: int):
    global interval_lengths
    global interval_limits
    interval_lengths[resource] = interval
    interval_limits[resource] = limit


def reset_limit(resource: str):
    global interval_end_times
    global counters
    interval_end_times[resource] = datetime.datetime.now() + datetime.timedelta(seconds=interval_lengths[resource])
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
    if resource not in interval_end_times or interval_end_times[resource] < datetime.datetime.now():
        reset_limit(resource)
    while interval_end_times[resource] >= datetime.datetime.now() and counters[resource] >= interval_limits[resource]:
        time.sleep(1)
    if interval_end_times[resource] <= datetime.datetime.now():
        reset_limit(resource)
    counters[resource] += 1
    return func(**args)




