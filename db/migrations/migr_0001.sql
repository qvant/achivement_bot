insert into achievements_hunt.platforms(id, name) values(2, 'Retroachievements');
insert into achievements_hunt.platform_languages(platform_id, name, locale_name) values(2, 'English', 'en');

create table  achievements_hunt.consoles
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null,
	ext_id		        varchar(1024) not null
);
create unique index u_consoles_ext_key on achievements_hunt.consoles(platform_id, ext_id);
alter table  achievements_hunt.consoles ADD CONSTRAINT u_consoles_ext_key unique using index u_consoles_ext_key;
alter table  achievements_hunt.consoles owner to achievements_hunt_bot;

alter table  achievements_hunt.games ADD console_id integer;
alter table  achievements_hunt.games ADD CONSTRAINT fk_games_to_consoles foreign key (console_id) references  achievements_hunt.consoles(id);

update achievements_hunt.version set n_version=2, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;