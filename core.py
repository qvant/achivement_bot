import json
import datetime
import time

from lib.config import Config, MODE_BOT
from lib.log import get_logger
from lib.platform import Platform
from lib.queue import set_config as set_queue_config, set_logger as set_queue_log, get_mq_connect, MAIN_QUEUE_NAME, \
    enqueue_command
from lib.queue_handlers import on_create, on_delete
from lib.stats import get_stats
from lib.telegram import set_logger, set_platforms, set_connect
from lib.db import load, load_players, set_load_logger


def main_core(config: Config):
    queue_log = get_logger("Rabbit_core", config.log_level, True)

    set_load_logger(config)
    set_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config, load_achievements=False, load_games=False)
    set_platforms(platforms)
    set_connect(Platform.get_connect())

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=MAIN_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='achievement_hunt',
                               exchange_type='direct',
                               durable=True)
    m_channel.queue_bind(exchange='achievement_hunt',
                         queue=MAIN_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    cmd = {"cmd": "process_response", "text": "Core started at {0}.".format(datetime.datetime.now())}
    enqueue_command(cmd, MODE_BOT)

    while is_running:

        try:
            for method_frame, properties, body in m_channel.consume(MAIN_QUEUE_NAME, inactivity_timeout=1,
                                                                    auto_ack=False,
                                                                    arguments={"routing_key": config.mode}):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    platform_id = cmd.get("platform_id")
                    player_id = cmd.get("player_id")
                    if cmd_type == 'create_player':
                        for i in platforms:
                            if i.id == platform_id:
                                players = load_players(platform=i, config=config, player_id=player_id)
                                if len(players) > 0:
                                    player = players[0]
                                    on_create(platform=i, player=player)
                                    queue_log.error("Player {0} validated".format(player_id))
                                else:
                                    queue_log.error("Player {0} not found".format(player_id))
                    elif cmd_type == 'delete_user':
                        for i in platforms:
                            if i.id == platform_id:
                                players = load_players(platform=i, config=config, player_id=player_id)
                                if len(players) > 0:
                                    player = players[0]
                                    on_delete(platform=i, player=player)
                                    queue_log.error("Player {0} deleted".format(player_id))
                                else:
                                    queue_log.error("Player {0} not found".format(player_id))
                    elif cmd_type == 'stop_server':
                        is_running = False
                        cmd = {"cmd": "process_response", "text": "Core shutdown started"}
                        enqueue_command(cmd, MODE_BOT)
                    elif cmd_type == "get_stats":
                        msg = get_stats()
                        msg["module"] = "Core"
                        msg["platform_stats"] = {}
                        for i in platforms:
                            msg["platform_stats"][i.name] = str(i.get_stats())
                        cmd = {"cmd": "process_response", "text": str(msg)}
                        enqueue_command(cmd, MODE_BOT)
                    elif cmd_type == "msg_to_user":
                        if cmd.get("telegram_id") is not None:
                            enqueue_command(cmd, MODE_BOT)
                        else:
                            queue_log.info("Message resening terminated {0}")
                    else:
                        queue_log.info("Unknown command type {0}".format(cmd_type))
                    m_channel.basic_ack(method_frame.delivery_tag)
                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(MAIN_QUEUE_NAME))
                    m_channel.cancel()
                    break
            time.sleep(4)
        except BaseException as err:
            queue_log.critical(err)
            queue_log.exception(err)
            if config.supress_errors:
                queue_log.info("Continue work because supress errors mode")
            else:
                raise
