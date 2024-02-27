select
  coalesce(tr.name, a.name),
  coalesce(tr.description, a.description)
from achievements_hunt.achievements a
left join achievements_hunt.achievement_translations tr
on tr.achievement_id  = a.id
  and tr.game_id = a.game_id
  and tr.platform_id = a.platform_id
  and tr.locale = %s
where a.platform_id = %s
  and a.game_id = %s
  and a.id = %s