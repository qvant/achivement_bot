import json
import datetime
import time
from logging import Logger

import psycopg2
import psycopg2.extras
from pika.adapters.blocking_connection import BlockingChannel

from lib.config import Config, MODE_BOT, MODE_CORE
from lib.log import get_logger
from lib.platform import Platform
from lib.query_holder import get_query, LOCK_QUEUE_GAMES_UPDATE, get_query_for_prepare, UPDATE_GAME_SET_NUM_OWNERS, \
    DELETE_QUEUE_GAMES_UPDATE, UPDATE_ACHIEVEMENT_SET_PERCENT_OWNERS, LOCK_QUEUE_ACHIEVEMENTS_UPDATE, \
    UPDATE_PLAYER_GAME_SET_PERCENT_COMPLETE, UPDATE_PLAYER_GAMES_SET_PERFECT, DELETE_QUEUE_ACHIEVEMENTS_UPDATE, \
    LOCK_QUEUE_PLAYER_ACHIEVEMENTS_UPDATE, UPDATE_ACHIEVEMENT_SET_NUM_OWNERS, \
    UPDATE_ACHIEVEMENTS_SET_PERCENT_OWNERS_BY_ID, UPDATE_PLAYER_GAME_SET_PERCENT_COMPLETE_BY_PLAYER, \
    DELETE_QUEUE_PLAYER_ACHIEVEMENTS_UPDATE, CHECK_QUEUE_GAMES_IS_EMPTY, CHECK_QUEUE_ACHIEVEMENTS_IS_EMPTY, \
    CHECK_QUEUE_PLAYER_ACHIEVEMENTS_UPDATE_IS_EMPTY
from lib.queue import set_config as set_queue_config, set_logger as set_queue_log, get_mq_connect, UPDATER_QUEUE_NAME, \
    enqueue_command
from lib.stats import get_stats
from lib.db import set_load_logger
from lib.db_api import set_db_config


def main_updater(config: Config):
    db_log, m_channel, queue_log = init_updater(config)

    is_running = True

    while is_running:

        queues_are_empty = True
        # TODO: split into procedures

        try:
            games_queue_are_empty = process_games_queue(config, db_log)
            achievements_queue_are_empty = process_achievements_queue(config, db_log)
            player_achievements_queue_are_empty = process_player_achievements_queue(config, db_log)
            queues_are_empty = \
                games_queue_are_empty and achievements_queue_are_empty and player_achievements_queue_are_empty
            db_log.debug("""Pause db queue processing, check rabbitMQ for new messages...""")
        except BaseException as err:
            db_log.exception(err)
            if config.supress_errors:
                pass
            else:
                raise

        need_to_stop = process_external_messages(config, m_channel, queue_log)
        if need_to_stop:
            is_running = False
        if queues_are_empty and is_running:
            # Additional sleep if all queues are empty, so there is noting to do.
            # Other processes has unconditional sleep between work cycles
            time.sleep(4)


def process_player_achievements_queue(config: Config, db_log: Logger) -> bool:
    # Process player achievements queue, renew percent of achievers and update player perfect games status
    db_log.debug("""Check queue_player_achievements_update""")
    connect = Platform.get_connect()
    cursor = connect.cursor()
    queue_is_empty = True
    query_prepared = False
    for step in range(config.db_update_cycles):
        db_log.debug("""Check queue_achievements_update, step {0}""".format(step))
        if step == 0:
            cursor.execute(get_query(CHECK_QUEUE_PLAYER_ACHIEVEMENTS_UPDATE_IS_EMPTY))
            exists = cursor.fetchone()
            if exists is None:
                connect.commit()
                db_log.debug("""Queue queue_achievements_update is empty""")
                break
        cursor.execute(get_query(LOCK_QUEUE_PLAYER_ACHIEVEMENTS_UPDATE), (config.db_update_size,))
        achievements = {}
        recs = []
        player_games = []
        for id_rec, achievement_id, player_id, game_id, platform_id, operation in cursor:
            if achievement_id not in achievements:
                achievements[achievement_id] = 0
            if operation == "INSERT":
                achievements[achievement_id] += 1
            else:
                achievements[achievement_id] -= 1
            recs.append((id_rec,))
            player_games.append((player_id, game_id, platform_id))
        if len(player_games) > 0:
            queue_is_empty = False
            db_log.info("""Process queue_player_achievements_update, found {0} records for {1} achievements""".
                        format(len(recs), len(achievements)))
            if not query_prepared:
                query_prepared = True
                cursor.execute(get_query_for_prepare("upd_achievements", UPDATE_ACHIEVEMENT_SET_NUM_OWNERS))
                cursor.execute(get_query_for_prepare("upd_achievement_percent",
                                                     UPDATE_ACHIEVEMENTS_SET_PERCENT_OWNERS_BY_ID))
                cursor.execute(get_query_for_prepare("update_player_games",
                                                     UPDATE_PLAYER_GAME_SET_PERCENT_COMPLETE_BY_PLAYER))
                cursor.execute(get_query_for_prepare("del_q", DELETE_QUEUE_PLAYER_ACHIEVEMENTS_UPDATE))
            game_res = []
            game_4_ach = []
            for i in achievements:
                game_res.append((achievements[i], i))
                game_4_ach.append((i,))

            psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievements (%s, %s)""", game_res)

            psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievement_percent (%s)""", game_4_ach)

            db_log.debug(""" start EXECUTE update_player_games""")
            psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games (%s, %s, %s)""", player_games)
            db_log.debug(""" end EXECUTE update_player_games""")

            db_log.debug(""" start EXECUTE del_q""")
            psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)
            db_log.debug(""" end EXECUTE del_q""")
            connect.commit()

        else:
            connect.commit()
            db_log.debug("""No more in queue queue_player_achievements_update on step {0}""".format(step))
            break
    if query_prepared:
        cursor.execute("""DEALLOCATE update_player_games""")
        cursor.execute("""DEALLOCATE upd_achievements""")
        cursor.execute("""DEALLOCATE del_q""")
        cursor.execute("""DEALLOCATE upd_achievement_percent""")
        connect.commit()
    db_log.debug("""Finish queue_player_achievements_update processing""")
    return queue_is_empty


def process_achievements_queue(config: Config, db_log: Logger) -> bool:
    # Process new achievements queue - reset perfect games and recalc % complete for all players
    db_log.debug("""Check queue_achievements_update""")
    queue_is_empty = True
    query_prepared = False
    connect = Platform.get_connect()
    cursor = connect.cursor()
    for step in range(config.db_update_cycles):
        db_log.debug("""Check queue_achievements_update, step {0}""".format(step))
        if step == 0:
            cursor.execute(get_query(CHECK_QUEUE_ACHIEVEMENTS_IS_EMPTY))
            exists = cursor.fetchone()
            if exists is None:
                db_log.debug("""Queue queue_achievements_update is empty""")
                break
        cursor.execute(get_query(LOCK_QUEUE_ACHIEVEMENTS_UPDATE), (config.db_update_size,))
        recs = []
        games = []
        games_ids = []
        for id_rec, game_id, platform_id in cursor:
            if game_id not in games_ids:
                games_ids.append(game_id)
                games.append((game_id, platform_id))
            recs.append((id_rec,))
        if len(games) > 0:
            queue_is_empty = False
            db_log.info("""Process queue_achievements_update, found {0} records for {1} games""".
                        format(len(recs), len(games_ids)))
            if not query_prepared:
                query_prepared = True
                cursor.execute(get_query_for_prepare("update_player_games",
                                                     UPDATE_PLAYER_GAME_SET_PERCENT_COMPLETE))
                cursor.execute(get_query_for_prepare("update_player_games_perf", UPDATE_PLAYER_GAMES_SET_PERFECT))
                cursor.execute(get_query_for_prepare("del_q", DELETE_QUEUE_ACHIEVEMENTS_UPDATE))
            psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games  (%s, %s)""", games)
            # TODO: check if possible one query instead of two
            psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games_perf  (%s, %s)""", games)

            psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)
            connect.commit()
        else:
            connect.commit()
            db_log.debug("""No more in queue queue_achievements_update on step {0}""".format(step))
            break
    if query_prepared:
        cursor.execute("""DEALLOCATE  update_player_games""")
        cursor.execute("""DEALLOCATE  update_player_games_perf""")
        cursor.execute("""DEALLOCATE  del_q""")
        connect.commit()
    db_log.debug("""Finish queue_achievements_update processing""")
    return queue_is_empty


def process_games_queue(config: Config, db_log: Logger) -> bool:
    queue_is_empty = True
    db_log.debug("""Check queue_games_update""")
    connect = Platform.get_connect()
    cursor = connect.cursor()
    query_prepared = False
    # Process new games queue - recalc owner numbers and percent of achievers
    for step in range(config.db_update_cycles):
        db_log.debug("""Check queue_games_update, step {0}""".format(step))
        if step == 0:
            cursor.execute(get_query(CHECK_QUEUE_GAMES_IS_EMPTY))
            exists = cursor.fetchone()
            if exists is None:
                db_log.debug("""Queue queue_games_update is empty""")
                break
        cursor.execute(get_query(LOCK_QUEUE_GAMES_UPDATE), (config.db_update_size,))
        games = {}
        recs = []
        for id_rec, game_id, operation in cursor:
            if game_id not in games:
                games[game_id] = 0
            if operation == "INSERT":
                games[game_id] += 1
            else:
                games[game_id] -= 1
            recs.append((id_rec,))
        if len(games) > 0:
            db_log.info("""Process queue_games_update, found {0} records for {1} games""".
                        format(len(recs), len(games)))
            queue_is_empty = False
            # TODO: constants
            if not query_prepared:
                query_prepared = True
                cursor.execute(get_query_for_prepare("upd_games", UPDATE_GAME_SET_NUM_OWNERS))
                cursor.execute(get_query_for_prepare("del_q", DELETE_QUEUE_GAMES_UPDATE))
                cursor.execute(get_query_for_prepare("upd_achievement", UPDATE_ACHIEVEMENT_SET_PERCENT_OWNERS))
            game_res = []
            game_4_ach = []
            for i in games:
                game_res.append((games[i], i))
                game_4_ach.append((i,))
            psycopg2.extras.execute_batch(cursor, """EXECUTE upd_games (%s, %s)""", game_res)
            psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievement (%s)""", game_4_ach)
            psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)
            connect.commit()
        else:
            connect.commit()
            db_log.debug("""No more in queue queue_games_update on step {0}""".format(step))
            break
    if query_prepared:
        cursor.execute("""DEALLOCATE upd_games""")
        cursor.execute("""DEALLOCATE del_q""")
        cursor.execute("""DEALLOCATE upd_achievement""")
        connect.commit()
    db_log.debug("""Finish queue_games_update processing""")
    return queue_is_empty


def process_external_messages(config: Config, m_channel: BlockingChannel, queue_log: Logger) -> bool:
    need_to_stop = False
    try:
        for method_frame, properties, body in m_channel.consume(UPDATER_QUEUE_NAME, inactivity_timeout=1,
                                                                auto_ack=False,
                                                                arguments={"routing_key": config.mode}):
            if body is not None:
                queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                        method_frame.delivery_tag))
                need_to_stop = process_queue_message(body)
                m_channel.basic_ack(method_frame.delivery_tag)
                queue_log.info("User message " + str(body) + " with delivery_tag " +
                               str(method_frame.delivery_tag) + " acknowledged")
            else:
                queue_log.debug("No more messages in {0}".format(UPDATER_QUEUE_NAME))
                m_channel.cancel()
                break

    except BaseException as err:
        queue_log.exception(err)
        if config.supress_errors:
            pass
        else:
            raise
    return need_to_stop


def process_queue_message(body: bytes) -> bool:
    cmd = json.loads(body)
    cmd_type = cmd.get("cmd")
    need_to_stop = False
    if cmd_type == 'stop_server':
        need_to_stop = True
        cmd = {"cmd": "process_response", "text": "Updater shutdown started"}
        enqueue_command(cmd, MODE_BOT)
    elif cmd_type == "get_stats":
        msg = get_stats()
        msg["module"] = "Updater"
        cmd = {"cmd": "process_response", "text": str(msg)}
        enqueue_command(cmd, MODE_BOT)
    elif cmd_type == "msg_to_user":
        enqueue_command(cmd, MODE_CORE)
    return need_to_stop


def init_updater(config: Config):
    queue_log = get_logger("Rabbit" + str(config.mode), config.log_level, True)
    db_log = get_logger("db_" + str(config.mode), config.log_level, True)
    set_load_logger(config)
    set_db_config(config)
    set_queue_config(config)
    set_queue_log(queue_log)
    Platform.set_config(config)
    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=UPDATER_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='achievement_hunt',
                               exchange_type='direct',
                               durable=True)
    m_channel.queue_bind(exchange='achievement_hunt',
                         queue=UPDATER_QUEUE_NAME,
                         routing_key=config.mode)
    cmd = {"cmd": "process_response", "text": "Updater started at {0}.".format(datetime.datetime.now())}
    enqueue_command(cmd, MODE_BOT)
    return db_log, m_channel, queue_log
