update achievements_hunt.achievements as a
                                        set percent_owners =
                                        case when num_owners > 0 then
                                            round(a.num_owners * 100 /
                                            greatest(1, (select g.num_owners
                                                            from achievements_hunt.games as g
                                                            where g.id = a.game_id
                                                                and g.platform_id = a.platform_id)), 2)
                                        else 0
                                        end
                                    where a.game_id = $1