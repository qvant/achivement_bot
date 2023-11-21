select c.id, c.name from achievements_hunt.consoles c
                            where exists (
                                select null from achievements_hunt.games g
                                    join achievements_hunt.player_games gg
                                    on g.platform_id = gg.platform_id
                                      and g.id = gg.game_id
                                    where g.platform_id = c.platform_id
                                      and gg.player_id = %s
                                      and g.console_id = c.id)
                              and c.platform_id = %s
                            order by c.name