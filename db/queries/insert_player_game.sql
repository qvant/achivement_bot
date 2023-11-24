insert into achievements_hunt.player_games(platform_id, game_id, player_id)
                                values (%s, %s, %s) returning id