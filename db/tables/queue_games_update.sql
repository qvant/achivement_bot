create table  achievements_hunt.queue_games_update
(
	id          serial primary key,
	game_id 	integer not null,
	platform_id integer not null,
	dt_insert	timestamp with time zone default current_timestamp not null,
	player_id   integer not null,
	operation   text
);
alter table  achievements_hunt.queue_games_update owner to achievements_hunt_bot;