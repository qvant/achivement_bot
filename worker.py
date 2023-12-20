import datetime
import json
import time
from datetime import timezone
from logging import Logger
from typing import List

import pika

from lib.config import Config, MODE_BOT, MODE_UPDATER
from lib.log import get_logger
from lib.platform import Platform
from lib.platforms.steam import set_skip_extra_info
from lib.player import STATUS_VALID
from lib.queue import set_config as set_queue_config, set_logger as set_queue_log, get_mq_connect, WORKER_QUEUE_NAME, \
    enqueue_command
from lib.stats import get_stats
from lib.db import load, load_players, set_load_logger, get_next_update_date, mark_update_done, start_update, \
    get_players_count
from lib.message_types import MT_ACCOUNT_UPDATED

ID_PROCESS_WORKER = 1


def main_worker(config: Config):
    queue_log = get_logger("Rabbit_worker", config.log_level, True)
    renew_log = get_logger("renew_worker", config.log_level, True)

    set_load_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config)
    set_skip_extra_info(True)

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()

    m_channel.queue_declare(queue=WORKER_QUEUE_NAME, durable=True)

    m_channel.exchange_declare(exchange='achievement_hunt',
                               exchange_type='direct',
                               durable=True)
    m_channel.queue_bind(exchange='achievement_hunt',
                         queue=WORKER_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    cmd = {"cmd": "process_response", "text": "Worker started at {0}.".format(datetime.datetime.now())}
    enqueue_command(cmd, MODE_BOT)

    dt_next_update = []
    for i in platforms:
        dt_next_update.append(get_next_update_date(i, ID_PROCESS_WORKER))
        i.load_languages()
        i.set_next_language()

    cur_players = []
    platform_players = []
    for i in platforms:
        cur_players.append(0)
        platform_players.append([])

    while is_running:

        try:

            for i in range(len(platforms)):
                if datetime.datetime.now().replace(tzinfo=timezone.utc) > \
                        dt_next_update[i].replace(tzinfo=timezone.utc):
                    renew_log.info("Begin update players on platform {0}, next update {1}".format(platforms[i].name,
                                                                                                  dt_next_update[i]))
                    platforms[i].set_next_language()
                    start_update(platforms[i], ID_PROCESS_WORKER)
                    if len(platform_players[i]) == 0:
                        renew_log.info("Update loading players for platform {0}".format(platforms[i].name))
                        player_buf = load_players(platforms[i], config)
                        for cur_player in player_buf:
                            platform_players[i].append(cur_player)
                        cur_players[i] = 0
                    else:
                        renew_log.info(
                            "Update platform {0} resumed from position {1}".format(platforms[i].name, cur_players[i]))
                    players_processed = 0
                    for j in range(cur_players[i], len(platform_players[i])):
                        cur_players[i] = j
                        renew_log.info("Update platform {} for player {} ({}). Total players {}".
                                       format(platforms[i].name,
                                              platform_players[i][j].name,
                                              platform_players[i][j].ext_id,
                                              len(platform_players[i])))
                        try:
                            platform_players[i][j].renew()
                            platform_players[i][j].save()
                        except BaseException as exc:
                            renew_log.exception(exc)
                        players_processed += 1
                        if players_processed >= platforms[i].players_pack_size:
                            renew_log.info(
                                "Update platform {0} paused in position {1}".format(platforms[i].name, cur_players[i]))
                            break
                    platforms[i].save()
                    if cur_players[i] + 1 >= len(platform_players[i]):
                        dt_next_update[i] = datetime.datetime.now() + \
                                            datetime.timedelta(seconds=platforms[i].config.update_interval)
                        platform_players[i] = []
                        platforms[i].mark_language_done()
                        platforms[i].reset_games()
                        renew_log.info("Update platform {0} finished, next_update {1}".format(platforms[i].name,
                                                                                              dt_next_update[i]))
                        mark_update_done(platforms[i], ID_PROCESS_WORKER, dt_next_update[i])
                    else:
                        renew_log.info(
                            "Update platform {0} postponed, progress {1}/{2}".format(platforms[i].name, cur_players[i],
                                                                                     len(platform_players[i])))
                else:
                    renew_log.debug("Skip update platform {0}, next update {1}".format(
                        platforms[i].name, dt_next_update[i]))
        except BaseException as err:
            queue_log.exception(err)
            if config.supress_errors:
                time.sleep(5)
            else:
                raise

        try:

            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()

            for method_frame, properties, body in m_channel.consume(WORKER_QUEUE_NAME, inactivity_timeout=1,
                                                                    auto_ack=False):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    need_stop = process_queue_command(body, config, method_frame, platforms, queue_log)
                    if need_stop:
                        is_running = False
                    try:
                        m_channel.basic_ack(method_frame.delivery_tag)
                    except BaseException as exc:
                        queue_log.critical("User message " + str(body) + " with delivery_tag " +
                                           str(method_frame.delivery_tag) +
                                           " acknowledged with error{0}, resending".format(str(exc)))
                        # TODO: handle
                        raise

                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(WORKER_QUEUE_NAME))
                    m_channel.cancel()
                    break
            time.sleep(4)
        except pika.exceptions.AMQPError as exc:
            queue_log.exception(exc)
            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()
        except BaseException as err:
            queue_log.exception(err)
            if config.supress_errors:
                pass
            else:
                raise


def process_queue_command(body: bytes, config: Config, method_frame, platforms: List[Platform],
                          queue_log: Logger) -> bool:
    cmd = json.loads(body)
    cmd_type = cmd.get("cmd")
    need_stop = False
    if cmd_type == 'renew_achievements':
        platform_id = cmd.get("platform_id")
        player_id = cmd.get("player_id")
        dt_sent = cmd.get("dt_sent")
        dt_sent = datetime.datetime.fromtimestamp(dt_sent)
        update_player_achievements_cmd_handler(body, config, dt_sent, method_frame, platform_id, platforms, player_id,
                                               queue_log)

    elif cmd_type == 'stop_server':
        need_stop = True
        cmd = {"cmd": "process_response", "text": "Worker shutdown started"}
        enqueue_command(cmd, MODE_BOT)
    elif cmd_type == "get_stats":
        get_stats_cmd_handler(platforms)
    return need_stop


def get_stats_cmd_handler(platforms: List[Platform]):
    msg = get_stats()
    msg["players"] = get_players_count()
    msg["module"] = "Worker"
    msg["platform_stats"] = {}
    for i in platforms:
        msg["platform_stats"][i.name] = str(i.get_stats())
    cmd = {"cmd": "process_response", "text": str(msg)}
    enqueue_command(cmd, MODE_BOT)


def update_player_achievements_cmd_handler(body: bytes, config: Config, dt_sent, method_frame, platform_id,
                                           platforms: List[Platform], player_id, queue_log):
    queue_log.info("Start renew achievements for player {2} and platform {3} because msg {0} "
                   "with delivery_tag {1}".format(body, method_frame.delivery_tag,
                                                  player_id, platform_id))
    player = None
    for i in platforms:
        queue_log.debug("Check platform {0} {1}".format(i.name, i.id))
        if int(i.id) == int(platform_id):
            players = load_players(platform=i, config=config, player_id=player_id,
                                   status_id=STATUS_VALID)
            if len(players) > 0:
                player = players[0]
                if player.dt_updated is None or player.dt_updated.replace(tzinfo=timezone.utc) < \
                        dt_sent.replace(tzinfo=timezone.utc):
                    queue_log.info(
                        "Start actually renew achievements for player {2}  and platform {3} "
                        "because msg {0} with delivery_tag {1}".format(
                            body,
                            method_frame.delivery_tag,
                            player_id, i.name))
                    i.set_def_locale()
                    player.renew()
                    player.platform.save()
                    player.save()
                    cmd = {"chat_id": player.telegram_id,
                           "cmd": "msg_to_user",
                           "text": 'Achievements for account {} platform {} renewed'.format(
                               player.ext_id, i.name),
                           "type": MT_ACCOUNT_UPDATED,
                           "telegram_id": player.telegram_id,
                           "name": player.name,
                           "platform": i.name
                           }
                    enqueue_command(cmd, MODE_UPDATER)
                else:
                    queue_log.info(
                        "Skipped renew achievements for player {2} and platform {3} because msg "
                        "{0} with delivery_tag {1} was sent at {4} and last renew was {5}".format(
                            body,
                            method_frame.delivery_tag,
                            player_id, i.name, dt_sent, player.dt_updated))
                    cmd = {"chat_id": player.telegram_id,
                           "cmd": "msg_to_user",
                           "text": 'Achievements for account {} platform {} renewed'.format(
                               player.ext_id, i.name),
                           "type": MT_ACCOUNT_UPDATED,
                           "telegram_id": player.telegram_id,
                           "name": player.name,
                           "platform": i.name
                           }
                    enqueue_command(cmd, MODE_UPDATER)
            else:
                queue_log.error(
                    "Player {0} for platform {1} wasn't found in db".format(player_id, platform_id))
    if player is None:
        queue_log.error("Player {0} for platform {1} wasn't proceed".format(player_id, platform_id))
