import json
import codecs
import requests
import time
import datetime
from typing import Dict

from ..ApiException import ApiException
from ..achievement import Achievement
from ..config import Config
from ..game import Game
from ..platform import Platform
from ..platform_utils import save_api_key, inc_call_cnt, get_call_cnt, sef_daily_call_limit, set_call_counters_retain, \
    inc_error_cnt
from ..rates import do_with_limit, set_limit, get_limit_counter, get_limit_interval_end
from ..security import is_password_encrypted, encrypt_password, decrypt_password
from ..config import MODE_CORE

PLATFORM_STEAM = 1
PLATFORM_NAME = "Steam"

global api_log
global api_key
global max_api_call_tries
global api_call_pause_on_error
global hardcoded_games
global skip_extra_info
global session
global summary_cache
global summary_cache_key

summary_cache_key = None


def get_key():
    global api_key
    return api_key


def set_key(key):
    global api_key
    api_key = key


def set_skip_extra_info(val: bool = False):
    global skip_extra_info
    skip_extra_info = val


def _call_steam_api(url: str, method_name: str, params: Dict, require_auth: bool = True) -> requests.Response:
    global max_api_call_tries
    global api_call_pause_on_error
    global api_log
    global session
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
    headers = {'Accept-Encoding': 'gzip'}
    while True:
        if require_auth:
            inc_call_cnt(PLATFORM_NAME, method_name)
        api_log.debug("Request to {} for {}".
                      format(url, params if len(params) > 0 else "no parameters"))
        try:
            r = session.get(real_url, timeout=30, headers=headers)
            api_log.debug("Response from {} for {} is {}".
                          format(url, params if len(params) > 0 else "no parameters", r))
            if r.status_code != 200:
                inc_error_cnt(PLATFORM_NAME, method_name, str(r.status_code))
            if r.status_code == 200 or cnt >= max_api_call_tries:
                api_log.debug("Full response {} for {} is {}".
                              format(url, params if len(params) > 0 else "no parameters", r.text))
                break
            if r.status_code == 400 and r.json() is not None:
                player_stats = r.json().get("playerstats")
                if player_stats is not None and not player_stats.get("success"):
                    if player_stats.get("error") == "Requested app has no stats":
                        api_log.info("Can't get achievements info for {}, probably because it's not on account anymore"
                                     .format(params))
                        break
            api_log.error("Full response from {} for {} is {}, Limit used: {}, ends {}, response code {}".
                          format(url, params if len(params) > 0 else "no parameters", r.text,
                                 get_limit_counter(url), get_limit_interval_end(url), r.status_code),
                          exc_info=True,
                          )
            if r.status_code == 400:
                break
            if r.status_code == 403:
                api_log.info("Didn't have access to {}, probably because of private profile".format(url))
                break
        except requests.exceptions.ConnectTimeout as exc:
            session = requests.Session()
            api_log.error(exc)
            if cnt >= max_api_call_tries:
                raise ApiException("Steam timeout")
        except requests.exceptions.ReadTimeout as exc:
            session = requests.Session()
            api_log.error(exc)
            if cnt >= max_api_call_tries:
                raise ApiException("Steam timeout")
        cnt += 1
        time.sleep(api_call_pause_on_error)
    return r


def init_platform(config: Config) -> Platform:
    global api_log
    global max_api_call_tries
    global api_call_pause_on_error
    global hardcoded_games
    global session
    session = requests.Session()
    hardcoded_games = {}
    f = config.file_path[:config.file_path.rfind('/')] + "steam.json"
    fp = codecs.open(f, 'r', "utf-8")
    steam_config = json.load(fp)
    key_read = steam_config.get("API_KEY")
    incremental_update_enabled = steam_config.get("INCREMENTAL_UPDATE_ENABLED")
    incremental_update_interval = steam_config.get("INCREMENTAL_UPDATE_INTERVAL")
    incremental_skip_chance = steam_config.get("INCREMENTAL_SKIP_CHANCE")
    api_calls_daily_limit = steam_config.get("API_CALLS_DAILY_LIMIT")
    if api_calls_daily_limit is not None:
        sef_daily_call_limit(PLATFORM_NAME, int(api_calls_daily_limit))
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
    call_counters_retain = steam_config.get("CALL_COUNTERS_RETAIN")
    if call_counters_retain is not None:
        set_call_counters_retain(PLATFORM_NAME, int(call_counters_retain))
    steam = Platform(name='Steam', get_games=get_player_games, get_achievements=get_player_achievements,
                     get_game=get_game, games=None, id=PLATFORM_STEAM, validate_player=get_player_stats,
                     get_player_id=get_name,
                     get_stats=get_api_counters, incremental_update_enabled=incremental_update_enabled,
                     incremental_update_interval=incremental_update_interval, get_last_games=get_player_last_games,
                     incremental_skip_chance=incremental_skip_chance, get_consoles=None,
                     get_player_stats=get_player_stats_for_game, set_hardcoded=set_hardcoded,
                     get_player_avatar=get_player_avatar)
    api_log = steam.logger
    if is_password_encrypted(key_read):
        api_log.info("Steam key encrypted, do nothing")
        open_key = decrypt_password(key_read, config.server_name, config.db_port)
    elif config.mode == MODE_CORE:
        api_log.info("Steam key in plain text, start encrypt")
        password = encrypt_password(key_read, config.server_name, config.db_port)
        save_api_key(password, f)
        api_log.info("Steam key encrypted and save back in config")
        open_key = key_read
    else:
        api_log.info("Steam key in plain text, but work in not core")
        open_key = key_read
    set_key(open_key)
    # actual limit 200 requests per 300 seconds
    set_limit("https://store.steampowered.com/api/appdetails/", 305, 198, api_log)
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
    global session
    params = {
        "steamid": player_id,
        "include_played_free_games": True,
        "include_appinfo": True,
        "skip_unvetted_apps": False,
    }
    session = requests.Session()
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
    global skip_extra_info
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
        if len(game_name) == 0:
            game_name = obj.get("gameName")
            api_log.warn("For game {0}, found name {1} instead of empty one".format(game_id, game_name))
        api_log.info(
            "For game \"{2}\" ( ext_id: {0}), found {1} achievements".format(
                game_id, len(achievements), game_name))
    params = {
        "appids": game_id,
    }
    if not skip_extra_info:
        r = do_with_limit("https://store.steampowered.com/api/appdetails/",
                          _call_steam_api,
                          dict(url="https://store.steampowered.com/api/appdetails/",
                               method_name="appdetails",
                               params=params,
                               require_auth=False)
                          )
    icon_url = None
    release_date = None
    developer = None
    publisher = None
    genres = []
    features = []
    if skip_extra_info or r.status_code == 200:
        obj = r.json()
        if obj is not None:
            obj = obj.get(game_id)
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
    if player_stats is not None:
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
    global session
    global summary_cache
    global summary_cache_key
    params = {
        "steamids": player_id,
    }
    session = requests.Session()
    if summary_cache_key is not None and summary_cache_key == player_id:
        r = summary_cache
        summary_cache_key = None
    else:
        r = _call_steam_api(url="http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
                            method_name="GetPlayerSummaries",
                            params=params)
    res = r.json().get("response").get("players")
    if len(res) == 0:
        return None
    else:
        summary_cache_key = player_id
        summary_cache = r
        if "personaname" in res[0]:
            name = res[0]["personaname"]
        elif "realname" in res[0]:
            name = res[0]["realname"]
        else:
            name = None
        return name


def get_player_avatar(player_id):
    global summary_cache
    global summary_cache_key
    if summary_cache_key is not None and summary_cache_key == player_id:
        r = summary_cache
    else:
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
        summary_cache_key = player_id
        summary_cache = r
        if "avatarmedium" in res[0]:
            url = res[0]["avatarmedium"]
        elif "avatarfull" in res[0]:
            url = res[0]["avatarfull"]
        elif "avatar" in res[0]:
            url = res[0]["avatar"]
        else:
            url = None
        return url


def get_api_counters():
    return get_call_cnt(PLATFORM_NAME)


def set_hardcoded(games_names_map: Dict):
    global hardcoded_games
    hardcoded_games = games_names_map
