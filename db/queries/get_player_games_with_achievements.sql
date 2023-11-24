select g.game_id, g.is_perfect from achievements_hunt.player_games g
                                join achievements_hunt.games gg on gg.id = g.game_id
                                 where g.platform_id = %s and g.player_id = %s
                                   and gg.has_achievements
                                   and (gg.console_id = %s or %s is null)
                                 order by gg.name