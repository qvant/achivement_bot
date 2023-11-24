insert into achievements_hunt.player_game_stats as s
                            (platform_id, game_id, stat_id, player_id, stat_value)
                            values (%s, %s, %s, %s, %s )
                            on conflict ON CONSTRAINT u_player_game_stats_key do update
                                set dt_update=current_timestamp, stat_value=EXCLUDED.stat_value