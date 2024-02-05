from typing import Union, List, Dict

from .achievement import Achievement
from .console import Console


class Game:
    def __init__(self, name: str, platform_id: int, id: Union[int, None], ext_id: str, achievements,
                 console_ext_id: Union[str, None], console: Union[Console, None],
                 icon_url: Union[str, None] = None, release_date: Union[str, None] = None,
                 genres: List[str] = None, publisher: str = None, developer: str = None, publisher_id: int = None,
                 developer_id: int = None, genre_ids: List[int] = None, features: List[str] = None,
                 feature_ids: List[int] = None, stats: Dict[str, str] = None):
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
        # TODO: this list better keep on platform level
        self.genres = []
        if stats is not None:
            self.stats = stats
        else:
            self.stats = {}
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

    def _get_company_id(self, company_name: str) -> Union[None, int]:
        if company_name is None:
            return None
        from lib.cache import get_company_id as get_company_id_cached
        return get_company_id_cached(company_name, self.platform_id)

    def get_publisher_id(self, company_name: str) -> Union[None, int]:
        return self._get_company_id(company_name)

    def get_developer_id(self, company_name: str) -> Union[None, int]:
        return self._get_company_id(company_name)

    def get_genre_id(self, genre):
        if genre is None:
            return None
        from lib.cache import get_genre_id as get_genre_id_cached
        return get_genre_id_cached(genre, self.platform_id)

    def get_feature_id(self, feature):
        if feature is None:
            return None
        from lib.cache import get_feature_id as get_feature_id_cached
        return get_feature_id_cached(feature_name=feature, platform_id=self.platform_id)

    def save(self, active_locale: str):
        developer_id = self.get_developer_id(self.developer)
        publisher_id = self.get_publisher_id(self.publisher)
        genres = []
        features = []
        # TODO: remove call on init
        if self.genres is not None:
            for i in self.genres:
                genre_id = self.get_genre_id(i)
                if genre_id not in genres:
                    genres.append(genre_id)
        if self.features is not None:
            for i in self.features:
                feature_id = self.get_feature_id(i)
                if feature_id not in features:
                    features.append(feature_id)
        if self.id is None or not self._is_persist:
            from lib.db_api import save_game, save_game_genres, save_game_features
            save_game(self, developer_id, publisher_id)
            save_game_genres(self.platform_id, self.id, genres)
            save_game_features(self.platform_id, self.id, features)
        if len(self.achievements) > 0 and not self._achievements_saved:
            from lib.db_api import save_achievements
            save_achievements(platform_id=self.platform_id, game_id=self.id, achievements=self.achievements,
                              active_locale=active_locale)
        if not self._stats_saved:
            from lib.db_api import save_game_stats
            save_game_stats(platform_id=self.platform_id, game_id=self.id, stats=self.stats)
        self._is_persist = True
        self._achievements_saved = True
        self._stats_saved = True

    def __str__(self):
        return "{0}".format(self.id)
