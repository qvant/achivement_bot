select id,
       name,
       ext_id
from achievements_hunt.consoles c
where c.platform_id = %s
    and id = %s