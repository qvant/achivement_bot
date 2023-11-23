select achievement_id
                        from achievements_hunt.player_achievements t
                        where t.player_id = %s
                            and t.platform_id = %s
                            and t.game_id = %s