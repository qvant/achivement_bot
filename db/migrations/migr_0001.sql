insert into achievements_hunt.platforms(id, name) values(2, 'Retroachievements');
insert into achievements_hunt.platform_languages(platform_id, name, locale_name) values(2, 'English', 'en');

update achievements_hunt.version set n_version=2, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;