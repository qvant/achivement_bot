global queries
global query_texts

GET_NEXT_UPDATE_DATE = "get_next_update_date"
MARK_UPDATE_DONE = "mark_update_done"
CHECK_UPDATE_ACTIVE = "check_update_active"
START_UPDATE = "start_update"
GET_PLAYER_COUNT = "get_player_count"
GET_PLAYER = "get_player"
GET_PLAYERS = "get_players"
GET_PLAYERS_BY_TELEGRAM_ID = "get_players_by_telegram_id"
SET_USER_LOCALE = "set_user_locale"
GET_PLAYER_GAMES = "get_player_games"
GET_PLAYER_STATS = "get_player_stats"

queries = {GET_NEXT_UPDATE_DATE: r"db\queries\get_next_update_date.sql",
           MARK_UPDATE_DONE: r"db\queries\mark_update_done.sql",
           CHECK_UPDATE_ACTIVE: r"db\queries\check_update_active.sql",
           START_UPDATE: r"db\queries\start_update.sql",
           GET_PLAYER_COUNT: r"db\queries\get_player_count.sql",
           GET_PLAYER: r"db\queries\get_player.sql",
           GET_PLAYERS: r"db\queries\get_players.sql",
           GET_PLAYERS_BY_TELEGRAM_ID: r"db\queries\get_players_by_telegram_id.sql",
           SET_USER_LOCALE: r"db\queries\set_user_locale.sql",
           GET_PLAYER_GAMES: r"db\queries\get_player_games.sql",
           GET_PLAYER_STATS: r"db\queries\get_player_stats.sql",
           }
query_texts = {}


def read_query(name: str) -> str:
    return open(queries[name], "r").read()


def get_query(name: str) -> str:
    global query_texts
    if name not in query_texts:
        query_texts[name] = read_query(name)
    return query_texts[name]
