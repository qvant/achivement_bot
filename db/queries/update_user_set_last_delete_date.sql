update achievements_hunt.users u set dt_last_delete = current_timestamp
                                where u.telegram_id = %s