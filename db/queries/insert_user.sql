insert into achievements_hunt.users(telegram_id, locale)
                                                values (%s, %s)
                                                on conflict (telegram_id) do nothing