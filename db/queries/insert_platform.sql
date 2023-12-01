insert into achievements_hunt.platforms as l (name, id )
                        values(%s, %s)
                        on conflict (id) do nothing
                        returning id