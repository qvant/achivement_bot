from typing import Union


class Console:
    def __init__(self, id: Union[int, None], name: str, ext_id: str, platform_id: int):
        self.id = id
        self.name = name
        self.ext_id = ext_id
        self.platform_id = platform_id

    def save(self):
        if self.id is None:
            from lib.db_api import get_console_id
            self.id = get_console_id(self.platform_id, self.ext_id)
            if self.id is None:
                from lib.db_api import save_console
                save_console(self)
