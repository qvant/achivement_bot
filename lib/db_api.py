import psycopg2

from lib.achievement import Achievement
from lib.config import Config
from lib.query_holder import get_query, UPSERT_ACHIEVEMENT_ENGLISH, INSERT_ACHIEVEMENT,\
    UPSERT_ACHIEVEMENT_TRANSLATION, GET_ACHIEVEMENT_TEXT, GET_ACHIEVEMENT_ID

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
