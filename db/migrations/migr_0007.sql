
alter table achievements_hunt.achievements alter column name type varchar(4096);

update achievements_hunt.version set n_version=7, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;