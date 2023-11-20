select s.id, s.ext_id, s.name from achievements_hunt.game_stats s
                where s.platform_id = %s and s.game_id = %s