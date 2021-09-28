alter table achievements_hunt.achievements add is_hidden       boolean default false not null;
update achievements_hunt.version set n_version=4, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;