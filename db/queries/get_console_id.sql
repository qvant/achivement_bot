select id
from achievements_hunt.consoles c
where c.platform_id = %s
  and c.ext_id = %s