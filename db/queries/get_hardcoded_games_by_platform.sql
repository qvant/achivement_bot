select ext_id,
       name
from achievements_hunt.games_hardcoded h
where h.platform_id = %s