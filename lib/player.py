import datetime
import random
from typing import Union
from .platform import Platform
from datetime import timezone

STATUS_NEW = 1
STATUS_VALID = 2

GAMES_ALL = 1
GAMES_WITH_ACHIEVEMENTS = 2
GAMES_PERFECT = 3


class Player:
    def __init__(self, name: str, ext_id: str, platform: Platform, id: Union[int, None], telegram_id: Union[int, None],
                 dt_updated=None, dt_updated_full=None, dt_updated_inc=None):
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
        self.has_perfect_games = True
        self.is_public = True

    def set_ext_id(self, ext_id):
        self.ext_id = ext_id
        self.dt_updated = datetime.datetime.now()
        conn = self.platform.get_connect()
        cur = conn.cursor()
        cur.execute("""
                        update achievements_hunt.players set ext_id = %s, dt_update = %s where id = %s
                    """, (self.ext_id, self.dt_updated, self.id,))
        conn.commit()

    def set_name(self, name):
        self.name = name
        self.dt_updated = datetime.datetime.now()

    def mark_valid(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        cur.execute("""
            update achievements_hunt.players set status_id = %s, name=%s where id = %s""",
                    (STATUS_VALID, self.name, self.id))
        conn.commit()

    def delete(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        if self.id is not None:
            cur.execute("""
                select dt_last_delete from achievements_hunt.users u where u.telegram_id = %s
            """, (self.telegram_id,))
            ret = cur.fetchone()
            if ret[0].replace(tzinfo=timezone.utc) + datetime.timedelta(days=3) > datetime.datetime.now()\
                    .replace(tzinfo=timezone.utc):
                # TODO: throw error
                self.platform.logger.info("Skip deleting player {0}, dt_last_delete {1}".format(self.ext_id, ret))
                pass
            else:
                self.platform.logger.info("Deleting player {0}".format(self.ext_id))
                cur.execute("""
                            delete from achievements_hunt.players where id = %s and platform_id = %s
                        """, (self.id, self.platform.id))
                cur.execute("""
                                update achievements_hunt.users u set dt_last_delete = current_timestamp
                                where u.telegram_id = %s
                            """, (self.telegram_id,))
                conn.commit()
                self.platform.logger.info("Deleted player {0}".format(self.ext_id))
        conn.close()

    def is_unique(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        cur.execute("""select count(1) from achievements_hunt.players where platform_id = %s and ext_id = %s""",
                    (self.platform.id, self.ext_id))
        ret = cur.fetchone()
        if ret[0] > 0:
            return False, "Account already bound"
        cur.execute("""select count(1) from achievements_hunt.players where platform_id = %s and telegram_id = %s""",
                    (self.platform.id, self.telegram_id))
        ret = cur.fetchone()
        if ret[0] > 0:
            return False, "Only one account per telegram user for platform"
        return True, "Ok"

    def get_owned_games(self, mode=GAMES_ALL, force=False):
        if len(self.games) == 0 or force:
            if force:
                self.games = []
            self.platform.logger.info("Load games for player {0}, mode {1} force mode {2}".format(self.id, mode, force))
            conn = self.platform.get_connect()
            cur = conn.cursor()
            if mode == GAMES_ALL:
                cur.execute("""select g.game_id, g.is_perfect from achievements_hunt.player_games g
                join achievements_hunt.games gg on gg.id = g.game_id
                 where g.platform_id = %s and g.player_id = %s
                 order by gg.name""",
                            (self.platform.id, self.id))
            elif mode == GAMES_WITH_ACHIEVEMENTS:
                cur.execute("""select g.game_id, g.is_perfect from achievements_hunt.player_games g
                                join achievements_hunt.games gg on gg.id = g.game_id
                                 where g.platform_id = %s and g.player_id = %s
                                 and gg.has_achievements
                                 order by gg.name""",
                            (self.platform.id, self.id))
            elif mode == GAMES_PERFECT:
                cur.execute("""select g.game_id, g.is_perfect from achievements_hunt.player_games g
                                join achievements_hunt.games gg on gg.id = g.game_id
                                 where g.platform_id = %s and g.player_id = %s
                                 and g.is_perfect
                                 order by gg.name""",
                            (self.platform.id, self.id))
            else:
                self.platform.logger.critical("incorrect get games mode {0}".format(mode))
                cur.execute("""select g.game_id, g.is_perfect from achievements_hunt.player_games g
                                join achievements_hunt.games gg on gg.id = g.game_id
                                 where g.platform_id = %s and g.player_id = %s
                                 order by gg.name""",
                            (self.platform.id, self.id))
            ret = cur.fetchall()
            self.has_perfect_games = False
            for j in ret:
                self.games.append(self.platform.get_game_by__id(j[0], load_if_not_found=True))
                if j[1]:
                    self.has_perfect_games = True

    @property
    def cur_achievement_stats(self):
        for i in self.achievement_stats:
            return self.achievement_stats[i]

    def get_achievement_stats(self, game_id, locale: str):
        if game_id not in self.achievement_stats:
            self.achievement_stats = {game_id: []}
            conn = self.platform.get_connect()
            cur = conn.cursor()
            cur.execute("""select coalesce (tr.name, a.name) as name, pa.id, a.percent_owners, a.id from
             achievements_hunt.achievements a
             left join achievements_hunt.player_achievements pa
             on pa.achievement_id = a.id and pa.player_id = %s
             left join achievements_hunt.achievement_translations tr
             on tr.achievement_id = a.id and tr.platform_id = a.platform_id
             and tr.locale = %s
             where a.platform_id = %s
             and a.game_id = %s
             order by a.percent_owners desc, a.name""",
                        (self.id, locale, self.platform.id, game_id))
            ret = cur.fetchall()
            for j in ret:
                self.achievement_stats[game_id].append({"name": j[0], "owned": j[1] is not None,
                                                        "percent": j[2], "id": j[3]})

    def save(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        if self.id is None:
            if self.telegram_id is not None:
                self.platform.logger.info("Saving user {0}".format(self.telegram_id))
                cur.execute("""
                                insert into achievements_hunt.users(telegram_id)
                                values (%s)
                                on conflict (telegram_id) do nothing
                            """, (self.telegram_id,))
            self.platform.logger.info("Saving player {0}".format(self.ext_id))
            cur.execute("""
                insert into achievements_hunt.players(platform_id, name, ext_id, telegram_id, status_id, dt_update,
                                                      is_public)
                values (%s, %s, %s, %s, %s, %s,
                        %s) on conflict ON CONSTRAINT u_players_ext_key do nothing returning id
            """, (self.platform.id, self.name, self.ext_id, self.telegram_id, STATUS_NEW, self.dt_updated,
                  self.is_public))
            ret = cur.fetchone()
            if ret is not None:
                self.id = ret[0]
        else:
            cur.execute("""
            select id from achievements_hunt.players where id = %s for update
            """, (self.id,))
            ret = cur.fetchone()
            if ret is None:
                self.platform.logger.info("Empty result on getting lock for player {0}, so it was deleted.".
                                          format(self.id))
                return
            cur.execute("""
                update achievements_hunt.players set dt_update = %s,
                                                     is_public = %s,
                                                     dt_update_full = coalesce(%s, dt_update_full),
                                                     dt_update_inc = coalesce(%s, dt_update_inc)
                where id = %s
            """, (self.dt_updated, self.is_public, self.dt_updated_full, self.dt_updated_inc, self.id,))
        self.platform.logger.info("Get saved games for player {0} ".format(self.ext_id))
        cur.execute("""
                            select game_id
                                from achievements_hunt.player_games t
                                where t.player_id = %s
                                    and t.platform_id = %s
                        """, (self.id, self.platform.id))
        ret = cur.fetchall()
        saved_games = []
        for j in ret:
            saved_games.append(j[0])
        for i in range(len(self.games)):
            game = self.platform.get_game_by_ext_id(str(self.games[i]))
            if game.id not in saved_games:
                cur.execute("""
                                insert into achievements_hunt.player_games(platform_id, game_id, player_id)
                                values (%s, %s, %s) returning id
                                                """,
                            (self.platform.id, game.id, self.id))
            if self.games[i] in self.achievements:
                if len(self.achievements[self.games[i]]) == 0:
                    continue

                self.platform.logger.info("Get saved achievements for player {0} and game {1}".
                                          format(self.ext_id, game.ext_id))
                cur.execute("""
                    select achievement_id
                        from achievements_hunt.player_achievements t
                        where t.player_id = %s
                            and t.platform_id = %s
                            and t.game_id = %s
                """,  (self.id, self.platform.id, game.id))
                ret = cur.fetchall()
                saved_achievements = []
                saved_cnt = 0
                for j in ret:
                    saved_achievements.append(j[0])
                self.platform.logger.info(
                    "Saved achievements for player {0} and game {1}: {2}".format(
                        self.ext_id, game.ext_id, len(saved_achievements)))
                for j in range(len(self.achievements[self.games[i]])):
                    achievement = game.get_achievement_by_ext_id(self.achievements[self.games[i]][j])
                    achievement_date = self.achievement_dates[self.games[i]][j]
                    if achievement.id in saved_achievements:
                        continue
                    cur.execute("""
                                    insert into achievements_hunt.player_achievements
                                    (platform_id, game_id, achievement_id, player_id, dt_unlock)
                                    values (%s, %s, %s, %s, %s) returning id
                                """, (self.platform.id, game.id, achievement.id, self.id, achievement_date))
                    saved_cnt += 1
                    self.platform.logger.info(
                        "Saved into db achievement {2} for player {0} and game {1}.".format(self.ext_id, game.ext_id,
                                                                                            achievement.id))
                self.platform.logger.info(
                    "Saved achievements for player {0} and game {1}: {2}".format(self.ext_id, game.name, saved_cnt))
        self.platform.logger.info("Saved achievements for player {0}".format(self.ext_id))

        conn.commit()
        conn.close()
        self.platform.logger.info("Saved player {0}".format(self.ext_id))

    def renew(self):
        cur_time = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        if self.platform.incremental_update_enabled:
            delta = datetime.timedelta(days=self.platform.incremental_update_interval)
            if (self.dt_updated_inc is not None and (self.dt_updated_inc + delta) > cur_time) or \
                    (self.dt_updated_full is not None and (self.dt_updated_full + delta) > cur_time):
                self.games, names, = self.platform.get_last_games(self.ext_id)
                self.platform.logger.info("Prepared incremental update for player {0}. "
                                          "Last inc update {1}, last full update {2}".
                                          format(self.name, self.dt_updated_inc, self.dt_updated_full))
                self.dt_updated_inc = cur_time
            elif random.random() < self.platform.incremental_skip_chance:
                self.games, names, = self.platform.get_games(self.ext_id)
                self.dt_updated_full = cur_time
                self.platform.logger.info("Prepared full update (because random) for player {0}. "
                                          "Last inc update {1}, last full update {2}".
                                          format(self.name, self.dt_updated_inc, self.dt_updated_full))
            else:
                self.games, names, = self.platform.get_games(self.ext_id)
                self.platform.logger.info("Prepared full update for player {0}. "
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
        for i in range(games_num):
            self.platform.logger.info("Update game with id {1} and name {2} for player {0} {3}. Progress {4}/{5}".
                                      format(self.ext_id, self.games[i], names[i], self.name, i, games_num))
            self.platform.update_games(str(self.games[i]), names[i])
            self.platform.logger.info(
                "Get achievements for game with id {1} and name {2} for player {0} {3}. Progress {4}/{5}".format(
                    self.ext_id, self.games[i], names[i], self.name, i+1, games_num))
            if self.platform.get_game_by_ext_id(str(self.games[i])).has_achievements:
                if self.is_public:
                    try:
                        self.achievements[self.games[i]], self.achievement_dates[self.games[i]] = \
                            self.platform.get_achivements(self.ext_id, self.games[i])
                    except ValueError as err:
                        if str(err) == "Profile is not public":
                            self.is_public = False
                            self.dt_updated_inc = None
                            self.dt_updated_full = None
                else:
                    self.platform.logger.info(
                        "Skip checking achievements for game with id {1} and name {2} for player {0} {3}, "
                        "because profile is private. Progress {4}/{5}".format(
                            self.ext_id, self.games[i], names[i], self.name, i + 1, games_num))
            else:
                self.platform.logger.info(
                    "Skip checking achievements for game with id {1} and name {2} for player {0} {3}, "
                    "because not available. Progress {4}/{5}".format(
                        self.ext_id, self.games[i], names[i], self.name, i + 1, games_num))
        self.dt_updated = datetime.datetime.now()
