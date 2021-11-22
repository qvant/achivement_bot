create table  achievements_hunt.game_stats
(
	id 			        serial primary key,
	platform_id         integer not null,
	game_id		        integer not null,
	ext_id		        varchar(1024) not null,
	name		        varchar(1024) not null,
	dt_create	        timestamp with time zone default current_timestamp not null,
	dt_update	        timestamp with time zone
);
create unique index u_game_stats_ext_key on achievements_hunt.game_stats(platform_id, game_id, ext_id);
alter table  achievements_hunt.game_stats ADD CONSTRAINT u_game_stats_ext_key unique using index u_game_stats_ext_key;
alter table  achievements_hunt.game_stats ADD CONSTRAINT fk_game_stats_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table  achievements_hunt.game_stats ADD CONSTRAINT fk_game_stats_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);

alter table  achievements_hunt.game_stats owner to achievements_hunt_bot;