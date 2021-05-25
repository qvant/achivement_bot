CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_achievements_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_player_achievements_update(achievement_id, game_id, platform_id, player_id, operation) values (new.achievement_id, new.game_id, new.platform_id, new.player_id, TG_OP);
	    return new;
	END;
$function$
;
