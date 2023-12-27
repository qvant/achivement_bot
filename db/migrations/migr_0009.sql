alter table achievements_hunt.achievements add is_removed boolean not null default false;
comment on column achievements_hunt.achievements.is_removed is 'Achievement removed by developer';
alter table achievements_hunt.achievements add is_broken boolean not null default false;
comment on column achievements_hunt.achievements.is_broken is 'Achievement can''t be obtained in legit way any more';

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

create trigger trg_on_achievements_au after
update of is_removed
    on
    achievements_hunt.achievements for each row execute procedure achievements_hunt.f_on_achievements_upd();

update achievements_hunt.version set n_version=9, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;