select
                coalesce(tr.name, a.name),
                a.percent_owners,
                g.name || case when c.name is not null then ' (' || c.name || ')' else '' end,
                ar.name
            from achievements_hunt.player_achievements aa
            join achievements_hunt.achievements a
            on aa.achievement_id  = a.id
              and aa.game_id  = a.game_id
              and aa.platform_id = a.platform_id
            left join achievements_hunt.achievement_translations tr
            on tr.achievement_id  = a.id
              and tr.game_id = aa.game_id
              and tr.platform_id = aa.platform_id
              and tr.locale = %s
            join achievements_hunt.games g
            on aa.game_id = g.id
              and aa.platform_id = g.platform_id
            left join achievements_hunt.consoles c
            on c.id = g.console_id
              and c.platform_id = g.platform_id
            left join achievements_hunt.achievement_rarity ar
            on ar.n_bottom_border < a.percent_owners
              and ar.n_upper_border >= a.percent_owners
            where aa.player_id = %s
              and (c.id = %s or %s is null)
            order by a.percent_owners, coalesce(tr.name, a.name) limit 10
