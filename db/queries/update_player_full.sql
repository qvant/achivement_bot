update achievements_hunt.players set dt_update = %s,
                                                     is_public = %s,
                                                     dt_update_full = coalesce(%s, dt_update_full),
                                                     dt_update_inc = coalesce(%s, dt_update_inc),
                                                     name = coalesce(%s, name),
                                                     avatar_url = coalesce(%s, avatar_url)
                where id = %s