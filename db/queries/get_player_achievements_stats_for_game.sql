select coalesce (tr.name, a.name) as name, pa.id, a.percent_owners, a.id,
             coalesce(tr.description, a.description) as description, pa.dt_unlock,
             case when pa.id is not null then a.icon_url else a.locked_icon_url end,
             ar.name,
             a.is_hidden
             from achievements_hunt.achievements a
             left join achievements_hunt.player_achievements pa
             on pa.achievement_id = a.id and pa.player_id = %s
             left join achievements_hunt.achievement_translations tr
             on tr.achievement_id = a.id and tr.platform_id = a.platform_id
             and tr.locale = %s
             left join achievements_hunt.achievement_rarity ar
             on ar.n_bottom_border < a.percent_owners
               and ar.n_upper_border >= a.percent_owners
             where a.platform_id = %s
             and a.game_id = %s
             order by a.percent_owners desc, a.name