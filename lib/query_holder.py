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
GET_PLAYER_INFO = "get_player_info"
GET_PLAYER_STATS = "get_player_stats"
UPSERT_ACHIEVEMENT_ENGLISH = "upsert_achievement_english"
INSERT_ACHIEVEMENT = "insert_achievement"
GET_ACHIEVEMENT_TEXT = "get_achievement_text"
UPSERT_ACHIEVEMENT_TRANSLATION = "upsert_achievement_translation"
INSERT_CONSOLE = "insert_console"
GET_CONSOLE_ID = "get_console_id"
GET_COMPANY_ID = "get_company_id"
INSERT_COMPANY = "insert_company"
GET_GENRE_ID = "get_genre_id"
INSERT_GENRE = "insert_genre"
GET_FEATURE_ID = "get_feature_id"
INSERT_FEATURE = "insert_feature"
INSERT_GAME = "insert_game"
GET_GAME_ID = "get_game_id"
GET_GAME_GENRES = "get_game_genres"
DELETE_GAME_GENRES = "delete_game_genres"
INSERT_GAME_GENRE = "insert_game_genre"
GET_GAME_FEATURES = "get_game_features"
DELETE_GAME_FEATURES = "delete_game_features"
INSERT_GAME_FEATURE = "insert_game_feature"
UPDATE_GAME = "update_game"
GET_ACHIEVEMENTS_FOR_GAME = "get_achievements_for_game"
GET_TRANSLATED_ACHIEVEMENTS_FOR_GAME = "get_translated_achievements_for_game"
GET_GAME_STATS = "get_game_stats"
UPSERT_GAME_STATS = "upsert_game_stats"
GET_ACCOUNT_LAST_ACHIEVEMENTS = "GET_ACCOUNT_LAST_ACHIEVEMENTS"
GET_ACCOUNT_RAREST_ACHIEVEMENTS = "GET_ACCOUNT_RAREST_ACHIEVEMENTS"
GET_PLAYER_CONSOLES = "get_player_consoles"
GET_PLAYER_LAST_UPDATE_DATE = "get_player_last_update_date"
GET_USER_LOCALE = "get_user_locale"
INSERT_USER = "insert_user"
GET_LAST_GLOBAL_ACHIEVEMENTS = "get_last_global_achievements"
GET_LAST_GAME_PERFECTED_TIME_FOR_PLAYER = "get_last_game_perfected_time_for_player"
UPDATE_PLAYER_EXT_ID = "update_player_ext_id"
DELETE_PLAYER = "delete_player"
UPDATE_PLAYER_TELEGRAM_ID = "update_player_telegram_id"
UPDATE_PLAYER_STATUS = "update_player_status"
GET_PLAYER_STATUS = "get_player_status"
GET_USER_LAST_DELETE = "get_user_last_delete"
UPDATE_USER_SET_LAST_DELETE_DATE = "update_user_set_last_delete_date"
CHECK_PLAYERS_FOR_TELEGRAM_ID = "check_players_for_telegram_id"
CHECK_PLAYERS_FOR_EXT_ID = "check_players_for_ext_id"
CHECK_IS_PLAYER_BOUND_TO_TELEGRAM = "check_is_player_bound_to_telegram"
GET_PLAYER_GAMES = "get_player_games"
GET_PLAYER_GAMES_WITH_ACHIEVEMENTS = "get_player_games_with_achievements"
GET_PLAYER_PERFECT_GAMES = "get_player_perfect_games"
GET_PLAYER_ACHIEVEMENTS_STATS_FOR_GAME = "get_player_achievements_stats_for_game"
GET_PLAYER_GAME_STATS = "get_player_game_stats"
INSERT_PLAYER = "insert_player"
LOCK_PLAYER = "lock_player"
UPDATE_PLAYER_FULL = "update_player_full"
GET_PLAYER_GAME_IDS = "get_player_game_ids"
INSERT_PLAYER_GAME = "insert_player_game"
GET_PLAYER_ACHIEVEMENT_IDS = "get_player_achievement_ids"
GET_ACHIEVEMENT_ID = "get_achievement_id"
INSERT_PLAYER_ACHIEVEMENT = "insert_player_achievement"
GET_PLAYER_GAME_STATS_FOR_GAME = "get_player_game_stats_for_game"
INSERT_PLAYER_GAME_STATS = "insert_player_game_stats"

queries = {GET_NEXT_UPDATE_DATE: r"db/queries/get_next_update_date.sql",
           MARK_UPDATE_DONE: r"db/queries/mark_update_done.sql",
           CHECK_UPDATE_ACTIVE: r"db/queries/check_update_active.sql",
           START_UPDATE: r"db/queries/start_update.sql",
           GET_PLAYER_COUNT: r"db/queries/get_player_count.sql",
           GET_PLAYER: r"db/queries/get_player.sql",
           GET_PLAYERS: r"db/queries/get_players.sql",
           GET_PLAYERS_BY_TELEGRAM_ID: r"db/queries/get_players_by_telegram_id.sql",
           SET_USER_LOCALE: r"db/queries/set_user_locale.sql",
           GET_PLAYER_INFO: r"db/queries/get_player_info.sql",
           GET_PLAYER_STATS: r"db/queries/get_player_stats.sql",
           UPSERT_ACHIEVEMENT_ENGLISH: r"db/queries/upsert_achievement_english.sql",
           INSERT_ACHIEVEMENT: r"db/queries/insert_achievement.sql",
           GET_ACHIEVEMENT_TEXT: r"db/queries/get_achievement_text.sql",
           UPSERT_ACHIEVEMENT_TRANSLATION: r"db/queries/upsert_achievement_translation.sql",
           INSERT_CONSOLE: r"db/queries/insert_console.sql",
           GET_CONSOLE_ID: r"db/queries/get_console_id.sql",
           GET_COMPANY_ID: r"db/queries/get_company_id.sql",
           INSERT_COMPANY: r"db/queries/insert_company.sql",
           GET_GENRE_ID: r"db/queries/get_genre_id.sql",
           INSERT_GENRE: r"db/queries/insert_genre.sql",
           GET_FEATURE_ID: r"db/queries/get_feature_id.sql",
           INSERT_FEATURE: r"db/queries/insert_feature.sql",
           INSERT_GAME: r"db/queries/insert_game.sql",
           GET_GAME_ID: r"db/queries/get_game_id.sql",
           GET_GAME_GENRES: r"db/queries/get_game_genres.sql",
           DELETE_GAME_GENRES: r"db/queries/delete_game_genres.sql",
           INSERT_GAME_GENRE: r"db/queries/insert_game_genre.sql",
           GET_GAME_FEATURES: r"db/queries/get_game_features.sql",
           DELETE_GAME_FEATURES: r"db/queries/delete_game_features.sql",
           INSERT_GAME_FEATURE: r"db/queries/insert_game_feature.sql",
           UPDATE_GAME: r"db/queries/update_game.sql",
           GET_ACHIEVEMENTS_FOR_GAME: r"db/queries/get_achievements_for_game.sql",
           GET_TRANSLATED_ACHIEVEMENTS_FOR_GAME: r"db/queries/get_translated_achievements_for_game.sql",
           GET_GAME_STATS: r"db/queries/get_game_stats.sql",
           UPSERT_GAME_STATS: r"db/queries/upsert_game_stats.sql",
           GET_ACCOUNT_LAST_ACHIEVEMENTS: r"db/queries/get_account_last_achievements.sql",
           GET_ACCOUNT_RAREST_ACHIEVEMENTS: r"db/queries/get_account_rarest_achievements.sql",
           GET_PLAYER_CONSOLES: r"db/queries/get_player_consoles.sql",
           GET_PLAYER_LAST_UPDATE_DATE: r"db/queries/get_player_last_update_date.sql",
           GET_USER_LOCALE: r"db/queries/get_user_locale.sql",
           INSERT_USER: r"db/queries/insert_user.sql",
           GET_LAST_GLOBAL_ACHIEVEMENTS: r"db/queries/get_last_global_achievements.sql",
           GET_LAST_GAME_PERFECTED_TIME_FOR_PLAYER: r"db/queries/get_last_game_perfected_time_for_player.sql",
           UPDATE_PLAYER_EXT_ID: r"db/queries/update_player_ext_id.sql",
           DELETE_PLAYER: r"db/queries/delete_player.sql",
           UPDATE_PLAYER_TELEGRAM_ID: r"db/queries/update_player_telegram_id.sql",
           UPDATE_PLAYER_STATUS: r"db/queries/update_player_status.sql",
           GET_PLAYER_STATUS: r"db/queries/get_player_status.sql",
           GET_USER_LAST_DELETE: r"db/queries/get_user_last_delete.sql",
           UPDATE_USER_SET_LAST_DELETE_DATE: r"db/queries/update_user_set_last_delete_date.sql",
           CHECK_PLAYERS_FOR_TELEGRAM_ID: r"db/queries/check_players_for_telegram_id.sql",
           CHECK_PLAYERS_FOR_EXT_ID: r"db/queries/check_players_for_ext_id.sql",
           CHECK_IS_PLAYER_BOUND_TO_TELEGRAM: r"db/queries/check_is_player_bound_to_telegram.sql",
           GET_PLAYER_GAMES: r"db/queries/get_player_games.sql",
           GET_PLAYER_GAMES_WITH_ACHIEVEMENTS: r"db/queries/get_player_games_with_achievements.sql",
           GET_PLAYER_PERFECT_GAMES: r"db/queries/get_player_perfect_games.sql",
           GET_PLAYER_ACHIEVEMENTS_STATS_FOR_GAME: r"db/queries/get_player_achievements_stats_for_game.sql",
           GET_PLAYER_GAME_STATS: r"db/queries/get_player_game_stats.sql",
           INSERT_PLAYER: r"db/queries/insert_player.sql",
           LOCK_PLAYER: r"db/queries/lock_player.sql",
           UPDATE_PLAYER_FULL: r"db/queries/update_player_full.sql",
           GET_PLAYER_GAME_IDS: r"db/queries/get_player_game_ids.sql",
           INSERT_PLAYER_GAME: r"db/queries/insert_player_game.sql",
           GET_PLAYER_ACHIEVEMENT_IDS: r"db/queries/get_player_achievement_ids.sql",
           GET_ACHIEVEMENT_ID: r"db/queries/get_achievement_id.sql",
           INSERT_PLAYER_ACHIEVEMENT: r"db/queries/insert_player_achievement.sql",
           GET_PLAYER_GAME_STATS_FOR_GAME: r"db/queries/get_player_game_stats_for_game.sql",
           INSERT_PLAYER_GAME_STATS: r"db/queries/insert_player_game_stats.sql",
           }
query_texts = {}


def read_query(name: str) -> str:
    return open(queries[name], "r").read()


def get_query(name: str) -> str:
    global query_texts
    if name not in query_texts:
        query_texts[name] = read_query(name)
    return query_texts[name]
