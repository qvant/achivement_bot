import gettext
import psycopg2

from .config import Config, MODE_CORE, MODE_WORKER, MODE_UPDATER, MODE_BOT
from .platform import Platform
from .player import Player, GAMES_ALL, GAMES_PERFECT, GAMES_WITH_ACHIEVEMENTS
from .log import get_logger
from .queue import enqueue_command
from .stats import get_stats
from typing import Union, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

_ = gettext.gettext

en = gettext.translation('base', localedir='locale', languages=['en'])
en.install()
ru = gettext.translation('base', localedir='locale', languages=['ru'])
ru.install()

global telegram_logger
global platforms
global db
global register_progress
global players_by_tlg_id
global games_by_player_id
global user_states
global user_games_offsets
global user_achievement_offsets
global user_achievement_details
global user_active_accounts
global user_locales
global user_games_modes
global users_in_delete_process
global config
global user_command_counters

MAX_MENU_LENGTH = 30
MAX_MENU_ITEMS = 3

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
ACHIEVEMENTS_LIST_DETAIL = "list_of_achievements_detail"
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
    global user_achievement_details
    global user_active_accounts
    global user_locales
    global user_games_modes
    global users_in_delete_process
    global user_command_counters
    user_states = {}
    user_games_offsets = {}
    user_achievement_offsets = {}
    user_achievement_details = {}
    user_active_accounts = {}
    register_progress = {}
    players_by_tlg_id = {}
    games_by_player_id = {}
    user_locales = {}
    user_games_modes = {}
    users_in_delete_process = {}
    user_command_counters = {}


def inc_command_counter(counter: str):
    global user_command_counters
    if counter not in user_command_counters:
        user_command_counters[counter] = 0
    user_command_counters[counter] += 1


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
    telegram_logger.info("Received command {0} from user {1} in platform_choice, callback".
                         format(Update, update.effective_chat.id))
    _ = set_locale(update)
    register_progress[update.effective_chat.id] = update["callback_query"]["data"][9:]
    context.bot.send_message(chat_id=update.effective_chat.id, text=_("Enter account name"))


def main_keyboard(chat_id: int):
    global db
    global platforms
    global config
    global telegram_logger
    _ = set_locale(chat_id=chat_id)
    players_by_tlg_id[chat_id] = []
    try:
        cursor = db.cursor()
        cursor.execute("""
                    select id, platform_id, name, ext_id, dt_update, is_public
                    from achievements_hunt.players
                    where telegram_id = %s
                    order by id
                    """, (chat_id,))

        for id, platform_id, name, ext_id, dt_update, is_public in cursor:
            for i in platforms:
                if i.id == platform_id:
                    player = Player(name=name, platform=i, ext_id=ext_id, id=id, telegram_id=chat_id,
                                    dt_updated=dt_update)
                    player.is_public = is_public
                    players_by_tlg_id[chat_id].append(player)
                    user_games_offsets[chat_id] = 0
    except psycopg2.Error as err:
        telegram_logger.exception(err)
        if config.supress_errors:
            try:
                set_connect(Platform.get_connect())
            except BaseException as err2:
                telegram_logger.exception(err2)
                pass
        else:
            raise
    keyboard = [
        InlineKeyboardButton(_("New account"), callback_data="main_NEW_ACCOUNT"),
        InlineKeyboardButton(_("Delete account"), callback_data="main_DELETE_ACCOUNT"),
        # TODO: remove later
        InlineKeyboardButton(_("List of games"), callback_data="main_LIST_OF_GAMES"),
        InlineKeyboardButton(_("Language choice"), callback_data="main_SET_LOCALE"),
        InlineKeyboardButton(_("About"), callback_data="main_ABOUT"),
        # there's still not enough users to make it look interesting
        # InlineKeyboardButton(_("Activity feed"), callback_data="main_ACTIVITY"),
    ]
    for i in players_by_tlg_id[chat_id]:
        keyboard.append(InlineKeyboardButton("{}({})".format(i.name, i.platform.name),
                                             callback_data="accounts_" + str(i.id)),)
    if chat_id in config.admin_list:
        keyboard.append(InlineKeyboardButton(_("Admin..."), callback_data="main_ADMIN"),)

    return pretty_menu(keyboard)


def account_keyboard(chat_id: int):
    global players_by_tlg_id
    keyboard = []
    for i in players_by_tlg_id[chat_id]:
        keyboard.append(InlineKeyboardButton("{}({})".format(i.name, i.platform.name),
                                             callback_data="accounts_" + str(i.id)),)

    return pretty_menu(keyboard)


def admin_keyboard(chat_id: int):
    _ = set_locale(chat_id=chat_id)
    keyboard = [
        InlineKeyboardButton(_("Stats..."), callback_data="admin_stats"),
        InlineKeyboardButton(_("Shutdown..."), callback_data="admin_shutdown"),
    ]
    return pretty_menu(keyboard)


def shutdown_keyboard(chat_id: int):
    _ = set_locale(chat_id=chat_id)
    keyboard = [
        InlineKeyboardButton(_("Shutdown core"), callback_data=SHUTDOWN_CORE),
        InlineKeyboardButton(_("Shutdown bot"), callback_data=SHUTDOWN_BOT),
        InlineKeyboardButton(_("Shutdown worker"), callback_data=SHUTDOWN_WORKER),
        InlineKeyboardButton(_("Shutdown updater"), callback_data=SHUTDOWN_UPDATER),
    ]
    return pretty_menu(keyboard)


def stats_keyboard(chat_id: int):
    _ = set_locale(chat_id=chat_id)
    keyboard = [
        InlineKeyboardButton(_("Stats core"), callback_data=STATS_CORE),
        InlineKeyboardButton(_("Stats bot"), callback_data=STATS_BOT),
        InlineKeyboardButton(_("Stats worker"), callback_data=STATS_WORKER),
        InlineKeyboardButton(_("Stats updater"), callback_data=STATS_UPDATER),
    ]
    return pretty_menu(keyboard)


def games_keyboard(chat_id: int, games, cur_games=GAMES_WITH_ACHIEVEMENTS, has_perfect_games: bool = True):
    _ = set_locale(chat_id=chat_id)
    keyboard = [InlineKeyboardButton(_("Begin"), callback_data=GAMES_LIST_FIRST),
                InlineKeyboardButton(_("Previous"), callback_data=GAMES_LIST_PREV)]
    for i in games:
        game_name = i.name
        if i.console_name is not None:
            game_name += " (" + i.console_name + ")"
        keyboard.append(InlineKeyboardButton("{}".format(game_name), callback_data="games_of_" + str(i.id)),)
    keyboard.append(InlineKeyboardButton(_("Next"), callback_data=GAMES_LIST_NEXT))
    keyboard.append(InlineKeyboardButton(_("End"), callback_data=GAMES_LIST_LAST))
    keyboard.append(InlineKeyboardButton(_("Index"), callback_data=GAMES_LIST_INDEX))
    if cur_games == GAMES_ALL:
        keyboard.append(InlineKeyboardButton(_("With achievements"), callback_data=GAMES_LIST_ONLY_ACHIEVEMENTS))
    elif cur_games == GAMES_WITH_ACHIEVEMENTS and has_perfect_games:
        keyboard.append(InlineKeyboardButton(_("Perfect"), callback_data=GAMES_LIST_ONLY_PERFECT))
    else:
        keyboard.append(InlineKeyboardButton(_("All games"), callback_data=GAMES_LIST_ALL))
    keyboard.append(InlineKeyboardButton(_("Exit"), callback_data=GAMES_LIST_BACK))
    return pretty_menu(keyboard)


def games_index_keyboard():
    keyboard = []
    for i in range(26):
        keyboard.append(InlineKeyboardButton("{}".format(chr(97+i).upper()),
                                             callback_data="list_of_games_begin_" + chr(97+i)), )
    return pretty_menu(keyboard)


def achievements_keyboard(chat_id: int, achievements: List):
    _ = set_locale(chat_id=chat_id)
    keyboard = [InlineKeyboardButton(_("Begin"), callback_data=ACHIEVEMENTS_LIST_FIRST),
                InlineKeyboardButton(_("Previous"), callback_data=ACHIEVEMENTS_LIST_PREV),
                InlineKeyboardButton(_("Next"), callback_data=ACHIEVEMENTS_LIST_NEXT),
                InlineKeyboardButton(_("End"), callback_data=ACHIEVEMENTS_LIST_LAST),
                InlineKeyboardButton(_("Detail on/off"), callback_data=ACHIEVEMENTS_LIST_DETAIL),
                InlineKeyboardButton(_("To the games..."), callback_data=ACHIEVEMENTS_LIST_BACK)]
    if len(achievements) > 0:
        for i in achievements:
            keyboard.append(InlineKeyboardButton(i.get("name"), callback_data="ACHIEVEMENT_ID_" + str(i.get("id"))))
    return pretty_menu(keyboard)


def new_account(update: Update, context: CallbackContext):
    _ = set_locale(update)
    reply_markup = InlineKeyboardMarkup(platform_menu())
    context.bot.send_message(chat_id=update.effective_chat.id, text=_("Choose the platform"), reply_markup=reply_markup)


def delete_account(update: Update, context: CallbackContext):
    global users_in_delete_process
    _ = set_locale(update)
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
    _ = set_locale(update)
    locale = get_locale_name(update)
    telegram_logger.info("Locale {0} set for user {1}".
                         format(locale, update.effective_chat.id))
    player = get_player_by_chat_id(chat_id)
    if player is not None:
        player.get_achievement_stats(cur_item, locale)
        user_achievement_offsets[chat_id] = 0
        show_account_achievements(update, context)
    else:
        account_choice(update, context)


def achievement_detail(update: Update, context: CallbackContext):
    global telegram_logger
    global user_achievement_offsets
    chat_id = update.effective_chat.id
    cur_item = update["callback_query"]["data"][15:]
    telegram_logger.info("Received command {0} from user {1} in achievement_detail menu".
                         format(cur_item, update.effective_chat.id))
    _ = set_locale(update)
    locale = get_locale_name(update)
    telegram_logger.info("Locale {0} set for user {1}".
                         format(locale, update.effective_chat.id))
    player = get_player_by_chat_id(chat_id)
    if player is not None and len(player.cur_achievement_stats) > 0:
        for i in player.cur_achievement_stats:
            if i.get("id") == int(cur_item):
                achievements = []
                start_achievement = user_achievement_offsets[chat_id] + 1
                achievement_number = len(player.cur_achievement_stats)
                for j in range(start_achievement - 1, achievement_number):
                    achievements.append(player.cur_achievement_stats[j])
                    if len(achievements) >= ACHIEVEMENT_MENU_LENGTH:
                        break
                reply_markup = InlineKeyboardMarkup(achievements_keyboard(chat_id, achievements))
                msg = _("Achievement {0}: {1}.").format(i.get("name"), i.get("description"))
                msg += chr(10)
                msg += _("Percent owners: {0}.").format(i.get("percent"))
                msg += chr(10)
                if i.get("owned"):
                    msg += _("Status: {0}.").format(_("Unlocked"))
                    msg += chr(10)
                    msg += _("Obtained at: {0}.").format(i.get("dt_unlock"))
                else:
                    msg += _("Status: {0}.").format(_("Locked"))
                if i.get("image_url") is not None and len(i.get("image_url")) > 0:
                    msg += """<a href="{0}">&#8205;</a>""".format(i.get("image_url"))
                context.bot.send_message(chat_id=chat_id,
                                         text=msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
                                         disable_web_page_preview=False)

    else:
        account_choice(update, context)


def locale_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global user_locales
    chat_id = update.effective_chat.id
    _ = set_locale(chat_id=chat_id)
    cur_item = update["callback_query"]["data"][7:].lower()
    telegram_logger.info("Received command {0} from user {1} in locale_choice menu".
                         format(cur_item, update.effective_chat.id))
    user_locales[chat_id] = cur_item
    cursor = db.cursor()
    cursor.execute("""
    update achievements_hunt.users set locale = %s, dt_last_update = current_timestamp where telegram_id = %s""",
                   (cur_item, chat_id))
    db.commit()
    reply_markup = InlineKeyboardMarkup(main_keyboard(chat_id))
    context.bot.send_message(chat_id=chat_id, text=_("Language chosen"),
                             reply_markup=reply_markup)


def admin_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    chat_id = update.effective_chat.id
    _ = set_locale(chat_id=chat_id)
    if chat_id in config.admin_list:
        cur_item = update["callback_query"]["data"]
        telegram_logger.info("Received command {0} from user {1} in admin_choice menu".
                             format(cur_item, update.effective_chat.id))
        if cur_item == "admin_shutdown":
            reply_markup = InlineKeyboardMarkup(shutdown_keyboard(chat_id))
        else:
            reply_markup = InlineKeyboardMarkup(stats_keyboard(chat_id))
        context.bot.send_message(chat_id=chat_id, text=_("Select action"),
                                 reply_markup=reply_markup)
    else:
        telegram_logger.critical("Received illegal cmd {1} from user {0} in admin_choice menu".format(chat_id, update))


def shutdown_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    chat_id = update.effective_chat.id
    _ = set_locale(chat_id=chat_id)
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
        context.bot.send_message(chat_id=chat_id, text=_("Command sent: {0}").format(cmd))
    else:
        telegram_logger.critical("Received illegal cmd {1} from user {0} in shutdown_choice menu".format(
            chat_id, update))


def stats_choice(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    global user_command_counters
    chat_id = update.effective_chat.id
    _ = set_locale(chat_id=chat_id)
    if chat_id in config.admin_list:
        cur_item = update["callback_query"]["data"]
        telegram_logger.info("Received command {0} from user {1} in stats_choice menu".
                             format(cur_item, update.effective_chat.id))
        reply_markup = InlineKeyboardMarkup(stats_keyboard(chat_id))
        if cur_item == STATS_BOT:
            obj = get_stats()
            obj["module"] = "Bot"
            msg = ""
            for i in obj:
                msg += i + ": " + str(obj[i]) + chr(10)
            for i in sorted(user_command_counters):
                msg += "  " + str(i) + ": " + str(user_command_counters[i]) + chr(10)
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
        telegram_logger.critical("Received illegal cmd {1} from user {0} in stats_choice menu".format(chat_id, update))


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
    inc_command_counter("game_navigation")
    _ = set_locale(update)
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
    global user_achievement_details
    global user_active_accounts
    global telegram_logger
    not_ready = False
    cur_item = update["callback_query"]["data"]
    chat_id = update.effective_chat.id
    telegram_logger.info("Received command {0} from user {1} in achievement_navigation menu".
                         format(cur_item, chat_id))
    inc_command_counter("achievement_navigation")

    _ = set_locale(update)

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
    elif cur_item == ACHIEVEMENTS_LIST_DETAIL:
        if chat_id not in user_achievement_details:
            user_achievement_details[chat_id] = False
        user_achievement_details[chat_id] = not user_achievement_details[chat_id]
    telegram_logger.info("Set achievements offset = {1} for user {0} ".
                         format(update.effective_chat.id, user_achievement_offsets[update.effective_chat.id]))
    if not_ready:
        account_choice(update, context)
    elif cur_item == ACHIEVEMENTS_LIST_BACK:
        game_navigation(update, context)
    else:
        show_account_achievements(update=update, context=context)


def locale_keyboard(chat_id):
    _ = set_locale(chat_id=chat_id)
    keyboard = [InlineKeyboardButton(_("ru"), callback_data=LOCALE_RU),
                InlineKeyboardButton(_("en"), callback_data=LOCALE_EN),
                InlineKeyboardButton(_("dynamic"), callback_data=LOCALE_DYNAMIC)]
    return pretty_menu(keyboard)


def list_of_locales(update: Update, context: CallbackContext):
    _ = set_locale(update)
    chat_id = update.effective_chat.id
    reply_markup = InlineKeyboardMarkup(locale_keyboard(chat_id))
    context.bot.send_message(chat_id=chat_id, text=_("Choose the language"),
                             reply_markup=reply_markup)


def list_of_games(update: Update, context: CallbackContext):
    global db
    global platforms
    global players_by_tlg_id
    global user_games_offsets
    chat_id = update.effective_chat.id
    _ = set_locale(chat_id=chat_id)
    cursor = db.cursor()
    cursor.execute("""
            select id, platform_id, name, ext_id from achievements_hunt.players where telegram_id = %s order by id
            """, (update.effective_chat.id,))
    players_by_tlg_id[update.effective_chat.id] = []
    _ = set_locale(update)

    for id, platform_id, name, ext_id in cursor:
        for i in platforms:
            if i.id == platform_id:
                player = Player(name=name, platform=i, ext_id=ext_id, id=id, telegram_id=chat_id)
                players_by_tlg_id[chat_id].append(player)
                user_games_offsets[chat_id] = 0
    reply_markup = InlineKeyboardMarkup(account_keyboard(chat_id))
    context.bot.send_message(chat_id=chat_id, text=_("Choose account"),
                             reply_markup=reply_markup)


def main_menu(update: Update, context: CallbackContext):
    global telegram_logger
    cur_item = update["callback_query"]["data"][5:]
    telegram_logger.debug("Main menu called. Update {}".format(update))
    telegram_logger.debug("Main menu called. Context {}".format(context))
    telegram_logger.info("Received command {0} from user {1} in main menu".
                         format(cur_item, update.effective_chat.id))
    inc_command_counter("main_menu")
    _ = set_locale(update)
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
    elif cur_item == "ABOUT":
        about(update, context)
    elif cur_item == "ACTIVITY":
        activity_feed(update, context)


def admin_options(update: Update, context: CallbackContext):
    global telegram_logger
    global config
    chat_id = update.effective_chat.id
    if chat_id in config.admin_list:
        telegram_logger.info("Received admin_options cmd from user {0} in global".
                             format(chat_id))
        reply_markup = InlineKeyboardMarkup(admin_keyboard(chat_id))
        context.bot.send_message(chat_id=chat_id, text=_("Choose account"),
                                 reply_markup=reply_markup)
    else:
        telegram_logger.critical("Received illegal admin_options cmd from user {0} in global".format(chat_id))


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
    inc_command_counter("account_choice")

    _ = set_locale(update)

    if chat_id in players_by_tlg_id:
        for i in players_by_tlg_id[chat_id]:
            if str(i.id) == str(cur_item):
                user_active_accounts[chat_id] = i.id
                user_games_modes[chat_id] = GAMES_WITH_ACHIEVEMENTS
                i.get_owned_games(mode=user_games_modes[chat_id])
                games_by_player_id[i.id] = i.games
                user_games_offsets[chat_id] = 0
        show_account_stats(update=update, context=context)
        show_account_games(update=update, context=context)
    else:
        list_of_games(update, context)


def show_account_stats(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    _ = set_locale(update)
    locale = get_locale_name(update)
    player = get_player_by_chat_id(chat_id)
    if player is not None:
        cursor = db.cursor()
        cursor.execute("""
        select
            round(avg(case when g.has_achievements
                then pg.percent_complete else null
                end)::numeric, 2),
            count(case when pg.is_perfect then 1 end),
            count(1),
            count(case when g.has_achievements then 1 end)
        from achievements_hunt.player_games pg
        join achievements_hunt.games g
            on pg.game_id = g.id
            and pg.platform_id = g.platform_id
        where pg.player_id = %s
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
        select
                coalesce(tr.name, a.name),
                a.percent_owners,
                g.name || case when c.name is not null then ' (' || c.name || ')' else '' end
            from achievements_hunt.player_achievements aa
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
            left join achievements_hunt.consoles c
            on c.id = g.console_id
              and c.platform_id = g.platform_id
            where aa.player_id = %s
            order by a.percent_owners, coalesce(tr.name, a.name) limit 10
        """, (locale, player.id))
        buf = cursor.fetchall()
        if len(buf) > 0:
            achievement_list = chr(10) + chr(10) + _("Rarest achievements:") + chr(10)
            for i in buf:
                achievement_list += _(r"{} (game {}) percent owners {}").format(i[0], i[2], i[1])
                achievement_list += chr(10)
        else:
            achievement_list = ""
        cursor.execute("""
                select
                        coalesce(tr.name, a.name),
                        a.percent_owners,
                        g.name || case when c.name is not null then ' (' || c.name || ')' else '' end
                    from achievements_hunt.player_achievements aa
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
                    left join achievements_hunt.consoles c
                    on c.id = g.console_id
                      and c.platform_id = g.platform_id
                    where aa.player_id = %s
                    order by dt_unlock desc, coalesce(tr.name, a.name) limit 5
                """, (locale, player.id))
        buf = cursor.fetchall()
        if len(buf) > 0:
            new_achievement_list = chr(10) + _("Last achievements:") + chr(10)
            for i in buf:
                new_achievement_list += _(r"{} (game {}) percent owners {}").format(i[0], i[2], i[1])
                new_achievement_list += chr(10)
        else:
            new_achievement_list = ""
        private_warning = ""
        if not player.is_public:
            private_warning = chr(10)
            private_warning += _("Profile is private, available information is limited")
        context.bot.send_message(chat_id=chat_id, text=_("Total games {0}, games with achievement support {1}, "
                                                         "average completion percent {2}"
                                                         ", perfect games {3}, was updated at {4} {5}{7}{6}").
                                 format(total_games, achievement_games, avg_percent, perfect_games, player.dt_updated,
                                        achievement_list, private_warning, new_achievement_list))
    else:
        start(update, context)


def show_account_games(update: Update, context: CallbackContext):
    global telegram_logger
    global players_by_tlg_id
    global games_by_player_id
    global user_games_offsets
    global user_active_accounts
    global user_games_modes
    global db
    chat_id = update.effective_chat.id
    telegram_logger.info("Show games for user {0} in menu show_account_games".
                         format(update.effective_chat.id))
    inc_command_counter("show_account_games")
    _ = set_locale(update)

    has_perfect_games = False
    player = None
    games = []
    if chat_id in user_active_accounts:
        if user_active_accounts[chat_id] in games_by_player_id:
            if chat_id in user_games_offsets:
                for j in range(user_games_offsets[chat_id], len(games_by_player_id[user_active_accounts[chat_id]])):
                    games.append(games_by_player_id[user_active_accounts[chat_id]][j])
                    if len(games) >= GAME_MENU_LENGTH:
                        break
        player = get_player_by_chat_id(chat_id)
        if player is not None:
            has_perfect_games = player.has_perfect_games
    if chat_id not in user_games_modes:
        user_games_modes[chat_id] = GAMES_WITH_ACHIEVEMENTS
        telegram_logger.debug("Reset game mode for user {0}".format(chat_id))
    else:
        telegram_logger.debug("Used existing game mode {1} for user {0}".format(chat_id, user_games_modes[chat_id]))

    if len(games) > 0:
        reply_markup = InlineKeyboardMarkup(games_keyboard(chat_id, games, cur_games=user_games_modes[chat_id],
                                                           has_perfect_games=has_perfect_games))
        context.bot.send_message(chat_id=chat_id, text=_("Choose games (shown {0})").
                                 format(get_mode_name(user_games_modes[chat_id], chat_id)),
                                 reply_markup=reply_markup)
    else:
        dt_update_full = None
        if player is not None:
            cursor = db.cursor()
            cursor.execute("select dt_update_full from achievements_hunt.players where id = %s", (player.id,))
            dt_update_full, = cursor.fetchone()
        if dt_update_full is not None:
            context.bot.send_message(chat_id=chat_id, text=_("There is no games on account."))
        else:
            context.bot.send_message(chat_id=chat_id, text=_("Games receiving in progress, please, wait..."))
        start(update, context)


def get_mode_name(mode, chat_id):
    global telegram_logger
    _ = set_locale(chat_id=chat_id)
    if mode == GAMES_ALL:
        mode_name = _("all games")
    elif mode == GAMES_WITH_ACHIEVEMENTS:
        mode_name = _("games with achievements")
    elif mode == GAMES_PERFECT:
        mode_name = _("perfect games")
    else:
        telegram_logger.critical("Incorrect mode {0}".format(mode))
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
    inc_command_counter("show_games_index")

    _ = set_locale(update)

    if chat_id in user_active_accounts and chat_id in user_games_modes:
        reply_markup = InlineKeyboardMarkup(games_index_keyboard())
        context.bot.send_message(chat_id=chat_id, text=_("Choose games (shown {0})").
                                 format(get_mode_name(user_games_modes[chat_id], chat_id)),
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
    global user_achievement_details

    chat_id = update.effective_chat.id
    telegram_logger.info("Show achievements for user {0} in show_account_achievements".
                         format(chat_id))
    inc_command_counter("show_account_achievements")
    _ = set_locale(update)

    achievements = []
    player = get_player_by_chat_id(chat_id)
    if player is None or chat_id not in user_achievement_offsets:
        start(update, context)
    else:
        achievement_number = len(player.cur_achievement_stats)
        start_achievement = user_achievement_offsets[chat_id] + 1
        current_achievement = start_achievement
        cur_game = player.cur_achievements_game
        for i in range(start_achievement - 1, achievement_number):
            achievements.append(player.cur_achievement_stats[i])
            if len(achievements) >= ACHIEVEMENT_MENU_LENGTH:
                break
        if start_achievement == 1 and len(player.cur_achievements_game.icon_url) > 0:
            msg = """"<a href="{0}">&#8205;</a>""".format(cur_game.icon_url)
        else:
            msg = ""
        if start_achievement == 1:
            if len(cur_game.developer) > 0:
                msg += _("Developer: {0}").format(cur_game.developer) + chr(10)
            if len(cur_game.publisher) > 0:
                msg += _("Publisher: {0}").format(cur_game.publisher) + chr(10)
            if len(cur_game.release_date) > 0:
                msg += _("Release date: {0}").format(cur_game.release_date) + chr(10)
            # TODO: fix properly
            if cur_game.genres != [None] and len(cur_game.genres) > 0:
                msg += _("Genre: {0}").format(", ".join(cur_game.genres)) + chr(10)
        prev_unlocked = False
        first_achievement = True
        for i in achievements:
            telegram_logger.debug("Added achievement {1} for user {0} in menu".
                                  format(chat_id, i))
            is_unlocked = i.get("owned")
            if first_achievement:
                first_achievement = False
                if is_unlocked:
                    msg = _("Unlocked:")
                    msg += chr(10)
                    prev_unlocked = True
                else:
                    msg = _("Locked:")
                    msg += chr(10)
            elif prev_unlocked != is_unlocked:
                msg += _("Locked:")
                msg += chr(10)
                prev_unlocked = False

            msg += _(r"{}/{}. Achievement {} percent owners {}").format(
                current_achievement, achievement_number, i.get("name"), i.get("percent"))
            msg += chr(10)
            current_achievement += 1
        if len(msg) == 0:
            msg = _("There is no achievements.")
        if chat_id not in user_achievement_details:
            user_achievement_details[chat_id] = False
        if user_achievement_details[chat_id]:
            reply_markup = InlineKeyboardMarkup(achievements_keyboard(chat_id, achievements))
        else:
            reply_markup = InlineKeyboardMarkup(achievements_keyboard(chat_id, []))
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=reply_markup,
                                 parse_mode=ParseMode.HTML, disable_web_page_preview=False)


def set_locale(update: Union[Update, None] = None, chat_id: Union[int, None] = None):
    global user_locales
    global db
    global telegram_logger
    if update is not None:
        chat_id = update.effective_chat.id
    user_id = None
    if chat_id not in user_locales:
        try:
            cursor = db.cursor()
            cursor.execute("""select locale, id from achievements_hunt.users where telegram_id = %s""",
                           (chat_id,))
            res = cursor.fetchone()
            locale = ""
            if res is not None:
                locale = res[0]
                user_id = res[1]
            if locale is None or len(locale) == 0:
                if update is not None:
                    msg = update.message
                    if msg is not None:
                        fr = msg.from_user
                        if fr is not None:
                            locale = fr.language_code
            if locale is None or len(locale) == 0:
                if update is not None:
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
        except psycopg2.Error as err:
            telegram_logger.exception(err)
            if config.supress_errors:
                try:
                    set_connect(Platform.get_connect())
                except BaseException as err2:
                    telegram_logger.exception(err2)
                    pass
            else:
                raise
        user_locales[chat_id] = locale
    locale = user_locales[chat_id]
    if locale == 'ru':
        _ = ru.gettext
    elif locale == 'en':
        _ = en.gettext
    else:
        _ = en.gettext
    return _


def get_locale_name(update: Union[Update, None], chat_id: Union[int, None] = None):
    global user_locales
    global db
    if update is not None:
        chat_id = update.effective_chat.id
    user_id = None
    if chat_id not in user_locales:
        cursor = db.cursor()
        cursor.execute("""select locale, id from achievements_hunt.users where telegram_id = %s""",
                       (chat_id,))
        res = cursor.fetchone()
        locale = ""
        if res is not None:
            locale = res[0]
            user_id = res[1]
        if locale is None or len(locale) == 0:
            if update is not None:
                msg = update.message
                if msg is not None:
                    fr = msg.from_user
                    if fr is not None:
                        locale = fr.language_code
        if locale is None or len(locale) == 0:
            if update is not None:
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
    return locale


def start(update: Update, context: CallbackContext):
    global telegram_logger

    telegram_logger.info("start: update: {0}, context {1}".format(update, context))
    inc_command_counter("start")
    reply_markup = InlineKeyboardMarkup(main_keyboard(update.effective_chat.id))
    _ = set_locale(update)

    context.bot.send_message(chat_id=update.effective_chat.id, text=_("Achievement_hunt_bot was designed for track and "
                                                                      "analyze rarity of game achievements and "
                                                                      "controlled through keyboard under messages. "
                                                                      "To return to the main menu send text  start."
                                                                      ),
                             reply_markup=reply_markup)


def about(update: Update, context: CallbackContext):
    global telegram_logger

    telegram_logger.info("About: update: {0}, context {1}".format(update, context))
    inc_command_counter("about")
    reply_markup = InlineKeyboardMarkup(main_keyboard(update.effective_chat.id))
    _ = set_locale(update)

    context.bot.send_message(chat_id=update.effective_chat.id, text=_("Achievement_hunt_bot was designed for track and "
                                                                      "analyze rarity of game achievements and "
                                                                      "controlled through keyboard under messages. "
                                                                      "To return to the main menu send text /start."
                                                                      "You can see the bot sources on "
                                                                      "https://github.com/qvant/achivement_bot"
                                                                      ),
                             reply_markup=reply_markup)


def activity_feed(update: Update, context: CallbackContext):
    global telegram_logger

    telegram_logger.info("activity_feed: update: {0}, context {1}".format(update, context))
    inc_command_counter("activity_feed")
    reply_markup = InlineKeyboardMarkup(main_keyboard(update.effective_chat.id))
    _ = set_locale(update)
    locale = get_locale_name(update)

    cursor = db.cursor()

    cursor.execute("""
                    select
                            coalesce(tr.name, a.name),
                            a.percent_owners,
                            g.name || case when c.name is not null then ' (' || c.name || ')' else '' end,
                            p.name,
                            pr.name
                        from achievements_hunt.players p
                        join achievements_hunt.platforms pr
                        on pr.id = p.platform_id
                        join achievements_hunt.player_achievements aa
                        on p.id = aa.player_id
                          and p.platform_id = aa.platform_id
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
                        left join achievements_hunt.consoles c
                        on c.id = g.console_id
                          and c.platform_id = g.platform_id
                        order by dt_unlock desc, coalesce(tr.name, a.name) limit 25
                    """, (locale,))
    buf = cursor.fetchall()
    activity_list = ""
    if len(buf) > 0:
        activity_list = chr(10) + _("Last activity:") + chr(10)
        for i in buf:
            activity_list += _(r"{}({}) unlocked {} (game {}) percent owners {}").format(i[3], i[4], i[0], i[2], i[1])
            activity_list += chr(10)

    context.bot.send_message(chat_id=update.effective_chat.id, text=activity_list,
                             reply_markup=reply_markup)


def echo(update: Update, context: CallbackContext):
    global telegram_logger
    global register_progress
    global platforms
    global users_in_delete_process
    chat_id = update.effective_chat.id
    _ = set_locale(update)
    telegram_logger.info("Echo: update: {0}, context {1}".format(update, context))
    inc_command_counter("text input")
    player_created = False
    if chat_id in register_progress:
        cur_platform = register_progress[chat_id]
        del register_progress[chat_id]
        for i in platforms:
            if i.name == cur_platform:
                player = Player(name=update["message"]["text"], ext_id=update["message"]["text"],
                                platform=i, id=None, telegram_id=chat_id)
                player_created = True
                buf = player.is_unique()
                if buf[0]:
                    player.save()
                    cmd = {"cmd": "create_player", "player_id": player.id, "platform_id": player.platform.id}
                    enqueue_command(cmd, MODE_CORE)
                if player.id is not None:
                    context.bot.send_message(chat_id=chat_id, text=_("Account {0} bound to you").format(player.name))
                else:
                    context.bot.send_message(chat_id=chat_id,
                                             text=_("You already have account for this platform"))
        if not player_created:
            context.bot.send_message(chat_id=update.effective_chat.id, text=_("Platform {0} not found").
                                     format(cur_platform))
    elif chat_id in users_in_delete_process:
        if update["message"]["text"] == "CONFIRM":
            if chat_id not in players_by_tlg_id:
                start(update, context)
                return
            found = False
            for i in players_by_tlg_id[chat_id]:
                cmd = {"cmd": "delete_user", "chat_id": chat_id, "player_id": i.id, "platform_id": i.platform.id}
                telegram_logger.info("Delete command sent for telegram user {0} and player {1}".format(chat_id, i.id))
                enqueue_command(cmd, MODE_CORE)
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=_("Delete command sent for account {0} and platform {1}").
                                         format(i.name, i.platform.name))
            del users_in_delete_process[chat_id]
            if not found:
                reply_markup = InlineKeyboardMarkup(main_keyboard(update.effective_chat.id))
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=_("You haven't accounts"),
                                         reply_markup=reply_markup)
        else:
            telegram_logger.info("Delete command not confirmed for telegram user {0}".format(chat_id))
            reply_markup = InlineKeyboardMarkup(main_keyboard(update.effective_chat.id))
            context.bot.send_message(chat_id=update.effective_chat.id, text=_("Deletion cancelled"),
                                     reply_markup=reply_markup)


def set_logger(cfg: Config):
    global telegram_logger
    telegram_logger = get_logger("Telegram", cfg.log_level)
