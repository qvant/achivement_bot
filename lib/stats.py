import gc
import os
import sys

import psutil
import datetime
from typing import Dict

global startup

TOP_OBJECT_LENGTH = 10


def get_memory_usage() -> float:
    process = psutil.Process(os.getpid())
    return round(process.memory_full_info().rss / 1024 ** 2, 2)


def get_memory_usage_by_object() -> Dict:
    objects_by_memory = {}
    for obj in gc.get_objects():
        try:
            objects_by_memory[obj.__name__] = sys.getsizeof(obj)
        except AttributeError as err:
            objects_by_memory[str(obj)[:100]] = sys.getsizeof(obj)
        except ModuleNotFoundError as err:
            objects_by_memory[str(obj)[:100]] = sys.getsizeof(obj)
    top_objects_by_memory = {}
    for k, v in sorted(objects_by_memory.items(), key=lambda item: item[1], reverse=True):
        top_objects_by_memory[k] = v
        if len(top_objects_by_memory) > TOP_OBJECT_LENGTH:
            break
    return top_objects_by_memory


def get_memory_percent() -> float:
    process = psutil.Process(os.getpid())
    return round(process.memory_percent("rss"), 2)


def get_cpu_times() -> str:
    process = psutil.Process(os.getpid())
    return str(process.cpu_times())


def get_cpu_percent() -> str:
    process = psutil.Process(os.getpid())
    return str(process.cpu_percent())


def set_startup():
    global startup
    startup = datetime.datetime.now().replace(microsecond=0)


def uptime() -> datetime.timedelta:
    global startup
    return datetime.datetime.now().replace(microsecond=0) - startup


def get_stats() -> Dict:
    stats = {"memory_usage": get_memory_usage(), "memory_percent": get_cpu_percent(), "cpu_times": get_cpu_times(),
             "cpu_percent": get_cpu_percent(), "uptime": uptime(), "objects": get_memory_usage_by_object()}

    return stats
