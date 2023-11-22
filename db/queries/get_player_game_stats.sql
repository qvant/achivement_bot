select gs.name,
                   s.stat_value
            from achievements_hunt.player_game_stats s
            join achievements_hunt.game_stats gs
            on gs.id = s.stat_id
            where s.player_id = %s
                and s.platform_id = %s
                and s.game_id = %s
            order by gs.name