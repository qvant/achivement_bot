select g.genre_id
from achievements_hunt.map_games_to_genres g
where g.platform_id = %s
  and g.game_id = %s
order by g.genre_id