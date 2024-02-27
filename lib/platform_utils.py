import codecs
import datetime
import json
from typing import Dict, Any

global call_counters
global call_counters_retain
global api_calls_daily_limit
global api_call_errors

api_calls_daily_limit: Dict[str, int] = {}
call_counters: Dict[str, Dict[str, int]] = {}
api_call_errors: Dict[str, Dict[str, Dict[str, int]]] = {}
call_counters_retain: Dict[str, int] = {}


def save_api_key(password: str, path: str):
    fp = codecs.open(path, 'r', "utf-8")
    config = json.load(fp)
    fp.close()
    fp = codecs.open(path, 'w', "utf-8")
    config["API_KEY"] = password
    json.dump(config, fp, indent=2)
    fp.close()


def sef_daily_call_limit(platform: str, limit: int):
    global api_calls_daily_limit
    api_calls_daily_limit[platform] = limit


def set_call_counters_retain(platform: str, days: int):
    global call_counters_retain
    call_counters_retain[platform] = days


def inc_call_cnt(platform: str, method: str):
    global call_counters
    global call_counters_retain
    cur_dt = str(datetime.date.today())
    if call_counters is None:
        call_counters = {}
    if platform not in call_counters:
        call_counters[platform] = {}
    platform_call_counters = call_counters[platform]
    if cur_dt not in platform_call_counters:
        platform_call_counters[cur_dt] = {}
    if method not in platform_call_counters[cur_dt]:
        platform_call_counters[cur_dt][method] = int(0)
    if call_counters_retain is None:
        call_counters_retain = {}
    if platform not in call_counters_retain:
        call_counters_retain[platform] = 7
    platform_call_counters[cur_dt][method] += int(1)
    while len(platform_call_counters) > call_counters_retain[platform] >= 0:
        keys = [key for key in platform_call_counters]
        keys.sort()
        old_dt = keys[0]
        platform_call_counters.pop(old_dt, 'None')


def inc_error_cnt(platform: str, method: str, code: str):
    global api_call_errors
    if platform not in api_call_errors:
        api_call_errors[platform] = {}
    cur_dt = str(datetime.date.today())
    if cur_dt not in api_call_errors[platform]:
        api_call_errors[platform][cur_dt] = {}
    if method not in api_call_errors[platform][cur_dt]:
        api_call_errors[platform][cur_dt][method] = {}
    if code not in api_call_errors[platform][cur_dt][method]:
        api_call_errors[platform][cur_dt][method][code] = int(0)
    api_call_errors[platform][cur_dt][method][code] += int(1)
    while len(api_call_errors[platform]) > call_counters_retain[platform] >= 0:
        keys = [key for key in api_call_errors[platform]]
        keys.sort()
        old_dt = keys[0]
        api_call_errors[platform].pop(old_dt, 'None')


def get_call_cnt(platform: str):
    call_counter: Dict[str, Dict[str, Any]] = {}
    if platform in call_counters:
        call_counter = call_counters[platform].copy()
        for i in call_counter:
            total = int(0)
            for j in call_counter[i]:
                if j != "Total":
                    total += int(call_counter[i][j])
            call_counter[i]["Total"] = total
            call_counter[i]["Used calls %"] = 0
            if total > 0:
                if platform not in api_calls_daily_limit:
                    sef_daily_call_limit(platform, 100000)
                call_counter[i]["Used calls %"] = round(total / api_calls_daily_limit[platform] * 100, 2)
    if platform in api_call_errors:
        call_counter["Errors"] = api_call_errors[platform]
    else:
        call_counter["Errors"] = {}
    return call_counter
