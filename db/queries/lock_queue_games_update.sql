select id, game_id, operation
                from achievements_hunt.queue_games_update
                order by game_id
                for update skip locked
                fetch first %s rows only