import datetime
import random
from psycopg2 import Error as PgError
from typing import Union, Dict
from .platform import Platform
from datetime import timezone

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
            cur.execute("""
                            update achievements_hunt.players set ext_id = %s, dt_update = %s where id = %s
                        """, (self.ext_id, self.dt_updated, self.id,))
        except PgError as err:
            if err.pgcode == "23505":
                conn.rollback()
                cur.execute("""
                    delete from achievements_hunt.players where id = %s
                """, (self.id,))
                cur.execute("""
                update achievements_hunt.players set telegram_id = %s where ext_id = %s and platform_id = %s
                    and telegram_id is null
                returning id
                                """, (self.telegram_id, self.ext_id, self.platform.id,))
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
        cur.execute("""
            update achievements_hunt.players set status_id = %s, name=%s where id = %s""",
                    (STATUS_VALID, self.name, self.id))
        conn.commit()

    def delete(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        if self.id is not None:
            cur.execute("""
                                           select status_id from achievements_hunt.players p where p.id = %s
                                       """, (self.id,))
            status, = cur.fetchone()
            cur.execute("""
                select dt_last_delete from achievements_hunt.users u where u.telegram_id = %s
            """, (self.telegram_id,))
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
                cur.execute("""
                            delete from achievements_hunt.players where id = %s and platform_id = %s
                        """, (self.id, self.platform.id))
                cur.execute("""
                                update achievements_hunt.users u set dt_last_delete = current_timestamp
                                where u.telegram_id = %s
                            """, (self.telegram_id,))
                conn.commit()
                self.platform.logger.info("Deleted player {0}".format(self.ext_id))
        self.platform.reset_connect()

    def is_unique(self):
        conn = self.platform.get_connect()
        cur = conn.cursor()
        cur.execute("""select count(1) from achievements_hunt.players where platform_id = %s and telegram_id = %s""",
                    (self.platform.id, self.telegram_id))
        ret = cur.fetchone()
        if ret[0] > 0:
            return False, "Only one account per telegram user for platform"
        cur.execute("""select count(1) from achievements_hunt.players where platform_id = %s and ext_id = %s""",
                    (self.platform.id, self.ext_id))
        ret = cur.fetchone()
        if ret[0] > 0:
            cur.execute("""select telegram_id, id from achievements_hunt.players where platform_id = %s
                        and ext_id = %s""",
                        (self.platform.id, self.ext_id))
            ret = cur.fetchone()
            if ret[0] is not None:
                return False, "Account already bound"
            else:
                self.id = ret[1]
                cur.execute("""update achievements_hunt.players set telegram_id = %s where platform_id = %s
                        and ext_id = %s and telegram_id is null""",
                            (self.telegram_id, self.platform.id, self.ext_id))
                conn.commit()
        return True, "Ok"

    def get_owned_games(self, mode=GAMES_ALL, force=False, console_id: Union[int, None] = None):
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
                   and (gg.console_id = %s or %s is null)
                 order by gg.name""",
                            (self.platform.id, self.id, console_id, console_id))
            elif mode == GAMES_WITH_ACHIEVEMENTS:
                cur.execute("""select g.game_id, g.is_perfect from achievements_hunt.player_games g
                                join achievements_hunt.games gg on gg.id = g.game_id
                                 where g.platform_id = %s and g.player_id = %s
                                   and gg.has_achievements
                                   and (gg.console_id = %s or %s is null)
                                 order by gg.name""",
                            (self.platform.id, self.id, console_id, console_id))
            elif mode == GAMES_PERFECT:
                cur.execute("""select g.game_id, g.is_perfect from achievements_hunt.player_games g
                                join achievements_hunt.games gg on gg.id = g.game_id
                                 where g.platform_id = %s and g.player_id = %s
                                   and g.is_perfect
                                   and (gg.console_id = %s or %s is null)
                                 order by gg.name""",
                            (self.platform.id, self.id, console_id, console_id))
            else:
                self.platform.logger.critical("incorrect get games mode {0}".format(mode))
                cur.execute("""select g.game_id, g.is_perfect from achievements_hunt.player_games g
                                join achievements_hunt.games gg on gg.id = g.game_id
                                 where g.platform_id = %s and g.player_id = %s
                                   and (gg.console_id = %s or %s is null)
                                 order by gg.name""",
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
            cur.execute("""select coalesce (tr.name, a.name) as name, pa.id, a.percent_owners, a.id,
             coalesce(tr.description, a.description) as description, pa.dt_unlock,
             case when pa.id is not null then a.icon_url else a.locked_icon_url end,
             ar.name,
             a.is_hidden
             from achievements_hunt.achievements a
             left join achievements_hunt.player_achievements pa
             on pa.achievement_id = a.id and pa.player_id = %s
             left join achievements_hunt.achievement_translations tr
             on tr.achievement_id = a.id and tr.platform_id = a.platform_id
             and tr.locale = %s
             left join achievements_hunt.achievement_rarity ar
             on ar.n_bottom_border < a.percent_owners
               and ar.n_upper_border >= a.percent_owners
             where a.platform_id = %s
             and a.game_id = %s
             order by a.percent_owners desc, a.name""",
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
        cur.execute("""
            select gs.name,
                   s.stat_value
            from achievements_hunt.player_game_stats s
            join achievements_hunt.game_stats gs
            on gs.id = s.stat_id
            where s.player_id = %s
                and s.platform_id = %s
                and s.game_id = %s
            order by gs.name""",
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
                cur.execute("""
                                insert into achievements_hunt.users(telegram_id)
                                values (%s)
                                on conflict (telegram_id) do nothing
                            """, (self.telegram_id,))
            self.platform.logger.info("Saving player {0}".format(self.ext_id))
            cur.execute("""
                insert into achievements_hunt.players(platform_id, name, ext_id, telegram_id, status_id, dt_update,
                                                      is_public, avatar_url)
                values (%s, %s, %s, %s, %s, %s,
                        %s, %s) on conflict ON CONSTRAINT u_players_ext_key do nothing returning id
            """, (self.platform.id, self.name, self.ext_id, self.telegram_id, STATUS_NEW, self.dt_updated,
                  self.is_public, self.avatar_url))
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
                                                     dt_update_inc = coalesce(%s, dt_update_inc),
                                                     name = coalesce(%s, name),
                                                     avatar_url = coalesce(%s, avatar_url)
                where id = %s
            """, (self.dt_updated, self.is_public, self.dt_updated_full, self.dt_updated_inc,
                  self.name, self.avatar_url,
                  self.id))
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
                    if achievement.id is None:
                        # TODO: normally shouldn't be, but is happens
                        self.platform.logger.warn("Empty id for achievement {} and game {} ({}) on platform {}".
                                                  format(self.achievements[self.games[i]][j], game.id, game.name,
                                                         self.platform.name))
                        cur.execute("""
                                        select id from achievements_hunt.achievements
                                        where platform_id = %s and ext_id = %s
                                        and game_id = %s
                                    """, (self.platform.id, str(self.achievements[self.games[i]][j]), game.id))
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
                            cur.execute("""
                                            select id from achievements_hunt.achievements
                                            where platform_id = %s and ext_id = %s
                                            and game_id = %s
                                        """,
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
                cur.execute("""
                    select gs.ext_id, s.stat_value from achievements_hunt.player_game_stats s
                            join achievements_hunt.game_stats gs
                            on gs.id = s.stat_id
                            where s.player_id = %s
                            and s.platform_id = %s and s.game_id = %s""",
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
                    cur.execute(
                        """
                            insert into achievements_hunt.player_game_stats as s
                            (platform_id, game_id, stat_id, player_id, stat_value)
                            values (%s, %s, %s, %s, %s )
                            on conflict ON CONSTRAINT u_player_game_stats_key do update
                                set dt_update=current_timestamp, stat_value=EXCLUDED.stat_value
                        """,
                        (self.platform.id, game.id, game.get_stat_id(j), self.id, stats_to_save[j])
                    )

        conn.commit()
        conn.close()
        self.platform.logger.info("Saved player {0}".format(self.ext_id))

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
                            self.platform.logger.info("Found new owned, but unplayed game {1} for player {0}. ".
                                                      format(self.name, owned_games[cg]))
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
