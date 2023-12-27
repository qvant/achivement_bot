CREATE OR REPLACE FUNCTION achievements_hunt.f_on_achievements_upd()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_achievements_update(achievement_id, game_id, platform_id, operation) values (old.id, old.game_id, old.platform_id, TG_OP);
	    return old;
	END;
$function$
;