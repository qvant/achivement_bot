select game_id
                                from achievements_hunt.player_games t
                                where t.player_id = %s
                                    and t.platform_id = %s