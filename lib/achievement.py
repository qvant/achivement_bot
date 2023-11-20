from typing import Union

from lib.query_holder import get_query, UPSERT_ACHIEVEMENT_ENGLISH, INSERT_ACHIEVEMENT, GET_ACHIEVEMENT_TEXT, \
    UPSERT_ACHIEVEMENT_TRANSLATION


class Achievement:
    def __init__(self, id: Union[int, None], game_id: Union[int, None], name: Union[str, None],
                 platform_id: int, ext_id: Union[str, None], description: str, icon_url: Union[str, None] = None,
                 locked_icon_url: Union[str, None] = None, is_hidden: bool = False):
        self.id = id
        self.game_id = game_id
        self.platform_id = platform_id
        self.description = description
        self.is_hidden = is_hidden
        if icon_url is not None:
            self.icon_url = icon_url
        else:
            self.icon_url = ""
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
        en_description = ""
        if self.id is None:
            if active_locale == 'en':
                cursor.execute(get_query(UPSERT_ACHIEVEMENT_ENGLISH),
                               (self.name, self.ext_id, self.platform_id, self.game_id, self.description, self.icon_url,
                                self.locked_icon_url, self.is_hidden)
                               )
            else:
                cursor.execute(get_query(INSERT_ACHIEVEMENT),
                               (self.name, self.ext_id, self.platform_id, self.game_id, self.description, self.icon_url,
                                self.locked_icon_url, self.is_hidden)
                               )
            ret = cursor.fetchone()
            if ret is not None:
                self.id = ret[0]
                en_name = ret[1]
                en_description = ret[2]
        if self.id is None:
            cursor.execute(get_query(GET_ACHIEVEMENT_TEXT), (self.platform_id, self.ext_id, self.game_id))
            ret = cursor.fetchone()
            if ret is not None:
                self.id = ret[0]
                en_name = ret[1]
                en_description = ret[2]
        if (en_name != self.name or en_description != self.description) and active_locale != 'en':
            cursor.execute(get_query(UPSERT_ACHIEVEMENT_TRANSLATION),
                           (self.platform_id, self.game_id, self.id, active_locale, self.name, self.description))

    def __str__(self):
        return "id: {0}, game_id: {1}, ext_id: {2}".format(self.id, self.game_id, self.ext_id)
