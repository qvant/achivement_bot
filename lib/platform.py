from .db_api import commit
from .game import Game
from .console import Console
from .config import Config
from .log import get_logger
from .achievement import Achievement
from typing import Union, List

from .platform_language import PlatformLanguage
from .query_holder import get_query, INSERT_PLATFORM, GET_CONSOLE_BY_ID, GET_CONSOLES_FOR_PLATFORM, \
    GET_HARDCODED_GAMES_BY_PLATFORM, GET_GAMES_BY_PLATFORM, GET_GAME_BY_PLATFORM_AND_ID, GET_ACHIEVEMENTS_BY_PLATFORM, \
    GET_ACHIEVEMENTS_BY_PLATFORM_AND_GAME_ID, UPDATE_PLATFORM_LANGUAGES_SET_LAST_UPDATE, \
    GET_PLATFORM_LANGUAGES_BY_PLATFORM_ID
from .db_api import get_connect as db_api_get_connect


class Platform:
    config = None
    conn = None

    def __init__(self, name: str, get_games, get_game, get_achievements, games: [Game], id: int,
                 validate_player, get_player_id, get_stats, incremental_update_enabled: bool,
                 incremental_update_interval: int, get_last_games, incremental_skip_chance: int,
                 get_consoles, get_player_stats=None, set_hardcoded=None, get_player_avatar=None):
        self.id = id
        self._is_persist = False
        self.name = name
        self.get_games = get_games
        self.get_last_games = get_last_games
        self.get_game = get_game
        self.get_achievements = get_achievements
        self.validate_player = validate_player
        self.get_player_id = get_player_id
        self.get_consoles = get_consoles
        self.get_player_stats = get_player_stats
        self.get_player_avatar = get_player_avatar
        self.set_hardcoded = set_hardcoded
        self.games = {}
        self.games_by_id = {}
        self.get_stats = get_stats
        self.incremental_update_enabled = incremental_update_enabled
        self.incremental_update_interval = incremental_update_interval
        self.incremental_skip_chance = incremental_skip_chance
        if games is not None:
            for i in games:
                self.games[str(i.ext_id)] = i
                self.games_by_id[i.id] = i
        self.logger = get_logger(self.name + "_" + self.config.mode, self.config.log_level)
        self.active_language = "english"
        self.languages = []
        self.games_pack_size = 100
        self.players_pack_size = 100
        self._consoles_by_id = {}
        self._consoles_by_ext_id = {}
        self._hardcoded_games = {}

    @classmethod
    def set_config(cls, config: Config):
        cls.config = config

    @classmethod
    def set_load_log(cls, load_log):
        cls.load_log = load_log

    def set_consoles(self, consoles: Union[None, List[Console]]):
        for i in consoles:
            if i.id is not None:
                self._consoles_by_id[i.id] = i
            if str(i.ext_id) in self._consoles_by_ext_id:
                self._consoles_by_ext_id[str(i.ext_id)].name = i.name
                self._consoles_by_ext_id[str(i.ext_id)].platform_id = i.platform_id
                # TODO: save changed data in db
            else:
                self._consoles_by_ext_id[str(i.ext_id)] = i

    def get_console_by_id(self, id: int) -> Union[Console, None]:
        return self._consoles_by_id.get(id)

    def get_console_by_ext(self, ext_id) -> Union[Console, None]:
        return self._consoles_by_ext_id.get(str(ext_id))

    def reset_games(self):
        self.games = {}
        self.games_by_id = {}

    def set_games(self, games):
        self.games = games
        if games is not None:
            for i in games:
                self.games_by_id[games[i].id] = games[i]
                if not isinstance(i, str):
                    self.games[str(i)] = games[i]

    def add_game(self, game: Game):
        self.games_by_id[game.id] = game
        self.games[str(game.ext_id)] = game

    def is_game_known(self, ext_id: str) -> bool:
        return ext_id in self.games

    def get_game_by_ext_id(self, ext_id: str) -> Game:
        return self.games[ext_id]

    def get_game_by__id(self, id: int, load_if_not_found: bool = False) -> Game:
        if id not in self.games_by_id and load_if_not_found:
            self.load_games(game_id=id, load_achievements=False)
        return self.games_by_id[id]

    # Temp!
    @classmethod
    def get_connect(cls):
        return db_api_get_connect()

    @classmethod
    def reset_connect(cls):
        cls.conn.close()
        cls.conn = None

    def save(self):
        conn = self.get_connect()
        cursor = conn.cursor()
        self.logger.debug("Start saving to db")
        if not self._is_persist:
            cursor.execute(get_query(INSERT_PLATFORM), (self.name, self.id))
            ret = cursor.fetchone()
            if ret is not None:
                self.id = [0]
            self._is_persist = True
            self.logger.info("Platform \"{}\" (id: {}) saved.".format(self.name, self.id))
        for i in self._consoles_by_ext_id:
            if self._consoles_by_ext_id[i].id is None:
                self.logger.info("Saving console {0}".format(self._consoles_by_ext_id[i].name))
                self._consoles_by_ext_id[i].save()
                if self._consoles_by_ext_id[i].id is not None:
                    self._consoles_by_id[self._consoles_by_ext_id[i].id] = self._consoles_by_ext_id[i]
                    self.logger.info("Set map id for console {0}".format(self._consoles_by_ext_id[i].name))
                else:
                    self.logger.error("Missed id for console {0} with ext_id {1}".
                                      format(self._consoles_by_ext_id[i].name, i))
        for i in self.games:
            if self.games[i].console_ext_id is not None and self.games[i].console is None:
                # TODO load console from database
                self.logger.debug("Set console {0} for game \"{1}\"".format(self.games[i].console_ext_id,
                                                                            self.games[i].name))
                self.games[i].set_console(self.get_console_by_ext(self.games[i].console_ext_id))
                self.logger.debug("New console {0} for game \"{1}\"".format(self.games[i].console_name,
                                                                            self.games[i].name))
            self.games[i].save(active_locale=self.active_locale)
        conn.commit()
        commit()
        self.logger.debug("Finish saving to db")

    def update_games(self, game_id: str, game_name: str, force: bool = False):
        if str(game_id) not in self.games or force:
            self.logger.info("Ask server for game \"{1}\" (ext_id: {0})".format(game_id, game_name))
            self.games[str(game_id)] = self.get_game(game_id, game_name, self.active_language)
            self.save()
            self.games_by_id[self.games[str(game_id)].id] = self.games[game_id]
            self.logger.info("Added game \"{1}\" (ext_id: {0}, id: {2})".format(game_id,
                                                                                game_name,
                                                                                self.games[str(game_id)].id))

    def load_consoles(self, console_id: Union[int, None] = None):
        conn = self.get_connect()
        cursor = conn.cursor()
        if console_id is not None:
            cursor.execute(get_query(GET_CONSOLE_BY_ID), (self.id, console_id))
        else:
            cursor.execute(get_query(GET_CONSOLES_FOR_PLATFORM), (self.id,))
        consoles = []
        for id, name, ext_id in cursor:
            consoles.append(Console(id=id, name=name, ext_id=ext_id, platform_id=self.id))
        self.set_consoles(consoles)

    def load_games(self, load_achievements=True, game_id=None, load_hardcoded: bool = False):
        conn = self.get_connect()
        cursor = conn.cursor()
        if game_id is None:
            if load_hardcoded:
                # TODO: check if still be useful
                cursor.execute(get_query(GET_HARDCODED_GAMES_BY_PLATFORM), (self.id,))
                for game_ext_id, game_name in cursor:
                    self._hardcoded_games[str(game_ext_id)] = game_name
                if self.set_hardcoded is not None:
                    self.set_hardcoded(self._hardcoded_games)
            cursor.execute(get_query(GET_GAMES_BY_PLATFORM), (self.id,))
        else:
            cursor.execute(get_query(GET_GAME_BY_PLATFORM_AND_ID), (self.id, game_id))
        games = {}
        if game_id is None and self.get_consoles is not None and not self._consoles_by_ext_id:
            self.load_consoles()
        # TODO: Shadows built-in name 'id
        for id, platform_id, name, ext_id, console_id, icon_url, release_date, developer_id, developer_name, \
                publisher_id, publisher_name, genre_ids, genres, feature_ids, features in cursor:
            self.logger.debug("Start loading game \"{0}\" (id: {1}, ext_id: {2}) for platform: {3}"
                              .format(name, id, ext_id, self.name))
            if self.get_consoles is not None and console_id is not None:
                console_id = int(console_id)
                if self.get_console_by_id(console_id) is None:
                    self.load_log.debug(
                        "Looking console with id {} into db"
                        .format(console_id))
                    self.load_consoles(console_id)
                console = self.get_console_by_id(console_id)
                games[str(ext_id)] = Game(name=name, platform_id=platform_id, id=id, ext_id=ext_id, achievements=None,
                                          console_ext_id=None, console=console,
                                          icon_url=icon_url, release_date=release_date,
                                          publisher_id=publisher_id,
                                          publisher=publisher_name,
                                          developer_id=developer_id,
                                          developer=developer_name,
                                          genres=genres,
                                          genre_ids=genre_ids,
                                          features=features,
                                          feature_ids=feature_ids,
                                          )
                self.load_log.debug("Loaded game \"{0}\" (id: {1}, ext_id: {2}, "
                                    "console {5} (id: {3})) for platform: {4}"
                                    .format(name, id, ext_id, console_id, self.name, console.name))
            else:
                games[str(ext_id)] = Game(name=name, platform_id=platform_id, id=id, ext_id=ext_id, achievements=None,
                                          console_ext_id=None, console=None,
                                          icon_url=icon_url, release_date=release_date,
                                          publisher_id=publisher_id,
                                          publisher=publisher_name,
                                          developer_id=developer_id,
                                          developer=developer_name,
                                          genres=genres,
                                          genre_ids=genre_ids,
                                          features=features,
                                          feature_ids=feature_ids,
                                          )
                self.load_log.debug("Loaded game \"{0}\" (id: {1}, ext_id: {2}) for platform {3}."
                                    .format(name, id, ext_id, self.name))
        if load_achievements:
            if game_id is None:
                cursor.execute(get_query(GET_ACHIEVEMENTS_BY_PLATFORM), (self.id,))
            else:
                cursor.execute(get_query(GET_ACHIEVEMENTS_BY_PLATFORM_AND_GAME_ID), (self.id, game_id))
            # TODO: Shadows built-in name 'id
            for id, platform_id, name, ext_id, game_ext_id, description, game_id, icon_url, locked_icon_url, \
                    is_hidden in cursor:
                self.load_log.debug("Loaded achievement {0} with id: {1}, ext_id: {2}, for game \"{3}\" "
                                    "on platform {4}".format(name, id, ext_id, game_ext_id, self.id))
                games[str(game_ext_id)].add_achievement(achievement=Achievement(id=id, game_id=game_id, name=name,
                                                                                platform_id=platform_id, ext_id=ext_id,
                                                                                description=description,
                                                                                icon_url=icon_url,
                                                                                locked_icon_url=locked_icon_url,
                                                                                is_hidden=is_hidden))
        if game_id is not None:
            self.games = {**self.games, **games}
        self.set_games(games=games)

    # TODO make fast
    @property
    def active_locale(self) -> str:
        for i in self.languages:
            if i.name == self.active_language:
                return i.locale_name
        return "en"

    def set_def_locale(self):
        for i in self.languages:
            if i.locale_name == "en":
                self.active_language = i.name

    def set_language(self, locale_name):
        is_found = False
        for i in self.languages:
            if i.locale_name == locale_name:
                self.active_language = i.name
                is_found = True
        if not is_found:
            self.set_def_locale()

    def set_next_language(self):
        for i in self.languages:
            self.active_language = i.name
            return

    def mark_language_done(self):
        conn = self.get_connect()
        cursor = conn.cursor()
        cursor.execute(get_query(UPDATE_PLATFORM_LANGUAGES_SET_LAST_UPDATE), (self.id, self.active_locale))
        conn.commit()

    def load_languages(self):
        self.languages = []
        conn = self.get_connect()
        cursor = conn.cursor()
        cursor.execute(get_query(GET_PLATFORM_LANGUAGES_BY_PLATFORM_ID), (self.id, ))
        for language_id, name, locale_name, dt_last_update in cursor:
            lang = PlatformLanguage(language_id, name, locale_name, dt_last_update)
            self.languages.append(lang)
        self.set_def_locale()
