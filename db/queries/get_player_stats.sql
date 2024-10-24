select
    round(avg(case when g.has_achievements and pg.percent_complete > 0
    then pg.percent_complete else null end)::numeric, 2),
    count(case when pg.is_perfect then 1 end),
    count(1),
    count(case when g.has_achievements then 1 end)
from achievements_hunt.player_games pg
join achievements_hunt.games g
    on pg.game_id = g.id
    and pg.platform_id = g.platform_id
where pg.player_id = %s