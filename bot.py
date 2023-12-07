import datetime
import json
import time

import telegram
from telegram import InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from lib.config import Config
from lib.log import get_logger
from lib.platform import Platform
from lib.queue import set_logger as set_queue_log, set_config as set_queue_config, get_mq_connect, BOT_QUEUE_NAME
from lib.queue_handlers import set_telegram
from lib.telegram import set_telegram_logger, telegram_init, set_connect, set_config as set_telegram_config, \
    set_platforms, \
    start, echo, main_menu, account_choice, platform_choice, game_choice, game_navigation, achievement_navigation, \
    locale_choice, admin_choice, shutdown_choice, stats_choice, set_locale, main_keyboard, achievement_detail, \
    consoles_navigation
from lib.db import load, set_load_logger
from lib.message_types import MT_VALIDATION_OK, MT_VALIDATION_FAILED, MT_ACCOUNT_DELETED, MT_ACCOUNT_UPDATED


def main_bot(config: Config):
    queue_log = get_logger("Rabbit_bot", config.log_level, True)
    set_load_logger(config)
    set_telegram_logger(config)
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
    set_handlers(dispatcher)

    updater.start_polling()

    for i in config.admin_list:
        updater.dispatcher.bot.send_message(chat_id=i,
                                            text="Bot started at {0}.".format(datetime.datetime.now()))
    m_channel = init_queue(config)
    is_running = True

    while is_running:

        try:

            for method_frame, properties, body in m_channel.consume(BOT_QUEUE_NAME, inactivity_timeout=1,
                                                                    auto_ack=False,
                                                                    arguments={"routing_key": config.mode}):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    is_running = process_queue_command(body, config, is_running, queue_log, updater)
                    m_channel.basic_ack(method_frame.delivery_tag)
                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(BOT_QUEUE_NAME))
                    m_channel.cancel()
                    break
            time.sleep(4)
        except BaseException as err:
            queue_log.exception(err)
            if config.supress_errors:
                pass
            else:
                raise
    updater.stop()
    queue_log.info("Job finished.")
    exit(0)


def process_queue_command(body, config, is_running, queue_log, updater):
    cmd = json.loads(body)
    cmd_type = cmd.get("cmd")
    chat_id = cmd.get("chat_id")
    if cmd_type == 'msg_to_user':
        _ = set_locale(update=None, chat_id=chat_id)
        msg = ""
        msg_type = cmd.get("type")
        if msg_type == MT_VALIDATION_OK:
            msg = _('Validation for account {} platform {} ok').format(
                cmd.get("ext_id"), cmd.get("platform"))
        elif msg_type == MT_VALIDATION_FAILED:
            msg = _('Validation for account {} platform {} failed').format(
                cmd.get("ext_id"), cmd.get("platform"))
        elif msg_type == MT_ACCOUNT_DELETED:
            msg = _('Account {} for platform {} deleted').format(
                cmd.get("name"), cmd.get("platform"))
        elif msg_type == MT_ACCOUNT_UPDATED:
            msg = _('Stats for account {} and platform {} renewed').format(
                cmd.get("name"), cmd.get("platform"))
        else:
            queue_log.error("Nothing to respond in msg {0}".format(body))
        if len(msg) > 0:
            reply_markup = InlineKeyboardMarkup(main_keyboard(chat_id))
            try:
                updater.dispatcher.bot.send_message(chat_id=chat_id,
                                                    text=msg,
                                                    reply_markup=reply_markup)
            except telegram.error.Unauthorized:
                queue_log.info("Bot banned by user {}, can\'t send message".format(chat_id))
    elif cmd_type == 'stop_server':
        is_running = False
        queue_log.info("Stop smd received")
    elif cmd_type == "process_response":
        try:
            resp = eval(cmd.get("text"))
            msg = ""
            for i in resp:
                if i == "platform_stats":
                    msg += r"  " + i + ": " + chr(10)
                    for j in sorted(resp[i]):
                        msg += r"    " + j + ": " + chr(10)
                        cur = eval(resp[i][j])
                        for m in cur:
                            msg += r"      " + m + ": " + chr(10)
                            for k in cur[m]:
                                msg += r"        " + k + ": " + str(cur[m][k]) + chr(10)
                elif i == "players":
                    msg += r"  " + i + ": " + chr(10)
                    for j in sorted(resp[i]):
                        msg += r"    " + j + ": " + str(resp[i][j]) + chr(10)
                else:
                    msg += i + ": " + str(resp.get(i)) + chr(10)
        except SyntaxError:
            msg = cmd.get("text")
        for i in config.admin_list:
            reply_markup = InlineKeyboardMarkup(main_keyboard(i))
            updater.dispatcher.bot.send_message(chat_id=i, text=msg, reply_markup=reply_markup)
    return is_running


def init_queue(config):
    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=BOT_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='achievement_hunt',
                               exchange_type='direct',
                               durable=True)
    m_channel.queue_bind(exchange='achievement_hunt',
                         queue=BOT_QUEUE_NAME,
                         routing_key=config.mode)
    return m_channel


def set_handlers(dispatcher):
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    main_menu_handler = CallbackQueryHandler(main_menu, pattern="main_")
    account_choice_handler = CallbackQueryHandler(account_choice, pattern="accounts_")
    platform_menu_handler = CallbackQueryHandler(platform_choice, pattern="PLATFORM_")
    games_menu_handler = CallbackQueryHandler(game_choice, pattern="games_")
    games_navigation_handler = CallbackQueryHandler(game_navigation, pattern="list_of_games")
    consoles_navigation_handler = CallbackQueryHandler(consoles_navigation, pattern="list_of_consoles")
    achievement_navigation_handler = CallbackQueryHandler(achievement_navigation, pattern="list_of_achievements")
    language_handler = CallbackQueryHandler(locale_choice, pattern="LOCALE")
    admin_handler = CallbackQueryHandler(admin_choice, pattern="admin_")
    shutdown_handler = CallbackQueryHandler(shutdown_choice, pattern="shutdown_")
    stats_handler = CallbackQueryHandler(stats_choice, pattern="stats_")
    achievement_detail_handler = CallbackQueryHandler(achievement_detail, pattern="ACHIEVEMENT_ID_")
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(main_menu_handler)
    dispatcher.add_handler(platform_menu_handler)
    dispatcher.add_handler(account_choice_handler)
    dispatcher.add_handler(games_menu_handler)
    dispatcher.add_handler(games_navigation_handler)
    dispatcher.add_handler(consoles_navigation_handler)
    dispatcher.add_handler(achievement_navigation_handler)
    dispatcher.add_handler(language_handler)
    dispatcher.add_handler(admin_handler)
    dispatcher.add_handler(shutdown_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(achievement_detail_handler)
