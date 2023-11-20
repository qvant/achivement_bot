from typing import Union

from lib.query_holder import get_query, INSERT_CONSOLE, GET_CONSOLE_ID


class Console:
    def __init__(self, id: Union[int, None], name: str, ext_id: str, platform_id: int):
        self.id = id
        self.name = name
        self.ext_id = ext_id
        self.platform_id = platform_id

    def save(self, connect):
        if self.id is None:
            cur = connect.cursor()
            cur.execute(get_query(INSERT_CONSOLE), (self.platform_id, self.name, str(self.ext_id,)))
            ret = cur.fetchone()
            if ret is not None:
                self.id = ret[0]
            else:
                cur.execute(get_query(GET_CONSOLE_ID), (self.platform_id, str(self.ext_id)))
                ret = cur.fetchone()
                if ret is not None:
                    self.id = ret[0]
