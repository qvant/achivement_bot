insert into achievements_hunt.consoles(platform_id, name, ext_id)
                values (%s, %s, %s)
                on conflict ON CONSTRAINT u_consoles_ext_key
                do nothing returning id