from typing import Union
from .achievement import Achievement
from .console import Console


class Game:
    def __init__(self, name: str, platform_id: int, id: Union[int, None], ext_id: str, achievements,
                 console_ext_id: Union[str, None], console: Union[Console, None]):
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

    def save(self, cursor, active_locale: str):
        if self.id is None:
            cursor.execute(
                """insert into achievements_hunt.games as l (name, ext_id, platform_id, has_achievements,
                        console_id)
                        values(%s, %s, %s, %s, %s)
                        on conflict ON CONSTRAINT u_games_ext_key do update
                        set dt_update=current_timestamp, name=%s, has_achievements=%s, console_id=%s
                        where l.name != EXCLUDED.name or l.has_achievements != EXCLUDED.has_achievements
                        or coalesce(l.console_id, -1) != coalesce(EXCLUDED.console_id, -2)
                        returning id
                """, (self.name, self.ext_id, self.platform_id, self.has_achievements, self.console_id(),
                      self.name, self.has_achievements, self.console_id())
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
            if len(self.achievements) > 0:
                for i in self.achievements:
                    self.achievements[i].set_game_id(self.id)
                    self.achievements[i].save(cursor, active_locale)
        else:
            cursor.execute(
                """update achievements_hunt.games l set dt_update=current_timestamp, name=%s,
                        has_achievements=%s, console_id=%s
                        where id = %s and platform_id = %s
                        and (%s != name or %s != has_achievements
                            or coalesce(%s, -1) != coalesce(console_id, -2))
                """, (self.name, self.has_achievements, self.console_id(),
                      self.id, self.platform_id, self.name, self.has_achievements, self.console_id())
            )
            if len(self.achievements) > 0:
                for i in self.achievements:
                    self.achievements[i].set_game_id(self.id)
                    self.achievements[i].save(cursor, active_locale)

    def __str__(self):
        return "{0}".format(self.id)
