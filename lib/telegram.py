import gettext
_ = gettext.gettext

en = gettext.translation('base', localedir='locale', languages=['en'])
en.install()
ru = gettext.translation('base', localedir='locale', languages=['ru'])
ru.install()

from .config import Config, MODE_CORE, MODE_WORKER, MODE_UPDATER, MODE_BOT
from .platform import Platform
from .player import Player, GAMES_ALL, GAMES_PERFECT, GAMES_WITH_ACHIEVEMENTS
from .log import get_logger
from .queue import enqueue_command
from .stats import get_stats
from typing import Union, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, CallbackQueryHandler
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

global telegram_logger
global platforms
global db
global register_progress
global players_by_tlg_id
global games_by_player_id
global user_states
global user_games_offsets
global user_achievement_offsets
global user_active_accounts
global user_locales
global user_games_modes
global users_in_delete_process
global config

MAX_MENU_LENGTH = 30
MAX_MENU_ITEMS = 8

GAME_MENU_LENGTH = 10
ACHIEVEMENT_MENU_LENGTH = 10

GAMES_LIST_FIRST = "list_of_games_first"
GAMES_LIST_PREV = "list_of_games_prev"
GAMES_LIST_NEXT = "list_of_games_next"
GAMES_LIST_LAST = "list_of_games_last"
GAMES_LIST_INDEX = "list_of_games_index"
GAMES_LIST_ONLY_ACHIEVEMENTS = "list_of_games_only_achievements"
GAMES_LIST_ONLY_PERFECT = "list_of_games_only_perfect"
GAMES_LIST_ALL = "list_of_games_all"
GAMES_LIST_BACK = "list_of_games_back"

ACHIEVEMENTS_LIST_FIRST = "list_of_achievements_first"
ACHIEVEMENTS_LIST_PREV = "list_of_achievements_prev"
ACHIEVEMENTS_LIST_NEXT = "list_of_achievements_next"
ACHIEVEMENTS_LIST_LAST = "list_of_achievements_last"
ACHIEVEMENTS_LIST_BACK = "list_of_achievements_back"

SHUTDOWN_CORE = "shutdown_core"
SHUTDOWN_BOT = "shutdown_bot"
SHUTDOWN_UPDATER = "shutdown_updater"
SHUTDOWN_WORKER = "shutdown_worker"

STATS_CORE = "stats_core"
STATS_BOT = "stats_bot"
STATS_UPDATER = "stats_updater"
STATS_WORKER = "stats_worker"

LOCALE_DYNAMIC = "LOCALE_DYNAMIC"
LOCALE_RU = "LOCALE_RU"
LOCALE_EN = "LOCALE_EN"


def telegram_init():
    global register_progress
    global players_by_tlg_id
    global games_by_player_id
    global user_states
    global user_games_offsets
    global user_achievement_offsets
    global user_active_accounts
    global user_locales
    global user_games_modes
    global users_in_delete_process
    user_states = {}
    user_games_offsets = {}
    user_achievement_offsets = {}
    user_active_accounts = {}
    register_progress = {}
    players_by_tlg_id = {}
    games_by_player_id = {}
    user_locales = {}
    user_games_modes = {}
    users_in_delete_process = {}


def pretty_menu(menu: List):
    res = [[]]
    cur_menu_len = 0
    cur_menu_items = 0
    for i in menu:
        if len(i.text) + cur_menu_len >= MAX_MENU_LENGTH or cur_menu_items >= MAX_MENU_ITEMS:
            res.append([])
            cur_menu_len = 0
            cur_menu_items = 0
        res[len(res) - 1].append(i)
        cur_menu_len += len(i.text)
        cur_menu_items += 1
    return res


def set_platforms(platform_list: [Platform]):
    global platforms
    platforms = platform_list


def set_connect(conn):
    global db
    db = conn

def set_config(cfg: Config):
    global config
    config = cfg


def platform_menu():
    global platforms
    keyboard = [
    ]
    for i in platforms:
        keyboard.append(InlineKeyboardButton(i.name, callback_data="PLATFORM_" + i.name))
    return pretty_menu(keyboard)


def platform_choice(update: Update, context: CallbackContext):
    global register_progress
    telegram_logger.info("Received command {0} from user {1} in platform_choice, callaback".
                         format(Update, update.effective_chat.id, context))
    set_locale(update)
    register_progress[update.effective_chat.id] = update["callback_query"]["data"][9:]
    context.bot.send_message(chat_id=update.effective_chat.id, text=_("Введите код аккаунта"))


def main_keyboard(chat_id: int):
    global db
    global platforms
    global config
    cursor = db.cursor()
    cursor.execute("""
                select id, platform_id, name, ext_id, dt_update from achievements_hunt.players where telegram_id = %s order by id
                """, (chat_id,))
    players_by_tlg_id[chat_id] = []

    for id, platform_id, name, ext_id, dt_update in cursor:
        for i in platforms:
            if i.id == platform_id:
                player = Player(name=name, platform=i, ext_id=ext_id, id=id, telegram_id=chat_id, dt_updated=dt_update)
                players_by_tlg_id[chat_id].append(player)
                user_games_offsets[chat_id] = 0
    keyboard = [
        InlineKeyboardButton(_("Новый аккаунт"), callback_data="main_NEW_ACCOUNT"),
        InlineKeyboardButton(_("Delete account"), callback_data="main_DELETE_ACCOUNT"),
        # TODO: remove later
        InlineKeyboardButton(_("Список игр"), callback_data="main_LIST_OF_GAMES"),
        InlineKeyboardButton(_("Выбор языка"), callback_data="main_SET_LOCALE"),
    ]
    for i in players_by_tlg_id[chat_id]:
        keyboard.append(InlineKeyboardButton("{}({})".format(i.name, i.platform.name), callback_data="accounts_" + str(i.id)),)
    if chat_id in config.admin_list:
        keyboard.append(InlineKeyboardButton(_("Администрирование"), callback_data="main_ADMIN"),)

    return pretty_menu(keyboard)


def account_keyboard(chat_id: int):
    global players_by_tlg_id
    keyboard = []
    for i in players_by_tlg_id[chat_id]:
        keyboard.append(InlineKeyboardButton("{}({})".format(i.name, i.platform.name), callback_data="accounts_" + str(i.id)),)

    return pretty_menu(keyboard)


def admin_keyboard():
    keyboard = [
        InlineKeyboardButton(_("Stats..."), callback_data="admin_stats"),
        InlineKeyboardButton(_("Shutdown..."), callback_data="admin_shutdown"),
    ]
    return pretty_menu(keyboard)


def shutdown_keyboard():
    keyboard = [
        InlineKeyboardButton(_("Shutdown core"), callback_data=SHUTDOWN_CORE),
        InlineKeyboardButton(_("Shutdown bot"), callback_data=SHUTDOWN_BOT),
        InlineKeyboardButton(_("Shutdown worker"), callback_data=SHUTDOWN_WORKER),
        InlineKeyboardButton(_("Shutdown updated"), callback_data=SHUTDOWN_UPDATER),
    ]
    return pretty_menu(keyboard)


def stats_keyboard():
    keyboard = [
        InlineKeyboardButton(_("Stats core"), callback_data=STATS_CORE),
        InlineKeyboardButton(_("Stats bot"), callback_data=STATS_BOT),
        InlineKeyboardButton(_("Stats worker"), callback_data=STATS_WORKER),
        InlineKeyboardButton(_("Stats updated"), callback_data=STATS_UPDATER),
    ]
    return pretty_menu(keyboard)


def games_keyboard(games, cur_games=GAMES_ALL):
    keyboard = []
    keyboard.append(InlineKeyboardButton(_("В начало"), callback_data=GAMES_LIST_FIRST))
    keyboard.append(InlineKeyboardButton(_("Предыдущая страница"), callback_data=GAMES_LIST_PREV))
    for i in games:
        keyboard.append(InlineKeyboardButton("{}".format(i.name), callback_data="games_of_" + str(i.id)),)
    keyboard.append(InlineKeyboardButton(_("Следующая страница"), callback_data=GAMES_LIST_NEXT))
    keyboard.append(InlineKeyboardButton(_("В конец"), callback_data=GAMES_LIST_LAST))
    keyboard.append(InlineKeyboardButton(_("Индекс"), callback_data=GAMES_LIST_INDEX))
    if cur_games == GAMES_ALL:
        keyboard.append(InlineKeyboardButton(_("С достижениями"), callback_data=GAMES_LIST_ONLY_ACHIEVEMENTS))
    elif cur_games == GAMES_WITH_ACHIEVEMENTS:
        keyboard.append(InlineKeyboardButton(_("Идеальные"), callback_data=GAMES_LIST_ONLY_PERFECT))
    else:
        keyboard.append(InlineKeyboardButton(_("Все игры"), callback_data=GAMES_LIST_ALL))
    keyboard.append(InlineKeyboardButton(_("Назад"), callback_data=GAMES_LIST_BACK))
    return pretty_menu(keyboard)


def games_index_keyboard():
    keyboard = []
    for i in range(26):
        keyboard.append(InlineKeyboardButton("{}".format(chr(97+i).upper()), callback_data="list_of_games_begin_" + chr(97+i)), )
    return pretty_menu(keyboard)


def achievements_keyboard():
    global players_by_tlg_id
    keyboard = []
    keyboard.append(InlineKeyboardButton(_("В начало"), callback_data=ACHIEVEMENTS_LIST_FIRST))
    keyboard.append(InlineKeyboardButton(_("Предыдущая страница"), callback_data=ACHIEVEMENTS_LIST_PREV))
    keyboard.append(InlineKeyboardButton(_("Следующая страница"), callback_data=ACHIEVEMENTS_LIST_NEXT))
    keyboard.append(InlineKeyboardButton(_("В конец"), callback_data=ACHIEVEMENTS_LIST_LAST))
    keyboard.append(InlineKeyboardButton(_("К списку игр"), callback_data=ACHIEVEMENTS_LIST_BACK))
    return pretty_menu(keyboard)


def new_account(update: Update, context: CallbackContext):
    set_locale(update)
    reply_markup = InlineKeyboardMarkup(platform_menu())
    context.bot.send_message(chat_id=update.effective_chat.id, text=_("Выберите платформу"), reply_markup=reply_markup)


def delete_account(update: Update, context: CallbackContext):
    global users_in_delete_process
    set_locale(update)
    users_in_delete_process[update.effective_chat.id] = update.effective_chat.id
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=_("Send message 'CONFIRM' (ALL LETTERS CAPITAL) to remove all data from system"))


def game_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global user_achievement_offsets
    chat_id = update.effective_chat.id
    cur_item = update["callback_query"]["data"][9:]
    telegram_logger.info("Received command {0} from user {1} in game_choice menu".
                         format(cur_item, update.effective_chat.id))
    locale = set_locale(update)
    telegram_logger.info("Locale {0} set for user {1}".
                         format(locale, update.effective_chat.id))
    player = get_player_by_chat_id(chat_id)
    if player is not None:
        player.get_achievement_stats(cur_item, locale)
        user_achievement_offsets[chat_id] = 0
        context.bot.send_message(chat_id=update.effective_chat.id, text=_("Игра выбрана"))
        show_account_achievements(update, context)
    else:
        account_choice(update, context)


def locale_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global user_locales
    chat_id = update.effective_chat.id
    cur_item = update["callback_query"]["data"][7:].lower()
    telegram_logger.info("Received command {0} from user {1} in locale_choice menu".
                         format(cur_item, update.effective_chat.id))
    user_locales[chat_id] = cur_item
    cursor = db.cursor()
    cursor.execute("""update achievements_hunt.users set locale = %s, dt_last_update = current_timestamp where telegram_id = %s""",
                   (cur_item, chat_id))
    db.commit()
    reply_markup = InlineKeyboardMarkup(main_keyboard(chat_id))
    context.bot.send_message(chat_id=chat_id, text=_("Язык выбран"),
                             reply_markup=reply_markup)


def admin_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    chat_id = update.effective_chat.id
    if chat_id in config.admin_list:
        cur_item = update["callback_query"]["data"]
        telegram_logger.info("Received command {0} from user {1} in admin_choice menu".
                             format(cur_item, update.effective_chat.id))
        if cur_item == "admin_shutdown":
            reply_markup = InlineKeyboardMarkup(shutdown_keyboard())
        else:
            reply_markup = InlineKeyboardMarkup(stats_keyboard())
        context.bot.send_message(chat_id=chat_id, text=_("Select action"),
                                 reply_markup=reply_markup)
    else:
        telegram_logger.critical("Received illegal cmd {1} from user {0} in admin_choice menu".
                             format(chat_id, update))


def shutdown_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    chat_id = update.effective_chat.id
    if chat_id in config.admin_list:
        cur_item = update["callback_query"]["data"]
        telegram_logger.info("Received command {0} from user {1} in shutdown_choice menu".
                             format(cur_item, update.effective_chat.id))
        cmd = {"cmd": "stop_server"}
        if cur_item == SHUTDOWN_BOT:
            enqueue_command(cmd, MODE_BOT)
            telegram_logger.info("Exit")
        elif cur_item == SHUTDOWN_CORE:
            enqueue_command(cmd, MODE_CORE)
        elif cur_item == SHUTDOWN_WORKER:
            enqueue_command(cmd, MODE_WORKER)
        elif cur_item == SHUTDOWN_UPDATER:
            enqueue_command(cmd, MODE_UPDATER)
        context.bot.send_message(chat_id=chat_id, text=_("Command sent: {0}".format(cmd)))
    else:
        telegram_logger.critical("Received illegal cmd {1} from user {0} in shutdown_choice menu".
                             format(chat_id, update))


def stats_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    chat_id = update.effective_chat.id
    if chat_id in config.admin_list:
        cur_item = update["callback_query"]["data"]
        telegram_logger.info("Received command {0} from user {1} in stats_choice menu".
                             format(cur_item, update.effective_chat.id))
        reply_markup = InlineKeyboardMarkup(stats_keyboard())
        if cur_item == STATS_BOT:
            msg = get_stats()
            msg["module"] = "Bot"
            context.bot.send_message(chat_id=chat_id, text=str(msg),
                                     reply_markup=reply_markup)
        else:
            cmd = {"cmd": "get_stats"}
            if cur_item == STATS_CORE:
                enqueue_command(cmd, MODE_CORE)
            elif cur_item == STATS_UPDATER:
                enqueue_command(cmd, MODE_UPDATER)
            elif cur_item == STATS_WORKER:
                enqueue_command(cmd, MODE_WORKER)
            context.bot.send_message(chat_id=chat_id, text=str("Command sent"),
                                     reply_markup=reply_markup)
    else:
        telegram_logger.critical("Received illegal cmd {1} from user {0} in stats_choice menu".
                             format(chat_id, update))


def game_navigation(update: Update, context: CallbackContext):
    global user_games_offsets
    global games_by_player_id
    global players_by_tlg_id
    global user_active_accounts
    global telegram_logger
    global user_games_modes
    chat_id = update.effective_chat.id
    cur_item = update["callback_query"]["data"]
    telegram_logger.info("Received command {0} from user {1} in game_navigation menu".
                         format(cur_item, update.effective_chat.id))
    set_locale(update)
    if chat_id not in user_games_offsets or chat_id not in user_active_accounts:
        user_games_offsets[chat_id] = 0
    elif user_active_accounts[chat_id] not in games_by_player_id:
        user_games_offsets[chat_id] = 0
    elif cur_item == GAMES_LIST_FIRST:
        user_games_offsets[chat_id] = 0
    elif cur_item == GAMES_LIST_PREV:
        user_games_offsets[chat_id] = max(0, user_games_offsets[chat_id] - GAME_MENU_LENGTH)
    elif cur_item == GAMES_LIST_NEXT:
        user_games_offsets[chat_id] =  \
            max(min(len(games_by_player_id[user_active_accounts[chat_id]]) - 1 - GAME_MENU_LENGTH,
                user_games_offsets[chat_id] + GAME_MENU_LENGTH), 0)
    elif cur_item == GAMES_LIST_LAST:
        user_games_offsets[chat_id] =  \
            max(0, len(games_by_player_id[user_active_accounts[chat_id]]) - 1 - GAME_MENU_LENGTH)
    elif cur_item.startswith("list_of_games_begin_"):
        user_games_offsets[chat_id] = 0
        letter = cur_item[20:]
        for i in range(len(games_by_player_id[user_active_accounts[chat_id]])):
            if games_by_player_id[user_active_accounts[chat_id]][i].name[:1].lower() == letter:
                user_games_offsets[chat_id] = i
                break
    telegram_logger.info("Set game offset = {1} for user {0} ".
                         format(update.effective_chat.id, user_games_offsets[update.effective_chat.id]))
    if cur_item in [GAMES_LIST_ONLY_ACHIEVEMENTS, GAMES_LIST_ALL, GAMES_LIST_ONLY_PERFECT]:
        if chat_id in user_active_accounts:
            for i in players_by_tlg_id[chat_id]:
                if str(i.id) == str(user_active_accounts[chat_id]):
                    user_active_accounts[chat_id] = i.id
                    if cur_item == GAMES_LIST_ALL:
                        i.get_owned_games(force=True)
                        user_games_modes[chat_id] = GAMES_ALL
                    elif cur_item == GAMES_LIST_ONLY_ACHIEVEMENTS:
                        i.get_owned_games(mode=GAMES_WITH_ACHIEVEMENTS, force=True)
                        user_games_modes[chat_id] = GAMES_WITH_ACHIEVEMENTS
                    elif cur_item == GAMES_LIST_ONLY_PERFECT:
                        i.get_owned_games(mode=GAMES_PERFECT, force=True)
                        user_games_modes[chat_id] = GAMES_PERFECT
                    games_by_player_id[user_active_accounts[chat_id]] = i.games
                    user_games_offsets[chat_id] = 0
            show_account_stats(update=update, context=context)
            show_account_games(update=update, context=context)
    elif cur_item == GAMES_LIST_BACK:
        start(update, context)
    elif cur_item != GAMES_LIST_INDEX:
        show_account_games(update=update, context=context)
    else:
        show_games_index(update=update, context=context)


def achievement_navigation(update: Update, context: CallbackContext):
    global user_achievement_offsets
    global user_active_accounts
    global telegram_logger
    not_ready = False
    cur_item = update["callback_query"]["data"]
    chat_id = update.effective_chat.id
    telegram_logger.info("Received command {0} from user {1} in achievement_navigation menu".
                         format(cur_item, chat_id))

    set_locale(update)

    if chat_id not in user_achievement_offsets or chat_id not in user_active_accounts:
        user_achievement_offsets[chat_id] = 0
        not_ready = True
    elif cur_item == ACHIEVEMENTS_LIST_FIRST:
        user_achievement_offsets[chat_id] = 0
    elif cur_item == ACHIEVEMENTS_LIST_PREV:
        user_achievement_offsets[chat_id] = max(0, user_achievement_offsets[chat_id] - ACHIEVEMENT_MENU_LENGTH)
    elif cur_item == ACHIEVEMENTS_LIST_NEXT:
        player = get_player_by_chat_id(chat_id)
        if player is not None:
            user_achievement_offsets[chat_id] =  \
                max(min(len(player.cur_achievement_stats) - ACHIEVEMENT_MENU_LENGTH,
                        user_achievement_offsets[chat_id] + ACHIEVEMENT_MENU_LENGTH), 0)
        else:
            not_ready = True
    elif cur_item == ACHIEVEMENTS_LIST_LAST:
        player = get_player_by_chat_id(chat_id)
        if player is not None:
            user_achievement_offsets[chat_id] = \
                max(len(player.cur_achievement_stats) - ACHIEVEMENT_MENU_LENGTH, 0)
        else:
            not_ready = True
    telegram_logger.info("Set achievements offset = {1} for user {0} ".
                         format(update.effective_chat.id, user_achievement_offsets[update.effective_chat.id]))
    if not_ready:
        account_choice(update, context)
    elif cur_item == ACHIEVEMENTS_LIST_BACK:
        game_navigation(update, context)
    else:
        show_account_achievements(update=update, context=context)


def locale_keyboard():
    keyboard = []
    keyboard.append(InlineKeyboardButton(_("ru"), callback_data=LOCALE_RU))
    keyboard.append(InlineKeyboardButton(_("en"), callback_data=LOCALE_EN))
    keyboard.append(InlineKeyboardButton(_("dynamic"), callback_data=LOCALE_DYNAMIC))
    return pretty_menu(keyboard)


def list_of_locales(update: Update, context: CallbackContext):
    set_locale(update)
    chat_id = update.effective_chat.id
    reply_markup = InlineKeyboardMarkup(locale_keyboard())
    context.bot.send_message(chat_id=chat_id, text=_("Выберите язык"),
                             reply_markup=reply_markup)


def list_of_games(update: Update, context: CallbackContext):
    global db
    global platforms
    global players_by_tlg_id
    global user_games_offsets
    chat_id = update.effective_chat.id
    cursor = db.cursor()
    cursor.execute("""
            select id, platform_id, name, ext_id from achievements_hunt.players where telegram_id = %s order by id
            """, (update.effective_chat.id,))
    players_by_tlg_id[update.effective_chat.id] = []
    set_locale(update)

    for id, platform_id, name, ext_id in cursor:
        for i in platforms:
            if i.id == platform_id:
                player = Player(name=name, platform=i, ext_id=ext_id, id=id, telegram_id=chat_id)
                players_by_tlg_id[chat_id].append(player)
                user_games_offsets[chat_id] = 0
    reply_markup = InlineKeyboardMarkup(account_keyboard(chat_id))
    context.bot.send_message(chat_id=chat_id, text=_("Выберите аккаунт для просмотра"),
                             reply_markup=reply_markup)


def main_menu(update: Update, context: CallbackContext):
    global telegram_logger
    cur_item = update["callback_query"]["data"][5:]
    telegram_logger.debug("Main menu called. Update {}".format(update))
    telegram_logger.debug("Main menu called. Context {}".format(context))
    telegram_logger.info("Received command {0} from user {1} in main menu".
                         format(cur_item, update.effective_chat.id))
    set_locale(update)
    if cur_item == "NEW_ACCOUNT":
        new_account(update, context)
    elif cur_item == "LIST_OF_GAMES":
        list_of_games(update, context)
    elif cur_item == "DELETE_ACCOUNT":
        delete_account(update, context)
    elif cur_item == "SET_LOCALE":
        list_of_locales(update, context)
    elif cur_item == "ADMIN":
        admin_options(update, context)


def admin_options(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    chat_id = update.effective_chat.id
    if chat_id in config.admin_list:
        telegram_logger.info("Received admin_options cmd from user {0} in global".
                             format(chat_id))
        reply_markup = InlineKeyboardMarkup(admin_keyboard())
        context.bot.send_message(chat_id=chat_id, text=_("Выберите аккаунт для просмотра"),
                                 reply_markup=reply_markup)
    else:
        telegram_logger.critical("Received illegal admin_options cmd from user {0} in global".
                             format(chat_id))


def account_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global players_by_tlg_id
    global games_by_player_id
    global user_games_offsets
    global user_active_accounts
    chat_id = update.effective_chat.id
    cur_item = update["callback_query"]["data"][9:]
    telegram_logger.debug("account_choice menu called. Update {}".format(update))
    telegram_logger.debug("account_choice menu called. Context {}".format(context))
    telegram_logger.info("Received command {0} from user {1} in account_choice menu".
                         format(update["callback_query"]["data"], chat_id))

    set_locale(update)

    if chat_id in players_by_tlg_id:
        for i in players_by_tlg_id[chat_id]:
            if str(i.id) == str(cur_item):
                user_active_accounts[chat_id] = i.id
                i.get_owned_games()
                games_by_player_id[i.id] = i.games
                user_games_offsets[chat_id] = 0
        show_account_stats(update=update, context=context)
        show_account_games(update=update, context=context)
    else:
        list_of_games(update, context)


def show_account_stats(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    locale = set_locale(update)
    player = get_player_by_chat_id(chat_id)
    if player is not None:
        cursor = db.cursor()
        cursor.execute("""select round(avg(case when g.has_achievements then pg.percent_complete else null end)::numeric, 2), count(case when pg.is_perfect then 1 end), 
        count(1), count(case when g.has_achievements then 1 end)
            from achievements_hunt.player_games pg
             join achievements_hunt.games g on pg.game_id = g.id and pg.platform_id = g.platform_id where pg.player_id = %s
             """,
                       (player.id,))
        res = cursor.fetchone()
        avg_percent = 0
        perfect_games = 0
        total_games = 0
        achievement_games = 0
        if res is not None:
            avg_percent = res[0]
            if avg_percent is None:
                avg_percent = 0
            perfect_games = res[1]
            total_games = res[2]
            achievement_games = res[3]
        if player.dt_updated is not None:
            player.dt_updated = player.dt_updated.replace(microsecond=0)
        cursor.execute("""
        select coalesce(tr.name, a.name), a.percent_owners, g.name percent_owners from achievements_hunt.player_achievements aa 
            join achievements_hunt.achievements a
            on aa.achievement_id  = a.id
              and aa.game_id  = a.game_id
              and aa.platform_id = a.platform_id 
            left join achievements_hunt.achievement_translations tr 
            on tr.achievement_id  = a.id 
              and tr.game_id = aa.game_id
              and tr.platform_id = aa.platform_id
              and tr.locale = %s
            join achievements_hunt.games g
            on aa.game_id = g.id
              and aa.platform_id = g.platform_id
             where aa.player_id = %s 
             order by a.percent_owners, a.name limit 10
        """, (locale, player.id))
        buf = cursor.fetchall()
        if len(buf) > 0:
            achievement_list = _("Самые редкие достижения:") + chr(10)
            for i in buf:
                achievement_list += _(r"{} (игра {}) процент выполнивших {}".format(i[0], i[2], i[1]))
                achievement_list += chr(10)
        else:
            achievement_list = ""
        context.bot.send_message(chat_id=chat_id, text=_("Игр всего {0}, с достижениями {1}, "
                                                         "средний процент достижений {2}"
                                                         ", идеальных игр {3}, последнее обновление {4} {5}".format(total_games, achievement_games,
                                                                                      avg_percent, perfect_games, player.dt_updated,
                                                                                                                    achievement_list)))
    else:
        start(update, context)


def show_account_games(update: Update, context: CallbackContext):
    global telegram_logger
    global players_by_tlg_id
    global games_by_player_id
    global user_games_offsets
    global user_active_accounts
    global user_games_modes
    chat_id = update.effective_chat.id
    telegram_logger.info("Show games for  user {0} in menu show_account_games".
                         format(update.effective_chat.id))

    set_locale(update)

    games = []
    if chat_id in user_active_accounts:
        if user_active_accounts[chat_id] in games_by_player_id:
            if chat_id in user_games_offsets:
                for j in range(user_games_offsets[chat_id], len(games_by_player_id[user_active_accounts[chat_id]]) - 1):
                    games.append(games_by_player_id[user_active_accounts[chat_id]][j])
                    if len(games) >= GAME_MENU_LENGTH:
                        break
    if chat_id not in user_games_modes:
        user_games_modes[chat_id] = GAMES_ALL
        telegram_logger.debug("Reset game mode for user {0}".format(chat_id))
    else:
        telegram_logger.debug("Used existing game mode {1} for user {0}".format(chat_id, user_games_modes[chat_id]))

    if len(games) > 0:
        reply_markup = InlineKeyboardMarkup(games_keyboard(games, cur_games=user_games_modes[chat_id]))
        context.bot.send_message(chat_id=chat_id, text=_("Выберите игру (показаны {0})").
                                 format(get_mode_name(user_games_modes[chat_id])),
                                 reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=chat_id, text=_("На аккаунте нет игр"))
        start(update, context)


def get_mode_name(mode):
    if mode == GAMES_ALL:
        mode_name = _("все игры")
    elif mode == GAMES_WITH_ACHIEVEMENTS:
        mode_name = _("игры с достижениями")
    elif mode == GAMES_PERFECT:
        mode_name = _("идеальные игры")
    else:
        mode_name = ""
    return mode_name


def show_games_index(update: Update, context: CallbackContext):
    global telegram_logger
    global players_by_tlg_id
    global games_by_player_id
    global user_games_offsets
    global user_active_accounts
    global user_games_modes
    chat_id = update.effective_chat.id
    telegram_logger.info("Show games for  user {0} in menu show_games_index".
                         format(update.effective_chat.id))

    set_locale(update)

    if chat_id in user_active_accounts and chat_id in user_games_modes:
        reply_markup = InlineKeyboardMarkup(games_index_keyboard())
        context.bot.send_message(chat_id=chat_id, text=_("Выберите игру (показаны {0})".
                                                         format(get_mode_name(user_games_modes[chat_id]))),
                                 reply_markup=reply_markup)
    else:
        start(update, context)


def get_player_by_chat_id(chat_id: int) -> Union[Player, None]:
    global user_active_accounts
    global players_by_tlg_id
    player = None
    if chat_id in user_active_accounts:
        if chat_id in players_by_tlg_id:
            players = players_by_tlg_id[chat_id]
            player = players[0]
            for i in players:
                if i.id == user_active_accounts[chat_id]:
                    player = i
    return player


def show_account_achievements(update: Update, context: CallbackContext):
    global telegram_logger

    global user_achievement_offsets

    chat_id = update.effective_chat.id
    telegram_logger.info("Show achievements for user {0} in menu".
                         format(chat_id))
    loc = set_locale(update)

    achievements = []
    player = get_player_by_chat_id(chat_id)
    if player is None or chat_id not in user_achievement_offsets:
        start(update, context)
    else:
        achievement_number = len(player.cur_achievement_stats)
        start_achievement = user_achievement_offsets[chat_id] + 1
        current_achievement = start_achievement
        for i in range(start_achievement - 1, achievement_number):
            achievements.append(player.cur_achievement_stats[i])
            if len(achievements) >= ACHIEVEMENT_MENU_LENGTH:
                break
        msg = ""
        prev_unlocked = False
        for i in achievements:
            telegram_logger.debug("Added achievement {1} for user {0} in menu".
                                  format(chat_id, i))
            is_unlocked = i.get("owned")
            if len(msg) == 0:
                if is_unlocked:
                    msg = _("Выполненные:")
                    msg += chr(10)
                    prev_unlocked = True
                else:
                    msg = _("Невыполненные:")
                    msg += chr(10)
            elif prev_unlocked != is_unlocked:
                msg += _("Невыполненные:")
                msg += chr(10)
                prev_unlocked = False

            msg += _(r"{}/{}. Достижение {} процент выполнивших {}").format(
                current_achievement, achievement_number, i.get("name"), i.get("percent"))
            msg += chr(10)
            current_achievement += 1
        if len(msg) == 0:
            msg = _("Нет достижений.")
        reply_markup = InlineKeyboardMarkup(achievements_keyboard())
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=reply_markup)


def set_locale(update: Update):
    global user_locales
    global db
    chat_id = update.effective_chat.id
    user_id = None
    if update.effective_chat.id not in user_locales:
        cursor = db.cursor()
        cursor.execute("""select locale, id from achievements_hunt.users where telegram_id = %s""",
                       (chat_id,))
        res = cursor.fetchone()
        locale = ""
        if res is not None:
            locale = res[0]
            user_id = res[1]
        if locale is None or len(locale) == 0:
            msg = update.message
            if msg is not None:
                fr = msg.from_user
                if fr is not None:
                    locale = fr.language_code
        if locale is None or len(locale) == 0:
            cb = update.callback_query
            if cb is not None:
                locale = cb.data[7:]
        if user_id is None:
            cursor.execute("""
                                            insert into achievements_hunt.users(telegram_id, locale)
                                            values (%s, %s) 
                                            on conflict (telegram_id) do nothing
                                        """, (chat_id, locale))
            db.commit()
        if len(locale) == 0:
            locale = "en"
        user_locales[chat_id] = locale
    locale = user_locales[chat_id]
    if locale == 'ru':
        _ = ru.gettext
    elif locale == 'en':
        _ = en.gettext
    else:
        _ = en.gettext
    return locale


def start(update: Update, context: CallbackContext):
    global telegram_logger

    telegram_logger.info("Echo: update: {0}, context {1}".format(update, context))
    reply_markup = InlineKeyboardMarkup(main_keyboard(update.effective_chat.id))
    set_locale(update)

    context.bot.send_message(chat_id=update.effective_chat.id, text=_("Я achievement_hunt_bot, анализирую редкость "
                                                                      "достижений, получаемых в видеоиграх. Для работы "
                                                                      "пользуйтесь клавиатурой под сообщениями. Для "
                                                                      "возврата в основное меня отправьте текст /start."
                                                                      ),
                             reply_markup=reply_markup)


def echo(update: Update, context: CallbackContext):
    global creation_process
    global deletion_process
    global feedback_process
    global feedback_reading
    global feedback_replying
    global telegram_logger
    global register_progress
    global platforms
    global users_in_delete_process
    chat_id = update.effective_chat.id
    set_locale(update)
    telegram_logger.info("Echo: update: {0}, context {1}".format(update, context))
    player_created = False
    if chat_id in register_progress:
        cur_platform = register_progress[chat_id]
        for i in platforms:
            context.bot.send_message(chat_id=chat_id,
                                     text=i.name)
            if i.name == cur_platform:
                player = Player(name=update["message"]["text"], ext_id=update["message"]["text"],
                                platform=i, id=None, telegram_id=chat_id)
                player_created = True
                buf = player.is_unique()
                if buf[0]:
                    player.save()
                    del register_progress[chat_id]
                    cmd = {"cmd": "create_player", "player_id": player.id, "platform_id": player.platform.id}
                    enqueue_command(cmd, MODE_CORE)
                if player.id is not None:
                    context.bot.send_message(chat_id=chat_id, text=_("Аккаунт привязан"))
                else:
                    context.bot.send_message(chat_id=chat_id, text=_("Аккаунт {0} уже привязан").
                                             format(update["message"]["text"]))
        if not player_created:
            context.bot.send_message(chat_id=update.effective_chat.id, text=_("Платформа {0} не найдена").
                                     format(cur_platform))
    elif chat_id in users_in_delete_process:
        if update["message"]["text"] == "CONFIRM":
            if chat_id not in players_by_tlg_id:
                start(update, context)
                return
            for i in players_by_tlg_id[chat_id]:
                cmd = {"cmd": "delete_user", "chat_id": chat_id, "player_id": i.id, "platform_id": i.platform.id}
                telegram_logger.info("Delete command sent for telegram user {0} and player {1}".format(chat_id, i.id))
                enqueue_command(cmd, MODE_CORE)
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=_("Delete command sent for account {0} and platform {1}".
                                                format(i.name, i.platform.name)))
            del users_in_delete_process[chat_id]
        else:
            telegram_logger.info("Delete command not confirmed for telegram user {0}".format(chat_id))
            del users_in_delete_process[chat_id]
            context.bot.send_message(chat_id=update.effective_chat.id, text=_("Deletion cancelled"))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=_("Платформа не выбрана"))


def set_logger(config: Config):
    global telegram_logger
    telegram_logger = get_logger("Telegram", config.log_level)
