import json
import codecs
import random
import requests
import time
import datetime
from typing import Dict
from ..achievement import Achievement
from ..config import Config
from ..game import Game
from ..log import get_logger
from ..platform import Platform
from ..security import is_password_encrypted, encrypt_password, decrypt_password
from ..config import MODE_CORE

PLATFORM_STEAM = 1

global api_log
global api_key
global call_counters
global api_calls_daily_limit
global max_api_call_tries
global api_call_pause_on_error
global app_details_sleep_time
global app_details_sleep_chance
global call_counters_retain
global hardcoded_games


def get_key():
    global api_key
    return api_key


def set_key(key):
    global api_key
    api_key = key


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
    global call_counters_retain
    cur_dt = str(datetime.date.today())
    if call_counters is None:
        call_counters = {}
    if cur_dt not in call_counters:
        call_counters[cur_dt] = {}
    if method not in call_counters[cur_dt]:
        call_counters[cur_dt][method] = int(0)
    call_counters[cur_dt][method] += 1
    if len(call_counters) > call_counters_retain:
        old_dt = str(datetime.date.today() - datetime.timedelta(days=call_counters_retain))
        call_counters.pop(old_dt, 'None')


def _call_steam_api(url: str, method_name: str, params: Dict, require_auth: bool = True) -> requests.Response:
    global max_api_call_tries
    global api_call_pause_on_error
    global api_log
    cnt = 0
    if require_auth:
        real_url = "{}?key={}&".format(url, get_key())
    elif len(params) > 0:
        real_url = "{}?".format(url)
    else:
        real_url = "{}".format(url)
    for i in params:
        real_url += "{}={}&".format(i, params[i])
    if len(params) > 0:
        real_url = real_url[:len(real_url) - 1]
    while True:
        if require_auth:
            inc_call_cnt(method_name)
        api_log.info("Request to {} for {}".
                     format(url, params))
        r = requests.get(real_url)
        api_log.info("Response from {} for {} is {}".
                     format(url, params, r))
        if r.status_code == 200 or cnt >= max_api_call_tries:
            api_log.debug("Full response {} for {} is {}".
                          format(url, params, r.text))
            break
        api_log.error("Full response from {} for {} is {}".
                      format(url, params, r.text),
                      exc_info=True,
                      )
        cnt += 1
        time.sleep(api_call_pause_on_error)
    return r


def get_call_cnt():
    global call_counters
    if call_counters is not None:
        for i in call_counters:
            total = int(0)
            for j in call_counters[i]:
                if j != "Total":
                    total += call_counters[i][j]
            call_counters[i]["Total"] = total
            call_counters[i]["Used calls %"] = 0
            if total > 0:
                call_counters[i]["Used calls %"] = round(total / api_calls_daily_limit * 100, 2)

    return call_counters


def init_platform(config: Config) -> Platform:
    global api_log
    global call_counters
    global api_calls_daily_limit
    global max_api_call_tries
    global api_call_pause_on_error
    global app_details_sleep_time
    global app_details_sleep_chance
    global call_counters_retain
    global hardcoded_games
    call_counters = {}
    hardcoded_games = {}
    api_log = get_logger("LOG_API_steam_" + str(config.mode), config.log_level, True)
    f = config.file_path[:config.file_path.rfind('/')] + "steam.json"
    fp = codecs.open(f, 'r', "utf-8")
    steam_config = json.load(fp)
    key_read = steam_config.get("API_KEY")
    incremental_update_enabled = steam_config.get("INCREMENTAL_UPDATE_ENABLED")
    incremental_update_interval = steam_config.get("INCREMENTAL_UPDATE_INTERVAL")
    incremental_skip_chance = steam_config.get("INCREMENTAL_SKIP_CHANCE")
    api_calls_daily_limit = steam_config.get("API_CALLS_DAILY_LIMIT")
    if api_calls_daily_limit is None:
        api_calls_daily_limit = 100000
    else:
        api_calls_daily_limit = int(api_calls_daily_limit)
    max_api_call_tries = steam_config.get("MAX_API_CALL_TRIES")
    if max_api_call_tries is None:
        max_api_call_tries = 3
    else:
        max_api_call_tries = int(max_api_call_tries)
    api_call_pause_on_error = steam_config.get("API_CALL_PAUSE_ON_ERROR")
    if api_call_pause_on_error is None:
        api_call_pause_on_error = 5
    else:
        api_call_pause_on_error = int(api_call_pause_on_error)
    app_details_sleep_chance = steam_config.get("APP_DETAILS_SLEEP_CHANCE")
    if app_details_sleep_chance is None:
        app_details_sleep_chance = 0.4
    else:
        app_details_sleep_chance = float(app_details_sleep_chance)
    app_details_sleep_time = steam_config.get("APP_DETAILS_SLEEP_TIME")
    if app_details_sleep_time is None:
        app_details_sleep_time = 1
    else:
        app_details_sleep_time = int(app_details_sleep_time)
    call_counters_retain = steam_config.get("CALL_COUNTERS_RETAIN")
    if call_counters_retain is None:
        call_counters_retain = 7
    else:
        call_counters_retain = int(call_counters_retain)
    steam = Platform(name='Steam', get_games=get_player_games, get_achivements=get_player_achievements,
                     get_game=get_game, games=None, id=PLATFORM_STEAM, validate_player=get_player_stats,
                     get_player_id=get_name,
                     get_stats=get_call_cnt, incremental_update_enabled=incremental_update_enabled,
                     incremental_update_interval=incremental_update_interval, get_last_games=get_player_last_games,
                     incremental_skip_chance=incremental_skip_chance, get_consoles=None,
                     get_player_stats=get_player_stats_for_game, set_hardcoded=set_hardcoded)
    if is_password_encrypted(key_read):
        api_log.info("Steam key encrypted, do nothing")
        open_key = decrypt_password(key_read, config.server_name, config.db_port)
    elif config.mode == MODE_CORE:
        api_log.info("Steam key in plain text, start encrypt")
        password = encrypt_password(key_read, config.server_name, config.db_port)
        _save_api_key(password, f)
        api_log.info("Steam key encrypted and save back in config")
        open_key = key_read
    else:
        api_log.info("Steam key in plain text, but work in not core")
        open_key = key_read
    set_key(open_key)
    return steam


def get_player_last_games(player_id):
    params = {
        "steamid": player_id,
        "include_played_free_games": True,
        "include_appinfo": True,
              }
    r = _call_steam_api(url="http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/",
                        method_name="GetRecentlyPlayedGames",
                        params=params)
    res = [[], []]
    obj = r.json().get("response")
    if obj is not None and "games" in obj:
        for i in obj.get("games"):
            res[0].append(i.get("appid"))
            res[1].append(i.get("name"))
    return res


def get_player_games(player_id):
    params = {
        "steamid": player_id,
        "include_played_free_games": True,
        "include_appinfo": True,
        "skip_unvetted_apps": False,
    }
    r = _call_steam_api(url="http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/",
                        method_name="GetOwnedGames",
                        params=params)
    res = [[], []]
    obj = r.json().get("response")
    if obj is not None and "games" in obj:
        for i in obj.get("games"):
            res[0].append(i.get("appid"))
            res[1].append(i.get("name"))
    return res


def get_game(game_id: str, name: str, language: str = "English") -> Game:
    global api_log
    global hardcoded_games
    params = {
        "appid": game_id,
        "l": language,
    }
    r = _call_steam_api(url="http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/",
                        method_name="GetSchemaForGame",
                        params=params)
    achievements = {}
    game_name = name
    if game_name is None or len(game_name) == 0:
        game_name = "EMPTY_NAME: id" + str(game_id)
        # If there is API error, using hardcoded name
        if game_id in hardcoded_games:
            game_name = hardcoded_games[game_id]
    stats = {}
    obj = r.json().get("game")
    if len(obj) > 0:
        if "availableGameStats" in obj:
            obj_stats = obj.get("availableGameStats").get("stats")
            if obj_stats is not None:
                for i in obj_stats:
                    ext_id = i.get("name")
                    stat_name = i.get("displayName")
                    if stat_name is None or len(stat_name) == 0:
                        stat_name = ext_id
                    stats[ext_id] = stat_name
            obj_achievements = obj.get("availableGameStats").get("achievements")
            if obj_achievements is not None:
                for i in obj_achievements:
                    ext_id = i.get("ext_id")
                    if ext_id is None or len(ext_id) == 0:
                        ext_id = i.get("name")
                    hidden_flag = i.get("hidden")
                    if hidden_flag is not None:
                        is_hidden = str(hidden_flag) != "0"
                    else:
                        is_hidden = False
                    achievements[ext_id] = Achievement(id=None,
                                                       game_id=None,
                                                       name=i.get("displayName"),
                                                       ext_id=i.get("name"),
                                                       platform_id=PLATFORM_STEAM,
                                                       description=i.get("description"),
                                                       icon_url=i.get("icon"),
                                                       locked_icon_url=i.get("icongray"),
                                                       is_hidden=is_hidden,
                                                       )
        api_log.info(
            "For game {0}, found {1} achievements".format(
                game_id, len(achievements)))
        if len(game_name) == 0:
            game_name = obj.get("gameName")
            api_log.warn("For game {0}, found name {1} instead of empty one".format(game_id, game_name))
    params = {
        "appids": game_id,
    }
    if random.random() > app_details_sleep_chance:
        api_log.info("Sleep before https://store.steampowered.com/api/appdetails/ because random")
        time.sleep(app_details_sleep_time)
        api_log.info("Waked up")
    r = _call_steam_api(url="https://store.steampowered.com/api/appdetails/",
                        method_name="appdetails",
                        params=params,
                        require_auth=False)
    icon_url = None
    release_date = None
    developer = None
    publisher = None
    genres = []
    features = []
    if r.status_code == 200:
        obj = r.json().get(game_id)
        if obj is not None:
            obj = obj.get("data")
            if obj is not None:
                icon_url = obj.get("header_image")
                developers = obj.get("developers")
                if developers is not None and len(developers) > 0:
                    developer = developers[0]
                publishers = obj.get("publishers")
                if publishers is not None and len(publishers) > 0:
                    publisher = publishers[0]
                if "genres" in obj:
                    for cur_gen in obj.get("genres"):
                        genres.append(cur_gen.get("description"))
                obj_release = obj.get("release_date")
                if obj_release is not None:
                    release_date = obj_release.get("date")
                if "categories" in obj:
                    for cur_feature in obj.get("categories"):
                        features.append(cur_feature.get("description"))
    return Game(name=game_name, platform_id=PLATFORM_STEAM, ext_id=game_id, id=None, achievements=achievements,
                console_ext_id=None, console=None, icon_url=icon_url, release_date=release_date, publisher=publisher,
                developer=developer, genres=genres, features=features, stats=stats)


def get_player_achievements(player_id, game_id):
    params = {
        "steamid": player_id,
        "appid": game_id,
    }
    r = _call_steam_api(url="http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/",
                        method_name="GetPlayerAchievements",
                        params=params)
    player_stats = r.json().get("playerstats")
    if player_stats.get("success"):
        if player_stats.get("achievements"):
            achievements = []
            achievement_dates = []
            for o in player_stats.get("achievements"):
                if o.get("achieved") == 1:
                    achievements.append(o.get("apiname"))
                    achievement_dates.append(datetime.datetime.fromtimestamp(o.get("unlocktime")))
            return achievements, achievement_dates
    else:
        err = player_stats.get("error")
        if err == "Profile is not public":
            raise ValueError("Profile is not public")
    return [], []


def get_player_stats_for_game(player_id, game_id):
    params = {
        "steamid": player_id,
        "appid": game_id,
    }
    r = _call_steam_api(url="http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/",
                        method_name="GetUserStatsForGame",
                        params=params)
    player_stats = r.json().get("playerstats")
    stats = {}
    player_stats = player_stats.get("stats")
    if player_stats is not None:
        for i in player_stats:
            ext_id = i.get("name")
            val = i.get("value")
            stats[ext_id] = str(val)
    return stats


def get_name(player_name: str):
    params = {
        "vanityurl": player_name,
    }
    r = _call_steam_api(url="http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/",
                        method_name="ResolveVanityURL",
                        params=params)
    player_id = None
    buf = r.json().get("response")
    if buf is not None:
        player_id = buf.get("steamid")
    if player_id is None and player_name.isnumeric():
        buf = get_player_stats(player_name)
        if buf is not None:
            player_id = player_name
    return player_id


def get_player_stats(player_id):
    params = {
        "steamids": player_id,
    }
    r = _call_steam_api(url="http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
                        method_name="GetPlayerSummaries",
                        params=params)
    res = r.json().get("response").get("players")
    if len(res) == 0:
        return None
    else:
        if "personaname" in res[0]:
            name = res[0]["personaname"]
        elif "realname" in res[0]:
            name = res[0]["realname"]
        else:
            name = None
        return name


def set_hardcoded(games_names_map: Dict):
    global hardcoded_games
    hardcoded_games = games_names_map
