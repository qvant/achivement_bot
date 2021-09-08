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
