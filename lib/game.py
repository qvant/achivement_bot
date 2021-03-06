from typing import Union, List, Dict
from .achievement import Achievement
from .console import Console


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
        # this two lists better keep on platform level
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
            cursor.execute("""select c.id from achievements_hunt.companies c
            where c.platform_id = %s and c.name = %s""", (self.platform_id, company_name,))
            ret = cursor.fetchone()
            if ret is not None:
                self.companies[company_name] = ret[0]
            else:
                cursor.execute("""
                insert into achievements_hunt.companies (platform_id, name) values (%s, %s)
                returning id
                """, (self.platform_id, company_name,))
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
            cursor.execute("""select c.id from achievements_hunt.genres c
            where c.platform_id = %s and c.name = %s""", (self.platform_id, genre,))
            ret = cursor.fetchone()
            if ret is not None:
                self.genre_ids[genre] = ret[0]
            else:
                cursor.execute("""
                insert into achievements_hunt.genres (platform_id, name) values (%s, %s)
                returning id
                """, (self.platform_id, genre,))
                ret = cursor.fetchone()
                self.genre_ids[genre] = ret[0]
        return int(self.genre_ids[genre])

    def get_feature_id(self, feature, cursor):
        if feature is None:
            return None
        if feature not in self.feature_ids:
            cursor.execute("""select c.id from achievements_hunt.features c
            where c.platform_id = %s and c.name = %s""", (self.platform_id, feature,))
            ret = cursor.fetchone()
            if ret is not None:
                self.feature_ids[feature] = ret[0]
            else:
                cursor.execute("""
                insert into achievements_hunt.features (platform_id, name) values (%s, %s)
                returning id
                """, (self.platform_id, feature,))
                ret = cursor.fetchone()
                self.feature_ids[feature] = ret[0]
        return int(self.feature_ids[feature])

    def save(self, cursor, active_locale: str):
        developer_id = self.get_developer_id(self.developer, cursor)
        publisher_id = self.get_publisher_id(self.publisher, cursor)
        genres = []
        features = []
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
            cursor.execute(
                """insert into achievements_hunt.games as l (name, ext_id, platform_id, has_achievements,
                        console_id, icon_url, release_date, developer_id, publisher_id)
                        values(%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict ON CONSTRAINT u_games_ext_key do update
                        set dt_update=current_timestamp, name=%s, has_achievements=%s, console_id=%s,
                        icon_url=%s, release_date=%s, developer_id=%s, publisher_id=%s
                        where l.name != EXCLUDED.name or l.has_achievements != EXCLUDED.has_achievements
                        or coalesce(l.console_id, -1) != coalesce(EXCLUDED.console_id, -1)
                        or coalesce(l.release_date, '') != coalesce(EXCLUDED.release_date, l.release_date, '')
                        or coalesce(l.icon_url, '') != coalesce(EXCLUDED.icon_url, l.icon_url, '')
                        or coalesce(l.developer_id, -1) != coalesce(EXCLUDED.developer_id, l.developer_id, -1)
                        or coalesce(l.publisher_id, -1) != coalesce(EXCLUDED.publisher_id, l.publisher_id, -1)
                        returning id
                """, (self.name, self.ext_id, self.platform_id, self.has_achievements, self.console_id(),
                      self.icon_url, self.release_date, developer_id, publisher_id,
                      self.name, self.has_achievements, self.console_id(), self.icon_url, self.release_date,
                      developer_id, publisher_id)
            )
            ret = cursor.fetchone()
            if ret is not None:
                self.id = ret[0]
            else:
                cursor.execute("""
                    select id from achievements_hunt.games where platform_id = %s and ext_id = %s
                """, (self.platform_id, str(self.ext_id)))
                ret = cursor.fetchone()
                if ret is not None:
                    self.id = ret[0]
            cursor.execute("""
                                select genre_id from achievements_hunt.map_games_to_genres g
                                    where g.platform_id = %s
                                          and g.game_id = %s
                            """, (self.platform_id, self.id))
            saved_genres = []
            for i in cursor:
                saved_genres.append(i)
            if set(saved_genres) != set(genres) and len(genres) > 0:
                cursor.execute("""delete from achievements_hunt.map_games_to_genres g
                                      where g.platform_id = %s
                                            and g.game_id = %s
                                            """, (self.platform_id, self.id))
                for cur_g in genres:
                    # there not that many records, so no profit from bulk
                    cursor.execute("""
                        insert into achievements_hunt.map_games_to_genres(platform_id, game_id, genre_id)
                        values(%s, %s, %s)
                    """, (self.platform_id, self.id, cur_g))
            cursor.execute("""
                                select feature_id from achievements_hunt.map_games_to_features f
                                    where f.platform_id = %s
                                          and f.game_id = %s
                            """, (self.platform_id, self.id))
            saved_features = []
            for i in cursor:
                saved_features.append(i)
            if set(saved_features) != set(features) and len(features) > 0:
                cursor.execute("""delete from achievements_hunt.map_games_to_features f
                                                  where f.platform_id = %s
                                                        and f.game_id = %s
                                                        """, (self.platform_id, self.id))
                for cur_f in features:
                    # there not that many records, so no profit from bulk
                    cursor.execute("""
                                    insert into achievements_hunt.map_games_to_features(platform_id, game_id,
                                    feature_id)
                                    values(%s, %s, %s)
                                """, (self.platform_id, self.id, cur_f))
        else:
            if not self._is_persist:
                cursor.execute(
                    """update achievements_hunt.games l set dt_update=current_timestamp, name=%s,
                            has_achievements=%s, console_id=%s,
                            icon_url=%s, release_date=%s,
                            developer_id=%s, publisher_id=%s
                            where id = %s and platform_id = %s
                            and (%s != name or %s != has_achievements
                                or coalesce(%s, -1) != coalesce(console_id, -1)
                                or coalesce(%s, icon_url, '') != coalesce(icon_url, '')
                                or coalesce(%s, release_date, '') != coalesce(release_date, '')
                                or coalesce(%s, developer_id, -1) != coalesce(developer_id, -1)
                                or coalesce(%s, publisher_id, -1) != coalesce(publisher_id, -1)
                                )
                    """, (self.name, self.has_achievements, self.console_id(),
                          self.icon_url, self.release_date, developer_id, publisher_id,
                          self.id, self.platform_id, self.name, self.has_achievements, self.console_id(),
                          self.icon_url, self.release_date, developer_id, publisher_id)
                )
                cursor.execute("""
                    select genre_id from achievements_hunt.map_games_to_genres g
                        where g.platform_id = %s
                              and g.game_id = %s
                """, (self.platform_id, self.id))
                saved_genres = []
                for i in cursor:
                    saved_genres.append(i)
                if set(saved_genres) != set(genres) and len(genres) > 0:
                    cursor.execute("""
                                        delete from achievements_hunt.map_games_to_genres g
                                            where g.platform_id = %s
                                                  and g.game_id = %s
                                    """, (self.platform_id, self.id))
                    for cur_g in genres:
                        # there not that many records, so no profit from bulk
                        cursor.execute("""
                            insert into achievements_hunt.map_games_to_genres(platform_id, game_id, genre_id)
                            values(%s, %s, %s)
                        """, (self.platform_id, self.id, cur_g))
                # TODO: remove duplicate code
                cursor.execute("""
                                    select f.feature_id from achievements_hunt.map_games_to_features f
                                        where f.platform_id = %s
                                              and f.game_id = %s
                                """, (self.platform_id, self.id))
                saved_features = []
                for i in cursor:
                    saved_features.append(i)
                if set(saved_features) != set(features) and len(features) > 0:
                    cursor.execute("""
                                                        delete from achievements_hunt.map_games_to_features g
                                                            where g.platform_id = %s
                                                                  and g.game_id = %s
                                                    """, (self.platform_id, self.id))
                    for cur_f in features:
                        # there not that many records, so no profit from bulk
                        cursor.execute("""
                                            insert into achievements_hunt.map_games_to_features(platform_id, game_id,
                                            feature_id)
                                            values(%s, %s, %s)
                                        """, (self.platform_id, self.id, cur_f))
        if len(self.achievements) > 0 and not self._achievements_saved:
            if active_locale == 'en':
                cursor.execute(
                    """select id, ext_id, name, description, icon_url, locked_icon_url, is_hidden
                            from achievements_hunt.achievements
                            where platform_id = %s and game_id = %s
                    """, (self.platform_id, self.id)
                )
            else:
                cursor.execute(
                    """select a.id, a.ext_id, coalesce(l.name, a.name), coalesce(a.description, l.description),
                              icon_url, locked_icon_url, is_hidden
                            from achievements_hunt.achievements a
                            left join achievements_hunt.achievement_translations l
                            on l.achievement_id  = a.id
                                and l.game_id = a.game_id
                                and l.platform_id = a.platform_id
                                and l.locale = %s
                            where a.platform_id = %s and a.game_id = %s
                    """, (active_locale, self.platform_id, self.id)
                )
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
            if need_save:
                for i in self.achievements:
                    if self.achievements[i].id is None or i in to_save:
                        self.achievements[i].set_game_id(self.id)
                        self.achievements[i].id = None
                        self.achievements[i].save(cursor, active_locale)
        if not self._stats_saved:
            stats_to_save = {}
            stats_exists = {}
            cursor.execute("""
                select s.id, s.ext_id, s.name from achievements_hunt.game_stats s
                where s.platform_id = %s and s.game_id = %s
            """, (self.platform_id, self.id))
            for stat_id, stat_ext_id, stat_name in cursor:
                stats_exists[stat_ext_id] = stat_name
                self._stats_ext_to_id_map[stat_ext_id] = stat_id
            for i in self.stats:
                if i not in stats_exists:
                    stats_to_save[i] = self.stats[i]
                elif stats_exists[i] != self.stats[i]:
                    stats_to_save[i] = self.stats[i]
            for i in stats_to_save:
                cursor.execute("""
                    insert into achievements_hunt.game_stats as s(platform_id, game_id, ext_id, name)
                    values (%s, %s, %s, %s )
                    on conflict ON CONSTRAINT u_game_stats_ext_key do update
                        set dt_update=current_timestamp, name=EXCLUDED.name
                    returning id
                """, (self.platform_id, self.id, i, stats_to_save[i]))
                ret = cursor.fetchone()
                if ret is not None:
                    self._stats_ext_to_id_map[i] = ret[0]
        self._is_persist = True
        self._achievements_saved = True
        self._stats_saved = True

    def __str__(self):
        return "{0}".format(self.id)
