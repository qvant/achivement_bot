insert into achievements_hunt.games as l (name, ext_id, platform_id, has_achievements,
                        console_id, icon_url, release_date, developer_id, publisher_id)
                        values(%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict ON CONSTRAINT u_games_ext_key do nothing
                        returning id