update achievements_hunt.players set telegram_id = %s where ext_id = %s and platform_id = %s
                    and telegram_id is null
                returning id