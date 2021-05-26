import datetime
import json
from datetime import timezone

import pika

from lib.config import Config, MODE_BOT, MODE_WORKER
from lib.log import get_logger
from lib.platform import Platform
from lib.queue import set_config as set_queue_config, set_logger as set_queue_log, get_mq_connect, WORKER_QUEUE_NAME, \
    enqueue_command
from lib.stats import get_stats
from lib.telegram import set_logger, set_platforms, set_connect
from lib.db import load, load_players, set_load_logger


def main_worker(config: Config):
    queue_log = get_logger("Rabbit_worker", config.log_level, True)
    renew_log = get_logger("renew_worker", config.log_level, True)

    set_load_logger(config)
    set_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config)
    set_platforms(platforms)
    set_connect(Platform.get_connect())

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()

    m_channel.queue_declare(queue=WORKER_QUEUE_NAME, durable=True)

    m_channel.exchange_declare(exchange='main',
                               exchange_type='direct')
    m_channel.queue_bind(exchange='main',
                         queue=WORKER_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    dt_next_update = []
    conn = Platform.get_connect()
    cursor = conn.cursor()
    for i in platforms:
        cursor.execute("""
        select max(dt_next_update) from achievements_hunt.update_history where id_platform = %s and dt_ended is not null
        """, (i.id, ))
        ret = cursor.fetchone()
        if ret is not None and ret[0] is not None:
            dt_next_update.append(ret[0])
        else:
            dt_next_update.append(datetime.datetime.now())
        i.reset_games()
        i.load_languages()
        i.set_next_language()

    cur_players = []
    platform_players = []

    while is_running:

        try:

            for i in range(len(platforms)):
                if datetime.datetime.now().replace(tzinfo=timezone.utc) > \
                        dt_next_update[i].replace(tzinfo=timezone.utc):
                    renew_log.info("Update platform {0}, next update {1}".format(platforms[i].name, dt_next_update[i]))
                    platforms[i].set_next_language()
                    cursor.execute("""
                    select count(1) from achievements_hunt.update_history where id_platform = %s 
                    and dt_ended is null
                    """, (platforms[i].id,))
                    cnt, = cursor.fetchone()
                    if cnt == 0:
                        cursor.execute("""
                                        insert into achievements_hunt.update_history(id_platform) 
                                        values (%s)
                                        """, (platforms[i].id,))
                        conn.commit()
                    if len(platform_players) == 0:
                        renew_log.info("Update loading players for platform {0}".format(platforms[i].name))
                        platform_players.append(load_players(platforms[i], config))
                        cur_players.append(0)
                    else:
                        renew_log.info(
                            "Update platform {0} resumed from position {1}".format(platforms[i].name, cur_players[i]))
                    start_pos = 0
                    for j in range(cur_players[i], len(platform_players[i])):
                        cur_players[i] = j
                        renew_log.info("Update platform {0} for player {1}/{2}".format(platforms[i].name,
                                                                                       platform_players[i][j].ext_id,
                                                                                       len(platform_players[i])))
                        platform_players[i][j].renew()
                        platform_players[i][j].save()
                        start_pos += 1
                        if start_pos >= 100:
                            renew_log.info(
                                "Update platform {0} paused in position {1}".format(platforms[i].name, cur_players[i]))
                            break
                    platforms[i].save()
                    if cur_players[i] + 1 >= len(platform_players[i]):
                        dt_next_update[i] = datetime.datetime.now() + \
                                            datetime.timedelta(seconds=platforms[i].config.update_interval)
                        platform_players[i] = []
                        platforms[i].mark_language_done()
                        renew_log.info("Update platform {0} finished, next_update {1}".format(platforms[i].name,
                                                                                              dt_next_update[i]))
                        cursor.execute("""
                                update achievements_hunt.update_history 
                                    set dt_ended = current_timestamp, 
                                    dt_next_update = %s
                                    where id_platform = %s
                                    and dt_ended is null
                                """, (dt_next_update[i], platforms[i].id))
                        conn.commit()
                    else:
                        renew_log.info(
                            "Update platform {0} postponed, progress {1}/{2}".format(platforms[i].name, cur_players[i],
                                                                                     len(platform_players[i])))
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise

        try:

            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()

            for method_frame, properties, body in m_channel.consume(WORKER_QUEUE_NAME, inactivity_timeout=5,
                                                                    auto_ack=False):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    # cmd_response_callback(None, method_frame, properties, body)
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    if cmd_type == 'renew_achievements':
                        platform_id = cmd.get("platform_id")
                        player_id = cmd.get("player_id")
                        dt_sent = cmd.get("dt_sent")
                        dt_sent = datetime.datetime.fromtimestamp(dt_sent)
                        queue_log.info("Start renew achievements for player {2} and platform {3} because msg {0} "
                                       "with delivery_tag {1}".format(body, method_frame.delivery_tag,
                                                                      player_id, platform_id))
                        player = None
                        for i in platforms:
                            queue_log.debug("Check platform {0} {1}".format(i.name, i.id))
                            if int(i.id) == int(platform_id):
                                players = load_players(platform=i, config=config, player_id=player_id)
                                if len(players) > 0:
                                    player = players[0]
                                    if player.dt_updated is None or player.dt_updated.replace(tzinfo=timezone.utc) < \
                                            dt_sent.replace(tzinfo=timezone.utc):
                                        queue_log.info(
                                            "Start actially renew achievements for player {2}  and platform {3} "
                                            "becauese msg {0} with delivery_tag {1}".format(
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
                                                   player.ext_id, i.name)}
                                        enqueue_command(cmd, MODE_BOT)
                                    else:
                                        queue_log.info(
                                            "Skipped  renew achievements for player {2} and platform {3} because msg "
                                            "{0} with delivery_tag {1} was sent at {4} and last renew was {5}".format(
                                                body,
                                                method_frame.delivery_tag,
                                                player_id, i.name, dt_sent, player.dt_updated))
                                else:
                                    queue_log.error(
                                        "Player {0} for platform {1} wasn't found in db".format(player_id, platform_id))
                                pass
                        if player is None:
                            queue_log.error("Player {0} for platform {1} wasn't proceed".format(player_id, platform_id))

                    elif cmd_type == 'stop_server':
                        is_running = False
                        cmd = {"cmd": "process_response", "text": "Worker shutdown started"}
                        enqueue_command(cmd, MODE_WORKER)
                    elif cmd_type == "get_stats":
                        msg = get_stats()
                        # TODO less expensive way
                        cursor.execute("""
                                select count(1) from achievements_hunt.players
                                """)
                        res = cursor.fetchone()
                        msg["players"] = res[0]
                        msg["module"] = "Worker"
                        cmd = {"cmd": "process_response", "text": str(msg)}
                        enqueue_command(cmd, MODE_BOT)
                    try:
                        m_channel.basic_ack(method_frame.delivery_tag)
                    except BaseException as exc:
                        queue_log.info("User message " + str(body) + " with delivery_tag " +
                                       str(method_frame.delivery_tag) + " acknowledged with error, resending")
                        # TODO: handle
                        raise

                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(WORKER_QUEUE_NAME))
                    m_channel.cancel()
                    break
        except pika.exceptions.AMQPError as exc:
            queue_log.critical(exc)
            m_queue = get_mq_connect(config)
            m_channel = m_queue.channel()
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise
