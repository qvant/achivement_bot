select id,
       platform_id,
       name,
       ext_id,
       dt_update,
       is_public,
       avatar_url
from achievements_hunt.players
where telegram_id = %s
order by id