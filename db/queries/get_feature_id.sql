select c.id
from achievements_hunt.features c
where c.platform_id = %s
  and c.name = %s