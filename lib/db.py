from typing import Union

import psycopg2

from lib.config import Config
from lib.platform import Platform
from lib.platforms.steam import init_platform as init_steam
from lib.player import STATUS_VALID, Player
from .log import get_logger

global load_log


def set_load_logger(cfg: Config):
    global load_log
    load_log = get_logger("loader_" + str(cfg.mode), cfg.log_level)


def load(config: Config, load_games: bool = True, load_achievements: bool = True):
    global load_log
    platforms = [
        init_steam(config)]
    Platform.set_load_log(load_log)
    if load_games:
        for i in platforms:
            i.load_games(load_achievements)
    return platforms


def load_players(platform: Platform, config: Config, player_id: Union[int, None] = None):
    global load_log
    conn = psycopg2.connect(dbname=config.db_name, user=config.db_user,
                            password=config.db_password, host=config.db_host, port=config.db_port)
    cursor = conn.cursor()

    if player_id is None:
        cursor.execute("""
        select id, platform_id, name, ext_id, telegram_id, dt_update
        from achievements_hunt.players
        where platform_id = %s
            and status_id = %s
        order by id
        """, (platform.id, STATUS_VALID))
    else:
        cursor.execute("""
            select id, platform_id, name, ext_id, telegram_id, dt_update
            from achievements_hunt.players
            where platform_id = %s
                and id = %s
            order by id
            """, (platform.id, player_id))
    players = []
    for id, platform_id, name, ext_id, telegram_id, dt_updated in cursor:
        load_log.info("Loaded player {0} with id {1}, ext_id {2}, for platform {3} on platform".
                      format(name, ext_id, id, platform.name))
        test = Player(name=name, platform=platform, ext_id=ext_id, id=id, telegram_id=telegram_id,
                      dt_updated=dt_updated)
        players.append(test)
    conn.close()
    return players
