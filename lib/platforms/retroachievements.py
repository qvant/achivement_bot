import json
import codecs
import requests
import time
import datetime
from ..achievement import Achievement
from ..config import Config
from ..console import Console
from ..game import Game
from ..log import get_logger
from ..platform import Platform
from ..security import is_password_encrypted, encrypt_password, decrypt_password
from ..config import MODE_CORE

MAX_TRIES = 3
WAIT_BETWEEN_TRIES = 5

PLATFORM_RETRO = 2

ACHIEVEMENT_ICON_URL_TEMPLATE = "https://s3-eu-west-1.amazonaws.com/i.retroachievements.org/Badge/{0}.png"
GAME_ICON_URL_TEMPLATE = "https://retroachievements.org{0}"

global api_log
global api_key
global api_user
global call_counters


def get_key():
    global api_key
    return api_key


def set_key(key):
    global api_key
    api_key = key


def get_user():
    global api_user
    return api_user


def set_user(user):
    global api_user
    api_user = user


def _save_api_key(password: str, path: str):
    fp = codecs.open(path, 'r', "utf-8")
    config = json.load(fp)
    fp.close()
    fp = codecs.open(path, 'w', "utf-8")
    config["API_KEY"] = password
    json.dump(config, fp, indent=2)
    fp.close()


def inc_call_cnt(method: str):
    global call_counters
    cur_dt = str(datetime.date.today())
    if call_counters is None:
        call_counters = {}
    if cur_dt not in call_counters:
        call_counters[cur_dt] = {}
    if method not in call_counters[cur_dt]:
        call_counters[cur_dt][method] = int(0)
    call_counters[cur_dt][method] += 1
    if len(call_counters) > 7:
        old_dt = str(datetime.date.today() - datetime.timedelta(days=7))
        call_counters.pop(old_dt, 'None')


def get_call_cnt():
    global call_counters
    if call_counters is not None:
        for i in call_counters:
            total = 0
            for j in call_counters[i]:
                if j != "Total":
                    total += call_counters[i][j]
            call_counters[i]["Total"] = total
            call_counters[i]["Used calls %"] = 0
            if total > 0:
                call_counters[i]["Used calls %"] = round(total / 100000 * 100, 2)
    return call_counters


def get_name(player_name: str):
    global api_log
    cnt = 0
    player_id = None
    while True:
        inc_call_cnt("API_GetUserSummary")
        api_log.info("Request https://retroachievements.org/API/API_GetUserSummary.php"
                     " for player {0}".format(player_name))
        r = requests.get(
            "https://retroachievements.org/API/API_GetUserSummary.php?u={}&y={}&z={}".format(
                player_name, get_key(), get_user()))
        api_log.info("https://retroachievements.org/API/API_GetUserSummary.php:{0}".format(r))
        api_log.debug("Full https://retroachievements.org/API/API_GetUserSummary.php: {0}".
                      format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    buf = r.json().get("MemberSince")
    if buf is not None:
        player_id = player_name
    return player_id


def get_game_icon_url(icon_id: str):
    return GAME_ICON_URL_TEMPLATE.format(icon_id)


def get_icon_url(badge_id: str):
    return ACHIEVEMENT_ICON_URL_TEMPLATE.format(badge_id)


def get_icon_locked_url(badge_id: str):
    return ACHIEVEMENT_ICON_URL_TEMPLATE.format(str(badge_id) + "_lock")


def get_game(game_id: str, name: str, language: str = "English") -> Game:
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("API_GetUserSummary")
        api_log.info("https://retroachievements.org/API/API_GetGameExtended.php "
                     "for game {0}, name {1} language {2} supplied".format(game_id, name, language))
        r = requests.get(
            "https://retroachievements.org/API/API_GetGameExtended.php?i={}&y={}&z={}".format(
                game_id, get_key(), get_user()))
        api_log.info("Response from https://retroachievements.org/API/API_GetGameExtended.php "
                     "{0} from retroachievements".format(r))
        api_log.debug("Full response from https://retroachievements.org/API/API_GetGameExtended.php: {0}".
                      format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    achievements = {}
    game_name = None
    obj = r.json()
    if len(obj) > 0:
        console_ext_id = obj.get("ConsoleID")
        if "Achievements" in obj:
            obj_achievements = obj.get("Achievements")
            if obj_achievements is not None:
                for i in obj_achievements:
                    ext_id = str(i)
                    achievements[ext_id] = Achievement(id=None,
                                                       game_id=None,
                                                       name=obj_achievements[i].get("Title"),
                                                       ext_id=obj_achievements[i].get("ID"),
                                                       platform_id=PLATFORM_RETRO,
                                                       description=obj_achievements[i].get("Description"),
                                                       icon_url=get_icon_url(obj_achievements[i].get("BadgeName")),
                                                       locked_icon_url=get_icon_locked_url(obj_achievements[i].
                                                                                           get("BadgeName")))
                    achievements[str(ext_id) + "_hardcore"] = Achievement(id=None,
                                                                          game_id=None,
                                                                          name=obj_achievements[i].get(
                                                                              "Title") + " (Hardcore)",
                                                                          ext_id=str(obj_achievements[i].get(
                                                                              "ID")) + "_hardcore",
                                                                          platform_id=PLATFORM_RETRO,
                                                                          description=obj_achievements[i].get(
                                                                              "Description"),
                                                                          icon_url=get_icon_url(
                                                                              obj_achievements[i].get("BadgeName")),
                                                                          locked_icon_url=get_icon_locked_url(
                                                                              obj_achievements[i].
                                                                              get("BadgeName"))
                                                                          )
        api_log.info(
            "For game {0}, found {1} achievements and console type {2}".format(
                game_id, len(achievements), console_ext_id))
        game_name = obj.get("Title")
        "For game {0}, found name {1}".format(
            game_id, game_name)
    return Game(name=game_name, platform_id=PLATFORM_RETRO, ext_id=game_id, id=None, achievements=achievements,
                console_ext_id=str(obj.get("ConsoleID")), console=None,
                icon_url=get_game_icon_url(str(obj.get("ImageIcon"))),
                release_date=str(obj.get("Released")))


def get_player_achievements(player_id, game_id):
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("API_GetGameInfoAndUserProgress")
        api_log.info("Request https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php "
                     "for game {0} and player {1}".format(game_id, player_id))
        r = requests.get(
            "https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php?u={}&y={}&z={}&g={}".format(
                player_id, get_key(), get_user(), game_id))
        api_log.info("Response from https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php:{0}".format(r))
        api_log.debug("Full response from https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php/: {0}".
                      format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        if r.status_code == 403:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    player_stats = r.json()
    achievements_list = player_stats.get("Achievements")
    if len(achievements_list) > 0:
        achievements = []
        achievement_dates = []
        for o in achievements_list:
            if achievements_list[o].get("DateEarned") is not None:
                achievements.append(achievements_list[o].get("ID"))
                achievement_dates.append(datetime.datetime.strptime(achievements_list[o].get("DateEarned"),
                                                                    "%Y-%m-%d %H:%M:%S"))
            if achievements_list[o].get("DateEarnedHardcore") is not None:
                achievements.append(str(achievements_list[o].get("ID")) + "_hardcore")
                achievement_dates.append(datetime.datetime.strptime(achievements_list[o].get("DateEarnedHardcore"),
                                                                    "%Y-%m-%d %H:%M:%S"))
        return achievements, achievement_dates
    return [], []


def get_player_games(player_id):
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("API_GetUserRecentlyPlayedGames")
        api_log.info("Request https://retroachievements.org/API/API_GetUserRecentlyPlayedGames.php "
                     "for user {0}".format(player_id))
        r = requests.get(
            "https://retroachievements.org/API/API_GetUserRecentlyPlayedGames.php?y="
            "{}&z={}&u={}&c=99999".format(get_key(), get_user(), player_id))
        api_log.info("Response from https://retroachievements.org/API/API_GetUserRecentlyPlayedGames.php: "
                     "{1} for player {0}".
                     format(player_id, r))
        api_log.debug("Full response from https://retroachievements.org/API/API_GetUserRecentlyPlayedGames.php: "
                      "{1} for player {0}".format(player_id, r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    res = [[], []]
    obj = r.json()
    if obj is not None and len(obj) > 0 and len(obj[0]) > 0:
        for i in obj:
            res[0].append(i.get("GameID"))
            res[1].append(i.get("Title"))
    return res


def get_last_player_games(player_id):
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("API_GetUserSummary")
        api_log.info("Request https://retroachievements.org/API/API_GetUserSummary.php "
                     "for user {0}".format(player_id))
        r = requests.get(
            "https://retroachievements.org/API/API_GetUserSummary.php?y="
            "{}&z={}&u={}".format(get_key(), get_user(), player_id))
        api_log.info("Response from https://retroachievements.org/API/API_GetUserSummary.php: "
                     "{1} for player {0}".
                     format(player_id, r))
        api_log.debug("Full response from https://retroachievements.org/API/API_GetUserSummary.php: "
                      "{1} for player {0}".format(player_id, r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    res = [[], []]
    obj = r.json().get("RecentlyPlayed")
    if obj is not None and len(obj) > 0 and len(obj[0]) > 0:
        for i in obj:
            res[0].append(i.get("GameID"))
            res[1].append(i.get("Title"))
    return res


def get_consoles():
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("API_GetConsoleIDs")
        api_log.info("Request https://retroachievements.org/API/API_GetConsoleIDs.php")
        r = requests.get(
            "https://retroachievements.org/API/API_GetConsoleIDs.php?y="
            "{}&z={}".format(get_key(), get_user()))
        api_log.info("Response from https://retroachievements.org/API/API_GetConsoleIDs.php: "
                     "{0}".
                     format(r))
        api_log.debug("Full response from https://retroachievements.org/API/API_GetUserSummary.php: "
                      "{0}".format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    res = []
    obj = r.json()
    if obj is not None and len(obj) > 0:
        for i in obj:
            res.append(Console(id=None, ext_id=i["ID"], name=i["Name"], platform_id=PLATFORM_RETRO))
    return res


def init_platform(config: Config) -> Platform:
    global api_log
    global call_counters
    call_counters = {}
    api_log = get_logger("LOG_API_RETRO_" + str(config.mode), config.log_level, True)
    f = config.file_path[:config.file_path.rfind('/')] + "retroachievements.json"
    fp = codecs.open(f, 'r', "utf-8")
    retro_config = json.load(fp)
    key_read = retro_config.get("API_KEY")
    user = retro_config.get("API_USER")
    incremental_update_enabled = retro_config.get("INCREMENTAL_UPDATE_ENABLED")
    incremental_update_interval = retro_config.get("INCREMENTAL_UPDATE_INTERVAL")
    incremental_skip_chance = retro_config.get("INCREMENTAL_SKIP_CHANCE")
    retro = Platform(name='Retroachievements', get_games=get_player_games, get_achivements=get_player_achievements,
                     get_game=get_game, games=None, id=2, validate_player=get_name, get_player_id=get_name,
                     get_stats=get_call_cnt, incremental_update_enabled=incremental_update_enabled,
                     incremental_update_interval=incremental_update_interval, get_last_games=get_last_player_games,
                     incremental_skip_chance=incremental_skip_chance, get_consoles=get_consoles)
    if is_password_encrypted(key_read):
        api_log.info("Retroachievements key encrypted, do nothing")
        open_key = decrypt_password(key_read, config.server_name, config.db_port)
    elif config.mode == MODE_CORE:
        api_log.info("Retroachievements key in plain text, start encrypt")
        password = encrypt_password(key_read, config.server_name, config.db_port)
        _save_api_key(password, f)
        api_log.info("Retroachievements key encrypted and save back in config")
        open_key = key_read
    else:
        api_log.info("Retroachievements key in plain text, but work in not core")
        open_key = key_read
    set_key(open_key)
    set_user(user)
    return retro
