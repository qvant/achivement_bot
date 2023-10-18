update achievements_hunt.update_history
set dt_ended = current_timestamp,
    dt_next_update = %s
where id_platform = %s
    and id_process = %s
    and dt_ended is null