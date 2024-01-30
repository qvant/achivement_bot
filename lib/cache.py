from typing import Dict

global companies
global genres
global stats

companies: Dict[int, Dict[str, int]] = {}  # platform_id:[name: id]
genres: Dict[int, Dict[str, int]] = {}  # platform_id:[name: id]
stats: Dict[int, Dict[int, Dict[str, int]]] = {}  # platform_id:[game_id: [ext_id: id]]


def get_company_id(company_name: str, platform_id: int) -> int:
    global companies
    if platform_id not in companies:
        companies[platform_id] = {}
    if company_name not in companies[platform_id]:
        from lib.db_api import get_company_id as get_company_id_db
        companies[platform_id][company_name] = get_company_id_db(company_name, platform_id)
    return companies[platform_id][company_name]


def get_genre_id(genre_name: str, platform_id: int) -> int:
    global genres
    if platform_id not in genres:
        genres[platform_id] = {}
    if genre_name not in genres[platform_id]:
        from lib.db_api import get_genre_id as get_genre_id_db
        genres[platform_id][genre_name] = get_genre_id_db(genre_name, platform_id)
    return genres[platform_id][genre_name]


def get_stats_id(platform_id: int, game_id: int, ext_id: str) -> int:
    global stats
    if platform_id not in stats:
        stats[platform_id] = {}
    if game_id not in stats[platform_id]:
        stats[platform_id][game_id] = {}
    if ext_id not in stats[platform_id][game_id]:
        from lib.db_api import get_game_stat_id as get_game_stat_id
        stats[platform_id][game_id][ext_id] = get_game_stat_id(platform_id=platform_id, game_id=game_id, ext_id=ext_id)
    return stats[platform_id][game_id][ext_id]
