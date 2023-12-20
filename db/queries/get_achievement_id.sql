select id
from achievements_hunt.achievements
where platform_id = %s
  and ext_id = %s
  and game_id = %s