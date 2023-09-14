import datetime
import json
import time
from datetime import timezone

import pika

from lib.config import Config, MODE_BOT, MODE_UPDATER
from lib.log import get_logger
from lib.platform import Platform
from lib.platforms.steam import set_skip_extra_info
from lib.player import STATUS_VALID
from lib.queue import set_config as set_queue_config, set_logger as set_queue_log, get_mq_connect, GAME_UPDATER_QUEUE_NAME, \
    enqueue_command
from lib.stats import get_stats
from lib.telegram import set_logger, set_platforms, set_connect
from lib.db import load, load_players, set_load_logger
from lib.message_types import MT_ACCOUNT_UPDATED


def main_game_updater(config: Config):
    queue_log = get_logger("Rabbit_game_updater", config.log_level, True)
    renew_log = get_logger("renew_game_updater", config.log_level, True)

    set_load_logger(config)
    set_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config)
    set_platforms(platforms)
    set_skip_extra_info(False)
    set_connect(Platform.get_connect())

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
    conn = Platform.get_connect()
    cursor = conn.cursor()
    for j in platforms:
        cursor.execute("""
        select max(dt_next_update) from achievements_hunt.update_history where id_platform = %s and dt_ended is not null
        and id_process = 2
        """, (j.id,))
        ret = cursor.fetchone()
        if ret is not None and ret[0] is not None:
            dt_next_update.append(ret[0])
        else:
            dt_next_update.append(datetime.datetime.now())
        j.reset_games()
        j.load_languages()
        j.set_next_language()
    conn.commit()

    cur_players = []
    platform_players = []
    for j in platforms:
        cur_players.append(0)
        platform_players.append([])

    while is_running:

        try:
            conn = Platform.get_connect()
            cursor = conn.cursor()

            for i in range(len(platforms)):
                if datetime.datetime.now().replace(tzinfo=timezone.utc) > \
                        dt_next_update[i].replace(tzinfo=timezone.utc):
                    renew_log.info("Update platform {0}, next update {1}".format(platforms[i].name, dt_next_update[i]))
                    platforms[i].set_next_language()
                    cursor.execute("""
                                        select count(1) from achievements_hunt.update_history where id_platform = %s
                                        and dt_ended is null
                                        and id_process = 2
                                        """, (platforms[i].id,))
                    cnt, = cursor.fetchone()
                    if cnt == 0:
                        cursor.execute("""
                                                            insert into achievements_hunt.update_history(id_platform, id_process)
                                                            values (%s, 2)
                                                            """, (platforms[i].id,))
                        conn.commit()
                    if platforms[i].get_consoles is not None:
                        try:
                            platforms[i].set_consoles(platforms[i].get_consoles())
                            platforms[i].save()
                        except BaseException as exc:
                            renew_log.exception(exc)
                            try:
                                conn.rollback()
                            except BaseException as err:
                                queue_log.exception(err)
                            dt_next_update[i] = datetime.datetime.now() + \
                                                datetime.timedelta(seconds=platforms[i].config.update_interval)
                            conn = Platform.get_connect()
                            cursor = conn.cursor()
                            cursor.execute("""
                                                            update achievements_hunt.update_history
                                                                set dt_ended = current_timestamp,
                                                                dt_next_update = %s
                                                                where id_platform = %s
                                                                and dt_ended is null
                                                                and id_process = 2
                                                            """, (dt_next_update[i],platforms[i].id))
                            conn.commit()
                            renew_log.info(
                                "Update platform {0} skipped because of consoles not available".format(platforms[i].name))
                            continue
                    platforms[i].load_games()
                    games_num = len(platforms[i].games)
                    games_ext_ids = list(platforms[i].games.keys())
                    for j in range(len(games_ext_ids)):
                        game = platforms[i].games[games_ext_ids[j]]
                        platforms[i].logger.info(
                            "Update game with id {} and name {}. Progress {}/{}".
                            format(game.ext_id, game.name, j, games_num))
                        platforms[i].update_games(game.ext_id, game.name, True)
                        platforms[i].logger.info(
                            "Get achievements for game with id {} and name {}. Progress {}/{}".format(
                               game.ext_id, game.name, j + 1, games_num))
                    platforms[i].save()
                    dt_next_update[i] = datetime.datetime.now() + \
                                        datetime.timedelta(seconds=platforms[i].config.update_interval)
                    platforms[i].mark_language_done()
                    platforms[i].reset_games()
                    renew_log.info("Update platform {0} finished, next_update {1}".format(platforms[i].name,
                                                                                          dt_next_update[i]))
                    conn = Platform.get_connect()
                    cursor = conn.cursor()
                    cursor.execute("""
                            update achievements_hunt.update_history
                                set dt_ended = current_timestamp,
                                dt_next_update = %s
                                where id_platform = %s
                                and dt_ended is null
                                and id_process = 2
                            """, (dt_next_update[i],platforms[i].id))
                    conn.commit()
                else:
                    renew_log.debug("Skip update platform {0}, next update {1}".format(
                       platforms[i].name, dt_next_update[i]))
        except BaseException as err:
            queue_log.exception(err)
            if config.supress_errors:
                try:
                    conn.rollback()
                except BaseException as exc:
                    queue_log.exception(exc)
                time.sleep(5)
            else:
                raise

        try:

            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()

            for method_frame, properties, body in m_channel.consume(GAME_UPDATER_QUEUE_NAME, inactivity_timeout=1,
                                                                    auto_ack=False):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    if cmd_type == 'stop_server':
                        is_running = False
                        cmd = {"cmd": "process_response", "text": "Game updater shutdown started"}
                        enqueue_command(cmd, MODE_BOT)
                    elif cmd_type == "get_stats":
                        msg = get_stats()
                        # TODO less expensive way
                        cursor.execute("""
                                select count(1), p.name
                                from achievements_hunt.players pl
                                join achievements_hunt.platforms p
                                  on p.id = pl.platform_id
                                group by p.name
                                """)
                        msg["players"] = {}
                        for cnt, platform_name in cursor:
                            msg["players"][platform_name] = cnt
                        conn.commit()
                        msg["module"] = "Worker"
                        msg["platform_stats"] = {}
                        for j in platforms:
                            msg["platform_stats"][j.name] = str(j.get_stats())
                        cmd = {"cmd": "process_response", "text": str(msg)}
                        enqueue_command(cmd, MODE_BOT)
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
                    queue_log.info("No more messages in {0}".format(GAME_UPDATER_QUEUE_NAME))
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
                try:
                    conn.rollback()
                except BaseException as exc:
                    queue_log.exception(exc)
                pass
            else:
                raise
