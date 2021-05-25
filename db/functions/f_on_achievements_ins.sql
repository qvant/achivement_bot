CREATE OR REPLACE FUNCTION achievements_hunt.f_on_achievements_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_achievements_update(achievement_id, game_id, platform_id, operation) values (new.id, new.game_id, new.platform_id, TG_OP);
	    return new;
	END;
$function$
;