import datetime
import random
from psycopg2 import Error as PgError
from typing import Union, Dict
from .platform import Platform
from datetime import timezone

from .query_holder import UPDATE_PLAYER_EXT_ID, get_query, DELETE_PLAYER, UPDATE_PLAYER_TELEGRAM_ID, \
    UPDATE_PLAYER_STATUS, GET_PLAYER_STATUS, GET_USER_LAST_DELETE, UPDATE_USER_SET_LAST_DELETE_DATE, \
    CHECK_PLAYERS_FOR_TELEGRAM_ID, CHECK_PLAYERS_FOR_EXT_ID, CHECK_IS_PLAYER_BOUND_TO_TELEGRAM, GET_PLAYER_GAMES, \
    GET_PLAYER_GAMES_WITH_ACHIEVEMENTS, GET_PLAYER_PERFECT_GAMES, GET_PLAYER_ACHIEVEMENTS_STATS_FOR_GAME, \
    GET_PLAYER_GAME_STATS, INSERT_USER, INSERT_PLAYER, LOCK_PLAYER, UPDATE_PLAYER_FULL, GET_PLAYER_GAME_IDS, \
    INSERT_PLAYER_GAME, GET_PLAYER_ACHIEVEMENT_IDS, GET_ACHIEVEMENT_ID, INSERT_PLAYER_ACHIEVEMENT, \
    GET_PLAYER_GAME_STATS_FOR_GAME, INSERT_PLAYER_GAME_STATS

STATUS_NEW = 1
STATUS_VALID = 2

GAMES_ALL = 1
GAMES_WITH_ACHIEVEMENTS = 2
GAMES_PERFECT = 3


class Player:
    def __init__(self, name: str, ext_id: str, platform: Platform, id: Union[int, None], telegram_id: Union[int, None],
                 dt_updated=None, dt_updated_full=None, dt_updated_inc=None, avatar_url: Union[str, None] = None):
        self.id = id
        self.telegram_id = telegram_id
        self.ext_id = ext_id
        self.name = name
        self.dt_updated = dt_updated
        self.dt_updated_full = dt_updated_full
        self.dt_updated_inc = dt_updated_inc
        self.platform = platform
        self.games = []
        self.achievements = {}
        self.achievement_dates = {}
        self.achievement_stats = {}
        self.stats = {}
        self.has_perfect_games = True
        self.is_public = True
        self.avatar_url = avatar_url

    def set_ext_id(self, ext_id):
        self.ext_id = ext_id
        self.dt_updated = datetime.datetime.now()
        conn = self.platform.get_connect()
        cur = conn.cursor()
        try:
            cur.execute(get_query(UPDATE_PLAYER_EXT_ID), (self.ext_id, self.dt_updated, self.id,))
        except PgError as err:
            if err.pgcode == "23505":
                conn.rollback()
                cur.execute(get_query(DELETE_PLAYER), (self.id, self.platform.id))
                cur.execute(get_query(UPDATE_PLAYER_TELEGRAM_ID), (self.telegram_id, self.ext_id, self.platform.id,))
                buf = cur.fetchone()
                if buf is not None:
                    self.id = buf[0]
                else:
                    conn.rollback()
                    self.platform.logger.warn("Player with ext_id {0} on platform {1} already exists and can't be "
                                              "bound to the telegram account {2}".
                                              format(self.id, self.platform.id, self.telegram_id))
                    raise
                self.platform.logger.info("Bound existed player {0} to telegram account {1}".
                                          format(self.id, self.telegram_id))
            else:
                self.platform.logger.warn("Error: {} {} when set ext_id {} on platform {} for player {} and telegram "
                                          "account {}".
                                          format(err, err.pgcode, self.ext_id, self.platform.id, self.id,
                                                 self.telegram_id))
                raise
        conn.commit()

    def set_name(self, name):
        self.name = name
        self.dt_updated = datetime.datetime.now()

    def set_avatar(self, avatar):
        self.avatar_url = avatar
        self.dt_updated = datetime.datetime.now()

    def mark_valid(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        cur.execute(get_query(UPDATE_PLAYER_STATUS),
                    (STATUS_VALID, self.name, self.id))
        conn.commit()

    def delete(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        if self.id is not None:
            cur.execute(get_query(GET_PLAYER_STATUS), (self.id,))
            status, = cur.fetchone()
            cur.execute(get_query(GET_USER_LAST_DELETE), (self.telegram_id,))
            ret = cur.fetchone()
            if ret is not None and ret[0] is not None and \
                    ret[0].replace(tzinfo=timezone.utc) + datetime.timedelta(days=3) > datetime.datetime.now()\
                    .replace(tzinfo=timezone.utc) and status == STATUS_VALID:
                # TODO: throw error
                self.platform.logger.info("Skip deleting player {0}, dt_last_delete + delta = {1}".
                                          format(self.ext_id, ret))
                pass
            else:
                self.platform.logger.info("Deleting player {0}".format(self.ext_id))
                cur.execute(get_query(DELETE_PLAYER), (self.id, self.platform.id))
                cur.execute(get_query(UPDATE_USER_SET_LAST_DELETE_DATE), (self.telegram_id,))
                conn.commit()
                self.platform.logger.info("Deleted player {0}".format(self.ext_id))
        self.platform.reset_connect()

    def is_unique(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        cur.execute(get_query(CHECK_PLAYERS_FOR_TELEGRAM_ID),
                    (self.platform.id, self.telegram_id))
        ret = cur.fetchone()
        if ret[0] > 0:
            return False, "Only one account per telegram user for platform"
        cur.execute(get_query(CHECK_PLAYERS_FOR_EXT_ID),
                    (self.platform.id, self.ext_id))
        ret = cur.fetchone()
        if ret[0] > 0:
            cur.execute(get_query(CHECK_IS_PLAYER_BOUND_TO_TELEGRAM),
                        (self.platform.id, self.ext_id))
            ret = cur.fetchone()
            if ret[0] is not None:
                return False, "Account already bound"
            else:
                self.id = ret[1]
                cur.execute(get_query(UPDATE_PLAYER_TELEGRAM_ID),
                            (self.telegram_id, self.ext_id, self.platform.id))
                conn.commit()
        return True, "Ok"

    def get_owned_games(self, mode=GAMES_ALL, force=False, console_id: Union[int, None] = None):
        if len(self.games) == 0 or force:
            if force:
                self.games = []
            self.platform.logger.info("Load games for player {} (ext_id: {}, id: {}), mode {} force mode {}".
                                      format(self.name, self.ext_id, self.id, mode, force))
            conn = self.platform.get_connect()
            cur = conn.cursor()
            if mode == GAMES_ALL:
                # TODO: make one query for all branches
                cur.execute(get_query(GET_PLAYER_GAMES),
                            (self.platform.id, self.id, console_id, console_id))
            elif mode == GAMES_WITH_ACHIEVEMENTS:
                cur.execute(get_query(GET_PLAYER_GAMES_WITH_ACHIEVEMENTS),
                            (self.platform.id, self.id, console_id, console_id))
            elif mode == GAMES_PERFECT:
                cur.execute(get_query(GET_PLAYER_PERFECT_GAMES),
                            (self.platform.id, self.id, console_id, console_id))
            else:
                self.platform.logger.critical("incorrect get games mode {0}".format(mode))
                cur.execute(get_query(GET_PLAYER_GAMES),
                            (self.platform.id, self.id, console_id, console_id))
            ret = cur.fetchall()
            self.has_perfect_games = False
            for j in ret:
                self.games.append(self.platform.get_game_by__id(j[0], load_if_not_found=True))
                if j[1]:
                    self.has_perfect_games = True

    @property
    def cur_achievement_stats(self) -> Dict:
        for i in self.achievement_stats:
            return self.achievement_stats[i]
        return {}

    @property
    def cur_achievements_game(self):
        if self.achievement_stats:
            return self.platform.get_game_by__id(int(next(iter(self.achievement_stats))))
        else:
            return None

    def get_achievement_stats(self, game_id, locale: str):
        if game_id not in self.achievement_stats:
            self.achievement_stats = {game_id: []}
            conn = self.platform.get_connect()
            cur = conn.cursor()
            cur.execute(get_query(GET_PLAYER_ACHIEVEMENTS_STATS_FOR_GAME),
                        (self.id, locale, self.platform.id, game_id))
            ret = cur.fetchall()
            for j in ret:
                self.achievement_stats[game_id].append({"name": j[0], "owned": j[1] is not None,
                                                        "percent": j[2], "id": j[3],
                                                        "description": j[4],
                                                        "dt_unlock": j[5],
                                                        "image_url": j[6],
                                                        "rarity": j[7],
                                                        "is_hidden": j[8],
                                                        })

    def get_game_stats(self, game_id):
        stats = []
        conn = self.platform.get_connect()
        cur = conn.cursor()
        cur.execute(get_query(GET_PLAYER_GAME_STATS),
                    (self.id, self.platform.id, game_id))
        ret = cur.fetchall()
        for j in ret:
            stats.append({"name": j[0], "value": j[1]})
        return stats

    def save(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        if self.id is None:
            if self.telegram_id is not None:
                self.platform.logger.info("Saving user {0}".format(self.telegram_id))
                cur.execute(get_query(INSERT_USER), (self.telegram_id, "en"))
            self.platform.logger.info("Saving player {0}".format(self.ext_id))
            cur.execute(get_query(INSERT_PLAYER),
                        (self.platform.id, self.name, self.ext_id, self.telegram_id, STATUS_NEW, self.dt_updated,
                         self.is_public, self.avatar_url))
            ret = cur.fetchone()
            if ret is not None:
                self.id = ret[0]
        else:
            cur.execute(get_query(LOCK_PLAYER), (self.id,))
            ret = cur.fetchone()
            if ret is None:
                self.platform.logger.info("Empty result on getting lock for player {0}, so it was deleted.".
                                          format(self.id))
                return
            cur.execute(get_query(UPDATE_PLAYER_FULL),
                        (self.dt_updated, self.is_public, self.dt_updated_full, self.dt_updated_inc,
                         self.name, self.avatar_url,
                         self.id))
        self.platform.logger.info("Get saved games for player {} ({}) ".format(self.name, self.ext_id))
        # TODO: use single query for GET_PLAYER_GAME_IDS and GET_PLAYER_GAMES
        cur.execute(get_query(GET_PLAYER_GAME_IDS), (self.id, self.platform.id))
        ret = cur.fetchall()
        saved_games = []
        for j in ret:
            saved_games.append(j[0])
        for i in range(len(self.games)):
            if not (self.platform.is_game_known(str(self.games[i]))):
                # TODO: check
                new_game = self.platform.get_game(game_id=str(self.games[i]), name=str(self.games[i]))
                new_game.save(cursor=cur, active_locale='en')
                conn.commit()
                self.platform.load_games(game_id=new_game.id)
            game = self.platform.get_game_by_ext_id(str(self.games[i]))
            if game.id not in saved_games:
                cur.execute(get_query(INSERT_PLAYER_GAME),
                            (self.platform.id, game.id, self.id))
            if self.games[i] in self.achievements:
                if len(self.achievements[self.games[i]]) == 0:
                    continue

                self.platform.logger.info("Get saved achievements for player {} ({}) and game \"{}\" ({})".
                                          format(self.name, self.ext_id, game.name, game.ext_id))
                cur.execute(get_query(GET_PLAYER_ACHIEVEMENT_IDS), (self.id, self.platform.id, game.id))
                ret = cur.fetchall()
                saved_achievements = []
                saved_cnt = 0
                for j in ret:
                    saved_achievements.append(j[0])
                self.platform.logger.info(
                    "Found in db achievements for player {} and game \"{}\" ({}): {}".format(
                        self.ext_id, game.name, game.ext_id, len(saved_achievements)))
                for j in range(len(self.achievements[self.games[i]])):
                    achievement = game.get_achievement_by_ext_id(self.achievements[self.games[i]][j])
                    achievement_date = self.achievement_dates[self.games[i]][j]
                    if achievement.id in saved_achievements:
                        continue
                    if achievement.id is None:
                        # TODO: normally shouldn't be, but is happens
                        self.platform.logger.warn("Empty id for achievement {} and game {} ({}) on platform {}".
                                                  format(self.achievements[self.games[i]][j], game.id, game.name,
                                                         self.platform.name))
                        cur.execute(get_query(GET_ACHIEVEMENT_ID),
                                    (self.platform.id, str(self.achievements[self.games[i]][j]), game.id))
                        ret = cur.fetchone()
                        if ret is not None:
                            achievement.id = ret[0]
                        else:
                            new_game = self.platform.get_game(game_id=game.ext_id, name=game.name)
                            new_game.save(cursor=cur, active_locale='en')
                            conn.commit()
                            self.platform.logger.warn("Get id for achievement {} and game {} ({}) on platform {} after "
                                                      "refresh".
                                                      format(self.achievements[self.games[i]][j], game.id, game.name,
                                                             self.platform.name))
                            cur.execute(get_query(GET_ACHIEVEMENT_ID),
                                        (self.platform.id, str(self.achievements[self.games[i]][j]), game.id))
                            ret = cur.fetchone()
                            if ret is not None:
                                achievement.id = ret[0]
                            else:
                                self.platform.logger.error("Empty id for achievement {} and game {} ({})"
                                                           " on platform {} after refresh".
                                                           format(self.achievements[self.games[i]][j], game.id,
                                                                  game.name,
                                                                  self.platform.name))
                    cur.execute(get_query(INSERT_PLAYER_ACHIEVEMENT),
                                (self.platform.id, game.id, achievement.id, self.id, achievement_date))
                    saved_cnt += 1
                    self.platform.logger.info(
                        "Saved into db achievement \"{5}\" ({2}) for player {3} ({0}) and game \"{4}\" ({1}).".
                        format(self.ext_id,
                               game.ext_id,
                               achievement.id,
                               self.name,
                               game.name,
                               achievement.name
                               ))
                self.platform.logger.info(
                    "Achievements for player {} and game \"{}\" ({}) was saved: {}".format(
                        self.ext_id,
                        game.name,
                        game.ext_id,
                        saved_cnt))
        self.platform.logger.info("Saved achievements for player {0}".format(self.ext_id))

        # TODO: split into procedures
        if len(self.stats) > 0:
            self.platform.logger.info(
                "Find stats for player {0} games: {1}".format(
                    self.ext_id, len(self.stats)))
            for i in self.stats:
                game = self.platform.get_game_by_ext_id(str(i))
                self.platform.logger.info("Find stats for player {0} game {1} ({3}): {2}".format(
                    self.ext_id, game.ext_id, len(self.stats[i]), game.name))
                saved_stats = {}
                stats_to_save = {}
                # TODO: check if possible to unify player_game_stats queries
                cur.execute(get_query(GET_PLAYER_GAME_STATS_FOR_GAME),
                            (self.id, self.platform.id, game.id))
                for stat_id, stat_value in cur:
                    saved_stats[stat_id] = stat_value
                for j in self.stats[i]:
                    if j not in saved_stats:
                        stats_to_save[j] = self.stats[i][j]
                    elif saved_stats[j] != self.stats[i][j]:
                        stats_to_save[j] = self.stats[i][j]
                for j in stats_to_save:
                    if game.get_stat_id(j) is None:
                        new_game = self.platform.get_game(game_id=game.id, name=game.name)
                        new_game.save(cursor=cur, active_locale='en')
                        game = new_game
                    cur.execute(get_query(INSERT_PLAYER_GAME_STATS),
                                (self.platform.id, game.id, game.get_stat_id(j), self.id, stats_to_save[j])
                                )

        conn.commit()
        conn.close()
        self.platform.logger.info("Saved player {} ({})".format(self.name, self.ext_id))

    def renew(self):
        new_name = self.platform.validate_player(self.ext_id)
        if new_name is None:
            raise ValueError("Name is empty")
        if new_name != self.name:
            self.platform.logger.info("Found new name {1} for player {0}. ".
                                      format(self.name, new_name))
            self.set_name(new_name)
        if self.platform.get_player_avatar is not None:
            new_avatar = self.platform.get_player_avatar(self.ext_id)
            if self.avatar_url != new_avatar:
                self.platform.logger.info("Found new avatar {1} for player {0}. Old one: {2}".
                                          format(self.name, new_avatar, self.avatar_url))
                self.set_avatar(new_avatar)
        cur_time = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        if self.platform.incremental_update_enabled:
            delta = datetime.timedelta(days=self.platform.incremental_update_interval)
            if (self.dt_updated_inc is not None and (self.dt_updated_inc + delta) > cur_time) or \
                    (self.dt_updated_full is not None and (self.dt_updated_full + delta) > cur_time):
                if random.random() >= self.platform.incremental_skip_chance:
                    owned_games, owned_games_names = self.platform.get_games(self.ext_id)
                    self.get_owned_games(force=True)
                    new_games = []
                    new_game_names = []
                    saved_games_by_ext = {}
                    saved_game_names_by_ext = {}
                    for cg in self.games:
                        saved_games_by_ext[cg.ext_id] = cg
                        saved_game_names_by_ext[cg.ext_id] = cg.name
                    self.games, names, = self.platform.get_last_games(self.ext_id)
                    str_games = list(map(str, self.games))
                    for cg in range(len(owned_games)):
                        if str(owned_games[cg]) not in saved_games_by_ext and str(owned_games[cg]) not in str_games:
                            new_games.append(owned_games[cg])
                            new_game_names.append(owned_games_names[cg])
                            self.platform.logger.info("Found new owned, but not played yet game {2} ({1} "
                                                      "for player {0}.".
                                                      format(self.name, owned_games[cg], owned_games_names[cg]))
                    self.games = [*self.games, *new_games]
                    names = [*names, *new_game_names]
                    self.platform.logger.info("Prepared incremental update for player {0}. "
                                              "Last inc update {1}, last full update {2}".
                                              format(self.name, self.dt_updated_inc, self.dt_updated_full))
                    self.dt_updated_inc = cur_time
                else:
                    self.games, names, = self.platform.get_games(self.ext_id)
                    self.dt_updated_full = cur_time
                    self.platform.logger.info("Prepared full update (because random) for player {0}. "
                                              "Last inc update {1}, last full update {2}".
                                              format(self.name, self.dt_updated_inc, self.dt_updated_full))
            else:
                self.games, names, = self.platform.get_games(self.ext_id)
                self.platform.logger.info("Prepared full update (because inc not possible) for player {0}. "
                                          "Last inc update {1}, last full update {2}".
                                          format(self.name, self.dt_updated_inc, self.dt_updated_full))
                self.dt_updated_full = cur_time
        else:
            self.games, names, = self.platform.get_games(self.ext_id)
            self.dt_updated_full = cur_time
            self.platform.logger.info("Prepared full update (no choice) for player {0}. "
                                      "Last inc update {1}, last full update {2}".
                                      format(self.name, self.dt_updated_inc, self.dt_updated_full))
        games_num = len(self.games)
        self.is_public = True
        self.platform.logger.info("Begin to refresh {} games from player {}".
                                  format(games_num, self.name))
        for i in range(games_num):
            # if new game, not discovered by game updater yet
            if not self.platform.is_game_known(str(self.games[i])):
                self.platform.logger.info("Request new game ext id: {}, name: {} for player: {}. ".
                                          format(self.games[i], names[i], self.name))
                new_game = self.platform.get_game(str(self.games[i]), names[i])
                self.platform.add_game(new_game)

                conn = self.platform.get_connect()
                cur = conn.cursor()
                new_game.save(cur, "en")
                conn.commit()
                self.platform.logger.info("Saved new game ext id: {}, name: {} for player: {}. ".
                                          format(self.games[i], names[i], self.name))
            if self.platform.get_game_by_ext_id(str(self.games[i])).has_achievements:
                try:
                    self.achievements[self.games[i]], self.achievement_dates[self.games[i]] = \
                        self.platform.get_achievements(self.ext_id, self.games[i])
                except ValueError as err:
                    if str(err) == "Profile is not public":
                        self.is_public = False
                        self.dt_updated_inc = None
                        self.dt_updated_full = None
                        self.platform.logger.info(
                            "Skip checking achievements for player {} {}, because profile is private.".format(
                                self.ext_id, self.name))
                        break
                if self.platform.get_player_stats is not None and \
                        len(self.platform.get_game_by_ext_id(str(self.games[i])).stats) > 0:
                    self.stats[self.games[i]] = self.platform.get_player_stats(self.ext_id, self.games[i])
            else:
                self.platform.logger.info(
                    "Skip checking achievements for game with id {1} and name {2} for player {0} {3}, "
                    "because not available. Progress {4}/{5}".format(
                        self.ext_id, self.games[i], names[i], self.name, i + 1, games_num))
        self.dt_updated = datetime.datetime.now()
