insert into achievements_hunt.achievement_translations as l
                            (platform_id, game_id, achievement_id, locale, name, description )
                            values(%s, %s, %s, %s, %s, %s)
                            on conflict ON CONSTRAINT u_achievement_translations_key do update
                            set dt_update=current_timestamp, name=EXCLUDED.name, description=EXCLUDED.description
                            where l.name != EXCLUDED.name
                            returning id