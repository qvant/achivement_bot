from typing import Union
from .achievement import Achievement
from .console import Console


class Game:
    def __init__(self, name: str, platform_id: int, id: Union[int, None], ext_id: str, achievements,
                 console_ext_id: Union[str, None], console: Union[Console, None],
                 icon_url: Union[str, None] = None, release_date: Union[str, None] = None):
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
        self.icon_url = icon_url
        self.release_date = release_date
        self._is_persist = self.id is not None
        self._achievements_saved = False

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

    def save(self, cursor, active_locale: str):
        if self.id is None:
            cursor.execute(
                """insert into achievements_hunt.games as l (name, ext_id, platform_id, has_achievements,
                        console_id, icon_url, release_date)
                        values(%s, %s, %s, %s, %s, %s, %s)
                        on conflict ON CONSTRAINT u_games_ext_key do update
                        set dt_update=current_timestamp, name=%s, has_achievements=%s, console_id=%s,
                        icon_url=%s, release_date=%s
                        where l.name != EXCLUDED.name or l.has_achievements != EXCLUDED.has_achievements
                        or coalesce(l.console_id, -1) != coalesce(EXCLUDED.console_id, -1)
                        or coalesce(l.release_date, '') != coalesce(EXCLUDED.release_date, '')
                        or coalesce(l.icon_url, '') != coalesce(EXCLUDED.icon_url, '')
                        returning id
                """, (self.name, self.ext_id, self.platform_id, self.has_achievements, self.console_id(),
                      self.icon_url, self.release_date,
                      self.name, self.has_achievements, self.console_id(), self.icon_url, self.release_date)
            )
            ret = cursor.fetchone()
            if ret is not None:
                self.id = ret[0]
            else:
                cursor.execute("""
                    select id from achievements_hunt.games where platform_id = %s and ext_id = %s
                """, (self.platform_id, self.ext_id))
                ret = cursor.fetchone()
                if ret is not None:
                    self.id = ret[0]
        else:
            if not self._is_persist:
                cursor.execute(
                    """update achievements_hunt.games l set dt_update=current_timestamp, name=%s,
                            has_achievements=%s, console_id=%s,
                            icon_url=%s, release_date=%s
                            where id = %s and platform_id = %s
                            and (%s != name or %s != has_achievements
                                or coalesce(%s, -1) != coalesce(console_id, -1)
                                or coalesce(%s, '') != coalesce(icon_url, '')
                                or coalesce(%s, '') != coalesce(release_date, ''))
                    """, (self.name, self.has_achievements, self.console_id(),
                          self.icon_url, self.release_date,
                          self.id, self.platform_id, self.name, self.has_achievements, self.console_id(),
                          self.icon_url, self.release_date)
                )
        if len(self.achievements) > 0 and not self._achievements_saved:
            if active_locale == 'en':
                cursor.execute(
                    """select id, ext_id, name, description, icon_url, locked_icon_url from achievements_hunt.achievements
                            where platform_id = %s and game_id = %s
                    """, (self.platform_id, self.id)
                )
            else:
                cursor.execute(
                    """select a.id, a.ext_id, coalesce(l.name, a.name), coalesce(a.description, l.description),
                              icon_url, locked_icon_url
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
            for id, ext_id, name, description, icon_url, locked_icon_url in cursor:
                if ext_id in self.achievements:
                    self.achievements[ext_id].id = id
                    if name != self.achievements[ext_id].name \
                            or description != self.achievements[ext_id].description\
                            or icon_url != self.achievements[ext_id].icon_url \
                            or locked_icon_url != self.achievements[ext_id].locked_icon_url:
                        need_save = True
                        to_save.append(ext_id)
                else:
                    need_save = True
                    to_save.append(ext_id)
            if need_save:
                for i in self.achievements:
                    if self.achievements[i].id is None or i in to_save:
                        self.achievements[i].set_game_id(self.id)
                        self.achievements[i].id = None
                        self.achievements[i].save(cursor, active_locale)
        self._is_persist = True
        self._achievements_saved = True

    def __str__(self):
        return "{0}".format(self.id)
