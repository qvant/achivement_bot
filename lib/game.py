from typing import Union, List, Dict
from .achievement import Achievement
from .console import Console
from .query_holder import get_query, GET_COMPANY_ID, INSERT_COMPANY, GET_GENRE_ID, INSERT_GENRE, GET_FEATURE_ID, \
    INSERT_FEATURE, INSERT_GAME, GET_GAME_ID, GET_GAME_GENRES, DELETE_GAME_GENRES, \
    INSERT_GAME_GENRE, GET_GAME_FEATURES, \
    DELETE_GAME_FEATURES, UPDATE_GAME, INSERT_GAME_FEATURE, GET_ACHIEVEMENTS_FOR_GAME, \
    GET_TRANSLATED_ACHIEVEMENTS_FOR_GAME, GET_GAME_STATS, UPSERT_GAME_STATS


class Game:
    def __init__(self, name: str, platform_id: int, id: Union[int, None], ext_id: str, achievements,
                 console_ext_id: Union[str, None], console: Union[Console, None],
                 icon_url: Union[str, None] = None, release_date: Union[str, None] = None,
                 genres: List[str] = None, publisher: str = None, developer: str = None, publisher_id: int = None,
                 developer_id: int = None, genre_ids: List[int] = None, features: List[str] = None,
                 feature_ids: List[int] = None, stats: Dict = None):
        self.name = name
        self.platform_id = platform_id
        self.id = id
        self.ext_id = ext_id
        if console is not None:
            self.console_ext_id = console.ext_id
        else:
            self.console_ext_id = console_ext_id
        self.console = console
        if achievements is not None:
            self.achievements = achievements
        else:
            self.achievements = {}
        if icon_url is not None:
            self.icon_url = icon_url
        else:
            self.icon_url = ""
        if release_date is not None:
            self.release_date = release_date
        else:
            self.release_date = ""
        if publisher is not None:
            self.publisher = publisher
        else:
            self.publisher = ""
        if developer is not None:
            self.developer = developer
        else:
            self.developer = ""
        # TODO: this two lists better keep on platform level
        self.companies = {}
        self.genre_ids = {}
        self.genres = []
        if stats is not None:
            self.stats = stats
        else:
            self.stats = {}
        self._stats_ext_to_id_map = {}
        if genres is not None:
            for i in genres:
                if i is not None:
                    self.genres.append(i)
        self.features = []
        if features is not None:
            for i in features:
                if i is not None:
                    self.features.append(i)
        self.feature_ids = {}
        if feature_ids is not None and features is not None and len(feature_ids) == len(features):
            for i in range(len(feature_ids)):
                self.feature_ids[features[i]] = feature_ids[i]
        if publisher_id is not None and publisher is not None:
            self.companies[publisher] = int(publisher_id)
        if developer_id is not None and developer is not None:
            self.companies[developer] = int(developer_id)
        if genre_ids is not None and genres is not None and len(genre_ids) == len(genres):
            for i in range(len(genre_ids)):
                self.genre_ids[genres[i]] = genre_ids[i]
        self._is_persist = self.id is not None
        self._achievements_saved = False
        self._stats_saved = len(self.stats) == 0

    @property
    def console_name(self) -> Union[str, None]:
        if self.console is not None:
            return self.console.name
        return None

    def console_id(self) -> Union[int, None]:
        if self.console is not None:
            return self.console.id
        return None

    @property
    def has_achievements(self):
        return len(self.achievements) > 0

    def get_achievement_by_ext_id(self, ext_id: str) -> Achievement:
        return self.achievements[ext_id]

    def add_achievement(self, achievement: Achievement):
        self.achievements[achievement.ext_id] = achievement
        self._achievements_saved = False

    def set_console(self, cons: Console):
        self.console = cons
        self._is_persist = False

    def get_stat_id(self, stat_ext_id: str) -> Union[None, int]:
        if stat_ext_id in self._stats_ext_to_id_map:
            return int(self._stats_ext_to_id_map[stat_ext_id])
        return None

    def _get_company_id(self, company_name: str, cursor) -> Union[None, int]:
        if company_name is None:
            return None
        if company_name not in self.companies:
            cursor.execute(get_query(GET_COMPANY_ID), (self.platform_id, company_name,))
            ret = cursor.fetchone()
            if ret is not None:
                self.companies[company_name] = ret[0]
            else:
                cursor.execute(get_query(INSERT_COMPANY), (self.platform_id, company_name,))
                ret = cursor.fetchone()
                self.companies[company_name] = ret[0]
            return int(self.companies[company_name])

    def get_publisher_id(self, company_name: str, cursor) -> Union[None, int]:
        return self._get_company_id(company_name, cursor)

    def get_developer_id(self, company_name: str, cursor) -> Union[None, int]:
        return self._get_company_id(company_name, cursor)

    def get_genre_id(self, genre, cursor):
        if genre is None:
            return None
        if genre not in self.genre_ids:
            cursor.execute(get_query(GET_GENRE_ID), (self.platform_id, genre,))
            ret = cursor.fetchone()
            if ret is not None:
                self.genre_ids[genre] = ret[0]
            else:
                cursor.execute(get_query(INSERT_GENRE), (self.platform_id, genre,))
                ret = cursor.fetchone()
                self.genre_ids[genre] = ret[0]
        return int(self.genre_ids[genre])

    def get_feature_id(self, feature, cursor):
        if feature is None:
            return None
        if feature not in self.feature_ids:
            cursor.execute(get_query(GET_FEATURE_ID), (self.platform_id, feature,))
            ret = cursor.fetchone()
            if ret is not None:
                self.feature_ids[feature] = ret[0]
            else:
                cursor.execute(get_query(INSERT_FEATURE), (self.platform_id, feature,))
                ret = cursor.fetchone()
                self.feature_ids[feature] = ret[0]
        return int(self.feature_ids[feature])

    def save(self, cursor, active_locale: str):
        developer_id = self.get_developer_id(self.developer, cursor)
        publisher_id = self.get_publisher_id(self.publisher, cursor)
        genres = []
        features = []
        # TODO: remove call on init
        if self.genres is not None:
            for i in self.genres:
                genre_id = self.get_genre_id(i, cursor)
                if genre_id not in genres:
                    genres.append(genre_id)
        if self.features is not None:
            for i in self.features:
                feature_id = self.get_feature_id(i, cursor)
                if feature_id not in features:
                    features.append(feature_id)
        if self.id is None:
            cursor.execute(get_query(INSERT_GAME),
                           (self.name, self.ext_id, self.platform_id, self.has_achievements, self.console_id(),
                            self.icon_url, self.release_date, developer_id, publisher_id,
                            self.name, self.has_achievements, self.console_id(), self.icon_url, self.release_date,
                            developer_id, publisher_id)
                           )
            ret = cursor.fetchone()
            if ret is not None:
                self.id = ret[0]
            else:
                cursor.execute(get_query(GET_GAME_ID), (self.platform_id, str(self.ext_id)))
                ret = cursor.fetchone()
                if ret is not None:
                    self.id = ret[0]
            cursor.execute(get_query(GET_GAME_GENRES), (self.platform_id, self.id))
            saved_genres = []
            for i in cursor:
                saved_genres.append(i)
            if set(saved_genres) != set(genres) and len(genres) > 0:
                cursor.execute(get_query(DELETE_GAME_GENRES), (self.platform_id, self.id))
                for cur_g in genres:
                    # there not that many records, so no profit from bulk
                    cursor.execute(get_query(INSERT_GAME_GENRE), (self.platform_id, self.id, cur_g))
            cursor.execute(get_query(GET_GAME_FEATURES), (self.platform_id, self.id))
            saved_features = []
            for i in cursor:
                saved_features.append(i)
            if set(saved_features) != set(features) and len(features) > 0:
                cursor.execute(get_query(DELETE_GAME_FEATURES), (self.platform_id, self.id))
                for cur_f in features:
                    # there not that many records, so no profit from bulk
                    cursor.execute(get_query(INSERT_GAME_FEATURE), (self.platform_id, self.id, cur_f))
        else:
            if not self._is_persist:
                cursor.execute(get_query(UPDATE_GAME), (self.name, self.has_achievements, self.console_id(),
                                                        self.icon_url, self.release_date, developer_id, publisher_id,
                                                        self.id, self.platform_id, self.name, self.has_achievements,
                                                        self.console_id(), self.icon_url, self.release_date,
                                                        developer_id, publisher_id)
                               )
                cursor.execute(get_query(GET_GAME_GENRES), (self.platform_id, self.id))
                saved_genres = []
                for i in cursor:
                    saved_genres.append(i)
                if set(saved_genres) != set(genres) and len(genres) > 0:
                    cursor.execute(get_query(DELETE_GAME_GENRES), (self.platform_id, self.id))
                    for cur_g in genres:
                        # there not that many records, so no profit from bulk
                        cursor.execute(get_query(INSERT_GAME_GENRE), (self.platform_id, self.id, cur_g))
                # TODO: remove duplicate code
                cursor.execute(get_query(GET_GAME_FEATURES), (self.platform_id, self.id))
                saved_features = []
                for i in cursor:
                    saved_features.append(i)
                if set(saved_features) != set(features) and len(features) > 0:
                    cursor.execute(get_query(DELETE_GAME_FEATURES), (self.platform_id, self.id))
                    for cur_f in features:
                        # there not that many records, so no profit from bulk
                        cursor.execute(get_query(INSERT_GAME_FEATURE), (self.platform_id, self.id, cur_f))
        if len(self.achievements) > 0 and not self._achievements_saved:
            if active_locale == 'en':
                cursor.execute(get_query(GET_ACHIEVEMENTS_FOR_GAME), (self.platform_id, self.id))
            else:
                cursor.execute(get_query(GET_TRANSLATED_ACHIEVEMENTS_FOR_GAME),
                               (active_locale, self.platform_id, self.id))
            need_save = False
            to_save = []
            rows_found = False
            for id, ext_id, name, description, icon_url, locked_icon_url, is_hidden in cursor:
                rows_found = True
                if ext_id in self.achievements:
                    self.achievements[ext_id].id = id
                    if name != self.achievements[ext_id].name \
                            or description != self.achievements[ext_id].description\
                            or icon_url != self.achievements[ext_id].icon_url \
                            or locked_icon_url != self.achievements[ext_id].locked_icon_url\
                            or is_hidden != self.achievements[ext_id].is_hidden:
                        need_save = True
                        to_save.append(ext_id)
                else:
                    need_save = True
                    to_save.append(ext_id)
            if not rows_found:
                need_save = True
            if not need_save:
                for i in self.achievements:
                    if self.achievements[i].id is None:
                        need_save = True
                        break
            if need_save:
                for i in self.achievements:
                    if self.achievements[i].id is None or i in to_save:
                        self.achievements[i].set_game_id(self.id)
                        self.achievements[i].id = None
                        self.achievements[i].save(cursor, active_locale)
        if not self._stats_saved:
            stats_to_save = {}
            stats_exists = {}
            cursor.execute(get_query(GET_GAME_STATS), (self.platform_id, self.id))
            for stat_id, stat_ext_id, stat_name in cursor:
                stats_exists[stat_ext_id] = stat_name
                self._stats_ext_to_id_map[stat_ext_id] = stat_id
            for i in self.stats:
                if i not in stats_exists:
                    stats_to_save[i] = self.stats[i]
                elif stats_exists[i] != self.stats[i]:
                    stats_to_save[i] = self.stats[i]
            for i in stats_to_save:
                cursor.execute(get_query(UPSERT_GAME_STATS), (self.platform_id, self.id, i, stats_to_save[i]))
                ret = cursor.fetchone()
                if ret is not None:
                    self._stats_ext_to_id_map[i] = ret[0]
        self._is_persist = True
        self._achievements_saved = True
        self._stats_saved = True

    def __str__(self):
        return "{0}".format(self.id)
