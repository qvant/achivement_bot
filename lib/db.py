from datetime import datetime

from typing import Union, List

import psycopg2

from lib.config import Config, MODE_WORKER
from lib.platform import Platform
from lib.platforms.steam import init_platform as init_steam
from lib.platforms.retroachievements import init_platform as init_retro
from lib.player import STATUS_VALID, Player
from .log import get_logger
from .query_holder import get_query, GET_NEXT_UPDATE_DATE, MARK_UPDATE_DONE, CHECK_UPDATE_ACTIVE, START_UPDATE, \
    GET_PLAYER_COUNT, GET_PLAYERS, GET_PLAYER

global load_log

# TODO: Move everything into db_api.py


def set_load_logger(cfg: Config):
    global load_log
    load_log = get_logger("loader_" + str(cfg.mode), cfg.log_level)


def load(config: Config, load_games: bool = True, load_achievements: bool = True) -> List[Platform]:
    global load_log
    platforms = [
        init_steam(config), init_retro(config)]
    Platform.set_load_log(load_log)
    if load_games:
        for i in platforms:
            hardcoded = config.mode == MODE_WORKER
            i.load_games(load_achievements, load_hardcoded=hardcoded)
    return platforms


def load_players(platform: Platform, config: Config, player_id: Union[int, None] = None, status_id: [int, None] = None):
    global load_log
    conn = psycopg2.connect(dbname=config.db_name, user=config.db_user,
                            password=config.db_password, host=config.db_host, port=config.db_port)
    cursor = conn.cursor()

    if player_id is None:
        cursor.execute(get_query(GET_PLAYERS), (platform.id, STATUS_VALID))
    else:
        cursor.execute(get_query(GET_PLAYER), (platform.id, player_id, status_id, status_id))
    players = []
    for id, platform_id, name, ext_id, telegram_id, dt_updated, dt_update_full, dt_update_inc, avatar_url in cursor:
        load_log.debug("Loaded player {0} with id {1}, ext_id: {2}, for platform: {3}".
                       format(name, ext_id, id, platform.name))
        test = Player(name=name, platform=platform, ext_id=ext_id, id=id, telegram_id=telegram_id,
                      dt_updated=dt_updated, dt_updated_full=dt_update_full, dt_updated_inc=dt_update_inc,
                      avatar_url=avatar_url)
        players.append(test)
    conn.close()
    return players


def get_next_update_date(platform: Platform, id_process: int):
    conn = Platform.get_connect()
    cursor = conn.cursor()
    cursor.execute(get_query(GET_NEXT_UPDATE_DATE), (platform.id, id_process))
    ret = cursor.fetchone()
    conn.commit()
    if ret is not None and ret[0] is not None:
        return ret[0]
    else:
        return datetime.now()


def mark_update_done(platform: Platform, id_process: int, dt_next_update: datetime):
    conn = Platform.get_connect()
    cursor = conn.cursor()
    cursor.execute(get_query(MARK_UPDATE_DONE), (dt_next_update, platform.id, id_process))
    conn.commit()


def start_update(platform: Platform, id_process: int):
    conn = Platform.get_connect()
    cursor = conn.cursor()
    cursor.execute(get_query(CHECK_UPDATE_ACTIVE), (platform.id, id_process))
    cnt, = cursor.fetchone()
    if cnt == 0:
        cursor.execute(get_query(START_UPDATE), (platform.id, id_process))
    conn.commit()


def get_players_count():
    conn = Platform.get_connect()
    cursor = conn.cursor()
    res = {}
    # TODO less expensive way
    cursor.execute(get_query(GET_PLAYER_COUNT))
    for cnt, platform_name in cursor:
        res[platform_name] = cnt
    conn.commit()
    return res
