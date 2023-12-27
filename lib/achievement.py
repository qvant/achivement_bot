from typing import Union


class Achievement:
    def __init__(self, id: Union[int, None], game_id: Union[int, None], name: Union[str, None],
                 platform_id: int, ext_id: Union[str, None], description: str, icon_url: Union[str, None] = None,
                 locked_icon_url: Union[str, None] = None, is_hidden: bool = False, is_removed: bool = False):
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
        self.is_removed = is_removed

    def get_id(self):
        return self.id

    def set_game_id(self, game_id):
        self.game_id = game_id

    def save(self, active_locale: str):
        from lib.db_api import save_english_achievement, save_l18n_achievement, save_achievement_translation, \
            get_achievement_text_for_locale
        if self.id is None:
            if active_locale == 'en':
                self.id = save_english_achievement(self)
            else:
                self.id = save_l18n_achievement(self)
        if active_locale != 'en':
            # TODO check it level higher
            saved_name, saved_description = get_achievement_text_for_locale(self, active_locale)
            if saved_name != self.name or saved_description != self.description:
                save_achievement_translation(self, active_locale)

    def __str__(self):
        return "id: {0}, game_id: {1}, ext_id: {2}".format(self.id, self.game_id, self.ext_id)
