insert into achievements_hunt.achievements as l (name, ext_id, platform_id, game_id, description,
                            icon_url, locked_icon_url, is_hidden)
                            values(%s, %s, %s, %s, %s, %s, %s, %s)
                            on conflict ON CONSTRAINT u_achievements_ext_key do nothing
                            returning id, name, description