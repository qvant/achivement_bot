select id,
       platform_id,
       name,
       ext_id,
       telegram_id,
       dt_update,
       dt_update_full,
       dt_update_inc,
       avatar_url
from achievements_hunt.players
where platform_id = %s
    and status_id = %s
order by id