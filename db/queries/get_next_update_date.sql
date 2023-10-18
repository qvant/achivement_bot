select max(dt_next_update)
from achievements_hunt.update_history
where id_platform = %s
    and dt_ended is not null
    and id_process = %s