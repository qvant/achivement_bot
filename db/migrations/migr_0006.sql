CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_games_upd()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
	    new.is_perfect := new.percent_complete = 100;
	    if new.is_perfect then
		    select max(aa.dt_unlock) into new.dt_last_perfected
		        from achievements_hunt.player_achievements aa
                where aa.platform_id = new.platform_id
                    and aa.player_id = new.player_id
                    and aa.game_id = new.game_id;
        end if;
	    return new;
	END;
$function$
;


create trigger trg_on_player_games_zbu before
  update on achievements_hunt.player_games
  for each row execute procedure suppress_redundant_updates_trigger();

update achievements_hunt.version set n_version=6, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;