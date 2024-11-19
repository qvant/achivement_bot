import pika
import json
import time
from typing import Dict
from .config import Config
from logging import Logger

MAIN_QUEUE_NAME = "AchievementQueue"
UPDATER_QUEUE_NAME = "AchievementQueueUpdater"
BOT_QUEUE_NAME = "AchievementQueueBot"
WORKER_QUEUE_NAME = "AchievementQueueWorker"
GAME_UPDATER_QUEUE_NAME = "AchievementQueueGameUpdater"

global queue_logger
global config


def get_mq_connect(mq_config: Config) -> pika.BlockingConnection:
    if mq_config.queue_password is None:
        return pika.BlockingConnection(pika.ConnectionParameters(host=mq_config.queue_host, port=mq_config.queue_port))
    else:
        return pika.BlockingConnection(pika.ConnectionParameters(host=mq_config.queue_host, port=mq_config.queue_port,
                                                                 credentials=pika.credentials.PlainCredentials(
                                                                     mq_config.queue_user, mq_config.queue_password)))


def set_config(cfg: Config):
    global config
    config = cfg


def set_logger(logger: Logger):
    global queue_logger
    queue_logger = logger


def enqueue_command(obj: Dict, send_to: str):
    global queue_logger
    global config

    obj["dt_sent"] = time.time()

    msg_body = json.dumps(obj)
    try:
        queue = get_mq_connect(config)
        channel = queue.channel()
        channel.basic_publish(exchange="achievement_hunt", routing_key=send_to,
                              body=msg_body, properties=pika.BasicProperties(delivery_mode=2,
                                                                             content_type="application/json",
                                                                             content_encoding="UTF-8"))
        queue.close()
        queue_logger.info("Sent command {} for {}".format(msg_body, send_to))
    except pika.exceptions.AMQPError as exc:
        queue_logger.critical("Error {1} when Sent command {0} for {2}".format(msg_body, exc, send_to))
