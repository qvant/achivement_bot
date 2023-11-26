select id, achievement_id, player_id, game_id, platform_id, operation
                        from achievements_hunt.queue_player_achievements_update
                        order by achievement_id
                        for update skip locked
                        fetch first %s rows only