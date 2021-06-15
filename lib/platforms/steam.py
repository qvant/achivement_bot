import json
import codecs
import requests
import time
import datetime
from ..achievement import Achievement
from ..config import Config
from ..game import Game
from ..log import get_logger
from ..platform import Platform
from ..security import is_password_encrypted, encrypt_password, decrypt_password
from ..config import MODE_CORE

MAX_TRIES = 0
WAIT_BETWEEN_TRIES = 5

PLATFORM_STEAM = 1

global api_log
global api_key
global call_counters


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
    cur_dt = str(datetime.date.today())
    if call_counters is None:
        call_counters = {}
    if cur_dt not in call_counters:
        call_counters[cur_dt] = {}
    if method not in call_counters[cur_dt]:
        call_counters[cur_dt][method] = 0
    call_counters[cur_dt][method] += 1


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


def init_platform(config: Config) -> Platform:
    global api_log
    global call_counters
    call_counters = {}
    api_log = get_logger("LOG_API_" + str(config.mode), config.log_level, True)
    f = config.file_path[:config.file_path.rfind('/')] + "steam.json"
    fp = codecs.open(f, 'r', "utf-8")
    steam_config = json.load(fp)
    key_read = steam_config.get("API_KEY")
    incremental_update_enabled = steam_config.get("INCREMENTAL_UPDATE_ENABLED")
    incremental_update_interval = steam_config.get("INCREMENTAL_UPDATE_INTERVAL")
    incremental_skip_chance = steam_config.get("INCREMENTAL_SKIP_CHANCE")
    steam = Platform(name='Steam', get_games=get_player_games, get_achivements=get_player_achievements,
                     get_game=get_game, games=None, id=1, validate_player=get_player_stats, get_player_id=get_name,
                     get_stats=get_call_cnt, incremental_update_enabled=incremental_update_enabled,
                     incremental_update_interval=incremental_update_interval, get_last_games=get_player_last_games,
                     incremental_skip_chance=incremental_skip_chance)
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
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("GetRecentlyPlayedGames")
        api_log.info("Request http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/ for user {0}".
                     format(player_id))
        r = requests.get(
            "http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/?key={0}&steamid={1}"
            "&include_played_free_games=true&include_appinfo=true".format(get_key(), player_id))
        api_log.info("Response from http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/:"
                     " {1} for player {0}".
                     format(player_id, r))
        api_log.debug("Full response from http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/: "
                      "{1} for player {0}".format(player_id, r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    res = [[], []]
    obj = r.json().get("response")
    if obj is not None and "games" in obj:
        for i in obj.get("games"):
            res[0].append(i.get("appid"))
            res[1].append(i.get("name"))
    return res


def get_player_games(player_id):
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("GetOwnedGames")
        api_log.info("Request http://api.steampowered.com/IPlayerService/GetOwnedGames/ for user {0}".format(player_id))
        r = requests.get(
            "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={0}&steamid={1}"
            "&include_played_free_games=true&include_appinfo=true".format(get_key(), player_id))
        api_log.info("Response from http://api.steampowered.com/IPlayerService/GetOwnedGames/: {1} for player {0}".
                     format(player_id, r))
        api_log.debug("Full response from http://api.steampowered.com/IPlayerService/GetOwnedGames/: "
                      "{1} for player {0}".format(player_id, r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    res = [[], []]
    obj = r.json().get("response")
    if obj is not None and "games" in obj:
        for i in obj.get("games"):
            res[0].append(i.get("appid"))
            res[1].append(i.get("name"))
    return res


def get_game(game_id: str, name: str, language: str = "English") -> Game:
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("GetSchemaForGame")
        api_log.info("Request http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/ "
                     "for game {0}, name {1} language {2} supplied".format(game_id, name, language))
        r = requests.get(
            "http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key={0}&appid={1}&l={2}".
            format(get_key(), game_id, language))
        api_log.info("Response from http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/ "
                     "{0} from Steam".format(r))
        api_log.debug("Full response from http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/: {0}".
                      format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    achievements = {}
    game_name = None
    obj = r.json().get("game")
    if len(obj) > 0:
        if "availableGameStats" in obj:
            obj_achievements = obj.get("availableGameStats").get("achievements")
            if obj_achievements is not None:
                for i in obj_achievements:
                    ext_id = i.get("ext_id")
                    if ext_id is None or len(ext_id) == 0:
                        ext_id = i.get("name")
                    achievements[ext_id] = Achievement(id=None,
                                                       game_id=None,
                                                       name=i.get("displayName"),
                                                       ext_id=i.get("name"),
                                                       platform_id=PLATFORM_STEAM,
                                                       description=i.get("description"))
        api_log.info(
            "For game {0}, found {1} achievements".format(
                game_id, len(achievements)))
        game_name = obj.get("gameName")
        "For game {0}, found name {1}".format(
            game_id, game_name)
    # there was logic of getting name from GetSchemaForGame responce, but it seems, that this data have lower quality
    if 1 == 1:
        api_log.info(
            "For game {0} skip name not found in response ({2}), used supplied name {1}".format(
                game_id, name, game_name))
        game_name = name
    return Game(name=game_name, platform_id=PLATFORM_STEAM, ext_id=game_id, id=None, achievements=achievements)


def get_player_achievements(player_id, game_id):
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("GetPlayerAchievements")
        api_log.info("Request http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements "
                     "for game {0} and player {1}".format(game_id, player_id))
        r = requests.get(
            "http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/"
            "v0001/?key={0}&steamid={1}&appid={2}".format(get_key(), player_id, game_id))
        api_log.info("Response from http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/:{0}".format(r))
        api_log.debug("Full response from http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/: {0}".
                      format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        if r.status_code == 403:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
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


def get_name(player_name: str):
    global api_log
    cnt = 0
    player_id = None
    while True:
        inc_call_cnt("ResolveVanityURL")
        api_log.info("Request http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001"
                     " for player {0}".format(player_name))
        r = requests.get(
            "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={0}&vanityurl={1}".format(
                get_key(), player_name))
        api_log.info("Response from http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/:{0}".format(r))
        api_log.debug("Full response from http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/: {0}".
                      format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    buf = r.json().get("response")
    if buf is not None:
        player_id = buf.get("steamid")
    if player_id is None and player_name.isnumeric():
        buf = get_player_stats(player_name)
        if buf is not None:
            player_id = player_name
    return player_id


def get_player_stats(player_id):
    global api_log
    cnt = 0
    while True:
        inc_call_cnt("GetPlayerSummaries")
        api_log.info("Request http://api.steampowered.com/ISteamUser/GetPlayerSummaries/ "
                     "for player {0}".format(player_id))
        r = requests.get(
            "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={0}&steamids={1}".format(get_key(),
                                                                                                           player_id))
        api_log.info("Response from http://api.steampowered.com/ISteamUser/GetPlayerSummaries/: {0}".format(r))
        api_log.debug("Full response from http://api.steampowered.com/"
                      "ISteamUser/GetPlayerSummaries/: {0}".format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
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
