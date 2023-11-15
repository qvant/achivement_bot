select count(1),
       p.name
from achievements_hunt.players pl
join achievements_hunt.platforms p
    on p.id = pl.platform_id
group by p.name