alter table achievements_hunt.games add icon_url varchar(1024);
alter table achievements_hunt.games add release_date varchar(255);
alter table achievements_hunt.achievements add icon_url varchar(1024);
alter table achievements_hunt.achievements add locked_icon_url varchar(1024);
update achievements_hunt.version set n_version=3, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;