from typing import Union


class Achievement:
    def __init__(self, id: Union[int, None], game_id: Union[int, None], name: Union[str, None],
                 platform_id: int, ext_id: Union[str, None], description: str, icon_url: Union[str, None] = None,
                 locked_icon_url: Union[str, None] = None):
        self.id = id
        self.game_id = game_id
        self.platform_id = platform_id
        self.description = description
        self.icon_url = icon_url
        if locked_icon_url is not None:
            self.locked_icon_url = locked_icon_url
        else:
            self.locked_icon_url = icon_url
        if ext_id is not None:
            self.ext_id = ext_id
        else:
            self.ext_id = name
        if name is not None:
            self.name = name
        else:
            self.name = ext_id

    def get_id(self):
        return self.id

    def set_game_id(self, game_id):
        self.game_id = game_id

    def save(self, cursor, active_locale: str):
        en_name = ""
        en_descr = ""
        if self.id is None:
            if active_locale == 'en':
                cursor.execute(
                    """insert into achievements_hunt.achievements as l (name, ext_id, platform_id, game_id, description,
                            icon_url, locked_icon_url)
                            values(%s, %s, %s, %s, %s, %s, %s)
                            on conflict ON CONSTRAINT u_achievements_ext_key do update
                            set dt_update=current_timestamp, name=EXCLUDED.name, description=EXCLUDED.description,
                            icon_url=EXCLUDED.icon_url, locked_icon_url=EXCLUDED.locked_icon_url
                            where l.name != EXCLUDED.name or l.description != EXCLUDED.description
                            or coalesce(l.icon_url, '') != coalesce(EXCLUDED.icon_url, l.icon_url, '')
                            or coalesce(l.locked_icon_url, '')
                                    != coalesce(EXCLUDED.locked_icon_url, l.locked_icon_url, '')
                            returning id, name, description
                    """, (self.name, self.ext_id, self.platform_id, self.game_id, self.description, self.icon_url,
                          self.locked_icon_url)
                )
            else:
                cursor.execute(
                    """insert into achievements_hunt.achievements as l (name, ext_id, platform_id, game_id, description,
                            icon_url, locked_icon_url)
                            values(%s, %s, %s, %s, %s, %s, %s)
                            on conflict ON CONSTRAINT u_achievements_ext_key do nothing
                            returning id, name, description
                    """, (self.name, self.ext_id, self.platform_id, self.game_id, self.description, self.icon_url,
                          self.locked_icon_url)
                )
            ret = cursor.fetchone()
            if ret is not None:
                self.id = ret[0]
                en_name = ret[1]
                en_descr = ret[2]
        if self.id is None:
            cursor.execute("""
                                select id, name, description from achievements_hunt.achievements
                                where platform_id = %s and ext_id = %s
                                and game_id = %s
                            """, (self.platform_id, self.ext_id, self.game_id))
            ret = cursor.fetchone()
            if ret is not None:
                self.id = ret[0]
                en_name = ret[1]
                en_descr = ret[2]
        if (en_name != self.name or en_descr != self.description) and active_locale != 'en':
            cursor.execute("""insert into achievements_hunt.achievement_translations as l
                            (platform_id, game_id, achievement_id, locale, name, description )
                            values(%s, %s, %s, %s, %s, %s)
                            on conflict ON CONSTRAINT u_achievement_translations_key do update
                            set dt_update=current_timestamp, name=EXCLUDED.name, description=EXCLUDED.description
                            where l.name != EXCLUDED.name
                            returning id
                    """, (self.platform_id, self.game_id, self.id, active_locale, self.name, self.description))

    def __str__(self):
        return "id: {0}, game_id: {1}, ext_id: {2}".format(self.id, self.game_id, self.ext_id)
