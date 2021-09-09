alter table achievements_hunt.player_games add dt_last_perfected   timestamp with time zone;
update achievements_hunt.player_games gg
set dt_last_perfected = (select max(aa.dt_unlock) from achievements_hunt.player_achievements aa where aa.platform_id = gg.platform_id
and aa.game_id = gg.game_id) where is_perfect;

CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_games_upd()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
	    if new.is_perfect then
		    select max(aa.dt_unlock) into new.dt_last_perfected
		        from achievements_hunt.player_achievements aa
                where aa.platform_id = new.platform_id
                    and aa.game_id = new.game_id;
        end if;
	    return new;
	END;
$function$
;

create trigger trg_player_games_bu before
update
    on
    achievements_hunt.player_games for each row execute procedure achievements_hunt.f_on_player_games_upd();

create table  achievements_hunt.achievement_rarity
(
	id 			    serial primary key,
	name            varchar(1024) not null,
	color_code      varchar(255) not null,
	n_bottom_border real,
	n_upper_border  real
);
alter table achievements_hunt.achievement_rarity owner to achievements_hunt_bot;

create unique index u_achievement_rarity_name_key on achievements_hunt.achievement_rarity(name);

insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Common', 'White', 50, 100);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Uncommon', '#0BDA51', 20, 50);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Rare', '#63b5cf', 10, 20);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Epic', '#800080', 5, 10);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Legendary', '##FFA500', -1, 5);


update achievements_hunt.version set n_version=4, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;