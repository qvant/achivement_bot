insert into achievements_hunt.player_achievements
                                    (platform_id, game_id, achievement_id, player_id, dt_unlock)
                                    values (%s, %s, %s, %s, %s) returning id