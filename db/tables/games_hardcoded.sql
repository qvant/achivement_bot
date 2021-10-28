create table  achievements_hunt.games_hardcoded
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null,
	ext_id		        varchar(1024) not null
);
create unique index u_games_hardcoded_key on achievements_hunt.games_hardcoded(platform_id, ext_id);
alter table achievements_hunt.games_hardcoded ADD CONSTRAINT fk_games_hardcoded_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.games_hardcoded owner to achievements_hunt_bot;

insert into achievements_hunt.games_hardcoded (platform_id, ext_id, name) values (1, '1317860', 'The Riftbreaker')