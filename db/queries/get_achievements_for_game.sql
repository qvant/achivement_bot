select id,
       ext_id,
       name,
       description,
       icon_url,
       locked_icon_url,
       is_hidden,
       is_removed
from achievements_hunt.achievements
where platform_id = %s
  and game_id = %s
order by id