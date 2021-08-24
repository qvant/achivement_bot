create table  achievements_hunt.games
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null,
	ext_id		        varchar(1024) not null,
	dt_create	        timestamp with time zone default current_timestamp not null,
	dt_update	        timestamp with time zone,
	num_owners          integer default 0 not null,
	has_achievements    boolean default true not null,
	console_id          integer,
	icon_url            varchar(1024),
	release_date        varchar(255)
);
create unique index u_games_ext_key on achievements_hunt.games(platform_id, ext_id);
alter table  achievements_hunt.games ADD CONSTRAINT u_games_ext_key unique using index u_games_ext_key;
alter table  achievements_hunt.games ADD CONSTRAINT fk_games_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table  achievements_hunt.games ADD CONSTRAINT fk_games_to_consoles foreign key (console_id) references  achievements_hunt.consoles(id);
alter table  achievements_hunt.games owner to achievements_hunt_bot;