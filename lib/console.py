from typing import Union


class Console:
    def __init__(self, id: Union[int, None], name: str, ext_id: str, platform_id: int):
        self.id = id
        self.name = name
        self.ext_id = ext_id
        self.platform_id = platform_id

    def save(self, connect):
        if self.id is None:
            cur = connect.cursor()
            cur.execute("""
                insert into achievements_hunt.consoles(platform_id, name, ext_id)
                values (%s, %s, %s)
                on conflict ON CONSTRAINT u_consoles_ext_key
                do nothing returning id""", (self.platform_id, self.name, self.ext_id,))
            ret = cur.fetchone()
            if ret is not None:
                self.id = ret[0]
            else:
                cur.execute("""
                select id from achievements_hunt.consoles c where c.platform_id = %s and c.ext_id = %s
                """, (self.platform_id, self.ext_id))
                ret = cur.fetchone()
                if ret is not None:
                    self.id = ret[0]
