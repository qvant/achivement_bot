CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_achievements_del()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_player_achievements_update(achievement_id, game_id, platform_id, player_id, operation) values (old.achievement_id, old.game_id, old.platform_id, old.player_id, TG_OP);
	    return old;
	END;
$function$
;
