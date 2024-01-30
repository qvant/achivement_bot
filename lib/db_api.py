from typing import Union, List, Dict

import psycopg2

from lib.achievement import Achievement
from lib.config import Config
from lib.game import Game
from lib.query_holder import get_query, UPSERT_ACHIEVEMENT_ENGLISH, INSERT_ACHIEVEMENT, \
    UPSERT_ACHIEVEMENT_TRANSLATION, GET_ACHIEVEMENT_TEXT, GET_ACHIEVEMENT_ID, GET_COMPANY_ID, INSERT_COMPANY, \
    GET_GENRE_ID, INSERT_GENRE, INSERT_GAME, GET_GAME_ID, UPDATE_GAME, GET_GAME_GENRES, DELETE_GAME_GENRES, \
    INSERT_GAME_GENRE, GET_GAME_FEATURES, DELETE_GAME_FEATURES, INSERT_GAME_FEATURE, GET_GAME_STATS, UPSERT_GAME_STATS, \
    GET_GAME_STAT_ID

global connect
global config

# new API module, free from unnessesary dependencies. When project completely moved here, db.py must be removed


def save_english_achievement(achievement: Achievement):
    cursor = get_cursor()
    cursor.execute(get_query(UPSERT_ACHIEVEMENT_ENGLISH),
                   (achievement.name, achievement.ext_id, achievement.platform_id, achievement.game_id,
                    achievement.description, achievement.icon_url, achievement.locked_icon_url,
                    achievement.is_hidden, achievement.is_removed)
                   )
    ret = cursor.fetchone()
    if ret is None:
        cursor = get_cursor()
        cursor.execute(get_query(GET_ACHIEVEMENT_ID),
                       (achievement.platform_id, achievement.ext_id, achievement.game_id))
    if ret is not None:
        id = ret[0]
    else:
        # TODO: add logs
        id = None
    return id


def save_l18n_achievement(achievement: Achievement):
    cursor = get_cursor()
    cursor.execute(get_query(INSERT_ACHIEVEMENT),
                   (achievement.name, achievement.ext_id, achievement.platform_id, achievement.game_id,
                    achievement.description, achievement.icon_url, achievement.locked_icon_url, achievement.is_hidden,
                    achievement.is_removed)
                   )
    ret = cursor.fetchone()
    if ret is None:
        cursor.execute(get_query(GET_ACHIEVEMENT_ID),
                       (achievement.platform_id, achievement.ext_id, achievement.game_id))
        ret = cursor.fetchone()
    id = ret[0]
    return id


def save_achievement_translation(achievement: Achievement, active_locale: str):
    cursor = get_cursor()
    cursor.execute(get_query(UPSERT_ACHIEVEMENT_TRANSLATION),
                   (achievement.platform_id, achievement.game_id, achievement.id, active_locale, achievement.name,
                    achievement.description))


def get_achievement_text_for_locale(achievement: Achievement, active_locale: str):
    cursor = get_cursor()
    cursor.execute(get_query(GET_ACHIEVEMENT_TEXT), (active_locale, achievement.platform_id, achievement.game_id,
                                                     achievement.id))
    ret = cursor.fetchone()
    achievement_name = ret[0]
    achievement_description = ret[1]
    return achievement_name, achievement_description


def get_game_id(game: Game) -> Union[int, None]:
    cursor = get_cursor()
    cursor.execute(get_query(GET_GAME_ID), (game.platform_id, str(game.ext_id)))
    ret = cursor.fetchone()
    if ret is not None:
        return ret[0]
    return None


def save_game(game: Game, developer_id: int, publisher_id: int) -> int:
    cursor = get_cursor()
    if game.id is None:
        game.id = get_game_id(game)
    if game.id is None:
        cursor.execute(get_query(INSERT_GAME),
                       (game.name, game.ext_id, game.platform_id, game.has_achievements, game.console_id(),
                        game.icon_url, game.release_date, developer_id, publisher_id)
                       )
        ret = cursor.fetchone()
        if ret is not None:
            game.id = ret[0]
        else:
            game.id = get_game_id(game)
    else:
        cursor.execute(get_query(UPDATE_GAME), (game.name, game.has_achievements, game.console_id(),
                                                game.icon_url, game.release_date, developer_id, publisher_id,
                                                game.id, game.platform_id, game.name, game.has_achievements,
                                                game.console_id(), game.icon_url, game.release_date,
                                                developer_id, publisher_id)
                       )


def save_game_genres(platform_id: int, game_id: int, genres: List[int]):
    cursor = get_cursor()
    cursor.execute(get_query(GET_GAME_GENRES), (platform_id, game_id))
    saved_genres = []
    for i in cursor:
        saved_genres.append(i)
    if set(saved_genres) != set(genres) and len(genres) > 0:
        # TODO: delete and insert only removed
        cursor.execute(get_query(DELETE_GAME_GENRES), (platform_id, game_id))
        for cur_g in genres:
            # there not that many records, so no profit from bulk
            cursor.execute(get_query(INSERT_GAME_GENRE), (platform_id, game_id, cur_g))


def save_game_features(platform_id: int, game_id: int, features: List[int]):
    cursor = get_cursor()
    cursor.execute(get_query(GET_GAME_FEATURES), (platform_id, game_id))
    saved_features = []
    for i in cursor:
        saved_features.append(i)
    if set(saved_features) != set(features) and len(features) > 0:
        # TODO: delete and insert only removed
        cursor.execute(get_query(DELETE_GAME_FEATURES), (platform_id, game_id))
        for cur_f in features:
            # there not that many records, so no profit from bulk
            cursor.execute(get_query(INSERT_GAME_FEATURE), (platform_id, game_id, cur_f))


def get_game_stat_id(platform_id: int, game_id: int, ext_id: str) -> Union[int, None]:
    cursor = get_cursor()
    cursor.execute(get_query(GET_GAME_STAT_ID), (platform_id, game_id, ext_id))
    ret = cursor.fetchone()
    if ret is not None:
        return ret[0]
    return None


def save_game_stats(platform_id: int, game_id: int, stats: Dict[str, str]):
    cursor = get_cursor()
    stats_to_save = {}
    stats_exists = {}
    cursor.execute(get_query(GET_GAME_STATS), (platform_id, game_id))
    for stat_id, stat_ext_id, stat_name in cursor:
        stats_exists[stat_ext_id] = stat_name
    for ext_id in stats:
        if ext_id not in stats_exists:
            stats_to_save[ext_id] = stats[ext_id]
        elif stats_exists[ext_id] != stats[ext_id]:
            stats_to_save[ext_id] = stats[ext_id]
    for ext_id in stats_to_save:
        cursor.execute(get_query(UPSERT_GAME_STATS), (platform_id, game_id, ext_id, stats_to_save[ext_id]))


def get_company_id(company_name: str, platform_id: int) -> int:
    cursor = get_cursor()
    cursor.execute(get_query(GET_COMPANY_ID), (platform_id, company_name,))
    ret = cursor.fetchone()
    if ret is None:
        cursor.execute(get_query(INSERT_COMPANY), (platform_id, company_name,))
        ret = cursor.fetchone()
    return ret[0]


def get_genre_id(genre_name: str, platform_id: int) -> int:
    cursor = get_cursor()
    cursor.execute(get_query(GET_GENRE_ID), (platform_id, genre_name,))
    ret = cursor.fetchone()
    if ret is None:
        cursor.execute(get_query(INSERT_GENRE), (platform_id, genre_name,))
        ret = cursor.fetchone()
    return ret[0]


def set_db_config(cfg: Config):
    global config
    global connect
    config = cfg
    connect = None


def commit():
    connect.commit()


def get_connect():
    global connect
    if connect is None:
        connect = psycopg2.connect(dbname=config.db_name, user=config.db_user,
                                   password=config.db_password, host=config.db_host,
                                   port=config.db_port)
    elif connect.closed != 0:
        connect = psycopg2.connect(dbname=config.db_name, user=config.db_user,
                                   password=config.db_password, host=config.db_host,
                                   port=config.db_port)
    return connect


def get_cursor():
    return get_connect().cursor()
