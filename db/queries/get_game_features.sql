select f.feature_id
from achievements_hunt.map_games_to_features f
where f.platform_id = %s
  and f.game_id = %s
order by f.feature_id