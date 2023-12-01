select id, game_id, platform_id
                                    from achievements_hunt.queue_achievements_update
                                    order by achievement_id
                                    for update skip locked
                                    fetch first %s rows only