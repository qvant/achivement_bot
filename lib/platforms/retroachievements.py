import json
import codecs
import requests
import time
import datetime
from typing import Dict

from ..ApiException import ApiException
from ..achievement import Achievement
from ..config import Config
from ..console import Console
from ..game import Game
from ..log import get_logger
from ..platform import Platform
from ..platform_utils import save_api_key, inc_call_cnt, get_call_cnt, set_call_counters_retain, sef_daily_call_limit
from ..rates import set_limit, do_with_limit
from ..security import is_password_encrypted, encrypt_password, decrypt_password
from ..config import MODE_CORE


PLATFORM_RETRO = 2
PLATFORM_NAME = "Retroachievements"

ACHIEVEMENT_ICON_URL_TEMPLATE = "https://s3-eu-west-1.amazonaws.com/i.retroachievements.org/Badge/{0}.png"
GAME_ICON_URL_TEMPLATE = "https://retroachievements.org{0}"
AVATAR_URL_TEMPLATE = "https://retroachievements.org{0}"

global api_log
global api_key
global api_user
global call_counters
global api_calls_daily_limit
global max_api_call_tries
global api_call_pause_on_error
global call_counters_retain


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


def _call_api(url: str, method_name: str, params: Dict) -> requests.Response:
    global max_api_call_tries
    global api_call_pause_on_error
    global api_log
    cnt = 0
    real_url = "{}?y={}&z={}".format(url, get_key(), get_user())
    for i in params:
        real_url += "&{}={}".format(i, params[i])
    while True:
        inc_call_cnt(PLATFORM_NAME, method_name)
        api_log.info("Request to {} for {}".
                     format(url, params if len(params) > 0 else "no parameters"))
        try:
            r = do_with_limit("https://retroachievements.org/",
                              requests.get,
                              dict(url=real_url, timeout=30))
            api_log.info("Response from {} for {} is {}".
                         format(url, params if len(params) > 0 else "no parameters", r))
            if r.status_code == 200 or cnt >= max_api_call_tries:
                api_log.debug("Full response {} for {} is {}".
                              format(url, params if len(params) > 0 else "no parameters", r.text))
                break
            if r.status_code == 403:
                api_log.info("Didn't have access to {}, probably because of private profile".format(url))
                break
            api_log.error("Full response from {} for {} is {}".
                          format(url, params if len(params) > 0 else "no parameters", r.text),
                          exc_info=True,
                          )
        except requests.exceptions.ConnectTimeout as exc:
            api_log.error(exc)
            if cnt >= max_api_call_tries:
                raise ApiException("Retroachievements timeout")
        cnt += 1
        time.sleep(api_call_pause_on_error)
    return r


def get_name(player_name: str):
    player_id = None
    params = {
        "u": player_name,
    }
    r = _call_api(url="https://retroachievements.org/API/API_GetUserSummary.php",
                  method_name="API_GetUserSummary",
                  params=params
                  )
    try:
        buf = r.json().get("MemberSince")
        if buf is not None:
            player_id = player_name
    except BaseException as exc:
        api_log.exception(exc)
    return player_id


def get_game_icon_url(icon_id: str):
    return GAME_ICON_URL_TEMPLATE.format(icon_id)


def get_avatar_url(avatar_name: str):
    return AVATAR_URL_TEMPLATE.format(avatar_name)


def get_icon_url(badge_id: str):
    return ACHIEVEMENT_ICON_URL_TEMPLATE.format(badge_id)


def get_icon_locked_url(badge_id: str):
    return ACHIEVEMENT_ICON_URL_TEMPLATE.format(str(badge_id) + "_lock")


def get_game(game_id: str, name: str, language: str = "English") -> Game:
    global api_log
    params = {
        "i": game_id,
    }
    r = _call_api(url="https://retroachievements.org/API/API_GetGameExtended.php",
                  method_name="API_GetGameExtended",
                  params=params,
                  )
    achievements = {}
    game_name = None
    genres = None
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
                                                       ext_id=str(obj_achievements[i].get("ID")),
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
            "For game with ext_id {0}, found {1} achievements and console type {2}".format(
                game_id, len(achievements), console_ext_id))
        game_name = obj.get("Title")
        if game_name is None and game_id == "0":
            game_name = "UNRECOGNISED"
        "For game {0}, found name {1}".format(
            game_id, game_name)
        genre = obj.get("Genre")
        if genre is not None:
            genres = genre.replace("\\/", "\\").split(",")

    return Game(name=game_name, platform_id=PLATFORM_RETRO, ext_id=game_id, id=None, achievements=achievements,
                console_ext_id=str(obj.get("ConsoleID")), console=None,
                icon_url=get_game_icon_url(str(obj.get("ImageIcon"))),
                release_date=str(obj.get("Released")),
                publisher=obj.get("Publisher"),
                developer=obj.get("Developer"),
                genres=genres,
                )


def get_player_achievements(player_id, game_id):
    params = {
        "u": player_id,
        "g": game_id,
    }
    r = _call_api(url="https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php",
                  method_name="API_GetGameInfoAndUserProgress",
                  params=params,
                  )
    player_stats = r.json()
    achievements_list = player_stats.get("Achievements")
    if len(achievements_list) > 0:
        achievements = []
        achievement_dates = []
        for o in achievements_list:
            if achievements_list[o].get("DateEarned") is not None:
                achievements.append(str(achievements_list[o].get("ID")))
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
    res = [[], []]
    pack_size = 50
    games_total = 0
    params = {
        "u": player_id,
        "c": pack_size,
        "o": 0
    }
    while True:
        r = _call_api(url="https://retroachievements.org/API/API_GetUserRecentlyPlayedGames.php",
                      method_name="API_GetUserRecentlyPlayedGames",
                      params=params,
                      )
        obj = r.json()
        games_fetched = 0
        if obj is not None:
            if len(obj) > 0 and len(obj[0]) > 0:
                games_fetched = len(obj)
                games_total += games_fetched
                api_log.info("Received {} games for player with ext_id {}".
                             format(games_fetched, player_id))
                for i in obj:
                    game_id = i.get("GameID")
                    if game_id != "0":
                        if game_id not in res[0]:
                            res[0].append(game_id)
                            res[1].append(i.get("Title"))
                        else:
                            api_log.info(
                                "Found game with ext_id {} for player {} "
                                "in GetUserRecentlyPlayedGames second time".format(player_id, game_id))
        if games_fetched == 0 or games_fetched < pack_size:
            api_log.info("All {} games for player with ext_id {} received from retroachievements.org".
                         format(games_total, player_id))
            break
        api_log.info("Continue to get games for player with ext_id {} from retroachievements.org. Received so far {}".
                     format(player_id, games_total))
        params["o"] = games_total
    return res


def get_last_player_games(player_id):
    global api_log
    params = {
        "u": player_id,
    }
    r = _call_api(url="https://retroachievements.org/API/API_GetUserSummary.php",
                  method_name="API_GetUserSummary",
                  params=params,
                  )
    res = [[], []]
    obj = r.json().get("RecentlyPlayed")
    if obj is not None and len(obj) > 0 and len(obj[0]) > 0:
        for i in obj:
            res[0].append(i.get("GameID"))
            res[1].append(i.get("Title"))
    return res


def get_player_avatar(player_id):
    global api_log
    params = {
        "u": player_id,
    }
    r = _call_api(url="https://retroachievements.org/API/API_GetUserSummary.php",
                  method_name="API_GetUserSummary",
                  params=params,
                  )
    avatar_name = r.json().get("UserPic")
    return get_avatar_url(avatar_name)


def get_consoles():
    params = {}
    r = _call_api(url="https://retroachievements.org/API/API_GetConsoleIDs.php",
                  method_name="API_GetConsoleIDs",
                  params=params,
                  )
    res = []
    obj = r.json()
    if obj is not None and len(obj) > 0:
        for i in obj:
            res.append(Console(id=None, ext_id=str(i["ID"]), name=i["Name"], platform_id=PLATFORM_RETRO))
    return res


def init_platform(config: Config) -> Platform:
    global api_log
    global call_counters
    global api_calls_daily_limit
    global max_api_call_tries
    global api_call_pause_on_error
    global call_counters_retain
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
    api_calls_daily_limit = retro_config.get("API_CALLS_DAILY_LIMIT")
    if api_calls_daily_limit is not None:
        sef_daily_call_limit(PLATFORM_NAME, int(api_calls_daily_limit))
    max_api_call_tries = retro_config.get("MAX_API_CALL_TRIES")
    if max_api_call_tries is None:
        max_api_call_tries = 3
    else:
        max_api_call_tries = int(max_api_call_tries)
    api_call_pause_on_error = retro_config.get("API_CALL_PAUSE_ON_ERROR")
    if api_call_pause_on_error is None:
        api_call_pause_on_error = 5
    else:
        api_call_pause_on_error = int(api_call_pause_on_error)
    call_counters_retain = retro_config.get("CALL_COUNTERS_RETAIN")
    if call_counters_retain is not None:
        set_call_counters_retain(PLATFORM_NAME, int(call_counters_retain))
    retro = Platform(name='Retroachievements', get_games=get_player_games, get_achievements=get_player_achievements,
                     get_game=get_game, games=None, id=PLATFORM_RETRO, validate_player=get_name, get_player_id=get_name,
                     get_stats=get_api_counters, incremental_update_enabled=incremental_update_enabled,
                     incremental_update_interval=incremental_update_interval, get_last_games=get_last_player_games,
                     incremental_skip_chance=incremental_skip_chance, get_consoles=get_consoles,
                     get_player_avatar=get_player_avatar)
    if is_password_encrypted(key_read):
        api_log.info("Retroachievements key encrypted, do nothing")
        open_key = decrypt_password(key_read, config.server_name, config.db_port)
    elif config.mode == MODE_CORE:
        api_log.info("Retroachievements key in plain text, start encrypt")
        password = encrypt_password(key_read, config.server_name, config.db_port)
        save_api_key(password, f)
        api_log.info("Retroachievements key encrypted and save back in config")
        open_key = key_read
    else:
        api_log.info("Retroachievements key in plain text, but work in not core")
        open_key = key_read
    set_key(open_key)
    set_user(user)
    # TODO: it's approximate limit, calculated by just one sample. Set exact
    set_limit("https://retroachievements.org/", 10, 12, api_log)
    return retro


def set_game_updater_limits():
    set_limit("https://retroachievements.org/", 1, 1, api_log)


def get_api_counters():
    return get_call_cnt(PLATFORM_NAME)
