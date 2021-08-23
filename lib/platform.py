from .game import Game
from .console import Console
from .config import Config
from .log import get_logger
from .achievement import Achievement
import psycopg2
from typing import Union, List


class Platform:
    config = None

    def __init__(self, name: str, get_games, get_game, get_achivements, games: [Game], id: int,
                 validate_player, get_player_id, get_stats, incremental_update_enabled: bool,
                 incremental_update_interval: int, get_last_games, incremental_skip_chance: int,
                 get_consoles):
        self.id = id
        self._is_persist = False
        self.name = name
        self.get_games = get_games
        self.get_last_games = get_last_games
        self.get_game = get_game
        self.get_achivements = get_achivements
        self.validate_player = validate_player
        self.get_player_id = get_player_id
        self.get_consoles = get_consoles
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
        self._consoles_by_id = {}
        self._consoles_by_ext_id = {}

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
            self._consoles_by_ext_id[str(i.ext_id)] = i

    def get_console_by_id(self, id) -> Union[Console, None]:
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

    def get_game_by_ext_id(self, ext_id: str) -> Game:
        return self.games[ext_id]

    def get_game_by__id(self, id: int, load_if_not_found: bool = False) -> Game:
        if id not in self.games_by_id and load_if_not_found:
            self.load_games(game_id=id, load_achievements=False)
        return self.games_by_id[id]

    # Temp!
    @classmethod
    def get_connect(cls):
        conn = psycopg2.connect(dbname=cls.config.db_name, user=cls.config.db_user,
                                password=cls.config.db_password, host=cls.config.db_host, port=cls.config.db_port)
        return conn

    def save(self):
        conn = self.get_connect()
        cursor = conn.cursor()
        self.logger.info("Start saving to db")
        if not self._is_persist:
            cursor.execute(
                """insert into achievements_hunt.platforms as l (name, id )
                        values(%s, %s)
                        on conflict (id) do nothing
                        returning id
                """, (self.name, self.id)
            )
            ret = cursor.fetchone()
            if ret is not None:
                self.id = [0]
                self._is_persist = True
        for i in self._consoles_by_ext_id:
            if self._consoles_by_ext_id[i].id is None:
                self.logger.info("Saving console {0}".format(self._consoles_by_ext_id[i].name))
                self._consoles_by_ext_id[i].save(conn)
                if self._consoles_by_ext_id[i].id is not None:
                    self._consoles_by_id[self._consoles_by_ext_id[i].id] = i
                    self.logger.error("Set map id for console {0}".format(self._consoles_by_ext_id[i].name))
                else:
                    self.logger.error("Missed id for console {0}".format(self._consoles_by_ext_id[i].name))
        for i in self.games:
            if self.games[i].console_ext_id is not None and self.games[i].console is None:
                self.logger.info("Set console {0} for game {1}".format(self.games[i].console_ext_id,
                                                                       self.games[i].name))
                self.games[i].set_console(self.get_console_by_ext(self.games[i].console_ext_id))
                self.logger.info("New console {0} for game {1}".format(self.games[i].console_name,
                                                                       self.games[i].name))
            self.games[i].save(cursor, self.active_locale)
        conn.commit()
        self.logger.info("Finish saving to db")

    def update_games(self, game_id: str, game_name: str):
        if str(game_id) not in self.games:
            self.logger.info("Ask server for game {0} {1}".format(game_id, game_name))
            self.games[str(game_id)] = self.get_game(game_id, game_name, self.active_language)
            self.save()
            self.games_by_id[self.games[str(game_id)].id] = self.games[game_id]
            self.logger.info("Added game {0} {1} with id {2}".format(game_id, game_name, self.games[str(game_id)].id))

    def load_consoles(self, console_id: Union[int, None] = None):
        conn = self.get_connect()
        cursor = conn.cursor()
        if console_id is None:
            cursor.execute("select id, name, ext_id from achievements_hunt.consoles c "
                           "where c.platform_id = %s and id = %s", (self.id, console_id))
        else:
            cursor.execute("select id, name, ext_id from achievements_hunt.consoles c "
                           "where c.platform_id = %s", (self.id,))
        consoles = []
        for id, name, ext_id in cursor:
            consoles.append(Console(id=id, name=name, ext_id=ext_id, platform_id=self.id))
        self.set_consoles(consoles)

    def load_games(self, load_achievements=True, game_id=None):
        conn = self.get_connect()
        cursor = conn.cursor()
        if game_id is None:
            cursor.execute("""
                    select id, platform_id, name, ext_id, console_id from achievements_hunt.games
                    where platform_id = %s order by id
                    """, (self.id,))
        else:
            cursor.execute("""
                                select id, platform_id, name, ext_id, console_id from achievements_hunt.games
                                where platform_id = %s and id = %s
                                order by id
                                """, (self.id, game_id))
        games = {}
        for id, platform_id, name, ext_id, console_id in cursor:
            self.load_log.info("Loaded game {0} with id {1}, ext_id {2}, for platform {3} and console {4}".
                               format(name, id, ext_id, self.id, console_id))
            if self.get_consoles is not None:
                if self.get_console_by_id(console_id) is None:
                    self.load_consoles(console_id)
                games[str(ext_id)] = Game(name=name, platform_id=platform_id, id=id, ext_id=ext_id, achievements=None,
                                          console_ext_id=None, console=self.get_console_by_id(console_id))
            else:
                games[str(ext_id)] = Game(name=name, platform_id=platform_id, id=id, ext_id=ext_id, achievements=None,
                                          console_ext_id=None, console=None)
        if load_achievements:
            if game_id is None:
                cursor.execute("""
                                    select a.id, a.platform_id, a.name, a.ext_id, g.ext_id, a.description, a.game_id
                                     from achievements_hunt.achievements a
                                     join  achievements_hunt.games g on a.game_id = g.id
                                      where a.platform_id = %s order by id
                                    """, (self.id,))
            else:
                cursor.execute("""
                                    select a.id, a.platform_id, a.name, a.ext_id, g.ext_id, a.description, a.game_id
                                     from achievements_hunt.achievements a
                                     join  achievements_hunt.games g on a.game_id = g.id  where a.platform_id = %s
                                      and a.game_id = %s order by id
                                                    """, (self.id, game_id))
            for id, platform_id, name, ext_id, game_ext_id, description, game_id in cursor:
                self.load_log.debug("Loaded achievement {0} with id {1}, ext_id {2}, for game {3} "
                                    "on platform {4}".format(name, id, ext_id, game_ext_id, self.id))
                games[str(game_ext_id)].add_achievement(achievement=Achievement(id=id, game_id=game_id, name=name,
                                                                                platform_id=platform_id, ext_id=ext_id,
                                                                                description=description))
        if game_id is not None:
            self.games = {**self.games, **games}
        self.set_games(games=games)

        conn.close()

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
        cursor.execute("""
                    update achievements_hunt.platform_languages set dt_last_update = current_timestamp
                    where platform_id = %s and locale_name = %s """, (self.id, self.active_locale))
        conn.commit()

    def load_languages(self):
        self.languages = []
        conn = self.get_connect()
        cursor = conn.cursor()
        cursor.execute("""
            select id, name, locale_name, dt_last_update from achievements_hunt.platform_languages
            where platform_id = %s order by dt_last_update nulls first, locale_name""", (self.id, ))
        for id, name, locale_name, dt_last_update in cursor:
            lang = PlatformLanguage(id, self, name, locale_name, dt_last_update)
            self.languages.append(lang)
        self.set_def_locale()


class PlatformLanguage:
    def __init__(self, id, platform: Platform, name, locale_name, dt_last_update):
        self.id = id
        self.platfrom = platform
        self.name = name
        self.locale_name = locale_name
        self.dt_last_update = dt_last_update
