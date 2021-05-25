create table  achievements_hunt.player_games
(
	id 			        serial primary key,
	platform_id         integer not null,
	game_id             integer not null,
	player_id           integer not null,
	percent_complete    real,
	is_perfect          boolean
);
create unique index u_player_games_key on achievements_hunt.player_games(platform_id, game_id, player_id);
create index idx_player_games_player on achievements_hunt.player_games(player_id);
create index idx_player_games_game on achievements_hunt.player_games(game_id);
alter table achievements_hunt.player_games ADD CONSTRAINT fk_player_games_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.player_games ADD CONSTRAINT fk_player_games_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table achievements_hunt.player_games ADD CONSTRAINT fk_player_games_to_players foreign key (player_id) references  achievements_hunt.players(id) on delete cascade;
alter table achievements_hunt.player_games owner to achievements_hunt_bot;