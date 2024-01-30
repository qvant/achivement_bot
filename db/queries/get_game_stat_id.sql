select g.id
from achievements_hunt.game_stats g
where g.platform_id = %s
  and g.game_id = %s
  and g.ext_id = %s