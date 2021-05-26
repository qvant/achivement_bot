import datetime
import json

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from lib.config import Config
from lib.log import get_logger
from lib.platform import Platform
from lib.queue import set_logger as set_queue_log, set_config as set_queue_config, get_mq_connect, BOT_QUEUE_NAME
from lib.queue_handlers import set_telegram
from lib.telegram import set_logger, telegram_init, set_connect, set_config as set_telegram_config, set_platforms, \
    start, echo, main_menu, account_choice, platform_choice, game_choice, game_navigation, achievement_navigation, \
    locale_choice, admin_choice, shutdown_choice, stats_choice
from lib.db import load, set_load_logger


def main_bot(config: Config):
    queue_log = get_logger("Rabbit_bot", config.log_level, True)
    set_load_logger(config)
    set_logger(config)
    set_queue_log(queue_log)
    telegram_init()
    Platform.set_config(config)
    set_connect(Platform.get_connect())
    set_telegram_config(config)
    platforms = load(config, True, False)
    set_platforms(platforms)

    set_queue_config(config)

    updater = Updater(token=config.secret, use_context=True)
    dispatcher = updater.dispatcher

    set_telegram(updater.dispatcher.bot)
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    main_menu_handler = CallbackQueryHandler(main_menu, pattern="main_")
    account_choice_handler = CallbackQueryHandler(account_choice, pattern="accounts_")
    platform_menu_handler = CallbackQueryHandler(platform_choice, pattern="PLATFORM_")
    games_menu_handler = CallbackQueryHandler(game_choice, pattern="games_")
    games_navigation_handler = CallbackQueryHandler(game_navigation, pattern="list_of_games")
    achievement_navigation_handler = CallbackQueryHandler(achievement_navigation, pattern="list_of_achievements")
    language_handler = CallbackQueryHandler(locale_choice, pattern="LOCALE")
    admin_handler = CallbackQueryHandler(admin_choice, pattern="admin_")
    shutdown_handler = CallbackQueryHandler(shutdown_choice, pattern="shutdown_")
    stats_handler = CallbackQueryHandler(stats_choice, pattern="stats_")
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(main_menu_handler)
    dispatcher.add_handler(platform_menu_handler)
    dispatcher.add_handler(account_choice_handler)
    dispatcher.add_handler(games_menu_handler)
    dispatcher.add_handler(games_navigation_handler)
    dispatcher.add_handler(achievement_navigation_handler)
    dispatcher.add_handler(language_handler)
    dispatcher.add_handler(admin_handler)
    dispatcher.add_handler(shutdown_handler)
    dispatcher.add_handler(stats_handler)

    updater.start_polling()

    for i in config.admin_list:
        updater.dispatcher.bot.send_message(chat_id=i,
                                            text="Bot started at {0}.".format(datetime.datetime.now()))
    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=BOT_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='main',
                               exchange_type='direct')
    m_channel.queue_bind(exchange='main',
                         queue=BOT_QUEUE_NAME,
                         routing_key=config.mode)
    is_running = True

    while is_running:

        try:

            for method_frame, properties, body in m_channel.consume(BOT_QUEUE_NAME, inactivity_timeout=5,
                                                                    auto_ack=False,
                                                                    arguments={"routing_key": config.mode}):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    # cmd_response_callback(None, method_frame, properties, body)
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    chat_id = cmd.get("chat_id")
                    if cmd_type == 'msg_to_user':
                        updater.dispatcher.bot.send_message(chat_id=chat_id, text=cmd.get("text"))
                    elif cmd_type == 'stop_server':
                        is_running = False
                        queue_log.info("Stop smd received")
                    elif cmd_type == "process_response":
                        for i in config.admin_list:
                            updater.dispatcher.bot.send_message(chat_id=i, text=cmd.get("text"))
                    m_channel.basic_ack(method_frame.delivery_tag)
                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(BOT_QUEUE_NAME))
                    m_channel.cancel()
                    break
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise
    updater.stop()
    queue_log.info("Job finished.")
    exit(0)