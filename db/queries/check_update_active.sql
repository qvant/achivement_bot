select count(1)
from achievements_hunt.update_history
where id_platform = %s
  and id_process = %s
  and dt_ended is null