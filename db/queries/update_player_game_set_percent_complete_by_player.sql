update achievements_hunt.player_games pg set percent_complete =
                                                round(
                                                (select count(1) from achievements_hunt.player_achievements a
                                                 where a.platform_id = pg.platform_id
                                                 and a.game_id = pg.game_id
                                                 and a.player_id = pg.player_id) * 100 /
                                                (select count(1) from achievements_hunt.achievements ac
                                                where ac.platform_id = pg.platform_id
                                                and ac.game_id = pg.game_id), 2)
                                                 where pg.player_id = $1 and pg.game_id = $2
                                                 and pg.platform_id = $3