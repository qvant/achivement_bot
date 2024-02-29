update achievements_hunt.player_games pg set percent_complete =
                                                round(
                                                (select count(1) from achievements_hunt.player_achievements a
                                                 where a.platform_id = pg.platform_id
                                                 and a.game_id = pg.game_id
                                                 and a.player_id = pg.player_id
                                                 and not exists (
                                                                 select null from achievements_hunt.achievements acc
                                                                 where acc.platform_id = a.platform_id
                                                                   and acc.game_id = a.game_id
                                                                    and acc.id = a.achievement_id
                                                                    and not acc.is_removed
                                                                )
                                                 ) * 100 /
                                                greatest(1, (select count(1) from achievements_hunt.achievements ac
                                                where ac.platform_id = pg.platform_id
                                                and ac.game_id = pg.game_id
                                                and not ac.is_removed
                                                )), 2)
                                                 where pg.player_id = $1 and pg.game_id = $2
                                                 and pg.platform_id = $3