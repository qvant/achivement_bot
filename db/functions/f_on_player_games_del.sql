CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_games_del()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_games_update(game_id, platform_id, player_id, operation) values (old.game_id, old.platform_id, old.player_id, TG_OP);
	    return old;
	END;
$function$
;
