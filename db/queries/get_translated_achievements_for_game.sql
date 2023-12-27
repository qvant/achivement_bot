select a.id, a.ext_id, coalesce(l.name, a.name), coalesce(a.description, l.description),
                              icon_url, locked_icon_url, is_hidden, is_removed
                            from achievements_hunt.achievements a
                            left join achievements_hunt.achievement_translations l
                            on l.achievement_id  = a.id
                                and l.game_id = a.game_id
                                and l.platform_id = a.platform_id
                                and l.locale = %s
                            where a.platform_id = %s and a.game_id = %s