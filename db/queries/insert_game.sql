insert into achievements_hunt.games as l (name, ext_id, platform_id, has_achievements,
                        console_id, icon_url, release_date, developer_id, publisher_id)
                        values(%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict ON CONSTRAINT u_games_ext_key do update
                        set dt_update=current_timestamp, name=%s, has_achievements=%s, console_id=%s,
                        icon_url=%s, release_date=%s, developer_id=%s, publisher_id=%s
                        where l.name != EXCLUDED.name or l.has_achievements != EXCLUDED.has_achievements
                        or coalesce(l.console_id, -1) != coalesce(EXCLUDED.console_id, -1)
                        or coalesce(l.release_date, '') != coalesce(EXCLUDED.release_date, l.release_date, '')
                        or coalesce(l.icon_url, '') != coalesce(EXCLUDED.icon_url, l.icon_url, '')
                        or coalesce(l.developer_id, -1) != coalesce(EXCLUDED.developer_id, l.developer_id, -1)
                        or coalesce(l.publisher_id, -1) != coalesce(EXCLUDED.publisher_id, l.publisher_id, -1)
                        returning id