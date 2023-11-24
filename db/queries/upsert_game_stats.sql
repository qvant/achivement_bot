insert into achievements_hunt.game_stats as s(platform_id, game_id, ext_id, name)
                    values (%s, %s, %s, %s )
                    on conflict ON CONSTRAINT u_game_stats_ext_key do update
                        set dt_update=current_timestamp, name=EXCLUDED.name
                    returning id