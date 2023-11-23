insert into achievements_hunt.players(platform_id, name, ext_id, telegram_id, status_id, dt_update,
                                                      is_public, avatar_url)
                values (%s, %s, %s, %s, %s, %s,
                        %s, %s) on conflict ON CONSTRAINT u_players_ext_key do nothing returning id