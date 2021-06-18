import argparse
import time

from bot import main_bot
from core import main_core
from lib.config import Config, MODE_CORE, MODE_BOT, MODE_WORKER, MODE_UPDATER
from updater import main_updater
from worker import main_worker


def main():
    parser = argparse.ArgumentParser(description='Idle RPG server.')
    parser.add_argument("--config", '-cfg', help="Path to config file", action="store", default="cfg//main.json")
    parser.add_argument("--mode", '-m', help="mode", action="store", default="core")
    parser.add_argument("--delay", help="Number seconds app will wait before start", action="store", default=None)
    args = parser.parse_args()
    if args.delay is not None:
        time.sleep(int(args.delay))

    mode = args.mode
    config = Config(args.config, mode=mode)

    if mode not in [MODE_CORE, MODE_BOT, MODE_WORKER, MODE_UPDATER]:
        raise ValueError("Mode {0} not supported".format(mode))
    if mode == MODE_BOT:
        main_bot(config)
    elif mode == MODE_CORE:
        main_core(config)
    elif mode == MODE_WORKER:
        main_worker(config)
    elif mode == MODE_UPDATER:
        main_updater(config)


if __name__ == '__main__':
    main()
