update achievements_hunt.player_games pg
                                                            set is_perfect = (percent_complete = 100)
                                                            where pg.game_id = $1 and pg.platform_id = $2