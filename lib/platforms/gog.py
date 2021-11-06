import json
import codecs
import requests
import time
import datetime
from bs4 import BeautifulSoup
from ..achievement import Achievement
from ..config import Config
from ..game import Game
from ..log import get_logger
from ..platform import Platform
from ..security import is_password_encrypted, encrypt_password, decrypt_password
from ..config import MODE_CORE

MAX_TRIES = 3
WAIT_BETWEEN_TRIES = 5

PLATFORM_GOG = 3

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
    while True:
        inc_call_cnt("https://www.gog.com/u/")
        api_log.info("Check if user {} exists".format(player_name))
        r = requests.get(
            "https://www.gog.com/u/{}".
            format(player_name))
        api_log.info("Response from https://www.gog.com/u/{} "
                     "{} from GOG".format(player_name, r))
        api_log.debug("Full response from https://www.gog.com/u/{1}: {0}".
                      format(r.text, player_name))
        if r.status_code == 200 or r.status_code == 404 or cnt >= MAX_TRIES:
            break
        api_log.error("Full response from https://www.gog.com/u/{1}: {0}".
                      format(r.text, player_name))
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    player_id = None
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        for i in soup.find_all('div'):
            player_id = i.get("prof-game-statistics-user-id")
            if player_id is not None:
                break
            player_id = i.get("prof-user-status")
            if player_id is not None:
                break
    return player_id


def get_game(game_id: str, name: str, language: str = "en-US") -> Game:
    global api_log
    cnt = 0
    game_name = name
    while True:
        inc_call_cnt("api.gog.com/v2/games")
        api_log.info("Request https://api.gog.com/v2/games/ "
                     "for game {0}, name {1} language {2} supplied".format(game_id, name, language))
        r = requests.get(
            "https://api.gog.com/v2/games/{}?locale={}".
            format(game_id, language))
        api_log.info("Response from https://api.gog.com/v2/games/ "
                     "{0} from GOG".format(r))
        api_log.debug("Full response from https://api.gog.com/v2/games/: {0}".
                      format(r.text))
        if r.status_code == 200 or cnt >= MAX_TRIES:
            break
        api_log.error("Full response from https://api.gog.com/v2/games/: {0}".
                      format(r.text))
        cnt += 1
        time.sleep(WAIT_BETWEEN_TRIES)
    obj = r.json().get("_embedded")
    if len(obj) > 0:
        product = obj.get("product")
        if len(product) > 0:
            game_name = product.get("title")
    # TODO: more info
    return Game(name=game_name, platform_id=PLATFORM_GOG, ext_id=game_id, id=None, achievements=None,
                console_ext_id=None, console=None)


def get_player_achievements(player_id, game_id):
    global api_log
    cnt = 0
    return [], []


def get_player_games(player_id):
    global api_log
    cnt = 0
    res = [[], []]
    return res


def get_last_player_games(player_id):
    global api_log
    cnt = 0
    res = [[], []]
    return res


def init_platform(config: Config) -> Platform:
    global api_log
    global call_counters
    call_counters = {}
    api_log = get_logger("LOG_API_GOG_" + str(config.mode), config.log_level, True)
    f = config.file_path[:config.file_path.rfind('/')] + "gog.json"
    fp = codecs.open(f, 'r', "utf-8")
    gog_config = json.load(fp)
    key_read = gog_config.get("API_KEY")
    user = gog_config.get("API_USER")
    incremental_update_enabled = gog_config.get("INCREMENTAL_UPDATE_ENABLED")
    incremental_update_interval = gog_config.get("INCREMENTAL_UPDATE_INTERVAL")
    incremental_skip_chance = gog_config.get("INCREMENTAL_SKIP_CHANCE")
    retro = Platform(name='GOG', get_games=get_player_games, get_achivements=get_player_achievements,
                     get_game=get_game, games=None, id=3, validate_player=get_name, get_player_id=get_name,
                     get_stats=get_call_cnt, incremental_update_enabled=incremental_update_enabled,
                     incremental_update_interval=incremental_update_interval, get_last_games=get_last_player_games,
                     incremental_skip_chance=incremental_skip_chance, get_consoles=None)
    if is_password_encrypted(key_read):
        api_log.info("GOG key encrypted, do nothing")
        open_key = decrypt_password(key_read, config.server_name, config.db_port)
    elif config.mode == MODE_CORE:
        api_log.info("GOG key in plain text, start encrypt")
        password = encrypt_password(key_read, config.server_name, config.db_port)
        _save_api_key(password, f)
        api_log.info("GOG key encrypted and save back in config")
        open_key = key_read
    else:
        api_log.info("GOG key in plain text, but work in not core")
        open_key = key_read
    set_key(open_key)
    set_user(user)
    return retro
