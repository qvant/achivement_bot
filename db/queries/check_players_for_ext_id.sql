select count(1)
from achievements_hunt.players
where platform_id = %s
  and ext_id = %s