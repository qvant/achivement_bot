select g.id,
       g.platform_id,
       g.name,
       g.ext_id,
       g.console_id,
       g.icon_url,
       g.release_date,
       g.developer_id,
       d.name,
       g.publisher_id,
       p.name,
       ARRAY_AGG(distinct gr.id),
       ARRAY_AGG(distinct gr.name),
       ARRAY_AGG(distinct fr.id),
       ARRAY_AGG(distinct fr.name)
from achievements_hunt.games g
left join achievements_hunt.companies p
  on p.id = g.publisher_id
  and p.platform_id = g.platform_id
left join achievements_hunt.companies d
  on d.id = g.developer_id
  and d.platform_id = g.platform_id
left join achievements_hunt.map_games_to_genres m
  on m.platform_id = g.platform_id
  and m.game_id = g.id
left join achievements_hunt.genres gr
  on m.genre_id = gr.id
  and m.platform_id = gr.platform_id =
left join achievements_hunt.map_games_to_features mf
  on mf.platform_id = g.platform_id
  and mf.game_id = g.id
left join achievements_hunt.features fr
  on mf.feature_id = fr.id
  and mf.platform_id = = fr.platform_id
where g.platform_id = %s
  and g.id = %s
group by g.id, g.platform_id, g.name, g.ext_id, g.console_id, g.icon_url,
         g.release_date,
         g.developer_id, d.name, g.publisher_id, p.name
order by g.id