from datetime import datetime

from typing import Union

import psycopg2

from lib.config import Config, MODE_WORKER
from lib.platform import Platform
from lib.platforms.steam import init_platform as init_steam
from lib.platforms.retroachievements import init_platform as init_retro
from lib.player import STATUS_VALID, Player
from .log import get_logger

global load_log


def set_load_logger(cfg: Config):
    global load_log
    load_log = get_logger("loader_" + str(cfg.mode), cfg.log_level)


def load(config: Config, load_games: bool = True, load_achievements: bool = True):
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
        cursor.execute("""
        select id, platform_id, name, ext_id, telegram_id, dt_update, dt_update_full, dt_update_inc, avatar_url
        from achievements_hunt.players
        where platform_id = %s
            and status_id = %s
        order by id
        """, (platform.id, STATUS_VALID))
    else:
        cursor.execute("""
            select id, platform_id, name, ext_id, telegram_id, dt_update, dt_update_full, dt_update_inc,
                avatar_url
            from achievements_hunt.players
            where platform_id = %s
                and id = %s
                and (status_id = %s or %s is null)
            order by id
            """, (platform.id, player_id, status_id, status_id))
    players = []
    for id, platform_id, name, ext_id, telegram_id, dt_updated, dt_update_full, dt_update_inc, avatar_url in cursor:
        load_log.info("Loaded player {0} with id {1}, ext_id: {2}, for platform: {3}".
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
    cursor.execute("""
            select max(dt_next_update) from achievements_hunt.update_history
                where id_platform = %s
                    and dt_ended is not null
                    and id_process = %s
            """, (platform.id, id_process))
    ret = cursor.fetchone()
    conn.commit()
    if ret is not None and ret[0] is not None:
        return ret[0]
    else:
        return datetime.now()


def mark_update_done(platform: Platform, id_process: int, dt_next_update: datetime):
    conn = Platform.get_connect()
    cursor = conn.cursor()
    cursor.execute("""
                    update achievements_hunt.update_history
                        set dt_ended = current_timestamp,
                        dt_next_update = %s
                        where id_platform = %s
                        and id_process = %s
                        and dt_ended is null
                    """, (dt_next_update, platform.id, id_process))
    conn.commit()


def start_update(platform: Platform, id_process: int):
    conn = Platform.get_connect()
    cursor = conn.cursor()
    cursor.execute("""
                        select count(1) from achievements_hunt.update_history where id_platform = %s
                        and id_process = %s
                        and dt_ended is null
                        """, (platform.id, id_process))
    cnt, = cursor.fetchone()
    if cnt == 0:
        cursor.execute("""insert into achievements_hunt.update_history(id_platform) values (%s)""", (platform.id,))
    conn.commit()


def get_players_count():
    conn = Platform.get_connect()
    cursor = conn.cursor()
    res = {}
    # TODO less expensive way
    cursor.execute("""
                    select count(1), p.name
                      from achievements_hunt.players pl
                      join achievements_hunt.platforms p
                        on p.id = pl.platform_id
                      group by p.name""")
    for cnt, platform_name in cursor:
        res[platform_name] = cnt
    conn.commit()
    return res
