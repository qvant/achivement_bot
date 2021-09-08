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

update achievements_hunt.version set n_version=4, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;