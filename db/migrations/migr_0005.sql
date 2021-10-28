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

create table  achievements_hunt.player_game_stats
(
	id 			        serial primary key,
	platform_id         integer not null,
	game_id		        integer not null,
	stat_id		        integer not null,
	player_id		    integer not null,
	stat_value          varchar(1024),
	dt_update	        timestamp with time zone default current_timestamp not null
);
create unique index u_player_game_stats_key on achievements_hunt.player_game_stats(player_id, platform_id, game_id, stat_id);
alter table  achievements_hunt.player_game_stats ADD CONSTRAINT u_player_game_stats_key unique using index u_player_game_stats_key;
alter table  achievements_hunt.player_game_stats ADD CONSTRAINT fk_player_game_stats_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table  achievements_hunt.player_game_stats ADD CONSTRAINT fk_player_game_stats_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table  achievements_hunt.player_game_stats ADD CONSTRAINT fk_player_game_stats_to_players foreign key (player_id) references  achievements_hunt.players(id) on delete cascade;
alter table  achievements_hunt.player_game_stats ADD CONSTRAINT fk_player_game_stats_to_game_stats foreign key (stat_id) references  achievements_hunt.game_stats(id);

alter table  achievements_hunt.player_game_stats owner to achievements_hunt_bot;

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

update achievements_hunt.version set n_version=5, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;