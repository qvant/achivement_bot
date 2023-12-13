select a.id,
       a.platform_id,
       a.name,
       a.ext_id,
       g.ext_id,
       a.description,
       a.game_id,
       a.icon_url,
       a.locked_icon_url,
       a.is_hidden
from achievements_hunt.achievements a
join  achievements_hunt.games g
  on a.game_id = g.id
where a.platform_id = %s
order by id