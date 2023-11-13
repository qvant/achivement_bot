update achievements_hunt.users
set locale = %s,
    dt_last_update = current_timestamp
where telegram_id = %s