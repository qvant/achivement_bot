import datetime
import json
import time
from datetime import timezone
from typing import List

import pika

from lib.config import Config, MODE_BOT
from lib.log import get_logger
from lib.platform import Platform
from lib.platforms.retroachievements import set_game_updater_limits
from lib.platforms.steam import set_skip_extra_info
from lib.queue import set_config as set_queue_config, set_logger as set_queue_log, get_mq_connect, \
    GAME_UPDATER_QUEUE_NAME, enqueue_command
from lib.stats import get_stats
from lib.db import load, set_load_logger, get_next_update_date, mark_update_done, start_update
from lib.db_api import set_db_config

ID_PROCESS_GAME_UPDATER = 2


def main_game_updater(config: Config):
    renew_log = get_logger("renew_game_updater", config.log_level)

    set_load_logger(config)
    set_db_config(config)
    set_queue_config(config)
    set_queue_log(renew_log)

    Platform.set_config(config)
    platforms = load(config)
    set_skip_extra_info(False)
    set_game_updater_limits()

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()

    m_channel.queue_declare(queue=GAME_UPDATER_QUEUE_NAME, durable=True)

    m_channel.exchange_declare(exchange='achievement_hunt',
                               exchange_type='direct',
                               durable=True)
    m_channel.queue_bind(exchange='achievement_hunt',
                         queue=GAME_UPDATER_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    cmd = {"cmd": "process_response", "text": "Game updater started at {0}.".format(datetime.datetime.now())}
    enqueue_command(cmd, MODE_BOT)

    dt_next_update = []
    platform_games_indexes = []
    for j in platforms:
        dt_next_update.append(get_next_update_date(j, ID_PROCESS_GAME_UPDATER))
        j.reset_games()
        j.load_languages()
        j.set_next_language()
        platform_games_indexes.append(0)

    while is_running:

        try:

            for i in range(len(platforms)):
                if datetime.datetime.now().replace(tzinfo=timezone.utc) > \
                        dt_next_update[i].replace(tzinfo=timezone.utc):
                    platforms[i].logger.info("Begin update games on platform {0} ({2}), next update {1}"
                                             .format(platforms[i].name,
                                                     dt_next_update[i],
                                                     platforms[i].id))
                    platforms[i].set_next_language()
                    start_update(platforms[i], ID_PROCESS_GAME_UPDATER)
                    if platforms[i].get_consoles is not None:
                        try:
                            platforms[i].set_consoles(platforms[i].get_consoles())
                            platforms[i].save()
                        except BaseException as exc:
                            platforms[i].logger.exception(exc)
                            dt_next_update[i] = datetime.datetime.now() + datetime.timedelta(
                                seconds=platforms[i].config.update_interval)
                            mark_update_done(platforms[i], ID_PROCESS_GAME_UPDATER, dt_next_update[i])
                            platforms[i].logger.info(
                                "Update platform {} ({}) skipped, because consoles not available".format(
                                    platforms[i].name,
                                    platforms[i].id
                                ))
                            continue
                    if platform_games_indexes[i] == 0:
                        platforms[i].load_games()
                    games_num = len(platforms[i].games)
                    games_ext_ids = list(platforms[i].games.keys())
                    games_processed = 0
                    for j in range(platform_games_indexes[i], len(games_ext_ids)):
                        game = platforms[i].games[games_ext_ids[j]]
                        platforms[i].logger.info(
                            "Update game \"{}\" (ext_id: {}). Progress {}/{}".
                            format(game.name, game.ext_id, j, games_num))
                        platforms[i].update_games(game.ext_id, game.name, True)
                        platforms[i].logger.info(
                            "Get achievements for game \"{}\" (ext_id: {}). Progress {}/{}".format(
                               game.name, game.ext_id, j + 1, games_num))
                        games_processed += 1
                        if games_processed >= platforms[i].games_pack_size:
                            break
                    platforms[i].save()
                    if platform_games_indexes[i] >= games_num:
                        dt_next_update[i] = datetime.datetime.now() + datetime.timedelta(
                            seconds=platforms[i].config.update_interval)
                        platforms[i].mark_language_done()
                        platforms[i].reset_games()
                        platforms[i].logger.info("Update platform {0} finished, next_update {1}"
                                                 .format(platforms[i].name, dt_next_update[i]))
                        mark_update_done(platforms[i], ID_PROCESS_GAME_UPDATER, dt_next_update[i])
                        platform_games_indexes[i] = 0
                    else:
                        platform_games_indexes[i] += games_processed
                        platforms[i].logger.info("Update platform {0} perform batch, progress {1}/{2}"
                                                 .format(platforms[i].name,
                                                         platform_games_indexes[i], games_num))
                else:
                    platforms[i].logger.debug("Skip update platform {0}, next update {1}".format(
                       platforms[i].name, dt_next_update[i]))
        except BaseException as err:
            renew_log.exception(err)
            if config.supress_errors:
                time.sleep(5)
            else:
                raise

        try:

            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()

            for method_frame, properties, body in m_channel.consume(GAME_UPDATER_QUEUE_NAME, inactivity_timeout=1,
                                                                    auto_ack=False):
                if body is not None:
                    renew_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    need_stop = process_queue_command(body, platforms)
                    if need_stop:
                        is_running = False
                    try:
                        m_channel.basic_ack(method_frame.delivery_tag)
                    except BaseException as exc:
                        renew_log.critical("User message " + str(body) + " with delivery_tag " +
                                           str(method_frame.delivery_tag) +
                                           " acknowledged with error{0}, resending".format(str(exc)))
                        # TODO: handle
                        raise

                    renew_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    renew_log.debug("No more messages in {0}".format(GAME_UPDATER_QUEUE_NAME))
                    m_channel.cancel()
                    break
            time.sleep(4)
        except pika.exceptions.AMQPError as exc:
            renew_log.exception(exc)
            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()
        except BaseException as err:
            renew_log.exception(err)
            if config.supress_errors:
                pass
            else:
                raise


def process_queue_command(body: bytes, platforms: List[Platform]) -> bool:
    cmd = json.loads(body)
    cmd_type = cmd.get("cmd")
    need_stop = False
    if cmd_type == 'stop_server':
        need_stop = True
        cmd = {"cmd": "process_response", "text": "Game updater shutdown started"}
        enqueue_command(cmd, MODE_BOT)
    elif cmd_type == "get_stats":
        msg = get_stats()
        msg["module"] = "Game updater"
        msg["platform_stats"] = {}
        for j in platforms:
            msg["platform_stats"][j.name] = str(j.get_stats())
        cmd = {"cmd": "process_response", "text": str(msg)}
        enqueue_command(cmd, MODE_BOT)
    return need_stop
