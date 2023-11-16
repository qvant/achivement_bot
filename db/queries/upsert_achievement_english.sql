insert into achievements_hunt.achievements as l (name, ext_id, platform_id, game_id, description,
                            icon_url, locked_icon_url, is_hidden)
                            values(%s, %s, %s, %s, %s, %s, %s, %s)
                            on conflict ON CONSTRAINT u_achievements_ext_key do update
                            set dt_update=current_timestamp, name=EXCLUDED.name, description=EXCLUDED.description,
                            icon_url=EXCLUDED.icon_url, locked_icon_url=EXCLUDED.locked_icon_url,
                            is_hidden = EXCLUDED.is_hidden
                            where l.name != EXCLUDED.name or l.description != EXCLUDED.description
                            or coalesce(l.icon_url, '') != coalesce(EXCLUDED.icon_url, l.icon_url, '')
                            or coalesce(l.locked_icon_url, '')
                                    != coalesce(EXCLUDED.locked_icon_url, l.locked_icon_url, '')
                            or l.is_hidden != EXCLUDED.is_hidden
                            returning id, name, description