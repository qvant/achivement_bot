select g.id
from achievements_hunt.games g
where g.platform_id = %s
  and g.ext_id = %s