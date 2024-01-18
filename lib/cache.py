from typing import Dict

global companies
global genres

companies: Dict[int, Dict[str, int]] = {}  # platform_id:[name: id]
genres: Dict[int, Dict[str, int]] = {}  # platform_id:[name: id]


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
